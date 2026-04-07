#!/usr/bin/env python3
"""
Architecture refiner for Ralph Loop.

Handles refinement of docs/ARCHITECTURE.md using AI agent suggestions.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ralph.paths import RalphPaths
from ralph.providers import get_provider, list_available_providers


class ArchitectureRefiner:
    """Refines architecture document using AI agent with user-provided prompts."""

    def __init__(
        self,
        project_dir: Path,
        provider: str = "qwen",
        dry_run: bool = False
    ):
        """
        Initialize ArchitectureRefiner.

        Args:
            project_dir: Target project directory
            provider: Agent provider name (qwen, claude, codex)
            dry_run: If True, preview without making changes
        """
        self.project_dir = project_dir
        self.architecture_path = project_dir / "docs" / "ARCHITECTURE.md"
        self.provider_name = provider
        self.dry_run = dry_run

        # Initialize paths
        self.paths = RalphPaths(project_dir)
        self.debug_dir = self.paths.logs_dir / "refine-architecture"

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

    def refine(self, user_prompt: str) -> int:
        """
        Refine architecture document using AI agent with user prompt.

        Args:
            user_prompt: Refinement instructions for the agent

        Returns:
            Exit code: 0 on success, 1 on error
        """
        print(f"Refining architecture: {self.architecture_path}", file=sys.stderr)
        print(f"Provider: {self.provider_name}", file=sys.stderr)
        print(f"Project directory: {self.project_dir}", file=sys.stderr)
        print(file=sys.stderr)

        # Ensure debug directory exists
        self.paths.ensure_dirs(self.debug_dir)

        try:
            # Step 1: Build refinement prompt
            from ralph.prompts import build_architecture_refinement_prompt

            # Create temp file for agent output
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            temp_output = self.debug_dir / f"architecture-{timestamp}.md"

            prompt = build_architecture_refinement_prompt(
                architecture_path=str(self.architecture_path),
                user_prompt=user_prompt,
                output_file=str(temp_output)
            )

            if self.dry_run:
                print("[DRY RUN] Would refine with prompt:", file=sys.stderr)
                print(prompt[:500] + "..." if len(prompt) > 500 else prompt, file=sys.stderr)
                print(f"\n[DRY RUN] Provider: {self.provider_name}", file=sys.stderr)
                return 0

            # Step 2: Invoke provider
            print("Invoking agent for architecture refinement...", file=sys.stderr)
            self._invoke_provider(prompt, temp_output)

            # Step 3: Verify output exists
            if not temp_output.exists():
                print("Error: Agent did not create output file", file=sys.stderr)
                return 1

            # Step 4: Create backup if architecture exists
            if self.architecture_path.exists():
                backup_path = self._create_backup()
                print(f"\nBackup created: {backup_path}", file=sys.stderr)

            # Step 5: Save refined architecture
            self._save_architecture(temp_output)
            print(f"\n✓ Architecture refined successfully: {self.architecture_path}", file=sys.stderr)

            return 0

        except KeyboardInterrupt:
            print("\n\nRefinement interrupted by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"\nRefinement failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1

    def _invoke_provider(self, prompt: str, temp_output: Path) -> None:
        """
        Invoke provider with refinement prompt.

        Args:
            prompt: Refinement meta-prompt
            temp_output: Temp file path for agent output
        """
        # Build command (YOLO mode always enabled for refinement)
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

        except Exception as e:
            raise RuntimeError(f"Provider invocation failed: {e}")

    def _create_backup(self) -> Path:
        """
        Create timestamped backup of current architecture.

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir = self.paths.backups_dir / "architecture"
        self.paths.ensure_dirs(backup_dir)

        backup_path = backup_dir / f"ARCHITECTURE-{timestamp}.md"

        # Copy current architecture to backup
        import shutil
        shutil.copy2(self.architecture_path, backup_path)

        return backup_path

    def _save_architecture(self, temp_path: Path) -> None:
        """
        Save architecture document atomically.

        Args:
            temp_path: Path to temporary architecture file
        """
        # Ensure docs directory exists
        self.architecture_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic move
        import shutil
        shutil.move(str(temp_path), str(self.architecture_path))
