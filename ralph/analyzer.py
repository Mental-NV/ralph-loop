#!/usr/bin/env python3
"""
Backlog analyzer for Ralph Loop.

Handles analysis of backlog.json for automation readiness.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from ralph.paths import RalphPaths
from ralph.providers import get_provider, list_available_providers


class BacklogAnalyzer:
    """Analyzes backlog for automation readiness."""

    def __init__(
        self,
        project_dir: Path,
        backlog_path: Path,
        provider: str = "qwen",
        dry_run: bool = False,
        save_analysis: bool = False,
        threshold: int = 75
    ):
        """
        Initialize BacklogAnalyzer.

        Args:
            project_dir: Target project directory
            backlog_path: Path to backlog.json
            provider: Agent provider name (qwen, claude, codex)
            dry_run: If True, preview without making changes
            save_analysis: If True, save analysis to .ralph/backlog-analysis.json
            threshold: Target quality score for automation readiness (1-100)
        """
        self.project_dir = project_dir
        self.backlog_path = backlog_path
        self.provider_name = provider
        self.dry_run = dry_run
        self.save_analysis = save_analysis
        self.threshold = threshold

        # Initialize paths
        self.paths = RalphPaths(project_dir)
        self.debug_dir = self.paths.analyze_logs

        # Initialize provider
        try:
            self.provider = get_provider(provider)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            available = list_available_providers()
            if available:
                print(f"Available providers: {', '.join(available)}", file=sys.stderr)
            else:
                print("No providers are available on this system", file=sys.stderr)
            sys.exit(1)

        if not self.provider.is_available():
            print(f"Error: Provider '{provider}' is not available", file=sys.stderr)
            available = list_available_providers()
            if available:
                print(f"Available providers: {', '.join(available)}", file=sys.stderr)
            else:
                print("No providers are available on this system", file=sys.stderr)
            sys.exit(1)

    def analyze(self) -> int:
        """
        Analyze backlog for automation readiness.

        Returns:
            Exit code: 0 on success, 1 on error
        """
        print(f"Analyzing backlog: {self.backlog_path}", file=sys.stderr)
        print(f"Provider: {self.provider_name}", file=sys.stderr)
        print(f"Project directory: {self.project_dir}", file=sys.stderr)
        print(file=sys.stderr)

        # Ensure debug directory exists
        self.paths.ensure_dirs(self.debug_dir)

        try:
            # Step 1: Load and validate backlog
            backlog = self._load_backlog()

            # Step 2: Build analysis prompt
            from ralph.prompts import build_analysis_prompt

            # Create temp file for agent output
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            temp_output = self.debug_dir / f"analysis-{timestamp}.json"

            backlog_json = json.dumps(backlog, indent=2)
            prompt = build_analysis_prompt(
                backlog_json=backlog_json,
                project_dir=str(self.project_dir),
                output_file=str(temp_output),
                threshold=self.threshold
            )

            if self.dry_run:
                print("[DRY RUN] Would analyze with prompt:", file=sys.stderr)
                print(prompt[:500] + "..." if len(prompt) > 500 else prompt, file=sys.stderr)
                print(f"\n[DRY RUN] Provider: {self.provider_name}", file=sys.stderr)
                return 0

            # Step 3: Invoke provider
            print("Invoking agent for analysis...", file=sys.stderr)
            response = self._invoke_provider(prompt, temp_output)

            # Step 4: Parse response
            from ralph.parsers import parse_analysis_response
            analysis = parse_analysis_response(response, self.debug_dir)

            # Step 5: Validate schema
            if not self._validate_analysis_schema(analysis):
                print("Error: Analysis response has invalid schema", file=sys.stderr)
                return 1

            # Step 6: Output to stdout
            print(json.dumps(analysis, indent=2))

            # Step 7: Optionally save to file
            if self.save_analysis:
                analysis_path = self.paths.analysis_file
                self._save_analysis(analysis, analysis_path)
                print(f"\nAnalysis saved to: {analysis_path}", file=sys.stderr)

            return 0

        except KeyboardInterrupt:
            print("\n\nAnalysis interrupted by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"\nAnalysis failed: {e}", file=sys.stderr)
            return 1

    def _load_backlog(self) -> Dict[str, Any]:
        """Load and validate backlog.json."""
        try:
            with open(self.backlog_path, 'r', encoding='utf-8') as f:
                backlog = json.load(f)
        except FileNotFoundError:
            print(f"Error: Backlog not found: {self.backlog_path}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in backlog: {e}", file=sys.stderr)
            sys.exit(1)

        # Basic validation
        from ralph.validator import validate_backlog
        if not validate_backlog(self.backlog_path):
            print("Error: Backlog validation failed", file=sys.stderr)
            sys.exit(1)

        return backlog

    def _invoke_provider(self, prompt: str, temp_output: Path) -> str:
        """
        Invoke provider with analysis prompt.

        Args:
            prompt: Analysis meta-prompt
            temp_output: Temp file path for agent output

        Returns:
            Raw agent response
        """
        # Build command (YOLO mode always enabled for analysis)
        cmd = self.provider.build_command(prompt, self.project_dir, yolo=True)

        # Get progress renderer if available
        renderer_cmd = self.provider.get_progress_renderer(self.project_dir)

        try:
            if renderer_cmd:
                # Pipe through renderer
                agent_proc = subprocess.Popen(
                    cmd,
                    cwd=self.project_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                renderer_proc = subprocess.Popen(
                    renderer_cmd,
                    stdin=agent_proc.stdout,
                    cwd=self.project_dir
                )

                # Close agent stdout in parent
                if agent_proc.stdout:
                    agent_proc.stdout.close()

                # Wait for renderer
                renderer_proc.wait()

                # Check agent exit code
                agent_proc.wait()
                if agent_proc.returncode != 0:
                    stderr = agent_proc.stderr.read() if agent_proc.stderr else ""
                    if stderr:
                        print(f"\nAgent error output:\n{stderr}", file=sys.stderr)
                    raise RuntimeError(f"Agent failed with exit code {agent_proc.returncode}")

                # Read output from temp file
                if temp_output.exists():
                    return temp_output.read_text()
                else:
                    raise RuntimeError("Agent did not create output file")

            else:
                # No renderer, run directly
                result = subprocess.run(
                    cmd,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    if result.stderr:
                        print(f"\nAgent error output:\n{result.stderr}", file=sys.stderr)
                    raise RuntimeError(f"Agent failed with exit code {result.returncode}")

                # Read output from temp file
                if temp_output.exists():
                    return temp_output.read_text()
                else:
                    # Fallback: try to parse from stdout
                    return result.stdout

        except Exception as e:
            raise RuntimeError(f"Provider invocation failed: {e}")

    def _validate_analysis_schema(self, analysis: Dict[str, Any]) -> bool:
        """
        Validate analysis response has expected structure.

        Args:
            analysis: Parsed analysis dict

        Returns:
            True if valid, False otherwise
        """
        required_fields = ['version', 'metrics', 'overall_score', 'ready_for_auto']

        for field in required_fields:
            if field not in analysis:
                print(f"Missing required field: {field}", file=sys.stderr)
                return False

        # Validate metrics structure
        if not isinstance(analysis['metrics'], dict):
            print("Invalid metrics structure", file=sys.stderr)
            return False

        required_metrics = [
            'clarity', 'completeness', 'automation_readiness',
            'dependency_structure', 'risk_awareness', 'granularity',
            'priority_alignment', 'environment_compatibility',
            'agent_capability_alignment'
        ]

        for metric in required_metrics:
            if metric not in analysis['metrics']:
                print(f"Missing required metric: {metric}", file=sys.stderr)
                return False

            metric_data = analysis['metrics'][metric]
            if not isinstance(metric_data, dict):
                print(f"Invalid metric structure: {metric}", file=sys.stderr)
                return False

            if 'score' not in metric_data or 'weight' not in metric_data:
                print(f"Metric missing score or weight: {metric}", file=sys.stderr)
                return False

        return True

    def _save_analysis(self, analysis: Dict[str, Any], output_path: Path) -> None:
        """
        Save analysis to file atomically.

        Args:
            analysis: Analysis dict
            output_path: Target file path
        """
        # Write to temp file first
        temp_path = self.paths.get_temp_file(output_path, '.tmp')
        self.paths.ensure_dirs(self.paths.tmp_dir)
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False)
                f.write('\n')
            # Atomic rename
            temp_path.replace(output_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to save analysis: {e}")
