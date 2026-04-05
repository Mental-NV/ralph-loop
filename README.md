# Ralph Loop

Provider-agnostic orchestration loop for agent-driven development.

Ralph Loop is a standalone tool that executes backlog items autonomously using AI agents. It supports multiple providers (Qwen, Claude Code, Codex) and orchestrates milestone-based development workflows.

## Features

- **Backlog initialization**: Generate backlog from natural language prompts using AI
- **Multi-provider support**: Qwen (local), Claude Code (CLI), Codex (API)
- **JSON-driven orchestration**: Backlog items defined in `docs/backlog.json`
- **Automatic validation**: Schema validation and semantic checks before execution
- **Progress rendering**: Real-time progress visualization for supported providers
- **Lock-based concurrency control**: Prevents multiple instances from running simultaneously
- **Git integration**: Automatic commit and optional push after each milestone
- **Dry-run mode**: Preview execution without making changes
- **Resilient execution**: Multi-phase execution with graceful cleanup handling
- **Manual overrides**: Commands to manually manage stuck items

## Installation

### Using pipx (recommended)

```bash
pipx install ~/projects/ralph-loop
```

### Using pip

```bash
pip install ~/projects/ralph-loop
```

### Development installation

```bash
git clone <repo-url>
cd ralph-loop
pipx install -e .
```

## Usage

### Quick Start: Initialize a new project

The fastest way to get started is to initialize a backlog from a natural language prompt:

```bash
cd ~/projects/my-new-project
git init
ralph --init "Build a web scraper in Python that extracts article titles from news sites"
```

This will:
1. Invoke an AI agent to generate a comprehensive roadmap
2. Create `docs/backlog.json` with structured milestones
3. Validate the generated backlog
4. Display a summary of milestones

Then run Ralph Loop to execute the backlog:

```bash
ralph
```

### Initialize with different providers

```bash
# Use Claude Code for roadmap generation
ralph --init "Build a REST API with FastAPI" --provider claude

# Use Codex
ralph --init "Create a CLI tool for file management" --provider codex

# Preview without creating files
ralph --init "Build a todo app" --dry-run
```

### Basic usage

Run Ralph Loop in a project directory with `docs/backlog.json`:

```bash
cd ~/projects/your-project
ralph
```

### Specify project directory

Run Ralph Loop against a specific project from anywhere:

```bash
ralph --project ~/projects/your-project
```

### Command-line options

```bash
# Initialize backlog from prompt
ralph --init "Project description"

# Validate backlog without executing
ralph --validate-only

# Show next item to be executed
ralph --show-next

# List available providers
ralph --list-providers

# Use specific provider (default: qwen)
ralph --provider claude
ralph --provider codex

# Dry-run mode (show what would be executed)
ralph --dry-run

# Limit iterations
ralph --max-iterations 5

# Auto-push commits to remote
ralph --auto-push

# Override backlog location
ralph --backlog /path/to/custom-backlog.json

# Manual override commands (for stuck items)
ralph --mark-complete ITEM-ID      # Mark item as done (bypasses validation)
ralph --mark-ready ITEM-ID         # Mark item as ready for validation
ralph --reset-item ITEM-ID         # Reset item back to todo status
```

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
ralph --mark-ready ITEM-ID

# Item stuck in ready_for_validation, but work is actually done
ralph --mark-complete ITEM-ID

# Need to re-run an item from scratch
ralph --reset-item ITEM-ID
```

## Git Integration

Ralph Loop automatically commits changes after each successful iteration.

### Automatic Commits

After each item completes validation:
1. All file changes are staged (`git add -A`)
2. A structured commit is created with:
   - Item ID and title
   - List of deliverables (with completion status)
   - List of exit criteria (with completion status)

Example commit message:
```
[implement-api-endpoints] Implement API Endpoints

Deliverables:
  ✓ Create API controllers
  ✓ Add unit tests
  ✓ Add integration tests

Exit criteria:
  ✓ All tests pass
  ✓ API responds correctly
