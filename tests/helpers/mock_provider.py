#!/usr/bin/env python3
"""
Mock AI provider for testing Ralph Loop CLI commands.

This provider returns pre-defined responses instead of calling real AI services,
enabling fast, deterministic, and cost-free testing.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from ralph.providers import AgentProvider


class MockAgentProvider(AgentProvider):
    """Mock provider that returns pre-defined responses for testing."""

    def __init__(self, response_data=None):
        """
        Initialize mock provider with optional response data.

        Args:
            response_data: Dictionary mapping call indices to response data,
                          or a single response to use for all calls.
                          If None, reads from RALPH_MOCK_RESPONSES env var.
        """
        # Try environment variable first (for subprocess usage)
        if response_data is None:
            import os
            env_responses = os.environ.get('RALPH_MOCK_RESPONSES')
            if env_responses:
                import json
                response_data = json.loads(env_responses)

        # Initialize responses
        if response_data is None:
            self.responses = {}
            self._single_response = False
        elif isinstance(response_data, dict):
            # Check if this is a multi-response dict (has integer keys)
            keys = list(response_data.keys())
            if keys and all(isinstance(k, int) or (isinstance(k, str) and k.isdigit()) for k in keys):
                # Multiple responses indexed by call number
                # Convert string keys to integers if needed (from JSON deserialization)
                self.responses = {int(k) if isinstance(k, str) else k: v for k, v in response_data.items()}
                self._single_response = False
            else:
                # Single response dict - use for all calls
                self.responses = {0: response_data}
                self._single_response = True
        else:
            # Non-dict response - use for all calls
            self.responses = {0: response_data}
            self._single_response = True

        self.call_count = 0
        self.call_history = []

    def get_name(self) -> str:
        """Return provider name."""
        return "mock"

    def is_available(self) -> bool:
        """Mock provider is always available."""
        return True

    def build_command(
        self,
        prompt: str,
        project_dir: Path,
        yolo: bool = False
    ) -> List[str]:
        """
        Build command that outputs pre-defined JSON response.

        Instead of calling a real AI provider, this returns a command that
        echoes the pre-defined response for the current call count.
        """
        # Record this call
        self.call_history.append({
            'prompt': prompt,
            'project_dir': str(project_dir),
            'yolo': yolo
        })

        # Get response for this call
        if self._single_response:
            response = self.responses.get(0, {})
        else:
            response = self.responses.get(self.call_count, {})

        # If no response configured, provide a minimal valid default
        if not response:
            response = {"version": "1.0.0", "items": []}

        self.call_count += 1

        # Check if prompt asks to write to a file (extract file path from prompt)
        import re
        file_match = re.search(r'write.*?to[:\s]+[`"]?([^`"\n]+\.(?:json|md))[`"]?', prompt, re.IGNORECASE)

        if file_match:
            # Extract the file path and write the response to it
            output_file = file_match.group(1)
            response_json = json.dumps(response, indent=2)
            write_cmd = f"""
import json
from pathlib import Path

output_file = Path({repr(output_file)})
output_file.parent.mkdir(parents=True, exist_ok=True)

response = {repr(response)}

# Handle different response types
if isinstance(response, dict):
    if 'content' in response:
        # Architecture document with content field
        output_file.write_text(response['content'], encoding='utf-8')
    else:
        # JSON response
        output_file.write_text(json.dumps(response, indent=2), encoding='utf-8')
else:
    output_file.write_text(str(response), encoding='utf-8')

# Print the response wrapped in markdown
print({repr(f"```json\n{response_json}\n```")})
"""
            return [sys.executable, "-c", write_cmd]
        else:
            # No file writing needed, just return the response
            response_json = json.dumps(response, indent=2)
            # Wrap in markdown code block as expected by parser
            wrapped_response = f"```json\n{response_json}\n```"
            return [sys.executable, "-c", f"print({repr(wrapped_response)})"]

    def supports_rich_progress(self) -> bool:
        """Mock provider doesn't support rich progress."""
        return False

    def get_progress_renderer(self, project_dir: Path) -> Optional[List[str]]:
        """Mock provider doesn't need a progress renderer."""
        return None

    def check_authentication(self) -> Tuple[bool, str]:
        """Mock provider is always authenticated."""
        return True, "Mock provider (always authenticated)"


# Pre-defined response templates for common scenarios

def get_init_response(num_items=3):
    """Generate a mock init response with specified number of items."""
    items = []
    for i in range(num_items):
        items.append({
            "id": f"task-{i+1}-setup-component-{i+1}",
            "title": f"Task {i+1}: Setup component {i+1}",
            "status": "todo",
            "priority": "P1",
            "order": i,
            "why": f"Component {i+1} is needed for the system",
            "dependsOn": [],
            "deliverables": [
                {
                    "id": f"d{i*2+1}",
                    "text": f"Create component {i+1} structure",
                    "done": False
                },
                {
                    "id": f"d{i*2+2}",
                    "text": f"Add component {i+1} tests",
                    "done": False
                }
            ],
            "exitCriteria": [
                {
                    "id": f"e{i*2+1}",
                    "text": f"Component {i+1} exists",
                    "done": False
                },
                {
                    "id": f"e{i*2+2}",
                    "text": f"Tests pass for component {i+1}",
                    "done": False
                }
            ],
            "risks": ["None identified"],
            "validation": {
                "commands": []
            }
        })

    # Return in the format expected by parse_roadmap_response
    # The parser expects {'version': '1.0.0', 'items': [...]} at the top level
    return {
        "version": "1.0.0",
        "items": items
    }


def get_tech_stack_response():
    """Generate a mock tech stack detection response."""
    return {
        "app_type": "webapp",
        "backend": "Python",
        "frontend": "React",
        "database": "SQLite",
        "testing": "pytest",
        "additional_tools": []
    }


def get_architecture_response():
    """Generate a mock architecture document response."""
    return {
        "content": "# Architecture\n\nThis is a test architecture document.\n\n## Components\n\n- Component 1\n- Component 2\n"
    }


def get_analyze_response(score=85, ready=True):
    """Generate a mock analyze response with specified score."""
    return {
        "version": "1.0.0",
        "metrics": [
            {"name": "clarity", "score": score, "weight": 0.15},
            {"name": "completeness", "score": score + 5, "weight": 0.15},
            {"name": "automation_readiness", "score": score - 5, "weight": 0.15},
            {"name": "dependency_structure", "score": score, "weight": 0.10},
            {"name": "risk_awareness", "score": score + 3, "weight": 0.10},
            {"name": "granularity", "score": score - 2, "weight": 0.10},
            {"name": "priority_alignment", "score": score + 2, "weight": 0.10},
            {"name": "environment_compatibility", "score": score, "weight": 0.10},
            {"name": "agent_capability_alignment", "score": score - 3, "weight": 0.05}
        ],
        "overall_score": score,
        "ready_for_auto": ready,
        "recommendations": ["Add more detailed exit criteria", "Consider edge cases"],
        "issues": [] if ready else ["Insufficient test coverage"],
        "follow_up_prompt": "Add integration tests and improve documentation"
    }


def get_refine_response(base_backlog, modifications=None):
    """Generate a mock refine response based on existing backlog."""
    import copy
    refined = copy.deepcopy(base_backlog)

    if modifications:
        # Apply modifications to the backlog
        if 'new_items' in modifications:
            refined['items'].extend(modifications['new_items'])
        if 'remove_ids' in modifications:
            refined['items'] = [
                item for item in refined['items']
                if item['id'] not in modifications['remove_ids']
            ]

    return refined
