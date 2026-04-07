# Ralph Loop - Advanced Guide

This guide covers advanced operational topics for Ralph Loop, including resilient execution, error handling, and system diagnostics.

## Table of Contents

- [Resilient Execution](#resilient-execution)
- [Agent Cancellation Handling](#agent-cancellation-handling)
- [Health Checks](#health-checks)

---

## Resilient Execution

Ralph Loop uses multi-phase execution to handle transient failures gracefully:

### Execution Phases

1. **Work Phase** (`todo` → `in_progress`)
   - Agent implements the milestone
   - Creates code, tests, documentation
   - On success: transitions to `ready_for_validation`

2. **Validation Phase** (`ready_for_validation` → `done`)
   - Runs validation commands
   - Separates critical validation from cleanup
   - On success: marks item as `done`

### Graceful Cleanup Handling

Validation commands are classified as either **critical** or **cleanup**:

- **Critical commands**: Must pass for validation to succeed (e.g., `dotnet test`, `pytest`)
- **Cleanup commands**: Best-effort, failures don't block completion (e.g., `pkill`, `docker stop`)

Cleanup commands are automatically detected by pattern matching:
- `pkill`, `killall`, `kill`
- `docker stop`, `docker rm`
- `npm stop`, `dotnet stop`
- `rm -rf`

Example validation with cleanup:
```json
{
  "validation": {
    "commands": [
      "dotnet test",              // Critical - must pass
      "curl http://localhost:5000", // Critical - must pass
      "pkill -f 'dotnet run'"     // Cleanup - failure is non-blocking
    ]
  }
}
```

If the cleanup command fails (e.g., process already stopped), the item is still marked as done.

### Manual Recovery

If an item gets stuck, use manual override commands:

```bash
# Item stuck in in_progress after agent crash
ralph item mark-ready ITEM-ID

# Item stuck in ready_for_validation, but work is actually done
ralph item mark-complete ITEM-ID

# Need to re-run an item from scratch
ralph item reset ITEM-ID
```

---

## Agent Cancellation Handling

Ralph Loop automatically detects when an agent (Qwen, Claude Code, Codex) is cancelled by the user and handles it gracefully:

### Automatic Detection

- When an agent is cancelled during work phase, Ralph Loop detects the cancellation
- The item remains in `in_progress` status (not marked as failed)
- You can retry by running Ralph Loop again, or use `ralph reset-item` to start over

### Continue on Error

- Use `--continue-on-error` to make Ralph Loop continue even when work phase fails
- Useful for handling transient failures or when you want to skip problematic items
- Without this flag, Ralph Loop stops on work phase failures (default behavior)

```bash
# Continue even if work phase fails
ralph run --continue-on-error
```

### Example Scenario

1. Agent starts working on an item
2. You cancel the agent (Ctrl+C or tool cancellation)
3. Ralph Loop detects the cancellation and logs it
4. Item stays in `in_progress` status
5. Next run of Ralph Loop will retry the same item

---

## Health Checks

Use `ralph doctor` to verify your environment is correctly configured:

```bash
ralph doctor
```

### What Gets Checked

- **System dependencies**: Python, Git, jsonschema
- **Provider installation**: Qwen, Claude Code, Codex
- **Provider authentication**: Authentication status for each provider
- **Project setup**: When `--project` specified, validates project structure

### Check Results

Each check shows:
- ✓ Pass - Check succeeded
- ✗ Fail - Check failed (with suggestion)
- ⚠ Warning - Non-critical issue
- ○ Skip - Check not applicable

Exit code 0 if all critical checks pass, 1 if any fail.

### Example Output

```
Ralph Loop Health Check
=======================

System Dependencies
  ✓ Python version: Python 3.12.3 (>= 3.9 required)
  ✓ Git installed: Git 2.43.0
  ✓ Git user.name: Configured
  ✓ Git user.email: Configured
  ✓ jsonschema library: Installed

Provider Installation
  ✓ Qwen CLI: Installed
  ✓ Claude Code CLI: Installed
  ✗ Codex CLI: Not found
    → Install Codex CLI

Provider Authentication
  ✓ Qwen authentication: Authenticated
  ✓ Claude Code authentication: Authenticated
  ○ Codex authentication: Skipped (not installed)

Summary
-------
1 error(s) found.

Critical issues:
  - Codex CLI: Not found
```

### Project-Specific Checks

Run with `--project` to validate a specific project:

```bash
ralph --project ~/projects/your-project doctor
```

This will additionally check:
- Git repository initialization
- Backlog file existence and validity
- Project directory structure
