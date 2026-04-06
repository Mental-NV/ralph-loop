#!/usr/bin/env python3
"""
Backlog refiner for Ralph Loop.

Handles refinement of backlog.json using AI agent suggestions.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ralph.paths import RalphPaths
from ralph.providers import get_provider, list_available_providers


class BacklogRefiner:
    """Refines backlog using AI agent with user-provided prompts."""

    def __init__(
        self,
        project_dir: Path,
        backlog_path: Path,
        provider: str = "qwen",
        dry_run: bool = False
    ):
        """
        Initialize BacklogRefiner.

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

        # Initialize paths
        self.paths = RalphPaths(project_dir)
        self.debug_dir = self.paths.refine_logs

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
        Refine backlog using AI agent with user prompt.

        Args:
            user_prompt: Refinement instructions for the agent

        Returns:
            Exit code: 0 on success, 1 on error
        """
        print(f"Refining backlog: {self.backlog_path}", file=sys.stderr)
        print(f"Provider: {self.provider_name}", file=sys.stderr)
        print(f"Project directory: {self.project_dir}", file=sys.stderr)
        print(file=sys.stderr)

        # Ensure debug directory exists
        self.paths.ensure_dirs(self.debug_dir)

        try:
            # Step 1: Load and validate current backlog
            current_backlog = self._load_backlog()

            # Step 2: Build refinement prompt
            from ralph.prompts import build_refinement_prompt

            # Create temp file for agent output
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            temp_output = self.debug_dir / f"refinement-{timestamp}.json"

            backlog_json = json.dumps(current_backlog, indent=2)
            prompt = build_refinement_prompt(
                backlog_json=backlog_json,
                user_prompt=user_prompt,
                output_file=str(temp_output)
            )

            if self.dry_run:
                print("[DRY RUN] Would refine with prompt:", file=sys.stderr)
                print(prompt[:500] + "..." if len(prompt) > 500 else prompt, file=sys.stderr)
                print(f"\n[DRY RUN] Provider: {self.provider_name}", file=sys.stderr)
                return 0

            # Step 3: Invoke provider
            print("Invoking agent for refinement...", file=sys.stderr)
            response = self._invoke_provider(prompt, temp_output)

            # Step 4: Parse response
            from ralph.parsers import parse_roadmap_response
            refined_backlog = parse_roadmap_response(response, self.debug_dir)

            # Step 5: Merge with preservation
            print("\nMerging refined backlog with preserved items...", file=sys.stderr)
            merged_backlog = self._merge_backlogs(current_backlog, refined_backlog)

            # Step 6: Validate merged backlog
            print("Validating merged backlog...", file=sys.stderr)
            if not self._validate_merged_backlog(merged_backlog):
                print("Error: Merged backlog validation failed", file=sys.stderr)
                return 1

            # Step 7: Show diff
            self._show_diff(current_backlog, merged_backlog)

            # Step 8: Create backup
            backup_path = self._create_backup()
            print(f"\nBackup created: {backup_path}", file=sys.stderr)

            # Step 9: Save refined backlog
            self._save_backlog(merged_backlog)
            print(f"\n✓ Backlog refined successfully: {self.backlog_path}", file=sys.stderr)

            return 0

        except KeyboardInterrupt:
            print("\n\nRefinement interrupted by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"\nRefinement failed: {e}", file=sys.stderr)
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
        Invoke provider with refinement prompt.

        Args:
            prompt: Refinement meta-prompt
            temp_output: Temp file path for agent output

        Returns:
            Raw agent response
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

    def _merge_backlogs(self, current: Dict[str, Any], refined: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge refined backlog with current, preserving in-progress and done items.

        Args:
            current: Current backlog
            refined: Refined backlog from agent

        Returns:
            Merged backlog
        """
        # Extract items to preserve (in_progress, ready_for_validation, done)
        preserved_statuses = ['in_progress', 'ready_for_validation', 'done']
        preserved_items = [
            item for item in current.get('items', [])
            if item.get('status') in preserved_statuses
        ]

        # Extract refined items (only todo, blocked, deferred, cancelled)
        refinable_statuses = ['todo', 'blocked', 'deferred', 'cancelled']
        refined_items = [
            item for item in refined.get('items', [])
            if item.get('status') in refinable_statuses
        ]

        # Combine
        merged_items = preserved_items + refined_items

        # Recalculate order values to ensure uniqueness
        for i, item in enumerate(sorted(merged_items, key=lambda x: x.get('order', 0))):
            item['order'] = i

        return {
            'version': refined.get('version', '1.0.0'),
            'items': merged_items
        }

    def _validate_merged_backlog(self, backlog: Dict[str, Any]) -> bool:
        """
        Validate merged backlog by writing to temp file and validating.

        Args:
            backlog: Merged backlog to validate

        Returns:
            True if valid, False otherwise
        """
        # Write to temp file
        temp_path = self.paths.get_temp_file(self.backlog_path, '.validate')
        self.paths.ensure_dirs(self.paths.tmp_dir)
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(backlog, f, indent=2, ensure_ascii=False)
                f.write('\n')

            # Validate
            from ralph.validator import validate_backlog
            is_valid = validate_backlog(temp_path)

            # Clean up
            temp_path.unlink()

            return is_valid

        except Exception as e:
            print(f"Validation error: {e}", file=sys.stderr)
            if temp_path.exists():
                temp_path.unlink()
            return False

    def _create_backup(self) -> Path:
        """
        Create timestamped backup of current backlog.

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = self.paths.get_backup_file(self.backlog_path, timestamp)
        self.paths.ensure_dirs(self.paths.backups_dir)

        # Copy current backlog to backup
        import shutil
        shutil.copy2(self.backlog_path, backup_path)

        return backup_path

    def _save_backlog(self, backlog: Dict[str, Any]) -> None:
        """
        Save backlog.json atomically.

        Args:
            backlog: Backlog to save
        """
        # Write to temp file first
        temp_path = self.paths.get_temp_file(self.backlog_path, '.tmp')
        self.paths.ensure_dirs(self.paths.tmp_dir)
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(backlog, f, indent=2, ensure_ascii=False)
                f.write('\n')
            # Atomic rename
            temp_path.replace(self.backlog_path)
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to save backlog: {e}")

    def _show_diff(self, current: Dict[str, Any], refined: Dict[str, Any]) -> None:
        """
        Show human-readable diff between current and refined backlogs.

        Args:
            current: Current backlog
            refined: Refined backlog
        """
        current_items = {item['id']: item for item in current.get('items', [])}
        refined_items = {item['id']: item for item in refined.get('items', [])}

        current_ids = set(current_items.keys())
        refined_ids = set(refined_items.keys())

        # Items added
        added_ids = refined_ids - current_ids
        # Items removed
        removed_ids = current_ids - refined_ids
        # Items potentially modified
        common_ids = current_ids & refined_ids

        # Items preserved (in_progress, ready_for_validation, done)
        preserved_statuses = ['in_progress', 'ready_for_validation', 'done']
        preserved_ids = {
            item_id for item_id, item in current_items.items()
            if item.get('status') in preserved_statuses
        }

        print("\n" + "="*80, file=sys.stderr)
        print("Backlog Diff", file=sys.stderr)
        print("="*80, file=sys.stderr)

        if preserved_ids:
            print(f"\nPreserved items ({len(preserved_ids)}):", file=sys.stderr)
            for item_id in sorted(preserved_ids):
                item = current_items[item_id]
                print(f"  ✓ {item_id} [{item['status']}] - {item['title']}", file=sys.stderr)

        if added_ids:
            print(f"\nAdded items ({len(added_ids)}):", file=sys.stderr)
            for item_id in sorted(added_ids):
                item = refined_items[item_id]
                print(f"  + {item_id} [{item.get('priority', 'P1')}] - {item['title']}", file=sys.stderr)

        if removed_ids:
            print(f"\nRemoved items ({len(removed_ids)}):", file=sys.stderr)
            for item_id in sorted(removed_ids):
                item = current_items[item_id]
                print(f"  - {item_id} [{item.get('priority', 'P1')}] - {item['title']}", file=sys.stderr)

        # Check for modifications in common items (excluding preserved)
        modified_ids = []
        for item_id in common_ids:
            if item_id not in preserved_ids:
                # Simple comparison: check if JSON differs
                current_json = json.dumps(current_items[item_id], sort_keys=True)
                refined_json = json.dumps(refined_items[item_id], sort_keys=True)
                if current_json != refined_json:
                    modified_ids.append(item_id)

        if modified_ids:
            print(f"\nModified items ({len(modified_ids)}):", file=sys.stderr)
            for item_id in sorted(modified_ids):
                item = refined_items[item_id]
                print(f"  ~ {item_id} [{item.get('priority', 'P1')}] - {item['title']}", file=sys.stderr)

        print("\n" + "="*80, file=sys.stderr)
