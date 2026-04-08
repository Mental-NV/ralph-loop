# Ralph Loop

Provider-agnostic orchestration loop for agent-driven development.

Ralph Loop is a standalone tool that executes backlog items autonomously using AI agents. It supports multiple providers (Qwen, Claude Code, Codex) and orchestrates milestone-based development workflows.

## Features

- **Backlog initialization**: Generate high-level, feature-oriented backlog from natural language prompts using AI
- **Architecture document generation**: Automatically create `docs/ARCHITECTURE.md` with tech stack and best practices
- **Backlog analysis**: Evaluate backlog readiness for autonomous execution with 11-metric assessment
- **Multi-provider support**: Qwen (local), Claude Code (CLI), Codex (API)
- **JSON-driven orchestration**: Backlog items defined in `docs/backlog.json`
- **Automatic validation**: Schema validation and semantic checks before execution
- **Progress rendering**: Real-time progress visualization for supported providers
- **Lock-based concurrency control**: Prevents multiple instances from running simultaneously
- **Git integration**: Automatic commit and optional push after each milestone
- **Dry-run mode**: Preview execution without making changes
- **Resilient execution**: Multi-phase execution with graceful cleanup handling
- **Manual overrides**: Commands to manually manage stuck items
- **Backlog refinement**: Iteratively improve backlog using AI agent suggestions
- **Architecture refinement**: Refine architecture document with `ralph refine-architecture`

For advanced topics like resilient execution, error handling, and health checks, see the [Advanced Guide](docs/ADVANCED.md).

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
ralph init "Build a web scraper in Python that extracts article titles from news sites"
```

This will:
1. Detect or recommend appropriate tech stack for your project
2. Generate `docs/ARCHITECTURE.md` with tech stack, patterns, and best practices
3. Generate high-level, feature-oriented `docs/backlog.json` with structured milestones
4. Validate the generated backlog
5. Display a summary of milestones

Then run Ralph Loop to execute the backlog:

```bash
ralph run
# or simply:
ralph
```

### Initialize with different providers

```bash
# Use Claude Code for roadmap generation
ralph init "Build a REST API with FastAPI" --provider claude

# Use Codex
ralph init "Create a CLI tool for file management" --provider codex

# Preview without creating files
ralph init "Build a todo app" --dry-run
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
ralph init "Project description"

# Analyze backlog for automation readiness
ralph analyze

# Save analysis to file
ralph analyze --save-analysis

# Validate backlog without executing
ralph validate

# Show next item to be executed
ralph item show-next

# List available providers
ralph list-providers

# Use specific provider (default: qwen)
ralph --provider claude run
ralph --provider codex init "Project description"

# Dry-run mode (show what would be executed)
ralph --dry-run run

# Limit iterations
ralph run --max-iterations 5

# Auto-push commits to remote
ralph run --auto-push

# Continue on work phase failures (useful for agent cancellations)
ralph run --continue-on-error

# Override backlog location
ralph --backlog /path/to/custom-backlog.json run

# Manual override commands (for stuck items)
ralph item mark-complete ITEM-ID      # Mark item as done (bypasses validation)
ralph item mark-ready ITEM-ID         # Mark item as ready for validation
ralph item reset ITEM-ID              # Reset item back to todo status

# Run health checks
ralph doctor

# Check with project-specific validation
ralph --project ~/projects/your-project doctor
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
ralph run --auto-push
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
      ],
      "validation": {
        "commands": [
          "Verify development environment can be set up from scratch",
          "Confirm all essential project files are present"
        ]
      }
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

Qwen Code CLI agent (Alibaba Cloud). Requires Qwen Code to be installed and authenticated.

```bash
ralph --provider qwen
```

**Requirements:**
- Qwen Code CLI installed (`qwen --version` works)
- Authenticated with Alibaba Cloud

**Features:**
- Real-time progress rendering with qwen_renderer
- Streaming output with syntax highlighting
- Supports any Qwen model

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

OpenAI Codex CLI. Requires Codex to be installed and authenticated.

```bash
ralph --provider codex
```

**Requirements:**
- Codex CLI installed (`codex --version` works)
- Authenticated with OpenAI

**Features:**
- Best-effort progress rendering
- Fast execution
- API-based

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
  - **Complete message mode** (default): Groups assistant messages into coherent blocks for better readability
  - **Partial streaming mode**: Shows character-by-character updates in real-time
- **Claude Code**: Best-effort rendering (depends on Claude Code output format)
- **Codex**: Best-effort rendering (depends on API response format)

Progress logs are stored in `<project>/logs/ralph/qwen-stream/` for debugging.

### Qwen Rendering Modes

The Qwen renderer supports two modes:

