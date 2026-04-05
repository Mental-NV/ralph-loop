#!/usr/bin/env python3
"""
Test git commit functionality.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from ralph.orchestrator import BacklogOrchestrator

def test_git_commit():
    """Test that git_commit creates commits with proper messages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, capture_output=True)

        # Create backlog
        backlog_path = project_dir / "docs" / "backlog.json"
        backlog_path.parent.mkdir(parents=True)
        backlog = {
            "version": "1.0.0",
            "items": [{
                "id": "test-item",
                "title": "Test Item",
                "status": "done",
                "priority": "P1",
                "order": 1,
                "dependsOn": [],
                "deliverables": [
                    {"id": "d1", "text": "Create test.txt", "done": True},
                    {"id": "d2", "text": "Add documentation", "done": True}
                ],
                "exitCriteria": [
                    {"id": "e1", "text": "File exists", "done": True},
                    {"id": "e2", "text": "Tests pass", "done": True}
                ],
                "validation": {"commands": []}
            }]
        }
        backlog_path.write_text(json.dumps(backlog, indent=2))

        # Create a test file to commit
        test_file = project_dir / "test.txt"
        test_file.write_text("Hello, world!")

        # Create orchestrator
        orch = BacklogOrchestrator(
            project_dir=project_dir,
            backlog_path=backlog_path,
            provider="qwen",
            dry_run=False
        )

        # Build commit message
        item = backlog["items"][0]
        commit_message = orch.build_commit_message(item)

        print("Generated commit message:")
        print("=" * 80)
        print(commit_message)
        print("=" * 80)

        # Verify message format
        assert "[test-item]" in commit_message, "Missing item ID"
        assert "Test Item" in commit_message, "Missing item title"
        assert "Deliverables:" in commit_message, "Missing deliverables section"
        assert "✓ Create test.txt" in commit_message, "Missing deliverable 1"
        assert "✓ Add documentation" in commit_message, "Missing deliverable 2"
        assert "Exit criteria:" in commit_message, "Missing exit criteria section"
        assert "✓ File exists" in commit_message, "Missing criterion 1"
        assert "✓ Tests pass" in commit_message, "Missing criterion 2"

        print("\n✓ Commit message format is correct")

        # Create commit
        success = orch.git_commit(commit_message)
        assert success, "git_commit should succeed"

        print("✓ Commit created successfully")

        # Verify commit was created
        result = subprocess.run(
            ["git", "log", "--format=%B", "-n", "1"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )

        actual_message = result.stdout.strip()
        print("\nActual commit message from git log:")
        print("=" * 80)
        print(actual_message)
        print("=" * 80)

        assert "[test-item]" in actual_message, "Commit message not in git log"
        assert "Test Item" in actual_message, "Item title not in git log"

        print("\n✓ Commit message verified in git log")

        # Verify files were committed
        result = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=project_dir,
            capture_output=True,
            text=True
        )

        committed_files = result.stdout.strip().split('\n')
        print(f"\nCommitted files: {committed_files}")

        assert "test.txt" in committed_files, "test.txt should be committed"
        assert "docs/backlog.json" in committed_files, "backlog.json should be committed"

        print("✓ All files committed correctly")

def test_git_commit_dry_run():
    """Test that dry-run mode doesn't create actual commits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_dir, capture_output=True)

        # Create backlog
        backlog_path = project_dir / "backlog.json"
        backlog_path.write_text('{"version":"1.0.0","items":[]}')

        # Create orchestrator in dry-run mode
        orch = BacklogOrchestrator(
            project_dir=project_dir,
            backlog_path=backlog_path,
            provider="qwen",
            dry_run=True
        )

        # Try to commit
        success = orch.git_commit("Test commit")
        assert success, "Dry-run should return success"

        # Verify no commit was created
        result = subprocess.run(
            ["git", "log"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )

        assert result.returncode != 0 or "Test commit" not in result.stdout, \
            "Dry-run should not create actual commits"

        print("✓ Dry-run mode works correctly")

if __name__ == "__main__":
    print("Testing git commit functionality...\n")
    test_git_commit()
    print("\n" + "=" * 80)
    test_git_commit_dry_run()
    print("\n✓ All git commit tests passed!")
