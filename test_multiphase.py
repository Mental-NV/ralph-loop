#!/usr/bin/env python3
"""
Quick test to verify multi-phase execution logic.
"""

import json
import tempfile
from pathlib import Path
from ralph.orchestrator import BacklogOrchestrator

def test_mark_work_complete():
    """Test that mark_work_complete transitions to ready_for_validation."""
    backlog = {
        "version": "1.0.0",
        "items": [
            {
                "id": "test-item",
                "title": "Test Item",
                "status": "in_progress",
                "priority": "P1",
                "order": 1,
                "dependsOn": [],
                "deliverables": [],
                "exitCriteria": [],
                "validation": {"commands": []}
            }
        ]
    }

    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        backlog_path = project_dir / "backlog.json"

        # Write initial backlog
        backlog_path.write_text(json.dumps(backlog, indent=2))

        # Create orchestrator
        orch = BacklogOrchestrator(
            project_dir=project_dir,
            backlog_path=backlog_path,
            provider="qwen",
            dry_run=True
        )

        # Mark work complete
        orch.mark_work_complete(backlog, "test-item")

        # Verify status changed
        item = backlog["items"][0]
        assert item["status"] == "ready_for_validation", f"Expected ready_for_validation, got {item['status']}"
        assert "workCompletedAt" in item, "Missing workCompletedAt timestamp"

        print("✓ mark_work_complete works correctly")

def test_mark_item_done():
    """Test that mark_item_done marks all deliverables and criteria as done."""
    backlog = {
        "version": "1.0.0",
        "items": [
            {
                "id": "test-item",
                "title": "Test Item",
                "status": "ready_for_validation",
                "priority": "P1",
                "order": 1,
                "dependsOn": [],
                "deliverables": [
                    {"id": "d1", "text": "Deliverable 1", "done": False},
                    {"id": "d2", "text": "Deliverable 2", "done": False}
                ],
                "exitCriteria": [
                    {"id": "e1", "text": "Criterion 1", "done": False}
                ],
                "validation": {"commands": []}
            }
        ]
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        backlog_path = project_dir / "backlog.json"
        backlog_path.write_text(json.dumps(backlog, indent=2))

        orch = BacklogOrchestrator(
            project_dir=project_dir,
            backlog_path=backlog_path,
            provider="qwen",
            dry_run=True
        )

        # Mark item done
        orch.mark_item_done(backlog, "test-item")

        # Verify status and checkboxes
        item = backlog["items"][0]
        assert item["status"] == "done", f"Expected done, got {item['status']}"
        assert "completedAt" in item, "Missing completedAt timestamp"

        for deliverable in item["deliverables"]:
            assert deliverable["done"], f"Deliverable {deliverable['id']} not marked done"

        for criterion in item["exitCriteria"]:
            assert criterion["done"], f"Criterion {criterion['id']} not marked done"

        print("✓ mark_item_done works correctly")

def test_cleanup_command_detection():
    """Test that cleanup commands are correctly identified."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        backlog_path = project_dir / "backlog.json"
        backlog_path.write_text('{"version":"1.0.0","items":[]}')

        orch = BacklogOrchestrator(
            project_dir=project_dir,
            backlog_path=backlog_path,
            provider="qwen",
            dry_run=True
        )

        # Test cleanup commands
        assert orch.is_cleanup_command("pkill -f 'dotnet run'"), "pkill should be cleanup"
        assert orch.is_cleanup_command("killall node"), "killall should be cleanup"
        assert orch.is_cleanup_command("docker stop mycontainer"), "docker stop should be cleanup"
        assert orch.is_cleanup_command("rm -rf /tmp/test"), "rm -rf should be cleanup"

        # Test non-cleanup commands
        assert not orch.is_cleanup_command("dotnet test"), "dotnet test should not be cleanup"
        assert not orch.is_cleanup_command("npm test"), "npm test should not be cleanup"
        assert not orch.is_cleanup_command("pytest"), "pytest should not be cleanup"

        print("✓ cleanup command detection works correctly")

if __name__ == "__main__":
    test_mark_work_complete()
    test_mark_item_done()
    test_cleanup_command_detection()
    print("\n✓ All tests passed!")
