#!/usr/bin/env python3
"""
Prompt loader for Ralph Loop.

Loads and renders prompt templates from text files.
"""

from pathlib import Path
from typing import Any


class PromptLoader:
    """Loads and renders prompt templates from text files."""

    def __init__(self):
        """Initialize prompt loader."""
        self.prompts_dir = Path(__file__).parent / "prompts"

    def load(self, template_name: str, **variables: Any) -> str:
        """
        Load and render a prompt template.

        Args:
            template_name: Name of template file (without .txt extension)
            **variables: Variables to substitute in template

        Returns:
            Rendered prompt string

        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If required variables are missing
        """
        template_path = self.prompts_dir / f"{template_name}.txt"

        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        # Read template
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # Substitute variables
        try:
            return template.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing variable in template {template_name}: {e}")
