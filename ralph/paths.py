#!/usr/bin/env python3
"""
Path management for Ralph Loop artifacts.

Centralizes all path construction for logs, temporary files, backups, and locks.
"""

import shutil
import sys
from pathlib import Path


class RalphPaths:
    """Centralized path management for ralph-loop artifacts."""

    def __init__(self, project_dir: Path):
        """
        Initialize path manager.

        Args:
            project_dir: Target project directory
        """
        self.project_dir = project_dir
        self.ralph_dir = project_dir / ".ralph"

        # Subdirectories
        self.logs_dir = self.ralph_dir / "logs"
        self.tmp_dir = self.ralph_dir / "tmp"
        self.backups_dir = self.ralph_dir / "backups"

        # Log subdirectories
        self.init_logs = self.logs_dir / "init"
        self.analyze_logs = self.logs_dir / "analyze"
        self.refine_logs = self.logs_dir / "refine"
        self.improve_logs = self.logs_dir / "improve"
        self.qwen_stream_logs = self.logs_dir / "qwen-stream"
        self.parse_failures = self.logs_dir / "parse-failures"

        # Lock file
        self.lock_file = self.ralph_dir / "execution.lock"

        # Analysis file
        self.analysis_file = self.ralph_dir / "backlog-analysis.json"

        # Perform migration if needed
        self._migrate_old_artifacts()

        # Ensure .gitignore entry
        self.ensure_gitignore_entry()

    def ensure_dirs(self, *dirs: Path) -> None:
        """
        Create directories if they don't exist.

        Args:
            *dirs: Directory paths to create
        """
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_temp_file(self, base_path: Path, suffix: str = ".tmp") -> Path:
        """
        Get temp file path in .ralph/tmp/ directory.

        Args:
            base_path: Original file path
            suffix: Suffix to append (default: .tmp)

        Returns:
            Path to temp file in .ralph/tmp/
        """
        filename = base_path.name + suffix
        return self.tmp_dir / filename

    def get_backup_file(self, base_path: Path, timestamp: str) -> Path:
        """
        Get backup file path in .ralph/backups/ directory.

        Args:
            base_path: Original file path
            timestamp: Timestamp string (YYYYMMDD-HHMMSS)

        Returns:
            Path to backup file in .ralph/backups/
        """
        filename = f"{base_path.stem}.backup-{timestamp}{base_path.suffix}"
        return self.backups_dir / filename

    def _migrate_old_artifacts(self) -> None:
        """
        Migrate artifacts from old locations to .ralph folder.

        This provides backward compatibility by automatically moving:
        - logs/ralph/ → .ralph/logs/
        - .ralph-loop.lock → .ralph/execution.lock
        """
        old_logs = self.project_dir / "logs" / "ralph"
        old_lock = self.project_dir / ".ralph-loop.lock"

        migrated = False

        # Migrate old logs directory
        if old_logs.exists() and not self.logs_dir.exists():
            print("Migrating ralph-loop artifacts to .ralph folder...", file=sys.stderr)
            self.ensure_dirs(self.ralph_dir)
            try:
                shutil.move(str(old_logs), str(self.logs_dir))
                migrated = True
                print(f"  ✓ Moved logs/ralph/ → .ralph/logs/", file=sys.stderr)
            except Exception as e:
                print(f"  Warning: Failed to migrate logs: {e}", file=sys.stderr)

        # Migrate old lock file
        if old_lock.exists() and not self.lock_file.exists():
            if not migrated:
                print("Migrating ralph-loop artifacts to .ralph folder...", file=sys.stderr)
            self.ensure_dirs(self.ralph_dir)
            try:
                shutil.move(str(old_lock), str(self.lock_file))
                print(f"  ✓ Moved .ralph-loop.lock → .ralph/execution.lock", file=sys.stderr)
            except Exception as e:
                print(f"  Warning: Failed to migrate lock file: {e}", file=sys.stderr)

        if migrated or (old_lock.exists() and not self.lock_file.exists()):
            print("  Migration complete.", file=sys.stderr)
            print(file=sys.stderr)

    def ensure_gitignore_entry(self) -> None:
        """
        Ensure .ralph/ is in .gitignore.

        Creates .gitignore if it doesn't exist, or appends .ralph/ entry if missing.
        Handles both .ralph and .ralph/ as valid existing entries.
        Silently continues on errors (prints warning to stderr).
        """
        gitignore_path = self.project_dir / ".gitignore"

        try:
            # Check if entry already exists
            needs_entry = True
            if gitignore_path.exists():
                try:
                    content = gitignore_path.read_text(encoding='utf-8')
                    lines = content.splitlines()
                    for line in lines:
                        stripped = line.strip()
                        if stripped == ".ralph/" or stripped == ".ralph":
                            needs_entry = False
                            break
                except Exception as e:
                    # If we can't read it, try to append anyway
                    print(f"Warning: Could not read .gitignore: {e}", file=sys.stderr)

            if needs_entry:
                # Prepare content to append
                if gitignore_path.exists():
                    # Add leading newline to separate from existing content
                    entry = "\n# Ralph Loop artifacts\n.ralph/\n"
                else:
                    # New file, no leading newline needed
                    entry = "# Ralph Loop artifacts\n.ralph/\n"

                # Append to .gitignore
                with open(gitignore_path, 'a', encoding='utf-8') as f:
                    f.write(entry)

                print("  ✓ Added .ralph/ to .gitignore", file=sys.stderr)

        except Exception as e:
            print(f"  Warning: Failed to add .ralph/ to .gitignore: {e}", file=sys.stderr)
            print(f"  You can manually add '.ralph/' to your .gitignore file.", file=sys.stderr)
