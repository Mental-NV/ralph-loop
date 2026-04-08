#!/usr/bin/env python3
"""
Pytest fixtures for Ralph Loop e2e tests.
"""

import json
import pytest
import subprocess
import sys
from pathlib import Path

from tests.helpers.test_environment import TestEnvironment
from tests.helpers.mock_provider import MockAgentProvider, get_init_response, get_analyze_response


@pytest.fixture
def test_env():
    """Provide an isolated test environment with git repository."""
    with TestEnvironment() as env:
        yield env


@pytest.fixture
def test_env_no_git():
    """Provide an isolated test environment without git repository."""
    with TestEnvironment(init_git=False) as env:
        yield env


@pytest.fixture
def mock_provider():
    """Provide a mock AI provider for testing."""
    return MockAgentProvider()


@pytest.fixture
def sample_backlog():
    """Provide a valid sample backlog for testing."""
    return {
        "version": "1.0.0",
        "items": [
            {
                "id": "setup-project",
                "title": "Setup Project Structure",
                "status": "todo",
                "priority": "P0",
                "order": 0,
                "why": "Foundation for development",
                "dependsOn": [],
                "deliverables": [
                    {"id": "d1", "text": "Create directory structure", "done": False},
                    {"id": "d2", "text": "Setup configuration", "done": False}
                ],
                "exitCriteria": [
                    {"id": "e1", "text": "Directories exist", "done": False},
                    {"id": "e2", "text": "Config is valid", "done": False}
                ],
                "risks": ["None identified"],
                "validation": {
                    "commands": ["echo 'validation passed'"]
                }
            },
            {
                "id": "add-tests",
                "title": "Add Test Suite",
                "status": "todo",
                "priority": "P1",
                "order": 1,
                "why": "Ensure code quality",
                "dependsOn": ["setup-project"],
                "deliverables": [
                    {"id": "d1", "text": "Create test files", "done": False}
                ],
                "exitCriteria": [
                    {"id": "e1", "text": "Tests pass", "done": False}
                ],
                "risks": [],
                "validation": {
                    "commands": ["echo 'tests passed'"]
                }
            }
        ]
    }


@pytest.fixture
def cli_runner(test_env):
    """
    Provide a helper function for running CLI commands.

    Returns a function that runs ralph commands in the test environment.
    """
    def run_command(*args, check=False, capture_output=True):
        """
        Run a ralph CLI command.

        Args:
            *args: Command arguments (e.g., 'init', 'run', etc.)
            check: Whether to raise exception on non-zero exit
            capture_output: Whether to capture stdout/stderr

        Returns:
            subprocess.CompletedProcess
        """
        # Try using 'ralph' command first (if installed), otherwise use python -m
        import shutil
        if shutil.which('ralph'):
            cmd = ["ralph"] + list(args)
        else:
            # Add project root to PYTHONPATH so ralph module can be found
            import os
            env = os.environ.copy()
            project_root = Path(__file__).parent.parent.parent
            env['PYTHONPATH'] = str(project_root) + os.pathsep + env.get('PYTHONPATH', '')

            cmd = [sys.executable, "-m", "ralph.cli"] + list(args)
            result = subprocess.run(
                cmd,
                cwd=test_env.project_dir,
                capture_output=capture_output,
                text=True,
                check=check,
                env=env
            )
            return result

        result = subprocess.run(
            cmd,
            cwd=test_env.project_dir,
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result

    return run_command


@pytest.fixture
def sample_backlog_with_done_items(sample_backlog):
    """Provide a backlog with some completed items."""
    backlog = sample_backlog.copy()
    backlog['items'][0]['status'] = 'done'
    backlog['items'][0]['completedAt'] = '2026-04-08T00:00:00Z'
    for deliverable in backlog['items'][0]['deliverables']:
        deliverable['done'] = True
    for criterion in backlog['items'][0]['exitCriteria']:
        criterion['done'] = True
    return backlog


@pytest.fixture
def mock_init_provider():
    """Provide a mock provider configured for init command."""
    return MockAgentProvider(response_data=get_init_response(num_items=3))


@pytest.fixture
def mock_analyze_provider():
    """Provide a mock provider configured for analyze command."""
    return MockAgentProvider(response_data=get_analyze_response(score=85, ready=True))
