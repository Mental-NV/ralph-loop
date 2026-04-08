#!/usr/bin/env python3
"""
Test environment manager for Ralph Loop e2e tests.

Provides isolated test environments with git repositories and automatic cleanup.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class TestEnvironment:
    """
    Manages an isolated test environment with git repository.

    Creates a temporary directory with initialized git repo, configured
    user, and initial commit. Automatically cleans up on context exit.
    """
    __test__ = False  # Tell pytest this is not a test class

    def __init__(self, init_git=True):
        """
        Initialize test environment.

        Args:
            init_git: Whether to initialize git repository (default: True)
        """
        self.tmpdir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.tmpdir.name)
        self._git_initialized = False

        if init_git:
            self._init_git()

    def _init_git(self):
        """Initialize git repository with initial commit."""
        if self._git_initialized:
            return

        # Initialize git repo
        subprocess.run(
            ["git", "init"],
            cwd=self.project_dir,
            capture_output=True,
            check=True
        )

        # Configure git user
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.project_dir,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.project_dir,
            capture_output=True,
            check=True
        )

        # Create initial commit (required for clean working tree checks)
        readme = self.project_dir / "README.md"
        readme.write_text("# Test Project\n")

        subprocess.run(
            ["git", "add", "."],
            cwd=self.project_dir,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=self.project_dir,
            capture_output=True,
            check=True
        )

        self._git_initialized = True

    def create_file(self, relative_path: str, content: str = ""):
        """
        Create a file in the test environment.

        Args:
            relative_path: Path relative to project directory
            content: File content (default: empty string)

        Returns:
            Path: Absolute path to created file
        """
        file_path = self.project_dir / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path

    def create_backlog(self, backlog_data: dict, path: Optional[str] = None):
        """
        Create a backlog.json file in the test environment.

        Args:
            backlog_data: Backlog dictionary to write as JSON
            path: Optional custom path (default: docs/backlog.json)

        Returns:
            Path: Absolute path to created backlog file
        """
        import json

        if path is None:
            path = "docs/backlog.json"

        backlog_path = self.project_dir / path
        backlog_path.parent.mkdir(parents=True, exist_ok=True)
        backlog_path.write_text(json.dumps(backlog_data, indent=2))
        return backlog_path

    def get_git_log(self, format_str: str = "%s") -> list:
        """
        Get git commit log.

        Args:
            format_str: Git log format string (default: %s for subject)

        Returns:
            List of commit messages
        """
        result = subprocess.run(
            ["git", "log", f"--format={format_str}"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return [line for line in result.stdout.strip().split('\n') if line]

    def get_git_status(self) -> str:
        """
        Get git status output.

        Returns:
            Git status output as string
        """
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

    def is_working_tree_clean(self) -> bool:
        """
        Check if git working tree is clean.

        Returns:
            True if working tree is clean, False otherwise
        """
        return len(self.get_git_status()) == 0

    def commit_all(self, message: str = "Test commit"):
        """
        Stage and commit all changes.

        Args:
            message: Commit message
        """
        subprocess.run(
            ["git", "add", "."],
            cwd=self.project_dir,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.project_dir,
            capture_output=True,
            check=True
        )

    def cleanup(self):
        """Clean up temporary directory."""
        self.tmpdir.cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
        return False
