#!/usr/bin/env python3
"""
Common assertion helpers for Ralph Loop e2e tests.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional, Union

from ralph.validator import validate_backlog as validate_backlog_file


def assert_file_exists(path: Union[str, Path], message: Optional[str] = None):
    """
    Assert that a file exists.

    Args:
        path: Path to file
        message: Optional custom error message
    """
    path = Path(path)
    if not path.exists():
        msg = message or f"Expected file does not exist: {path}"
        raise AssertionError(msg)
    if not path.is_file():
        msg = message or f"Path exists but is not a file: {path}"
        raise AssertionError(msg)


def assert_file_not_exists(path: Union[str, Path], message: Optional[str] = None):
    """
    Assert that a file does not exist.

    Args:
        path: Path to file
        message: Optional custom error message
    """
    path = Path(path)
    if path.exists():
        msg = message or f"File should not exist but does: {path}"
        raise AssertionError(msg)


def assert_directory_exists(path: Union[str, Path], message: Optional[str] = None):
    """
    Assert that a directory exists.

    Args:
        path: Path to directory
        message: Optional custom error message
    """
    path = Path(path)
    if not path.exists():
        msg = message or f"Expected directory does not exist: {path}"
        raise AssertionError(msg)
    if not path.is_dir():
        msg = message or f"Path exists but is not a directory: {path}"
        raise AssertionError(msg)


def assert_backlog_valid(backlog_path: Union[str, Path], message: Optional[str] = None):
    """
    Assert that a backlog file is valid according to schema.

    Args:
        backlog_path: Path to backlog.json file
        message: Optional custom error message

    Raises:
        AssertionError: If backlog is invalid
    """
    backlog_path = Path(backlog_path)
    assert_file_exists(backlog_path, "Backlog file does not exist")

    # Load backlog
    try:
        with open(backlog_path) as f:
            backlog_data = json.load(f)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Backlog is not valid JSON: {e}")

    # Validate using validate_backlog function
    # Note: validate_backlog returns True if valid, False if invalid
    # It prints errors to stderr, so we capture them
    import io
    import sys

    old_stderr = sys.stderr
    sys.stderr = io.StringIO()

    try:
        is_valid = validate_backlog_file(backlog_path)
        error_output = sys.stderr.getvalue()
    finally:
        sys.stderr = old_stderr

    if not is_valid:
        error_msg = message or f"Backlog validation failed:\n{error_output}"
        raise AssertionError(error_msg)


def assert_backlog_contains_item(
    backlog_path: Union[str, Path],
    item_id: str,
    message: Optional[str] = None
):
    """
    Assert that backlog contains an item with specified ID.

    Args:
        backlog_path: Path to backlog.json file
        item_id: Item ID to look for
        message: Optional custom error message
    """
    backlog_path = Path(backlog_path)
    with open(backlog_path) as f:
        backlog = json.load(f)

    item_ids = [item['id'] for item in backlog.get('items', [])]
    if item_id not in item_ids:
        msg = message or f"Backlog does not contain item '{item_id}'. Found: {item_ids}"
        raise AssertionError(msg)


def assert_backlog_item_status(
    backlog_path: Union[str, Path],
    item_id: str,
    expected_status: str,
    message: Optional[str] = None
):
    """
    Assert that a backlog item has the expected status.

    Args:
        backlog_path: Path to backlog.json file
        item_id: Item ID to check
        expected_status: Expected status value
        message: Optional custom error message
    """
    backlog_path = Path(backlog_path)
    with open(backlog_path) as f:
        backlog = json.load(f)

    item = next((item for item in backlog.get('items', []) if item['id'] == item_id), None)
    if item is None:
        raise AssertionError(f"Item '{item_id}' not found in backlog")

    actual_status = item.get('status')
    if actual_status != expected_status:
        msg = message or f"Item '{item_id}' has status '{actual_status}', expected '{expected_status}'"
        raise AssertionError(msg)


def assert_git_commit_exists(
    project_dir: Union[str, Path],
    message_pattern: str,
    message: Optional[str] = None
):
    """
    Assert that a git commit exists matching the pattern.

    Args:
        project_dir: Project directory with git repo
        message_pattern: Regex pattern to match commit message
        message: Optional custom error message
    """
    project_dir = Path(project_dir)

    result = subprocess.run(
        ["git", "log", "--format=%s"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=True
    )

    commit_messages = result.stdout.strip().split('\n')
    pattern = re.compile(message_pattern)

    for commit_msg in commit_messages:
        if pattern.search(commit_msg):
            return  # Found matching commit

    msg = message or f"No commit found matching pattern '{message_pattern}'. Commits:\n" + "\n".join(f"  - {m}" for m in commit_messages)
    raise AssertionError(msg)


def assert_git_working_tree_clean(
    project_dir: Union[str, Path],
    message: Optional[str] = None
):
    """
    Assert that git working tree is clean.

    Args:
        project_dir: Project directory with git repo
        message: Optional custom error message
    """
    project_dir = Path(project_dir)

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=True
    )

    if result.stdout.strip():
        msg = message or f"Git working tree is not clean:\n{result.stdout}"
        raise AssertionError(msg)


def assert_exit_code(result, expected: int, message: Optional[str] = None):
    """
    Assert that a command result has the expected exit code.

    Args:
        result: subprocess.CompletedProcess or similar with returncode
        expected: Expected exit code
        message: Optional custom error message
    """
    actual = result.returncode if hasattr(result, 'returncode') else result
    if actual != expected:
        msg = message or f"Expected exit code {expected}, got {actual}"
        if hasattr(result, 'stderr') and result.stderr:
            msg += f"\nStderr: {result.stderr}"
        raise AssertionError(msg)


def assert_json_valid(path: Union[str, Path], message: Optional[str] = None):
    """
    Assert that a file contains valid JSON.

    Args:
        path: Path to JSON file
        message: Optional custom error message
    """
    path = Path(path)
    assert_file_exists(path)

    try:
        with open(path) as f:
            json.load(f)
    except json.JSONDecodeError as e:
        msg = message or f"File does not contain valid JSON: {e}"
        raise AssertionError(msg)


def assert_file_contains(
    path: Union[str, Path],
    text: str,
    message: Optional[str] = None
):
    """
    Assert that a file contains specified text.

    Args:
        path: Path to file
        text: Text to search for
        message: Optional custom error message
    """
    path = Path(path)
    assert_file_exists(path)

    content = path.read_text()
    if text not in content:
        msg = message or f"File does not contain expected text: '{text}'"
        raise AssertionError(msg)


def assert_file_matches_pattern(
    path: Union[str, Path],
    pattern: str,
    message: Optional[str] = None
):
    """
    Assert that a file contains text matching regex pattern.

    Args:
        path: Path to file
        pattern: Regex pattern to match
        message: Optional custom error message
    """
    path = Path(path)
    assert_file_exists(path)

    content = path.read_text()
    if not re.search(pattern, content):
        msg = message or f"File does not match pattern: '{pattern}'"
        raise AssertionError(msg)
