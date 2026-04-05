"""
Backlog orchestrator for Ralph Loop.

Handles execution of backlog items with provider-agnostic orchestration.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ralph.providers import get_provider, list_available_providers


class BacklogOrchestrator:
    """Orchestrates execution of backlog items."""

    def __init__(
        self,
        project_dir: Path,
        backlog_path: Path,
        provider: str = "qwen",
        auto_push: bool = False,
        dry_run: bool = False
    ):
        self.project_dir = project_dir
        self.backlog_path = backlog_path
        self.provider_name = provider
        self.auto_push = auto_push
        self.dry_run = dry_run
        self.lock_path = project_dir / ".ralph-loop.lock"

        # Initialize provider (YOLO mode always enabled)
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
            sys.exit(1)

    def load_backlog(self) -> Dict[str, Any]:
        """Load and parse backlog.json."""
        try:
            with open(self.backlog_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.error(f"Backlog not found: {self.backlog_path}")
        except json.JSONDecodeError as e:
            self.error(f"Invalid JSON in backlog: {e}")

    def save_backlog(self, backlog: Dict[str, Any]) -> None:
        """Save backlog.json atomically."""
        if self.dry_run:
            print("[DRY RUN] Would save backlog.json")
            return

        # Write to temp file first
        temp_path = self.backlog_path.with_suffix('.json.tmp')
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(backlog, f, indent=2, ensure_ascii=False)
                f.write('\n')
            # Atomic rename
            temp_path.replace(self.backlog_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            self.error(f"Failed to save backlog: {e}")

    def validate_backlog(self) -> bool:
        """Validate backlog using bundled validator. Returns True if valid."""
        from ralph.validator import validate_backlog as validate_fn

        try:
            return validate_fn(self.backlog_path)
        except Exception as e:
            print(f"Validation error: {e}", file=sys.stderr)
            return False

    def acquire_lock(self) -> bool:
        """Acquire execution lock. Returns True if acquired."""
        if self.lock_path.exists():
            # Check if lock is stale (older than 1 hour)
            lock_age = time.time() - self.lock_path.stat().st_mtime
            if lock_age > 3600:
                print(f"Removing stale lock (age: {lock_age:.0f}s)")
                self.lock_path.unlink()
            else:
                return False

        try:
            self.lock_path.write_text(f"{os.getpid()}\n{datetime.now(timezone.utc).isoformat()}\n")
            return True
        except Exception as e:
            print(f"Failed to acquire lock: {e}", file=sys.stderr)
            return False

    def release_lock(self) -> None:
        """Release execution lock."""
        if self.lock_path.exists():
            self.lock_path.unlink()

    def check_git_clean(self) -> bool:
        """Check if git working tree is clean."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        return result.returncode == 0 and not result.stdout.strip()

    def git_fetch(self) -> bool:
        """Run git fetch. Returns True on success."""
        if self.dry_run:
            print("[DRY RUN] Would run: git fetch")
            return True

        result = subprocess.run(
            ["git", "fetch"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"git fetch failed: {result.stderr}", file=sys.stderr)
            return False
        return True

    def git_push(self) -> bool:
        """Run git push. Returns True on success."""
        if self.dry_run:
            print("[DRY RUN] Would run: git push")
            return True

        result = subprocess.run(
            ["git", "push"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"git push failed: {result.stderr}", file=sys.stderr)
            return False
        return True

    def git_commit(self, message: str) -> bool:
        """Create a git commit with all changes. Returns True on success."""
        if self.dry_run:
            print("[DRY RUN] Would run: git add -A")
            print(f"[DRY RUN] Would run: git commit -m '{message[:50]}...'")
            return True

        # Stage all changes
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"git add failed: {result.stderr}", file=sys.stderr)
            return False

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # No changes staged
            print("No changes to commit")
            return True

        # Create commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"git commit failed: {result.stderr}", file=sys.stderr)
            return False

        print(f"✓ Created commit: {message.split(chr(10))[0]}")  # First line only
        return True

    def select_next_item(self, backlog: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Select next item to execute based on:
        1. Status is 'todo'
        2. All dependencies are 'done'
        3. Lowest priority number (P0 < P1 < P2 < P3)
        4. Lowest order value (tiebreaker)

        Returns None if no eligible item found.
        """
        items = backlog.get('items', [])
        item_map = {item['id']: item for item in items}

        # Filter to todo items with satisfied dependencies
        eligible = []
        for item in items:
            if item['status'] != 'todo':
                continue

            # Check dependencies
            depends_on = item.get('dependsOn', [])
            deps_satisfied = all(
                item_map.get(dep_id, {}).get('status') == 'done'
                for dep_id in depends_on
            )

            if deps_satisfied:
                eligible.append(item)

        if not eligible:
            return None

        # Sort by priority (P0=0, P1=1, P2=2, P3=3), then by order
        priority_map = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        eligible.sort(key=lambda x: (priority_map.get(x['priority'], 99), x['order']))

        return eligible[0]

    def mark_item_started(self, backlog: Dict[str, Any], item_id: str) -> None:
        """Mark item as in_progress and set startedAt timestamp."""
        items = backlog.get('items', [])
        for item in items:
            if item['id'] == item_id:
                item['status'] = 'in_progress'
                item['startedAt'] = datetime.now(timezone.utc).isoformat()
                break

    def mark_work_complete(self, backlog: Dict[str, Any], item_id: str) -> None:
        """Mark work phase complete and transition to ready_for_validation."""
        items = backlog.get('items', [])
        for item in items:
            if item['id'] == item_id:
                item['status'] = 'ready_for_validation'
                item['workCompletedAt'] = datetime.now(timezone.utc).isoformat()
                break

    def mark_item_done(self, backlog: Dict[str, Any], item_id: str) -> None:
        """Mark item as done, set completedAt timestamp, and mark all deliverables/exit criteria as done."""
        items = backlog.get('items', [])
        for item in items:
            if item['id'] == item_id:
                item['status'] = 'done'
                item['completedAt'] = datetime.now(timezone.utc).isoformat()

                # Mark all deliverables as done
                for deliverable in item.get('deliverables', []):
                    deliverable['done'] = True

                # Mark all exit criteria as done
                for criterion in item.get('exitCriteria', []):
                    criterion['done'] = True

                break

    def is_cleanup_command(self, cmd: str) -> bool:
        """Identify cleanup commands that shouldn't block completion."""
        cleanup_patterns = [
            'pkill', 'killall', 'rm -rf', 'docker stop',
            'docker rm', 'npm stop', 'dotnet stop', 'kill '
        ]
        return any(pattern in cmd for pattern in cleanup_patterns)

    def run_validation_commands(self, item: Dict[str, Any]) -> bool:
        """Run validation commands for item with graceful cleanup handling. Returns True if all critical commands pass."""
        validation = item.get('validation', {})
        commands = validation.get('commands', [])

        if not commands:
            print("No validation commands defined, skipping validation")
            return True

        # Classify commands
        critical_commands = []
        cleanup_commands = []

        for cmd in commands:
            if self.is_cleanup_command(cmd):
                cleanup_commands.append(cmd)
            else:
                critical_commands.append(cmd)

        # Run critical validation
        if critical_commands:
            print(f"Running {len(critical_commands)} critical validation command(s)...")

            for i, cmd in enumerate(critical_commands, 1):
                print(f"  [{i}/{len(critical_commands)}] {cmd}")

                if self.dry_run:
                    print("  [DRY RUN] Would run command")
                    continue

                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    print(f"  FAILED (exit code {result.returncode})", file=sys.stderr)
                    if result.stdout:
                        print("  stdout:", result.stdout[:500], file=sys.stderr)
                    if result.stderr:
                        print("  stderr:", result.stderr[:500], file=sys.stderr)
                    return False

                print(f"  PASSED")

        # Run cleanup commands (best-effort)
        if cleanup_commands:
            print(f"\nRunning {len(cleanup_commands)} cleanup command(s) (best-effort)...")

            for i, cmd in enumerate(cleanup_commands, 1):
                print(f"  [{i}/{len(cleanup_commands)}] {cmd}")

                if self.dry_run:
                    print("  [DRY RUN] Would run command")
                    continue

                try:
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode != 0:
                        print(f"  WARNING: Cleanup failed (non-critical, continuing)", file=sys.stderr)
                        if result.stderr:
                            print(f"  stderr: {result.stderr[:200]}", file=sys.stderr)
                    else:
                        print(f"  PASSED")

                except subprocess.TimeoutExpired:
                    print(f"  WARNING: Cleanup timed out (non-critical, continuing)", file=sys.stderr)
                except KeyboardInterrupt:
                    print(f"\n  WARNING: Cleanup interrupted by user (non-critical, continuing)", file=sys.stderr)
                except Exception as e:
                    print(f"  WARNING: Cleanup error: {e} (non-critical, continuing)", file=sys.stderr)

        return True

    def execute_item(self, item: Dict[str, Any]) -> bool:
        """
        Execute a backlog item by invoking agent provider with appropriate prompt.
        Returns True if execution succeeded.
        """
        item_id = item['id']
        title = item['title']

        print(f"\n{'='*80}")
        print(f"Executing: {title}")
        print(f"ID: {item_id}")
        print(f"Priority: {item['priority']}")
        print(f"Provider: {self.provider_name} (YOLO mode)")
        print(f"{'='*80}\n")

        # Build execution prompt
        prompt = self.build_execution_prompt(item)

        if self.dry_run:
            print("[DRY RUN] Would execute with prompt:")
            print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            print(f"\n[DRY RUN] Provider: {self.provider_name}")
            print(f"[DRY RUN] YOLO mode: always enabled")
            return True

        # Build command (YOLO always enabled)
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

                # Close agent stdout in parent to allow agent to receive SIGPIPE
                if agent_proc.stdout:
                    agent_proc.stdout.close()

                # Wait for renderer to complete
                renderer_proc.wait()

                # Check agent exit code
                agent_proc.wait()
                if agent_proc.returncode != 0:
                    stderr = agent_proc.stderr.read() if agent_proc.stderr else ""
                    if stderr:
                        print(f"\nAgent error output:\n{stderr}", file=sys.stderr)
                    return False

            else:
                # No renderer, run directly
                result = subprocess.run(
                    cmd,
                    cwd=self.project_dir,
                    text=True
                )
                if result.returncode != 0:
                    return False

            return True

        except KeyboardInterrupt:
            print("\n\nExecution interrupted by user", file=sys.stderr)
            return False
        except Exception as e:
            print(f"\nExecution failed: {e}", file=sys.stderr)
            return False

    def build_execution_prompt(self, item: Dict[str, Any]) -> str:
        """Build execution prompt for item."""
        lines = [
            f"Execute backlog item: {item['title']}",
            "",
            f"**Why:** {item.get('why', 'No rationale provided')}",
            "",
            "**Deliverables:**"
        ]

        for deliverable in item.get('deliverables', []):
            status = "✓" if deliverable.get('done') else "○"
            lines.append(f"  {status} {deliverable['text']}")

        lines.append("")
        lines.append("**Exit Criteria:**")

        for criterion in item.get('exitCriteria', []):
            status = "✓" if criterion.get('done') else "○"
            lines.append(f"  {status} {criterion['text']}")

        if item.get('risks'):
            lines.append("")
            lines.append("**Risks:**")
            for risk in item['risks']:
                lines.append(f"  - {risk}")

        validation = item.get('validation', {})
        if validation.get('commands'):
            lines.append("")
            lines.append("**Validation Commands:**")
            for cmd in validation['commands']:
                lines.append(f"  - {cmd}")

        lines.append("")
        lines.append("Please implement this milestone following the deliverables and exit criteria.")

        return "\n".join(lines)

    def build_commit_message(self, item: Dict[str, Any]) -> str:
        """Build commit message for completed item."""
        lines = [
            f"[{item['id']}] {item['title']}",
            "",
        ]

        # Add deliverables
        deliverables = item.get('deliverables', [])
        if deliverables:
            lines.append("Deliverables:")
            for deliverable in deliverables:
                status = "✓" if deliverable.get('done') else "○"
                lines.append(f"  {status} {deliverable['text']}")
            lines.append("")

        # Add exit criteria
        exit_criteria = item.get('exitCriteria', [])
        if exit_criteria:
            lines.append("Exit criteria:")
            for criterion in exit_criteria:
                status = "✓" if criterion.get('done') else "○"
                lines.append(f"  {status} {criterion['text']}")

        return "\n".join(lines)

    def run_loop(self, max_iterations: Optional[int] = None) -> int:
        """
        Main execution loop with multi-phase execution.
        Returns exit code: 0 if all items done, 1 on error, 2 if work remains.
        """
        iteration = 0

        while True:
            iteration += 1
            if max_iterations and iteration > max_iterations:
                print(f"\nReached max iterations ({max_iterations}), stopping")
                return 2

            print(f"\n{'='*80}")
            print(f"Ralph Loop - Iteration {iteration}")
            print(f"{'='*80}")

            # Validate backlog
            if not self.validate_backlog():
                return 1

            # Load backlog
            backlog = self.load_backlog()

            # Check for items in ready_for_validation status first
            items = backlog.get('items', [])
            ready_items = [i for i in items if i['status'] == 'ready_for_validation']

            if ready_items:
                # Process validation phase for ready items
                item = ready_items[0]
                print(f"\nValidation phase for: {item['title']}")
                print(f"ID: {item['id']}")
                print(f"Work completed at: {item.get('workCompletedAt', 'unknown')}")

                # Run validation
                if not self.run_validation_commands(item):
                    print(f"\nValidation failed for {item['id']}", file=sys.stderr)
                    return 1

                # Mark item as done
                backlog = self.load_backlog()  # Reload in case of external changes
                self.mark_item_done(backlog, item['id'])
                self.save_backlog(backlog)

                print(f"\n✓ Completed: {item['title']}")

                # Create git commit with all changes
                commit_message = self.build_commit_message(item)
                if not self.git_commit(commit_message):
                    print("Warning: git commit failed", file=sys.stderr)
                    # Continue anyway - don't fail the iteration

                # Git push if auto-push enabled
                if self.auto_push:
                    if not self.git_push():
                        print("Warning: git push failed", file=sys.stderr)

                continue  # Process next iteration

            # Select next item to start
            next_item = self.select_next_item(backlog)

            if not next_item:
                # Check if any items are in_progress
                in_progress = [i for i in items if i['status'] == 'in_progress']

                if in_progress:
                    print("\nNo new items to start, but items in progress remain:")
                    for item in in_progress:
                        print(f"  - {item['id']}: {item['status']}")
                    return 2

                # Check if all items are done
                todo_count = sum(1 for i in items if i['status'] == 'todo')
                done_count = sum(1 for i in items if i['status'] == 'done')

                if todo_count == 0:
                    print(f"\n✓ All items complete! ({done_count} done)")
                    return 0
                else:
                    print(f"\nNo eligible items to execute ({todo_count} todo, {done_count} done)")
                    print("Remaining items may have unsatisfied dependencies or be blocked")
                    return 2

            # Mark item as started
            self.mark_item_started(backlog, next_item['id'])
            self.save_backlog(backlog)

            # Execute work phase
            print(f"\nWork phase for: {next_item['title']}")
            success = self.execute_item(next_item)

            if not success:
                print(f"\nWork phase failed for {next_item['id']}", file=sys.stderr)
                return 1

            # Mark work complete and transition to ready_for_validation
            backlog = self.load_backlog()  # Reload in case of external changes
            self.mark_work_complete(backlog, next_item['id'])
            self.save_backlog(backlog)

            print(f"\n✓ Work phase complete: {next_item['title']}")
            print(f"Status: ready_for_validation (will validate on next iteration)")

    def error(self, msg: str) -> None:
        """Print error and exit."""
        print(f"Error: {msg}", file=sys.stderr)
        sys.exit(1)
