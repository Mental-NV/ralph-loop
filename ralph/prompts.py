#!/usr/bin/env python3
"""
Prompt templates for Ralph Loop initialization.

Generates meta-prompts that instruct agents to produce structured roadmaps.
"""


def build_roadmap_prompt(user_prompt: str) -> str:
    """
    Build meta-prompt for roadmap generation.

    Returns a prompt that instructs the agent to:
    1. Analyze the user's project description
    2. Break it into logical milestones
    3. Output structured JSON matching backlog schema

    Args:
        user_prompt: User's project description (e.g., "Build a web scraper in Python")

    Returns:
        Formatted prompt for the agent
    """
    return f"""You are a software architect helping to plan a project for autonomous implementation by AI agents.

# Project Request
{user_prompt}

# Your Task
Generate a comprehensive project roadmap with milestones suitable for autonomous implementation. Each milestone should be independently implementable by a frontier AI agent (Claude, Qwen, Codex).

# Output Format
Respond with ONLY a JSON object matching this exact structure (no markdown, no explanations):

{{
  "version": "1.0.0",
  "items": [
    {{
      "title": "Milestone title",
      "why": "Why this milestone is important",
      "priority": "P0",
      "dependsOn": [],
      "deliverables": [
        "Concrete deliverable 1",
        "Concrete deliverable 2"
      ],
      "exitCriteria": [
        "Testable criterion 1",
        "Testable criterion 2"
      ],
      "risks": [
        "Risk 1",
        "Risk 2"
      ],
      "validation": {{
        "commands": ["command1", "command2"]
      }}
    }}
  ]
}}

# Guidelines

**Milestones:**
- Break the project into 5-15 logical milestones
- Each milestone should be completable in one focused work session
- Order milestones logically (foundation → core features → enhancements → polish)
- Make each milestone independently implementable where possible

**Priorities:**
- P0: Foundation and infrastructure (setup, core architecture)
- P1: Core features and functionality
- P2: Enhancements and improvements
- P3: Polish, optimization, nice-to-have features

**Dependencies:**
- Use dependsOn array to specify which milestones must complete first
- Reference dependencies by their exact title
- Ensure dependencies form a DAG (no circular dependencies)
- Minimize dependencies to allow parallel work where possible

**Deliverables:**
- List concrete, verifiable outputs (files, functions, tests, docs)
- Be specific: "Create src/parser.py with parse() function" not "Write parser"
- Each deliverable should be checkable by an agent

**Exit Criteria:**
- Define how to verify the milestone is complete
- Make criteria testable and objective
- Include both functional and quality checks
- Examples: "All tests pass", "Code follows style guide", "API returns expected responses"

**Risks:**
- Identify potential blockers or challenges
- Suggest mitigation strategies where applicable
- Be realistic about complexity

**Validation Commands:**
- Provide shell commands to verify completion
- Examples: "pytest tests/", "npm test", "python -m mypy src/"
- Commands should be runnable in the project directory

# Example Milestone

{{
  "title": "Setup Project Structure",
  "why": "Establishes foundation for all subsequent development work",
  "priority": "P0",
  "dependsOn": [],
  "deliverables": [
    "Create project directory structure (src/, tests/, docs/)",
    "Initialize git repository with .gitignore",
    "Create requirements.txt or package.json with dependencies",
    "Setup virtual environment or node_modules",
    "Create README.md with project overview"
  ],
  "exitCriteria": [
    "Project structure follows language best practices",
    "All dependencies install without errors",
    "Git repository is initialized and clean",
    "README documents project purpose and setup"
  ],
  "risks": [
    "Dependency conflicts - mitigate by pinning versions"
  ],
  "validation": {{
    "commands": [
      "ls -la",
      "git status",
      "test -f README.md"
    ]
  }}
}}

# Important Notes
- Output ONLY the JSON object, no markdown code fences, no explanations
- Ensure all JSON is valid and properly escaped
- Make milestones actionable and specific to the project request
- Consider the target language, framework, and tools mentioned in the request
- Design for autonomous implementation - agents won't ask clarifying questions

Generate the roadmap now:"""
