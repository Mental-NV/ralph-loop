#!/usr/bin/env python3
"""
Simple test script to verify e2e testing infrastructure.
Run without pytest to validate the setup.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.helpers.test_environment import TestEnvironment
from tests.helpers.mock_provider import MockAgentProvider, get_init_response, get_analyze_response
from tests.helpers.assertions import (
    assert_file_exists,
    assert_backlog_valid,
    assert_directory_exists
)


def test_test_environment():
    """Test that TestEnvironment creates isolated git repos."""
    print("Testing TestEnvironment...")

    with TestEnvironment() as env:
        # Verify project directory exists
        assert env.project_dir.exists()
        assert env.project_dir.is_dir()

        # Verify git is initialized
        assert (env.project_dir / ".git").exists()

        # Verify initial commit exists
        commits = env.get_git_log()
        assert len(commits) > 0
        assert "Initial commit" in commits[0]

        # Verify working tree is clean
        assert env.is_working_tree_clean()

        # Test file creation
        test_file = env.create_file("test.txt", "Hello, world!")
        assert test_file.exists()
        assert test_file.read_text() == "Hello, world!"

        # Test backlog creation
        backlog_data = {
            "version": "1.0.0",
            "items": []
        }
        backlog_path = env.create_backlog(backlog_data)
        assert backlog_path.exists()

        with open(backlog_path) as f:
            loaded = json.load(f)
        assert loaded == backlog_data

    print("✓ TestEnvironment works correctly")


def test_mock_provider():
    """Test that MockAgentProvider returns expected responses."""
    print("\nTesting MockAgentProvider...")

    # Test with single response
    response = {"test": "data"}
    provider = MockAgentProvider(response_data=response)

    assert provider.get_name() == "mock"
    assert provider.is_available() == True
    assert provider.supports_rich_progress() == False
    assert provider.get_progress_renderer(Path(".")) is None

    is_auth, msg = provider.check_authentication()
    assert is_auth == True

    # Test command building
    cmd = provider.build_command("test prompt", Path("."), yolo=False)
    assert isinstance(cmd, list)
    assert len(cmd) > 0

    print("✓ MockAgentProvider works correctly")


def test_response_templates():
    """Test that response templates generate valid data."""
    print("\nTesting response templates...")

    # Test init response
    init_resp = get_init_response(num_items=3)
    assert "items" in init_resp
    assert len(init_resp["items"]) == 3
    assert all('title' in item for item in init_resp['items'])

    # Test analyze response
    analyze_resp = get_analyze_response(score=85, ready=True)
    assert analyze_resp["version"] == "1.0.0"
    assert "metrics" in analyze_resp
    assert analyze_resp["overall_score"] == 85
    assert analyze_resp["ready_for_auto"] == True

    print("✓ Response templates work correctly")


def test_assertions():
    """Test that assertion helpers work correctly."""
    print("\nTesting assertion helpers...")

    with TestEnvironment() as env:
        # Test file existence assertions
        test_file = env.create_file("exists.txt", "content")

        try:
            assert_file_exists(test_file)
            print("  ✓ assert_file_exists works")
        except AssertionError:
            print("  ✗ assert_file_exists failed")
            raise

        # Test directory existence
        test_dir = env.project_dir / "testdir"
        test_dir.mkdir()

        try:
            assert_directory_exists(test_dir)
            print("  ✓ assert_directory_exists works")
        except AssertionError:
            print("  ✗ assert_directory_exists failed")
            raise

        # Test backlog validation
        backlog_data = {
            "version": "1.0.0",
            "items": [
                {
                    "id": "test-item",
                    "title": "Test Item",
                    "status": "todo",
                    "priority": "P1",
                    "order": 0,
                    "dependsOn": [],
                    "deliverables": [],
                    "exitCriteria": [],
                    "risks": [],
                    "validation": {"commands": []}
                }
            ]
        }
        backlog_path = env.create_backlog(backlog_data)

        try:
            assert_backlog_valid(backlog_path)
            print("  ✓ assert_backlog_valid works")
        except AssertionError as e:
            print(f"  ✗ assert_backlog_valid failed: {e}")
            raise

    print("✓ Assertion helpers work correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("E2E Testing Infrastructure Validation")
    print("=" * 60)

    try:
        test_test_environment()
        test_mock_provider()
        test_response_templates()
        test_assertions()

        print("\n" + "=" * 60)
        print("✓ All infrastructure tests passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ Test failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
