#!/usr/bin/env python3
"""
Ralph Loop CLI - Main entry point.

Provider-agnostic orchestration loop for agent-driven development.
"""

import argparse
import sys
from pathlib import Path

from ralph.orchestrator import BacklogOrchestrator
from ralph.providers import list_available_providers


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ralph Loop - Provider-agnostic orchestration for agent-driven development",
        epilog="YOLO mode (auto-approve all actions) is always enabled."
    )
    parser.add_argument(
        '--project',
        type=str,
        metavar='PATH',
        help='Target project directory (default: current directory)'
    )
    parser.add_argument(
        '--backlog',
        type=str,
        metavar='PATH',
        help='Override backlog.json location (default: <project>/docs/backlog.json)'
    )
    parser.add_argument(
        '--provider',
        type=str,
        default='qwen',
        choices=['qwen', 'claude', 'codex'],
        help='Agent provider to use (default: qwen)'
    )
    parser.add_argument(
        '--auto-push',
        action='store_true',
        help='Automatically push to remote after each completed item'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        metavar='N',
        help='Maximum number of loop iterations (for testing)'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate backlog.json and exit'
    )
    parser.add_argument(
        '--show-next',
        action='store_true',
        help='Show next item that would be executed and exit'
    )
    parser.add_argument(
        '--list-providers',
        action='store_true',
        help='List available providers and exit'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    parser.add_argument(
        '--init',
        type=str,
        metavar='PROMPT',
        help='Initialize backlog from prompt (e.g., "Build a web scraper in Python")'
    )

    args = parser.parse_args()

    # List providers mode
    if args.list_providers:
        available = list_available_providers()
        if available:
            print("Available providers:")
            for provider in available:
                print(f"  - {provider}")
        else:
            print("No providers are available on this system")
        sys.exit(0)

    # Init mode - initialize backlog from prompt
    if args.init:
        from ralph.initializer import BacklogInitializer

        # Resolve project directory
        if args.project:
            project_dir = Path(args.project).resolve()
        else:
            project_dir = Path.cwd()

        if not project_dir.exists():
            print(f"Error: Project directory does not exist: {project_dir}", file=sys.stderr)
            sys.exit(1)

        if not project_dir.is_dir():
            print(f"Error: Project path is not a directory: {project_dir}", file=sys.stderr)
            sys.exit(1)

        # Resolve backlog path
        if args.backlog:
            backlog_path = Path(args.backlog).resolve()
        else:
            backlog_path = project_dir / "docs" / "backlog.json"

        # Create initializer
        initializer = BacklogInitializer(
            project_dir=project_dir,
            backlog_path=backlog_path,
            provider=args.provider,
            dry_run=args.dry_run
        )

        # Run initialization
        exit_code = initializer.initialize(args.init)
        sys.exit(exit_code)

    # Resolve project directory
    if args.project:
        project_dir = Path(args.project).resolve()
    else:
        project_dir = Path.cwd()

    if not project_dir.exists():
        print(f"Error: Project directory does not exist: {project_dir}", file=sys.stderr)
        sys.exit(1)

    if not project_dir.is_dir():
        print(f"Error: Project path is not a directory: {project_dir}", file=sys.stderr)
        sys.exit(1)

    # Resolve backlog path
    if args.backlog:
        backlog_path = Path(args.backlog).resolve()
    else:
        backlog_path = project_dir / "docs" / "backlog.json"

    if not backlog_path.exists():
        print(f"Error: Backlog not found: {backlog_path}", file=sys.stderr)
        print(f"\nExpected location: {project_dir / 'docs' / 'backlog.json'}", file=sys.stderr)
        print("Use --backlog to specify a different location.", file=sys.stderr)
        sys.exit(1)

    # Create orchestrator
    orchestrator = BacklogOrchestrator(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        auto_push=args.auto_push,
        dry_run=args.dry_run
    )

    # Validate-only mode
    if args.validate_only:
        if orchestrator.validate_backlog():
            print("✓ Backlog is valid")
            sys.exit(0)
        else:
            sys.exit(1)

    # Show-next mode
    if args.show_next:
        if not orchestrator.validate_backlog():
            sys.exit(1)

        backlog = orchestrator.load_backlog()
        next_item = orchestrator.select_next_item(backlog)

        if next_item:
            print(f"Next item: {next_item['id']}")
            print(f"  Title: {next_item['title']}")
            print(f"  Priority: {next_item['priority']}")
            print(f"  Order: {next_item['order']}")
        else:
            print("No eligible items to execute")

        sys.exit(0)

    # Check git status
    if not orchestrator.check_git_clean():
        print("Error: Working tree is not clean. Commit or stash changes first.", file=sys.stderr)
        sys.exit(1)

    # Acquire lock
    if not orchestrator.acquire_lock():
        print("Error: Another ralph-loop instance is running (lock exists)", file=sys.stderr)
        sys.exit(1)

    try:
        # Git fetch
        if not orchestrator.git_fetch():
            sys.exit(1)

        # Run main loop
        exit_code = orchestrator.run_loop(max_iterations=args.max_iterations)
        sys.exit(exit_code)

    finally:
        orchestrator.release_lock()


if __name__ == '__main__':
    main()
