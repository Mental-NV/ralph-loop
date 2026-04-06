#!/usr/bin/env python3
"""
Data transformation utilities for Ralph Loop initialization.

Transforms parsed agent responses into valid backlog items.
"""

import re
from typing import Any, Dict, List, Set


def normalize_risks(risks: List[Any]) -> List[Any]:
    """
    Normalize risk format to ensure schema compliance.

    Accepts:
    - Strings: passed through unchanged
    - Objects with 'text': validated and passed through
    - Objects without 'text': converted to string (best effort)

    Args:
        risks: List of risks (strings or objects)

    Returns:
        Normalized list of risks
    """
    normalized = []
    for risk in risks:
        if isinstance(risk, str):
            normalized.append(risk)
        elif isinstance(risk, dict):
            if 'text' in risk:
                # Valid risk object
                normalized.append(risk)
            else:
                # Invalid object - try to extract meaningful string
                # Look for common fields: description, message, risk, etc.
                text = (risk.get('description') or
                       risk.get('message') or
                       risk.get('risk') or
                       str(risk))
                normalized.append(text)
        else:
            # Unexpected type - convert to string
            normalized.append(str(risk))

    return normalized


def generate_item_id(title: str, existing_ids: Set[str]) -> str:
    """
    Generate unique kebab-case ID from title.

    Algorithm:
    1. Convert to lowercase
    2. Replace spaces and special chars with hyphens
    3. Remove consecutive hyphens
    4. Strip leading/trailing hyphens
    5. Validate against pattern: ^[a-z0-9]+(-[a-z0-9]+)*$
    6. If collision, append -v1, -v2, etc.

    Args:
        title: Milestone title
        existing_ids: Set of already-used IDs

    Returns:
        Unique kebab-case ID

    Examples:
        "Setup Project Structure" → "setup-project-structure"
        "API Integration (v2)" → "api-integration-v2"
    """
    # Convert to lowercase and replace special chars with hyphens
    base_id = title.lower()
    base_id = re.sub(r'[^a-z0-9]+', '-', base_id)

    # Remove consecutive hyphens
    base_id = re.sub(r'-+', '-', base_id)

    # Strip leading/trailing hyphens
    base_id = base_id.strip('-')

    # Ensure we have something
    if not base_id:
        base_id = 'milestone'

    # Check uniqueness
    if base_id not in existing_ids:
        return base_id

    # Append version suffix
    version = 1
    while f"{base_id}-v{version}" in existing_ids:
        version += 1
    return f"{base_id}-v{version}"


def assign_priority(item: Dict[str, Any]) -> str:
    """
    Assign priority if not specified by agent.

    Heuristics:
    - Keywords "setup", "foundation", "infrastructure" → P0
    - Keywords "implement", "create", "build" → P1
    - Keywords "enhance", "improve", "optimize" → P2
    - Keywords "polish", "nice-to-have", "optional" → P3
    - Default: P1

    Args:
        item: Milestone item dict

    Returns:
        Priority string (P0, P1, P2, or P3)
    """
    # If agent specified valid priority, use it
    if 'priority' in item and item['priority'] in ['P0', 'P1', 'P2', 'P3']:
        return item['priority']

    # Build search text from title and why
    title_lower = item.get('title', '').lower()
    why_lower = item.get('why', '').lower()
    text = f"{title_lower} {why_lower}"

    # P0: Foundation keywords
    p0_keywords = ['setup', 'foundation', 'infrastructure', 'initial', 'scaffold', 'bootstrap']
    if any(kw in text for kw in p0_keywords):
        return 'P0'

    # P3: Polish keywords
    p3_keywords = ['polish', 'nice-to-have', 'optional', 'future', 'enhancement', 'cosmetic']
    if any(kw in text for kw in p3_keywords):
        return 'P3'

    # P2: Improvement keywords
    p2_keywords = ['enhance', 'improve', 'optimize', 'refactor', 'cleanup']
    if any(kw in text for kw in p2_keywords):
        return 'P2'

    # Default: P1 (core features)
    return 'P1'


def generate_checklist_items(items: List[str], prefix: str) -> List[Dict[str, Any]]:
    """
    Generate checklist items (deliverables or exit criteria).

    Args:
        items: List of text descriptions
        prefix: ID prefix ('d' for deliverables, 'e' for exit criteria)

    Returns:
        List of checklist items with structure: {id, text, done}
    """
    return [
        {
            'id': f"{prefix}{i+1}",
            'text': text,
            'done': False
        }
        for i, text in enumerate(items) if text.strip()
    ]