```

### Automatic Push

Use `--auto-push` to automatically push commits to remote:

```bash
ralph --auto-push
```

This will:
1. Commit changes after each iteration
2. Push commits to remote immediately

Without `--auto-push`, commits are created locally but not pushed.

### Requirements

- Git repository must be initialized
- Git user must be configured (`git config user.name` and `git config user.email`)
- For `--auto-push`: remote must be configured and accessible

## Project Requirements

Ralph Loop expects the following structure in target projects:

```
your-project/
├── docs/
│   └── backlog.json          # Required: backlog definition
├── .git/                     # Required: git repository
└── .ralph-loop.lock          # Created automatically during execution
```

### Backlog format

The `docs/backlog.json` file defines milestones and their execution order:

```json
{
  "items": [
    {
      "id": "ITEM-1",
      "title": "Implement feature X",
      "description": "Detailed description of the work",
      "status": "todo",
      "order": 1,
      "dependsOn": [],
      "deliverables": [
        {
          "id": "deliverable-1",
          "description": "Create X.cs",
          "done": false
        }
      ],
      "exitCriteria": [
        {
          "id": "exit-1",
          "description": "Tests pass",
          "done": false
        }
      ]
    }
  ]
}
```

**Status values:**
- `todo` - Not started
- `in_progress` - Currently being executed
- `ready_for_validation` - Implementation complete, awaiting validation
- `done` - Completed and validated
- `blocked` - Blocked by external dependency
- `deferred` - Postponed
- `cancelled` - Cancelled

**Validation rules:**
- All item IDs must be unique
- All order values must be unique
- Dependencies must reference existing items
- At most one item can be active (`in_progress` or `ready_for_validation`)
- Active items must have all dependencies completed
- Done items must have all deliverables and exit criteria marked done
- Blocked items must include `blockedReason`

## Providers

### Qwen (default)

Local Qwen model via Ollama. Requires Ollama to be installed and running.

```bash
ralph --provider qwen
```

**Requirements:**
- Ollama installed and running
- Qwen model pulled: `ollama pull qwen2.5-coder:32b`

**Features:**
- Real-time progress rendering with qwen_renderer
- Streaming output with syntax highlighting
- Local execution (no API costs)

### Claude Code

Claude Code CLI tool. Requires Claude Code to be installed.

```bash
ralph --provider claude
```

**Requirements:**
- Claude Code CLI installed
- Valid Anthropic API key or OAuth token

**Features:**
- Best-effort progress rendering
- High-quality code generation
- Advanced reasoning capabilities

### Codex

OpenAI Codex API. Requires OpenAI API key.

```bash
ralph --provider codex
```

**Requirements:**
- Valid OpenAI API key in `OPENAI_API_KEY` environment variable

**Features:**
- Best-effort progress rendering
- Fast execution
- API-based (no local setup)

## Execution Flow

1. **Validation**: Validate `docs/backlog.json` against bundled schema
2. **Selection**: Find next `todo` item with all dependencies completed
3. **Execution**: Run provider command with item context
4. **Validation**: Check deliverables and exit criteria
5. **Commit**: Create git commit with changes
6. **Push** (optional): Push commit to remote if `--auto-push` enabled
7. **Repeat**: Continue to next item until backlog is complete

## Progress Rendering

Ralph Loop provides real-time progress visualization for supported providers:

- **Qwen**: Full progress rendering with syntax highlighting, streaming output, and status updates
- **Claude Code**: Best-effort rendering (depends on Claude Code output format)
- **Codex**: Best-effort rendering (depends on API response format)

Progress logs are stored in `<project>/logs/ralph/qwen-stream/` for debugging.

## Lock File

Ralph Loop creates `.ralph-loop.lock` in the project directory to prevent concurrent execution. If the lock file exists and the process is still running, Ralph Loop will exit with an error.

To manually remove a stale lock:

```bash
rm .ralph-loop.lock
```

## Validation

Ralph Loop includes a comprehensive validator that checks:

- **Schema validation**: JSON structure matches `backlog.schema.json`
- **Unique IDs**: All item IDs are unique
- **Unique orders**: All order values are unique
- **Valid dependencies**: All dependency references exist
- **No cycles**: Dependency graph is acyclic
- **Active item limit**: At most one item is active
- **Dependency readiness**: Active items have completed dependencies
- **Done item completeness**: Done items have all deliverables/criteria marked done
- **Blocked item reasons**: Blocked items include `blockedReason`
- **Valid status transitions**: Status values are valid

Run validation without executing:

```bash
ralph --validate-only
```

## Backlog Initialization with `--init`

The `--init` command generates a comprehensive project roadmap from a natural language prompt. This feature uses AI agents to break down your project into structured milestones suitable for autonomous implementation.

### How it works

1. You provide a project description
2. Ralph Loop invokes an AI agent (Qwen, Claude Code, or Codex)
3. The agent generates a roadmap with milestones, deliverables, and exit criteria
4. Ralph Loop transforms the response into a valid `backlog.json`
5. The backlog is validated and saved to `docs/backlog.json`

### Usage examples

```bash
# Web application
ralph --init "Build a blog platform with user authentication and markdown support"

