#!/usr/bin/env python3
"""
Response parsing utilities for Ralph Loop initialization.

Handles parsing of agent responses into structured backlog data.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


def parse_stream_json_response(response: str) -> Optional[str]:
    """
    Extract text from stream-json format (one JSON object per line).

    This handles responses from providers that use --output-format stream-json,
    where each line is a JSON object with text_delta events.

    Args:
        response: Raw stream-json response

    Returns:
        Concatenated text content, or None if no text found
    """
    text_parts = []

    for line in response.split('\n'):
        line = line.strip()
        if not line:
            continue

        try:
            event = json.loads(line)

            # Look for text_delta events
            if (event.get('type') == 'stream_event' and
                event.get('event', {}).get('type') == 'content_block_delta' and
                event.get('event', {}).get('delta', {}).get('type') == 'text_delta'):

                text = event['event']['delta'].get('text', '')
                text_parts.append(text)

        except json.JSONDecodeError:
            continue

    if text_parts:
        return ''.join(text_parts)

    return None


def parse_json_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse response as pure JSON.

    Args:
        response: Raw agent response

    Returns:
        Parsed JSON dict, or None if parsing fails
    """
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        return None


def extract_json_from_markdown(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from markdown code fences.

    Handles formats like:
    - ```json ... ```
    - ``` ... ```
    - ```javascript ... ```

    Args:
        response: Raw agent response with markdown

    Returns:
        Parsed JSON dict, or None if extraction fails
    """
    # Pattern to match code fences with optional language specifier
    pattern = r'```(?:json|javascript|js)?\s*\n(.*?)\n```'
    matches = re.findall(pattern, response, re.DOTALL)

    # Try each match
    for match in matches:
        try:
            parsed = json.loads(match.strip())
            # Verify it has the expected structure
            if isinstance(parsed, dict) and 'items' in parsed:
                return parsed
        except json.JSONDecodeError:
            continue

    return None


def parse_markdown_roadmap(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse markdown-formatted roadmap into backlog structure.

    Expected format:
    ## Milestone 1: Title
    **Why:** Rationale
    **Priority:** P0
    **Depends on:** milestone-title

    **Deliverables:**
    - Item 1
    - Item 2

    **Exit Criteria:**
    - Criterion 1

    **Risks:**
    - Risk 1

    **Validation:**
    - command1
    - command2

    Args:
        response: Raw agent response in markdown format

    Returns:
        Parsed backlog dict, or None if parsing fails
    """
    try:
        items = []

        # Split by milestone headers (## or ###)
        milestone_pattern = r'^#{2,3}\s+(?:Milestone\s+\d+:\s+)?(.+?)$'
        lines = response.split('\n')

        current_item = None
        current_section = None

        for line in lines:
            line = line.strip()

            # Check for milestone header
            match = re.match(milestone_pattern, line)
            if match:
                # Save previous item
                if current_item and current_item.get('title'):
                    items.append(current_item)

                # Start new item
                current_item = {
                    'title': match.group(1).strip(),
                    'why': '',
                    'priority': 'P1',
                    'dependsOn': [],
                    'deliverables': [],
                    'exitCriteria': [],
                    'risks': [],
                    'validation': {'commands': []}
                }
                current_section = None
                continue

            if not current_item:
                continue

            # Check for section headers
            if line.startswith('**Why:**'):
                current_item['why'] = line.replace('**Why:**', '').strip()
                current_section = None
            elif line.startswith('**Priority:**'):
                priority = line.replace('**Priority:**', '').strip()
                if priority in ['P0', 'P1', 'P2', 'P3']:
                    current_item['priority'] = priority
                current_section = None
            elif line.startswith('**Depends on:**') or line.startswith('**Dependencies:**'):
                deps_text = line.split(':', 1)[1].strip()
                if deps_text and deps_text.lower() not in ['none', 'n/a', '-']:
                    # Split by comma or semicolon
                    deps = [d.strip() for d in re.split(r'[,;]', deps_text)]
                    current_item['dependsOn'] = [d for d in deps if d]
                current_section = None
            elif line.startswith('**Deliverables:**'):
                current_section = 'deliverables'
            elif line.startswith('**Exit Criteria:**') or line.startswith('**Exit criteria:**'):
                current_section = 'exitCriteria'
            elif line.startswith('**Risks:**'):
                current_section = 'risks'
            elif line.startswith('**Validation:**') or line.startswith('**Validation Commands:**'):
                current_section = 'validation'
            elif line.startswith('- ') or line.startswith('* '):
                # List item
                item_text = line[2:].strip()
                if current_section == 'deliverables':
                    current_item['deliverables'].append(item_text)
                elif current_section == 'exitCriteria':
                    current_item['exitCriteria'].append(item_text)
                elif current_section == 'risks':
                    current_item['risks'].append(item_text)
                elif current_section == 'validation':
                    current_item['validation']['commands'].append(item_text)

        # Save last item
        if current_item and current_item.get('title'):
            items.append(current_item)

        if not items:
            return None

        return {
            'version': '1.0.0',
            'items': items
        }

    except Exception:
        return None


def parse_roadmap_response(response: str, debug_dir: Path) -> Dict[str, Any]:
    """
    Parse agent response using multi-tier strategy.

    Tries in order:
    1. Stream-json extraction (for --output-format stream-json)
    2. Direct JSON parsing
    3. JSON extraction from markdown
    4. Markdown structure parsing

    Args:
        response: Raw agent response
        debug_dir: Directory to save debug output

    Returns:
        Parsed backlog dict

    Raises:
        ValueError: If all parsing strategies fail
    """
    # Try tier 0: Stream-json extraction
    # Check if response looks like stream-json (multiple lines with JSON objects)
    if response.count('\n') > 10 and '"type":"stream_event"' in response:
        extracted_text = parse_stream_json_response(response)
        if extracted_text:
            # Try parsing the extracted text as JSON
            result = parse_json_response(extracted_text)
            if result:
                return result

            # Try extracting JSON from markdown in the extracted text
            result = extract_json_from_markdown(extracted_text)
            if result:
                return result

    # Try tier 1: Direct JSON
    result = parse_json_response(response)
    if result:
        return result

    # Try tier 2: JSON extraction from markdown
    result = extract_json_from_markdown(response)
    if result:
        return result

    # Try tier 3: Markdown structure parsing
    result = parse_markdown_roadmap(response)
    if result:
        return result

    # All strategies failed - save debug output
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    debug_file = debug_dir / f"failed-parse-{timestamp}.txt"
    debug_file.write_text(response)

    # Show preview of response
    preview = response[:500] + "..." if len(response) > 500 else response

    raise ValueError(
        f"Failed to parse agent response. Tried JSON, markdown extraction, and markdown parsing.\n"
        f"Response preview:\n{preview}\n\n"
        f"Full response saved to: {debug_file}"
    )
