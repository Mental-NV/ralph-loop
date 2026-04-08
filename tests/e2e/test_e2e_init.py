#!/usr/bin/env python3
"""
E2E tests for 'ralph init' command.

Tests the initialization of backlog from natural language prompts.
"""

import json
import os
import pytest
import shutil
import subprocess
import sys
from pathlib import Path

from tests.helpers.assertions import (
    assert_file_exists,
    assert_file_not_exists,
    assert_directory_exists,
    assert_backlog_valid,
    assert_file_contains,
    assert_exit_code
)
from tests.helpers.mock_provider import get_init_response


def run_ralph_command(test_env, *args, mock_response=None):
    """
    Helper to run ralph CLI commands with proper PYTHONPATH.

    Args:
        test_env: TestEnvironment instance
        *args: Command arguments (e.g., "--provider", "mock", "init", "prompt")
               Note: Global options like --provider should come before subcommand
        mock_response: Optional mock response data to inject via env var

    Returns:
        subprocess.CompletedProcess
    """
    # Try using 'ralph' command first (if installed)
    if shutil.which('ralph'):
        cmd = ["ralph"] + list(args)
        env = os.environ.copy()
    else:
        # Add project root to PYTHONPATH so ralph module can be found
        env = os.environ.copy()
        project_root = Path(__file__).parent.parent.parent
        env['PYTHONPATH'] = str(project_root) + os.pathsep + env.get('PYTHONPATH', '')
        cmd = [sys.executable, "-m", "ralph.cli"] + list(args)

    # Check if mock provider is being used
    if '--provider' in args and args[args.index('--provider') + 1] == 'mock':
        env['RALPH_TEST_MODE'] = '1'

        # Inject mock response via environment variable if provided
        if mock_response is not None:
            env['RALPH_MOCK_RESPONSES'] = json.dumps(mock_response)

    result = subprocess.run(
        cmd,
        cwd=test_env.project_dir,
        capture_output=True,
        text=True,
        env=env
    )
    return result


def test_init_creates_backlog(test_env):
    """Test that 'ralph init' creates a valid backlog.json file."""
    from tests.helpers.mock_provider import get_tech_stack_response, get_architecture_response

    # Run init command with mock responses for all 3 calls
    # Call 0: roadmap, Call 1: tech stack, Call 2: architecture
    mock_responses = {
        0: get_init_response(num_items=3),
        1: get_tech_stack_response(),
        2: get_architecture_response()
    }

    result = run_ralph_command(
        test_env,
        "--provider", "mock",
        "init",
        "Create a test project",
        mock_response=mock_responses
    )

    # Verify exit code
    assert_exit_code(result, 0)

    # Verify backlog.json was created
    backlog_path = test_env.project_dir / "docs" / "backlog.json"
    assert_file_exists(backlog_path)

    # Verify backlog is valid
    assert_backlog_valid(backlog_path)

    # Verify backlog contains expected items
    with open(backlog_path) as f:
        backlog = json.load(f)

    assert backlog['version'] == '1.0.0'
    assert len(backlog['items']) == 3
    assert all('id' in item for item in backlog['items'])
    assert all('status' in item for item in backlog['items'])
    assert all(item['status'] == 'todo' for item in backlog['items'])


def test_init_creates_architecture(test_env):
    """Test that 'ralph init' creates ARCHITECTURE.md file."""
    from tests.helpers.mock_provider import get_tech_stack_response, get_architecture_response

    # Run init command with mock responses for all 3 calls
    mock_responses = {
        0: get_init_response(num_items=2),
        1: get_tech_stack_response(),
        2: get_architecture_response()
    }

    result = run_ralph_command(
        test_env,
        "--provider", "mock",
        "init",
        "Create a test project",
        mock_response=mock_responses
    )

    assert_exit_code(result, 0)

    # Verify ARCHITECTURE.md was created
    arch_path = test_env.project_dir / "docs" / "ARCHITECTURE.md"
    assert_file_exists(arch_path)

    # Verify it contains expected content
    assert_file_contains(arch_path, "# Architecture")