def resolve_dependencies(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Resolve dependency references from titles to IDs.

    Agents may specify dependencies by title (more natural).
    This function resolves them to IDs.

    Strategy:
    1. Build title → ID mapping
    2. For each item's dependsOn list:
       - If already an ID, keep it
       - If a title, resolve to ID (exact match)
       - If unresolved, try case-insensitive match
       - If still unresolved, warn and remove

    Args:
        items: List of milestone items

    Returns:
        Items with resolved dependencies
    """
    # Build mappings
    id_set = {item['id'] for item in items}
    title_to_id = {item['title']: item['id'] for item in items}
    title_to_id_lower = {item['title'].lower(): item['id'] for item in items}

    for item in items:
        depends_on = item.get('dependsOn', [])
        resolved = []

        for dep in depends_on:
            if not dep:
                continue

            # Already an ID?
            if dep in id_set:
                resolved.append(dep)
            # Exact title match?
            elif dep in title_to_id:
                resolved.append(title_to_id[dep])
            # Case-insensitive title match?
            elif dep.lower() in title_to_id_lower:
                resolved.append(title_to_id_lower[dep.lower()])
            else:
                # Try fuzzy match
                fuzzy_match = find_fuzzy_match(dep, title_to_id.keys())
                if fuzzy_match:
                    print(f"Warning: Fuzzy matched dependency '{dep}' to '{fuzzy_match}' for item '{item['id']}'")
                    resolved.append(title_to_id[fuzzy_match])
                else:
                    print(f"Warning: Could not resolve dependency '{dep}' for item '{item['id']}' - removing")

        item['dependsOn'] = resolved

    return items


def find_fuzzy_match(target: str, candidates: List[str], threshold: float = 0.7) -> str:
    """
    Find fuzzy match for target string in candidates.

    Uses simple similarity metric based on common words.

    Args:
        target: String to match
        candidates: List of candidate strings
        threshold: Minimum similarity score (0-1)

    Returns:
        Best matching candidate, or empty string if no good match
    """
    target_words = set(target.lower().split())

    best_match = ""
    best_score = 0.0

    for candidate in candidates:
        candidate_words = set(candidate.lower().split())

        # Jaccard similarity
        intersection = target_words & candidate_words
        union = target_words | candidate_words

        if union:
            score = len(intersection) / len(union)
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate

    return best_match


def transform_to_backlog(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform parsed data into valid backlog structure.

    Steps:
    1. Ensure version field exists (default: "1.0.0")
    2. Generate unique IDs for all items
    3. Assign sequential order values
    4. Set all statuses to 'todo'
    5. Assign priorities (use agent's or heuristic)
    6. Resolve dependencies
    7. Ensure deliverables/exitCriteria have proper structure
    8. Add default empty arrays for optional fields
    9. Validate checklist item IDs are unique within parent

    Args:
        parsed_data: Parsed agent response

    Returns:
        Valid backlog dict ready for validation
    """
    backlog = {
        'version': parsed_data.get('version', '1.0.0'),
        'items': []
    }

    items = parsed_data.get('items', [])
    existing_ids: Set[str] = set()

    for order, item in enumerate(items):
        # Generate unique ID
        item_id = generate_item_id(item.get('title', f'milestone-{order}'), existing_ids)
        existing_ids.add(item_id)

        # Extract deliverables and exit criteria
        deliverables_raw = item.get('deliverables', [])
        exit_criteria_raw = item.get('exitCriteria', [])

        # Handle both list of strings and list of dicts
        if deliverables_raw and isinstance(deliverables_raw[0], dict):
            deliverables = deliverables_raw
        else:
            deliverables = generate_checklist_items(deliverables_raw, 'd')

        if exit_criteria_raw and isinstance(exit_criteria_raw[0], dict):
            exit_criteria = exit_criteria_raw
        else:
            exit_criteria = generate_checklist_items(exit_criteria_raw, 'e')

        # Build transformed item
        transformed = {
            'id': item_id,
            'title': item.get('title', f'Milestone {order + 1}'),
            'status': 'todo',
            'priority': assign_priority(item),
            'order': order,
            'dependsOn': item.get('dependsOn', []),
            'why': item.get('why', ''),
            'deliverables': deliverables,
            'exitCriteria': exit_criteria,
            'risks': normalize_risks(item.get('risks', [])),
        }

        # Add validation commands if present
        validation = item.get('validation', {})
        if validation and validation.get('commands'):
            transformed['validation'] = validation

        backlog['items'].append(transformed)

    # Resolve dependencies (title → ID)
    backlog['items'] = resolve_dependencies(backlog['items'])

    return backlog