**Complete Message Mode (default)** - Recommended for better readability:
- Waits for complete assistant messages before displaying
- Eliminates fragmentation (no broken sentences or partial formatting)
- Tool calls still show in real-time for progress feedback
- Slight delay (~1 second) per message

**Partial Streaming Mode** - For real-time character-by-character updates:
- Shows text as it's generated
- May fragment messages at sentence boundaries
- More immediate feedback

The default mode provides the best balance of readability and responsiveness. Raw logs always capture all events regardless of rendering mode.

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
ralph validate
```

## Backlog Initialization with `ralph init`

The `ralph init` command generates a comprehensive project roadmap from a natural language prompt. This feature uses AI agents to break down your project into structured milestones suitable for autonomous implementation.

### How it works

1. You provide a project description
2. Ralph Loop invokes an AI agent (Qwen, Claude Code, or Codex)
3. The agent detects or recommends appropriate tech stack based on your description
4. The agent generates `docs/ARCHITECTURE.md` with:
   - Technology stack and versions
   - Project structure and patterns
   - Coding standards
   - Testing strategy
5. The agent generates a high-level, feature-oriented roadmap
6. Ralph Loop transforms the response into a valid `backlog.json`
7. The backlog is validated and saved to `docs/backlog.json`

### Usage examples

```bash
# Web application
ralph init "Build a blog platform with user authentication and markdown support"

# CLI tool
ralph init "Create a command-line tool for managing TODO lists with SQLite storage"

# Library
ralph init "Develop a Python library for parsing and validating JSON schemas"

# Data pipeline
ralph init "Build an ETL pipeline that extracts data from CSV files and loads into PostgreSQL"

# With specific provider
ralph init "Build a REST API with FastAPI" --provider claude

# Preview without creating files
ralph init "Build a calculator app" --dry-run
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

#### docs/backlog.json
Each milestone includes:
- **Title**: Clear, actionable milestone name
- **Why**: Rationale for the milestone
- **Priority**: P0 (foundation), P1 (core), P2 (enhancements), P3 (polish)
- **Dependencies**: Which milestones must complete first
- **Deliverables**: High-level capabilities and features (NOT specific files or classes)
- **Exit Criteria**: Outcome-based verification (NOT implementation details)
- **Risks**: Potential challenges and mitigations
- **Validation Approach**: Conceptual validation strategies (NOT specific commands)

**Important:** Backlogs are now **high-level and feature-oriented**:
- ✅ "User authentication capability" (not "Create UserController.cs")
- ✅ "Data persistence layer" (not "SQLite database with users table")
- ✅ "Verify authentication flow end-to-end" (not "Run: curl http://localhost:5000")

#### docs/ARCHITECTURE.md
The architecture document provides technical guidance:
- **Technology Stack**: Specific versions and tools
- **Project Structure**: Folder organization and naming conventions
- **Architectural Patterns**: Design patterns for this stack
- **Coding Standards**: Language-specific conventions
- **Testing Strategy**: Unit, integration, and e2e testing approach
- **Development Guidelines**: How to add features and structure code

Agents use ARCHITECTURE.md to make implementation decisions while following the high-level backlog.

### Customizing generated backlogs

After generation, you can manually edit `docs/backlog.json` to:
- Adjust priorities
- Add or remove milestones
- Modify deliverables and exit criteria
- Add validation commands
- Specify dependencies

Then validate your changes:

```bash
ralph validate
```

### Debug output

All initialization attempts save debug information to `logs/ralph/init/`:
- `prompt-*.txt`: The prompt sent to the agent
- `response-*.txt`: The raw agent response
- `failed-parse-*.txt`: Responses that failed to parse (if any)

This helps troubleshoot issues with agent responses or parsing.

## Backlog Analysis with `ralph analyze`

The `ralph analyze` command evaluates whether a backlog is suitable for full-auto long-running execution. It uses AI agents to assess the backlog across 11 dimensions and provides actionable recommendations for improvement.

### How it works

1. Loads and validates the backlog.json
2. Reads and evaluates docs/ARCHITECTURE.md (if present)
3. Invokes an AI agent with the backlog content, architecture, and project directory path
4. Agent dynamically assesses environment compatibility and agent capabilities
5. Returns structured JSON with metrics, scores, issues, and recommendations
6. Optionally saves analysis to `.ralph/backlog-analysis.json`

### Eleven-Metric Evaluation Framework

