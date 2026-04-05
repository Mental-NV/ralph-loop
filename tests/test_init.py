#!/usr/bin/env python3
"""
Unit tests for Ralph Loop initialization components.
"""

import unittest
from ralph.transformers import (
    generate_item_id,
    assign_priority,
    generate_checklist_items,
    transform_to_backlog
)


class TestIDGeneration(unittest.TestCase):
    """Test ID generation from titles."""

    def test_basic_kebab_case(self):
        """Test basic title to kebab-case conversion."""
        existing = set()
        self.assertEqual(
            generate_item_id("Setup Project Structure", existing),
            "setup-project-structure"
        )

    def test_special_characters(self):
        """Test handling of special characters."""
        existing = set()
        self.assertEqual(
            generate_item_id("API Integration (v2)", existing),
            "api-integration-v2"
        )

    def test_multiple_spaces(self):
        """Test handling of multiple spaces."""
        existing = set()
        self.assertEqual(
            generate_item_id("Create   Multiple   Spaces", existing),
            "create-multiple-spaces"
        )

    def test_uniqueness(self):
        """Test uniqueness handling with collisions."""
        existing = {"setup-project"}
        self.assertEqual(
            generate_item_id("Setup Project", existing),
            "setup-project-v1"
        )

    def test_multiple_collisions(self):
        """Test multiple collision handling."""
        existing = {"test", "test-v1", "test-v2"}
        self.assertEqual(
            generate_item_id("Test", existing),
            "test-v3"
        )


class TestPriorityAssignment(unittest.TestCase):
    """Test priority assignment heuristics."""

    def test_explicit_priority(self):
        """Test that explicit priorities are preserved."""
        item = {"title": "Test", "priority": "P2"}
        self.assertEqual(assign_priority(item), "P2")

    def test_foundation_keywords(self):
        """Test P0 assignment for foundation keywords."""
        item = {"title": "Setup Project Infrastructure"}
        self.assertEqual(assign_priority(item), "P0")

    def test_polish_keywords(self):
        """Test P3 assignment for polish keywords."""
        item = {"title": "Polish UI", "why": "Nice to have"}
        self.assertEqual(assign_priority(item), "P3")

    def test_improvement_keywords(self):
        """Test P2 assignment for improvement keywords."""
        item = {"title": "Optimize Performance"}
        self.assertEqual(assign_priority(item), "P2")

    def test_default_priority(self):
        """Test default P1 assignment."""
        item = {"title": "Implement Feature"}
        self.assertEqual(assign_priority(item), "P1")


class TestChecklistGeneration(unittest.TestCase):
    """Test checklist item generation."""

    def test_deliverables_generation(self):
        """Test deliverable checklist generation."""
        items = ["Create file.py", "Write tests"]
        result = generate_checklist_items(items, 'd')

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'd1')
        self.assertEqual(result[0]['text'], 'Create file.py')
        self.assertEqual(result[0]['done'], False)
        self.assertEqual(result[1]['id'], 'd2')

    def test_exit_criteria_generation(self):
        """Test exit criteria checklist generation."""
        items = ["Tests pass", "Code reviewed"]
        result = generate_checklist_items(items, 'e')

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'e1')
        self.assertEqual(result[1]['id'], 'e2')

    def test_empty_items_filtered(self):
        """Test that empty items are filtered out."""
        items = ["Valid item", "", "  ", "Another valid"]
        result = generate_checklist_items(items, 'd')

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['text'], 'Valid item')
        self.assertEqual(result[1]['text'], 'Another valid')


class TestBacklogTransformation(unittest.TestCase):
    """Test complete backlog transformation."""

    def test_basic_transformation(self):
        """Test basic transformation of parsed data."""
        parsed = {
            "version": "1.0.0",
            "items": [
                {
                    "title": "Setup Project",
                    "why": "Foundation",
                    "deliverables": ["Create structure"],
                    "exitCriteria": ["Structure exists"]
                }
            ]
        }

        result = transform_to_backlog(parsed)

        self.assertEqual(result['version'], '1.0.0')
        self.assertEqual(len(result['items']), 1)

        item = result['items'][0]
        self.assertEqual(item['id'], 'setup-project')
        self.assertEqual(item['title'], 'Setup Project')
        self.assertEqual(item['status'], 'todo')
        self.assertEqual(item['priority'], 'P0')  # Foundation keyword
        self.assertEqual(item['order'], 0)
        self.assertEqual(len(item['deliverables']), 1)
        self.assertEqual(len(item['exitCriteria']), 1)

    def test_multiple_items_ordering(self):
        """Test that multiple items get sequential orders."""
        parsed = {
            "items": [
                {"title": "First", "deliverables": [], "exitCriteria": []},
                {"title": "Second", "deliverables": [], "exitCriteria": []},
                {"title": "Third", "deliverables": [], "exitCriteria": []}
            ]
        }

        result = transform_to_backlog(parsed)

        self.assertEqual(result['items'][0]['order'], 0)
        self.assertEqual(result['items'][1]['order'], 1)
        self.assertEqual(result['items'][2]['order'], 2)

    def test_default_version(self):
        """Test that default version is added if missing."""
        parsed = {"items": []}
        result = transform_to_backlog(parsed)
        self.assertEqual(result['version'], '1.0.0')


if __name__ == '__main__':
    unittest.main()
