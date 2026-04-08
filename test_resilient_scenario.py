#!/usr/bin/env python3
"""
Test scenario: Simulate the iteration 5 failure case where cleanup fails.

This demonstrates that with the new multi-phase execution:
1. Work completes successfully
2. Item transitions to ready_for_validation
3. Validation runs with graceful cleanup handling
4. Cleanup failure doesn't block completion
5. Item is marked as done
"""

import json
import tempfile
from pathlib import Path
from ralph.orchestrator import BacklogOrchestrator

def test_cleanup_failure_scenario():
    """
    Simulate the exact scenario from iteration 5:
    - Work phase completes (API tests pass)
    - Validation has critical tests + cleanup command
    - Cleanup fails (pkill returns non-zero)
    - Item should still be marked as done
    """
    backlog = {
        "version": "1.0.0",
        "items": [
            {
                "id": "implement-api-endpoints",
                "title": "Implement API Endpoints",
                "status": "ready_for_validation",
                "priority": "P1",
                "order": 1,
                "dependsOn": [],
                "workCompletedAt": "2026-04-05T19:00:00Z",
                "deliverables": [
                    {"id": "d1", "text": "Create API controllers", "done": False},
                    {"id": "d2", "text": "Add unit tests", "done": False}
                ],
                "exitCriteria": [
                    {"id": "e1", "text": "All tests pass", "done": False},
                    {"id": "e2", "text": "API responds correctly", "done": False}
                ],
                "validation": {
                    "commands": [
                        "echo 'Running tests...'",  # Critical validation (will pass)
                        "echo 'Tests passed: 41/41'",  # Critical validation (will pass)
                        "pkill -f 'dotnet run'"  # Cleanup (will fail - no process running)
                    ]
                }
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
            dry_run=False  # Run for real to test actual command execution
        )

        print("="*80)
        print("Scenario: Cleanup failure during validation")
        print("="*80)
        print("\nInitial state:")
        print(f"  Status: {backlog['items'][0]['status']}")
        print(f"  Work completed at: {backlog['items'][0]['workCompletedAt']}")
        print("\nValidation commands:")
        for i, cmd in enumerate(backlog['items'][0]['validation']['commands'], 1):
            cmd_type = "cleanup" if orch.is_cleanup_command(cmd) else "critical"
            print(f"  [{i}] ({cmd_type}) {cmd}")

        print("\n" + "="*80)
        print("Running validation phase...")
        print("="*80 + "\n")

        # Run validation
        result = orch.run_validation_commands(backlog['items'][0])

        print("\n" + "="*80)
        print("Validation result:")
        print("="*80)
        print(f"  Passed: {result}")

        if result:
            # Mark item done
            orch.mark_item_done(backlog, "implement-api-endpoints")
            item = backlog['items'][0]

            print(f"  Status: {item['status']}")
            print(f"  Completed at: {item.get('completedAt', 'N/A')}")
            print(f"  Deliverables done: {all(d['done'] for d in item['deliverables'])}")
            print(f"  Exit criteria done: {all(e['done'] for e in item['exitCriteria'])}")

            # Verify expectations
            assert item['status'] == 'done', "Item should be marked as done"
            assert 'completedAt' in item, "Should have completedAt timestamp"
            assert all(d['done'] for d in item['deliverables']), "All deliverables should be done"
            assert all(e['done'] for e in item['exitCriteria']), "All exit criteria should be done"

            print("\n✓ SUCCESS: Item completed despite cleanup failure!")
            print("  This demonstrates resilient execution:")
            print("  - Critical validation passed (tests)")
            print("  - Cleanup failed (pkill) but was non-blocking")
            print("  - Item marked as done with all checkboxes")
        else:
            print("\n✗ FAILED: Validation failed (should not happen)")
            assert False, "Validation should have passed"

if __name__ == "__main__":
    success = test_cleanup_failure_scenario()
    exit(0 if success else 1)