1. **Clarity (12.5% weight)** - Clear titles, why statements, deliverables, exit criteria
2. **Completeness (8.3% weight)** - All required fields, adequate deliverables/criteria
3. **Abstraction Level (16.7% weight)** - High-level capabilities vs implementation details
4. **Dependency Structure (8.3% weight)** - Well-defined dependencies, parallelization opportunities
5. **Risk Awareness (8.3% weight)** - Risks identified with mitigation strategies
6. **Granularity (8.3% weight)** - Appropriately sized items (5-15 total)
7. **Priority Alignment (4.2% weight)** - P0=foundation, P1=core, P2=enhancements, P3=polish
8. **Environment Compatibility (12.5% weight)** - Required tools from ARCHITECTURE.md are available
9. **Architecture Quality (8.3% weight)** - ARCHITECTURE.md is comprehensive and actionable
10. **Agent Capability Alignment (4.2% weight)** - Tasks within AI agent's operational permissions
11. **Backlog-Architecture Alignment (8.3% weight)** - Backlog and architecture are consistent

**Overall Score:** Weighted average with 75/100 threshold for "ready for auto"

**Key Metrics Explained:**

- **Abstraction Level**: Ensures deliverables are high-level (e.g., "User authentication capability") not implementation-specific (e.g., "Create UserController.cs")
- **Environment Compatibility**: Checks if tools specified in ARCHITECTURE.md are installed, flags tools requiring sudo (Playwright, PostgreSQL, Docker)
- **Architecture Quality**: Evaluates if ARCHITECTURE.md exists and contains tech stack, patterns, standards, testing strategy
- **Backlog-Architecture Alignment**: Validates consistency between backlog items and architecture (no contradictions or gaps)

### Usage examples

```bash
# Basic analysis (outputs JSON to stdout)
ralph analyze

# Save analysis to .ralph/backlog-analysis.json
ralph analyze --save-analysis

# Use different provider
ralph analyze --provider claude

# Preview without executing
ralph analyze --dry-run

# Analyze specific backlog
ralph --backlog /path/to/backlog.json analyze
```

### Iterative improvement workflow

```bash
# 1. Generate initial backlog
ralph init "Build a task management API with React frontend"

# 2. Analyze for readiness
ralph analyze --save-analysis

# 3. Review recommendations
jq '.recommendations' .ralph/backlog-analysis.json

# 4. Check environment compatibility
jq '.metrics.environment_compatibility' .ralph/backlog-analysis.json

# 5. Check capability flags
jq '.metrics.agent_capability_alignment.permission_flags' .ralph/backlog-analysis.json

# 6. Edit backlog based on suggestions
vim docs/backlog.json

# 7. Re-analyze to verify improvements
ralph analyze

# 8. When ready_for_auto is true, execute
ralph run --max-iterations 10
```

### JSON output structure

The analysis returns structured JSON with:

- `version`: Schema version
- `analyzed_at`: Timestamp
- `backlog_path`: Path to analyzed backlog
- `architecture_path`: Path to ARCHITECTURE.md (or null if missing)
- `architecture_exists`: Boolean indicating if ARCHITECTURE.md exists
- `tech_stack_from_architecture`: Tech stack parsed from ARCHITECTURE.md
- `summary`: Item counts by priority and status
- `metrics`: 11 metrics with scores (0-100), weights, and findings
- `overall_score`: Weighted average
- `threshold`: Readiness threshold (75)
- `ready_for_auto`: Boolean decision
- `issues`: Structured list of problems (severity, category, item_id, message)
- `recommendations`: Actionable improvement suggestions
- `follow_up_prompt`: Detailed prompt for improving the backlog and/or architecture

### Environment compatibility assessment

The agent checks for required tools by:
1. Reading `docs/ARCHITECTURE.md` to identify tech stack requirements
2. Running bash commands to check if tools are installed (e.g., `dotnet --version`, `node --version`)
3. Flagging tools that require sudo/admin privileges (Playwright, PostgreSQL, Docker)
4. Comparing requirements vs. availability
5. Reporting missing tools that would block implementation

Example for .NET + React stack:
- Reads ARCHITECTURE.md to find ".NET 10" and "React + TypeScript + Vite"
- Checks for .NET SDK via `dotnet --version`
- Checks for Node.js via `node --version`
- Checks for xUnit via `dotnet test --help`
- Flags if Playwright is required but not installed (requires sudo for browser install)

### Agent capability assessment

The agent analyzes required operations and sets permission flags:
- `requires_network`: true if items need external API calls or package downloads
- `requires_destructive_ops`: true if items include file deletion or database drops
- `requires_system_admin`: true if items need elevated permissions
- `requires_external_services`: true if items depend on third-party APIs

These flags enable automated decision-making in CI/CD pipelines.

### Debug output

Analysis attempts save debug information to `logs/ralph/analyze/`:
- `analysis-*.json`: The temp output file from the agent
- `failed-analysis-parse-*.txt`: Responses that failed to parse (if any)

### Architecture Refinement

Use `ralph refine-architecture` to improve the architecture document:

```bash
# Refine architecture with specific instructions
ralph refine-architecture "Add more detail about error handling patterns"

# Update tech stack
ralph refine-architecture "Switch from SQLite to PostgreSQL"

# Add missing sections
ralph refine-architecture "Add section about API versioning strategy"
```