# CLI tool
ralph --init "Create a command-line tool for managing TODO lists with SQLite storage"

# Library
ralph --init "Develop a Python library for parsing and validating JSON schemas"

# Data pipeline
ralph --init "Build an ETL pipeline that extracts data from CSV files and loads into PostgreSQL"

# With specific provider
ralph --init "Build a REST API with FastAPI" --provider claude

# Preview without creating files
ralph --init "Build a calculator app" --dry-run
```

### Tips for effective prompts

**Be specific about technology:**
- ✓ "Build a web scraper in Python using BeautifulSoup"
- ✗ "Build a web scraper"

**Mention key requirements:**
- ✓ "Create a REST API with authentication, rate limiting, and PostgreSQL"
- ✗ "Create an API"

**Include testing requirements:**
- ✓ "Build a CLI tool with unit tests and integration tests"
- ✗ "Build a CLI tool"

**Specify the scope:**
- ✓ "Build a minimal viable product for a todo app with basic CRUD operations"
- ✗ "Build a todo app with every feature imaginable"

### What gets generated

Each milestone includes:
- **Title**: Clear, actionable milestone name
- **Why**: Rationale for the milestone
- **Priority**: P0 (foundation), P1 (core), P2 (enhancements), P3 (polish)
- **Dependencies**: Which milestones must complete first
- **Deliverables**: Concrete outputs (files, functions, tests)
- **Exit Criteria**: How to verify completion
- **Risks**: Potential challenges and mitigations
- **Validation Commands**: Shell commands to verify the milestone

### Customizing generated backlogs

After generation, you can manually edit `docs/backlog.json` to:
- Adjust priorities
- Add or remove milestones
- Modify deliverables and exit criteria
- Add validation commands
- Specify dependencies

Then validate your changes:

```bash
ralph --validate-only
```

### Debug output

All initialization attempts save debug information to `logs/ralph/init/`:
- `prompt-*.txt`: The prompt sent to the agent
- `response-*.txt`: The raw agent response
- `failed-parse-*.txt`: Responses that failed to parse (if any)

This helps troubleshoot issues with agent responses or parsing.

## Troubleshooting

### "Backlog not found"

Ensure `docs/backlog.json` exists in the project directory:

```bash
ls docs/backlog.json
```

Or use `--init` to generate one:

```bash
ralph --init "Your project description"
```

Or specify a custom location:

```bash
ralph --backlog /path/to/backlog.json
```

### "Lock file exists"

Another Ralph Loop instance is running, or a previous instance crashed. Check if the process is still running:

```bash
ps aux | grep ralph
```

If not, remove the stale lock:

```bash
rm .ralph-loop.lock
```

### "Provider not found"

Ensure the provider is installed and available:

- **Qwen**: `ollama list` should show qwen2.5-coder:32b
- **Claude Code**: `claude --version` should work
- **Codex**: `echo $OPENAI_API_KEY` should show your API key

### "Validation failed"

Run validation to see specific errors:

```bash
ralph --validate-only
```

Fix the reported issues in `docs/backlog.json` and try again.

## Development

### Running tests

```bash
pytest tests/
```

### Code structure

- `ralph/cli.py` - Main CLI entry point
- `ralph/orchestrator.py` - BacklogOrchestrator class
- `ralph/providers.py` - Provider abstraction layer
- `ralph/validator.py` - Backlog validation logic
- `ralph/schemas/backlog.schema.json` - Bundled JSON schema
- `ralph/renderers/qwen_renderer.py` - Qwen progress renderer
- `ralph/renderers/simple_renderer.py` - Simple progress renderer

### Adding a new provider

1. Add provider class to `ralph/providers.py`:

```python
class MyProvider(Provider):
    def build_command(self, item: Dict[str, Any], backlog_path: Path, project_dir: Path) -> List[str]:
        return ["my-tool", "execute", str(backlog_path)]
    
    def get_progress_renderer(self, project_dir: Path) -> Optional[List[str]]:
        return None  # or custom renderer command
```

2. Register provider in `PROVIDERS` dict:

```python
PROVIDERS = {
    "qwen": QwenProvider(),
    "claude": ClaudeCodeProvider(),
    "codex": CodexProvider(),
    "my-provider": MyProvider(),
}
```

3. Test the new provider:

```bash
ralph --provider my-provider --dry-run
```

## License

MIT

## Contributing

Contributions welcome! Please open an issue or pull request.
