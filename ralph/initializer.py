#!/usr/bin/env python3
"""
Backlog initializer for Ralph Loop.

Handles initialization of backlog.json from user prompts.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from ralph.providers import get_provider, list_available_providers

# ANSI color codes for output
DIM = "\033[2m"
RESET = "\033[0m"


class BacklogInitializer:
    """Handles backlog initialization from user prompts."""

    def __init__(
        self,
        project_dir: Path,
        backlog_path: Path,
        provider: str = "qwen",
        dry_run: bool = False
    ):
        """
        Initialize BacklogInitializer.

        Args:
            project_dir: Target project directory
            backlog_path: Path to backlog.json
            provider: Agent provider name (qwen, claude, codex)
            dry_run: If True, preview without making changes
        """
        self.project_dir = project_dir
        self.backlog_path = backlog_path
        self.provider_name = provider
        self.dry_run = dry_run
        self.debug_dir = project_dir / "logs" / "ralph" / "init"

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

    def initialize(self, user_prompt: str) -> int:
        """
        Initialize backlog from user prompt.

        Args:
            user_prompt: User's project description

        Returns:
            Exit code: 0 on success, 1 on error
        """
        print(f"Initializing backlog for: {user_prompt}")
        print(f"Provider: {self.provider_name}")
        print(f"Target: {self.backlog_path}")
        print()

        # Check for existing backlog
        if self.backlog_path.exists() and not self.dry_run:
            try:
                response = input(f"Backlog already exists at {self.backlog_path}. Overwrite? [y/N]: ")
                if response.lower() not in ['y', 'yes']:
                    print("Aborted.")
                    return 1
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                return 1

        # Ensure debug directory exists
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Build roadmap prompt with temp output file
            from ralph.prompts import build_roadmap_prompt

            # Create temp file for agent to write to
            temp_output = self.debug_dir / f"roadmap-{self._timestamp()}.json"
            prompt = build_roadmap_prompt(user_prompt, str(temp_output))

            # Save prompt for debugging
            prompt_file = self.debug_dir / f"prompt-{self._timestamp()}.txt"
            prompt_file.write_text(prompt, encoding='utf-8')
            print(f"Generated roadmap prompt (saved to {prompt_file})")

            # Step 2: Invoke provider
            print(f"\nInvoking {self.provider_name} to generate roadmap...")
            response = self._invoke_provider(prompt, temp_output)

            # Save response for debugging
            response_file = self.debug_dir / f"response-{self._timestamp()}.txt"
            response_file.write_text(response, encoding='utf-8')
            print(f"Received response (saved to {response_file})")

            # Step 3: Read the generated file
            print("\nReading generated roadmap file...")
            if not temp_output.exists():
                # Fallback: try parsing the response directly
                print("Warning: Agent did not write to file, attempting to parse response...")
                from ralph.parsers import parse_roadmap_response
                parsed_data = parse_roadmap_response(response, self.debug_dir)
            else:
                # Read the file the agent created
                import json
                with open(temp_output, 'r', encoding='utf-8') as f:
                    parsed_data = json.load(f)
                print(f"Successfully read roadmap from {temp_output}")

            print(f"Parsed {len(parsed_data.get('items', []))} milestones")

            # Step 4: Transform to backlog
            print("\nTransforming to backlog format...")
            from ralph.transformers import transform_to_backlog
            backlog = transform_to_backlog(parsed_data)

            # Step 5: Validate
            print("\nValidating backlog...")
            if not self._validate_backlog(backlog):
                print("Error: Generated backlog failed validation", file=sys.stderr)
                return 1
            print("✓ Validation passed")

            # Step 6: Save
            if self.dry_run:
                print("\n[DRY RUN] Would save backlog:")
                print(json.dumps(backlog, indent=2))
            else:
                print("\nSaving backlog...")
                self._save_backlog(backlog)
                print(f"✓ Backlog saved to {self.backlog_path}")

            # Step 7: Summary
            self._print_summary(backlog)

            return 0

        except KeyboardInterrupt:
            print("\n\nInterrupted by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"\nError during initialization: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    def _invoke_provider(self, prompt: str, temp_output: Path) -> str:
        """
        Invoke provider and return response.

        Args:
            prompt: Prompt to send to provider
            temp_output: Path where agent should write the roadmap

        Returns:
            Provider response text

        Raises:
            RuntimeError: If provider invocation fails
        """
        cmd = self.provider.build_command(prompt, self.project_dir, yolo=True)

        if self.dry_run:
            print(f"[DRY RUN] Would run: {' '.join(cmd)}")
            # Create mock file for dry-run
            mock_data = {
                "version": "1.0.0",
                "items": [
                    {
                        "title": "Example Milestone",
                        "why": "This is a dry-run example",
                        "priority": "P1",
                        "dependsOn": [],
                        "deliverables": ["Example deliverable"],
                        "exitCriteria": ["Example criterion"],
                        "risks": []
                    }
                ]
            }
            temp_output.write_text(json.dumps(mock_data, indent=2), encoding='utf-8')
            return json.dumps(mock_data)

        # Get progress renderer if available
        renderer_cmd = self.provider.get_progress_renderer(self.project_dir)

        try:
            # Always capture output to a file for later parsing
            raw_output_file = self.debug_dir / f"raw-output-{self._timestamp()}.txt"

            if renderer_cmd:
                # Run with renderer for real-time visualization
                print(f"{DIM}[info] raw log: {raw_output_file}{RESET}\n")

                with open(raw_output_file, 'w', encoding='utf-8') as raw_f:
                    agent_proc = subprocess.Popen(
                        cmd,
                        cwd=self.project_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )

                    renderer_proc = subprocess.Popen(
                        renderer_cmd,
                        stdin=subprocess.PIPE,
                        stdout=sys.stdout,
                        stderr=sys.stderr,
                        cwd=self.project_dir,
                        text=True
                    )

                    # Tee the output: send to both renderer and file
                    if agent_proc.stdout:
                        for line in agent_proc.stdout:
                            raw_f.write(line)
                            raw_f.flush()
                            if renderer_proc.stdin:
                                try:
                                    renderer_proc.stdin.write(line)
                                    renderer_proc.stdin.flush()
                                except BrokenPipeError:
                                    break

                    # Close renderer stdin
                    if renderer_proc.stdin:
                        renderer_proc.stdin.close()

                    # Wait for both processes
                    renderer_proc.wait()
                    agent_proc.wait()

                    if agent_proc.returncode != 0:
                        stderr = agent_proc.stderr.read() if agent_proc.stderr else ""
                        if stderr:
                            raise RuntimeError(f"Provider failed: {stderr}")
                        raise RuntimeError(f"Provider failed with exit code {agent_proc.returncode}")

                # Read the saved output
                return raw_output_file.read_text(encoding='utf-8')

            else:
                # No renderer, run directly and save output
                result = subprocess.run(
                    cmd,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                if result.returncode != 0:
                    error_msg = result.stderr if result.stderr else "Unknown error"
                    raise RuntimeError(f"Provider failed with exit code {result.returncode}: {error_msg}")

                # Save output to file
                raw_output_file.write_text(result.stdout, encoding='utf-8')
                return result.stdout

        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "Provider timed out after 5 minutes. Try a simpler prompt or different provider."
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"Provider command not found: {cmd[0]}. Ensure {self.provider_name} is installed."
            )

    def _validate_backlog(self, backlog: Dict[str, Any]) -> bool:
        """
        Validate backlog structure.

        Args:
            backlog: Backlog dict to validate

        Returns:
            True if valid, False otherwise
        """
        # Write to temp file for validation
        temp_path = self.backlog_path.with_suffix('.json.validate')
        try:
            # Ensure parent directory exists
            temp_path.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(backlog, f, indent=2)

            from ralph.validator import validate_backlog
            # Suppress validation output (it prints to stdout)
            import io
            import contextlib

            with contextlib.redirect_stdout(io.StringIO()):
                result = validate_backlog(temp_path)

            return result
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _save_backlog(self, backlog: Dict[str, Any]) -> None:
        """
        Save backlog atomically.

        Args:
            backlog: Backlog dict to save

        Raises:
            Exception: If save fails
        """
        # Ensure docs directory exists
        self.backlog_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write pattern from orchestrator
        temp_path = self.backlog_path.with_suffix('.json.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(backlog, f, indent=2, ensure_ascii=False)
                f.write('\n')
            temp_path.replace(self.backlog_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _print_summary(self, backlog: Dict[str, Any]) -> None:
        """
        Print summary of generated backlog.

        Args:
            backlog: Generated backlog dict
        """
        items = backlog.get('items', [])

        print(f"\n{'='*80}")
        print("Backlog Summary")
        print(f"{'='*80}")
        print(f"Total items: {len(items)}")

        # Count by priority
        priorities = {}
        for item in items:
            p = item['priority']
            priorities[p] = priorities.get(p, 0) + 1

        print(f"Priorities: {', '.join(f'{p}: {count}' for p, count in sorted(priorities.items()))}")

        # List items
        print(f"\nMilestones:")
        for item in items:
            deps = f" (depends on: {', '.join(item['dependsOn'])})" if item.get('dependsOn') else ""
            print(f"  [{item['priority']}] {item['title']}{deps}")

        print(f"\nNext steps:")
        print(f"  1. Review the generated backlog: {self.backlog_path}")
        print(f"  2. Make any necessary adjustments")
        print(f"  3. Run: ralph --project {self.project_dir}")

    def _timestamp(self) -> str:
        """
        Generate timestamp string.

        Returns:
            Timestamp in format YYYYMMDD-HHMMSS
        """
        return datetime.now().strftime("%Y%m%d-%H%M%S")