The command:
1. Reads current `docs/ARCHITECTURE.md`
2. Applies your refinement instructions
3. Creates a backup before modifying
4. Saves the improved architecture document

Use this when:
- Tech stack changes during development
- More architectural detail is needed
- Best practices need to be updated
- New patterns or guidelines should be added

## High-Level Design Philosophy

Ralph Loop uses a **high-level, feature-oriented** approach to backlog design. This paradigm shift enables better flexibility and adaptability during autonomous implementation.

### The Paradigm

**Backlogs describe WHAT, not HOW:**
- Focus on capabilities and outcomes
- Avoid implementation details
- Let AI agents make technical decisions based on ARCHITECTURE.md

**ARCHITECTURE.md provides technical guidance:**
- Specifies tech stack, patterns, and best practices
- Guides implementation decisions
- Ensures consistency across the project

### Examples of Proper Abstraction

**Deliverables:**
- ✅ GOOD: "User authentication capability"
- ❌ BAD: "Create UserController.cs with Login() method"
- ✅ GOOD: "Data persistence layer"
- ❌ BAD: "SQLite database with users table and password_hash column"
- ✅ GOOD: "Task management functionality"
- ❌ BAD: "TaskService class with CRUD methods"

**Exit Criteria:**
- ✅ GOOD: "Users can authenticate and receive access tokens"
- ❌ BAD: "UserController.Login() returns JWT token"
- ✅ GOOD: "Task data persists across application restarts"
- ❌ BAD: "Database contains tasks table with correct schema"
- ✅ GOOD: "All core functionality is covered by automated tests"
- ❌ BAD: "xUnit tests in Tests/UserControllerTests.cs pass"

**Validation Approaches:**
- ✅ GOOD: "Verify user authentication flow end-to-end"
- ❌ BAD: "Run: curl -X POST http://localhost:5000/api/auth/login"
- ✅ GOOD: "Validate task CRUD operations with various inputs"
- ❌ BAD: "Execute: pytest tests/test_tasks.py"
- ✅ GOOD: "Confirm data persistence across application lifecycle"
- ❌ BAD: "Check HTTP 200 response from GET /api/tasks"

### Why High-Level Design?

1. **Flexibility**: Agents can choose appropriate tools and approaches
2. **Adaptability**: Implementation changes don't cascade through backlog
3. **Future-proof**: High-level descriptions remain valid as tools evolve
4. **Better AI decisions**: Agents use ARCHITECTURE.md to make informed choices
5. **Easier maintenance**: Fewer brittle dependencies on specific implementations

### How Agents Use Both Documents

1. **Read backlog item**: Understand WHAT capability is needed
2. **Read ARCHITECTURE.md**: Understand HOW to implement (tech stack, patterns)
3. **Implement**: Create code following architectural guidelines
4. **Validate**: Verify the outcome matches exit criteria

This separation of concerns allows for better autonomous implementation while maintaining architectural consistency.

## Troubleshooting

### "Backlog not found"

Ensure `docs/backlog.json` exists in the project directory:

```bash
ls docs/backlog.json
```

Or use `ralph init` to generate one:

```bash
ralph init "Your project description"
```

Or specify a custom location:

```bash
ralph --backlog /path/to/backlog.json run
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

- **Qwen**: `qwen --version` should work and be authenticated
- **Claude Code**: `claude --version` should work
- **Codex**: `codex --version` should work and be authenticated

### "Validation failed"

Run validation to see specific errors:

```bash
ralph validate
```

Fix the reported issues in `docs/backlog.json` and try again.

## Artifact Management

Ralph Loop stores all temporary files, logs, and artifacts in a `.ralph` folder in your project root:

```
.ralph/
├── logs/
│   ├── init/          # Initialization logs and responses
│   ├── analyze/       # Analysis logs
│   ├── refine/        # Refinement logs
│   ├── qwen-stream/   # Qwen provider stream logs
│   └── parse-failures/ # Failed parse attempts for debugging
├── tmp/               # Temporary files during atomic operations
├── backups/           # Timestamped backlog backups
└── execution.lock     # Execution lock file
```

**Benefits:**
- Single cleanup: `rm -rf .ralph` removes all ralph-loop artifacts
- Single gitignore: Add `.ralph/` once to `.gitignore`
- Clear ownership: Everything in `.ralph` belongs to ralph-loop
- Better organization: Logs, temps, and backups are separated

**Migration:** If you have an existing project with `logs/ralph/` or `.ralph-loop.lock`, they will be automatically migrated to `.ralph/` on first run.

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
ralph --provider my-provider run --dry-run
```

## License

MIT

## Contributing

Contributions welcome! Please open an issue or pull request.
