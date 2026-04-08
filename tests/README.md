# E2E Testing for Ralph Loop

This directory contains end-to-end tests for the Ralph Loop CLI application.

## Overview

The testing strategy uses a **hybrid approach**:

1. **E2E tests with mock providers** (fast, deterministic, CI/CD ready)
2. **Integration tests with real providers** (manual, validates actual AI integration)

## Quick Start

```bash
# Run infrastructure validation
python tests/test_infrastructure.py

# Run all tests (requires pytest)
pytest

# Run only e2e tests
pytest tests/e2e/

# Run only unit tests
pytest tests/test_init.py

# Run with coverage
pytest --cov=ralph --cov-report=html
```

## Directory Structure

```
tests/
├── __init__.py
├── test_init.py                    # Unit tests (26 tests)
├── test_infrastructure.py          # Infrastructure validation
├── helpers/
│   ├── __init__.py
│   ├── mock_provider.py            # Mock AI provider
│   ├── test_environment.py         # Test environment manager
│   └── assertions.py               # Common assertions
├── e2e/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   ├── test_e2e_init.py           # Init command tests (7)
│   ├── test_e2e_analyze.py        # Analyze command tests (4) [TODO]
│   ├── test_e2e_refine.py         # Refine command tests (4) [TODO]
│   ├── test_e2e_improve.py        # Improve command tests (4) [TODO]
│   ├── test_e2e_run.py            # Run command tests (8) [TODO]
│   └── test_e2e_workflows.py      # Full workflow tests (2) [TODO]
└── integration/
    ├── __init__.py
    └── test_integration_smoke.py   # Real provider tests (3) [TODO]
```

## Test Infrastructure

### TestEnvironment

Creates isolated test environments with:
- Temporary directory
- Initialized git repository
- Configured git user
- Initial commit (for clean working tree checks)
- Automatic cleanup

```python
from tests.helpers.test_environment import TestEnvironment

with TestEnvironment() as env:
    # env.project_dir is a temporary directory with git repo
    env.create_file("test.txt", "content")
    env.create_backlog({"version": "1.0.0", "items": []})
    env.commit_all("Test commit")
```

### MockAgentProvider

Mock AI provider that returns pre-defined responses:

```python
from tests.helpers.mock_provider import MockAgentProvider, get_init_response

# Create mock provider with init response
provider = MockAgentProvider(response_data=get_init_response(num_items=3))

# Use in tests via monkeypatch
monkeypatch.setattr("ralph.initializer.get_provider", lambda name: provider)
```

### Assertion Helpers

Common assertions for testing:

```python
from tests.helpers.assertions import (
    assert_file_exists,
    assert_backlog_valid,
    assert_git_commit_exists,
    assert_exit_code
)

assert_file_exists(backlog_path)
assert_backlog_valid(backlog_path)
assert_git_commit_exists(project_dir, r"\[test-item\]")
assert_exit_code(result, 0)
```

## Writing Tests

### E2E Test Template

```python
def test_command_behavior(test_env, monkeypatch):
    """Test that command does something."""
    # Setup mock provider
    from tests.helpers.mock_provider import MockAgentProvider
    mock_provider = MockAgentProvider(response_data={...})
    
    monkeypatch.setattr("ralph.module.get_provider", lambda name: mock_provider)
    
    # Run command
    result = subprocess.run(
        [sys.executable, "-m", "ralph.cli", "command", "args"],
        cwd=test_env.project_dir,
        capture_output=True,
        text=True
    )
    
    # Verify results
    assert_exit_code(result, 0)
    assert_file_exists(test_env.project_dir / "expected_file.json")
```

## Mock Provider Strategy

The mock provider intercepts AI calls and returns pre-defined responses:

```python
# Instead of: qwen --prompt "Generate backlog"
# Mock returns: {"items": [...], "version": "1.0.0"}
```

### Response Templates

Pre-defined templates for common scenarios:

- `get_init_response(num_items)` - Init command response
- `get_analyze_response(score, ready)` - Analyze command response
- `get_refine_response(base_backlog, modifications)` - Refine command response

## CI/CD Integration

Tests run automatically on every push via GitHub Actions:

- Tests Python 3.9, 3.10, 3.11, 3.12
- Runs unit + e2e tests (not integration)
- Generates coverage reports
- Completes in < 2 minutes

## Integration Tests

Integration tests with real AI providers are marked with `@pytest.mark.integration` and skipped by default:

```bash
# Run integration tests (requires provider authentication)
pytest tests/integration/ -m integration
```

These tests:
- Use real AI providers (qwen, claude, codex)
- Require authentication
- Are slower and more expensive
- Should be run manually before releases

## Test Coverage

Current status:
- ✅ Infrastructure: Complete (test_environment, mock_provider, assertions)
- ✅ Unit tests: 26 tests (existing)
- ✅ E2E init tests: 7 tests
- 🚧 E2E analyze tests: TODO
- 🚧 E2E refine tests: TODO
- 🚧 E2E improve tests: TODO
- 🚧 E2E run tests: TODO
- 🚧 Workflow tests: TODO
- 🚧 Integration tests: TODO

Target: 35+ e2e tests covering all commands

## Troubleshooting

### Import errors

If you get `ModuleNotFoundError: No module named 'tests'`, run from project root:

```bash
cd /path/to/ralph-loop
python tests/test_infrastructure.py
```

### Pytest not found

Install dev dependencies:

```bash
pip install -e ".[dev]"
```

### Git errors in tests

Tests create isolated git repos. If you see git errors, ensure git is installed and configured.

## Next Steps

1. Complete remaining e2e test files (analyze, refine, improve, run, workflows)
2. Add integration tests for real providers
3. Increase test coverage to 90%+
4. Add performance benchmarks
5. Add snapshot testing for generated files

## Contributing

When adding new tests:

1. Use `TestEnvironment` for isolation
2. Use `MockAgentProvider` for AI calls
3. Use assertion helpers for validation
4. Follow existing test patterns
5. Add docstrings explaining what is tested
6. Ensure tests are deterministic (no random data)

## Resources

- Plan: `/home/mental/.claude/plans/lexical-exploring-sparkle.md`
- Infrastructure validation: `tests/test_infrastructure.py`
- Example e2e test: `tests/e2e/test_e2e_init.py`
