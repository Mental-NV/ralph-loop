#!/usr/bin/env python3
"""
Prompt templates for Ralph Loop initialization.

Loads prompts from text files and renders them with variables.
"""

import json
from ralph.prompt_loader import PromptLoader

# Initialize loader
_loader = PromptLoader()


def load_schema_for_prompt() -> str:
    """
    Load backlog schema and format it for inclusion in prompts.

    Returns:
        Formatted schema as string
    """
    from ralph.validator import load_bundled_schema

    schema = load_bundled_schema()

    # Format as readable JSON
    return json.dumps(schema, indent=2)


def build_roadmap_prompt(user_prompt: str, output_file: str) -> str:
    """
    Build meta-prompt for roadmap generation.

    Returns a prompt that instructs the agent to:
    1. Analyze the user's project description
    2. Break it into logical milestones
    3. Write structured JSON to a file

    Args:
        user_prompt: User's project description (e.g., "Build a web scraper in Python")
        output_file: Path where the agent should write the roadmap JSON

    Returns:
        Formatted prompt for the agent
    """
    schema = load_schema_for_prompt()
    return _loader.load('roadmap',
                       user_prompt=user_prompt,
                       output_file=output_file,
                       schema=schema)


def build_analysis_prompt(backlog_json: str, project_dir: str, output_file: str, threshold: int = 75) -> str:
    """
    Build meta-prompt for backlog analysis.

    Returns a prompt that instructs the agent to:
    1. Analyze the backlog for automation readiness
    2. Evaluate environment compatibility and agent capabilities
    3. Write structured JSON analysis to a file

    Args:
        backlog_json: Full backlog.json content as string
        project_dir: Project directory path for environment inspection
        output_file: Path where the agent should write the analysis JSON
        threshold: Target quality score for automation readiness (1-100)

    Returns:
        Formatted prompt for the agent
    """
    return _loader.load('analysis',
                       backlog_json=backlog_json,
                       project_dir=project_dir,
                       output_file=output_file,
                       threshold=threshold)


def build_refinement_prompt(backlog_json: str, user_prompt: str, output_file: str) -> str:
    """
    Build meta-prompt for backlog refinement.

    Returns a prompt that instructs the agent to:
    1. Read the current backlog
    2. Apply the user's refinement instructions
    3. Generate an improved backlog
    4. Write structured JSON to a file

    Args:
        backlog_json: Full backlog.json content as string
        user_prompt: User's refinement instructions
        output_file: Path where the agent should write the refined backlog JSON

    Returns:
        Formatted prompt for the agent
    """
    schema = load_schema_for_prompt()
    return _loader.load('refinement',
                       backlog_json=backlog_json,
                       user_prompt=user_prompt,
                       output_file=output_file,
                       schema=schema)


def load_tech_stack_schema() -> str:
    """
    Load tech stack schema for inclusion in prompts.

    Returns:
        Formatted schema as string
    """
    from pathlib import Path

    schema_path = Path(__file__).parent / "schemas" / "tech_stack.schema.json"
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    return json.dumps(schema, indent=2)


def build_tech_stack_detection_prompt(user_prompt: str, output_file: str) -> str:
    """
    Build meta-prompt for tech stack detection.

    Returns a prompt that instructs the agent to:
    1. Analyze the project description
    2. Detect or recommend appropriate tech stack
    3. Write structured JSON to a file

    Args:
        user_prompt: User's project description
        output_file: Path where the agent should write the tech stack JSON

    Returns:
        Formatted prompt for the agent
    """
    tech_stack_schema = load_tech_stack_schema()
    return _loader.load('tech_stack_detection',
                       user_prompt=user_prompt,
                       output_file=output_file,
                       tech_stack_schema=tech_stack_schema)


def build_architecture_prompt(user_prompt: str, tech_stack: dict, output_file: str) -> str:
    """
    Build meta-prompt for architecture document generation.

    Returns a prompt that instructs the agent to:
    1. Use the detected tech stack
    2. Generate comprehensive ARCHITECTURE.md with best practices
    3. Write markdown document to a file

    Args:
        user_prompt: User's project description
        tech_stack: Detected tech stack dictionary
        output_file: Path where the agent should write the architecture document

    Returns:
        Formatted prompt for the agent
    """
    tech_stack_str = json.dumps(tech_stack, indent=2)
    return _loader.load('architecture',
                       user_prompt=user_prompt,
                       tech_stack=tech_stack_str,
                       output_file=output_file)