def test_init_updates_gitignore(test_env):
    """Test that 'ralph init' updates .gitignore with .ralph/ entry."""
    from tests.helpers.mock_provider import get_tech_stack_response, get_architecture_response

    # Create initial .gitignore
    gitignore_path = test_env.project_dir / ".gitignore"
    gitignore_path.write_text("*.pyc\n__pycache__/\n")
    test_env.commit_all("Add .gitignore")

    # Run init command with mock responses
    mock_responses = {
        0: get_init_response(num_items=1),
        1: get_tech_stack_response(),
        2: get_architecture_response()
    }

    result = run_ralph_command(
        test_env,
        "--provider", "mock",
        "init",
        "Create a test project",
        mock_response=mock_responses
    )

    assert_exit_code(result, 0)

    # Verify .gitignore contains .ralph/
    assert_file_contains(gitignore_path, ".ralph/")

    # Verify original content is preserved
    assert_file_contains(gitignore_path, "*.pyc")
    assert_file_contains(gitignore_path, "__pycache__/")


def test_init_requires_git_repo(test_env_no_git):
    """Test that 'ralph init' fails when not in a git repository."""
    # Run init command in directory without git
    result = run_ralph_command(test_env_no_git, "--provider", "mock", "init", "Create a test project")

    # Verify it fails with exit code 1
    assert_exit_code(result, 1)

    # Verify error message mentions git
    assert "git" in result.stderr.lower() or "repository" in result.stderr.lower()


def test_init_dry_run(test_env):
    """Test that 'ralph init --dry-run' doesn't create files."""
    # In dry-run mode, the provider is not actually invoked,
    # so we don't need to provide mock responses
    result = run_ralph_command(
        test_env,
        "--provider", "mock",
        "--dry-run",
        "init",
        "Create a test project"
    )

    assert_exit_code(result, 0)

    # Verify files were NOT created
    backlog_path = test_env.project_dir / "docs" / "backlog.json"
    arch_path = test_env.project_dir / "docs" / "ARCHITECTURE.md"

    assert_file_not_exists(backlog_path)
    assert_file_not_exists(arch_path)


def test_init_with_custom_backlog_path(test_env):
    """Test that 'ralph init --backlog' uses custom path."""
    from tests.helpers.mock_provider import get_tech_stack_response, get_architecture_response

    # Run init with custom backlog path and mock responses
    custom_path = test_env.project_dir / "custom" / "my-backlog.json"
    mock_responses = {
        0: get_init_response(num_items=1),
        1: get_tech_stack_response(),
        2: get_architecture_response()
    }

    result = run_ralph_command(
        test_env,
        "--provider", "mock",
        "--backlog", str(custom_path),
        "init",
        "Create a test project",
        mock_response=mock_responses
    )

    assert_exit_code(result, 0)

    # Verify backlog was created at custom path
    assert_file_exists(custom_path)
    assert_backlog_valid(custom_path)

    # Verify default path was NOT used
    default_path = test_env.project_dir / "docs" / "backlog.json"
    assert_file_not_exists(default_path)


def test_init_creates_debug_logs(test_env):
    """Test that 'ralph init' creates debug logs in .ralph/logs/init/."""
    from tests.helpers.mock_provider import get_tech_stack_response, get_architecture_response

    # Run init command with mock responses
    mock_responses = {
        0: get_init_response(num_items=1),
        1: get_tech_stack_response(),
        2: get_architecture_response()
    }

    result = run_ralph_command(
        test_env,
        "--provider", "mock",
        "init",
        "Create a test project",
        mock_response=mock_responses
    )

    assert_exit_code(result, 0)

    # Verify .ralph/logs/init/ directory exists
    logs_dir = test_env.project_dir / ".ralph" / "logs" / "init"
    assert_directory_exists(logs_dir)

    # Verify .ralph/ is in .gitignore
    gitignore_path = test_env.project_dir / ".gitignore"
    if gitignore_path.exists():
        assert_file_contains(gitignore_path, ".ralph/")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
