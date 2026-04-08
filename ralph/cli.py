#!/usr/bin/env python3
"""
Ralph Loop CLI - Main entry point.

Provider-agnostic orchestration loop for agent-driven development.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from ralph.orchestrator import BacklogOrchestrator
from ralph.providers import list_available_providers


def resolve_project_dir(args):
    """Resolve project directory from args."""
    if hasattr(args, 'project') and args.project:
        project_dir = Path(args.project).resolve()
    else:
        project_dir = Path.cwd()

    if not project_dir.exists():
        print(f"Error: Project directory does not exist: {project_dir}", file=sys.stderr)
        sys.exit(1)

    if not project_dir.is_dir():
        print(f"Error: Project path is not a directory: {project_dir}", file=sys.stderr)
        sys.exit(1)

    return project_dir


def resolve_backlog_path(args, project_dir, check_exists=True):
    """Resolve backlog path from args."""
    if hasattr(args, 'backlog') and args.backlog:
        backlog_path = Path(args.backlog).resolve()
    else:
        backlog_path = project_dir / "docs" / "backlog.json"

    if check_exists and not backlog_path.exists():
        print(f"Error: Backlog not found: {backlog_path}", file=sys.stderr)
        print(f"\nExpected location: {project_dir / 'docs' / 'backlog.json'}", file=sys.stderr)
        print("Use --backlog to specify a different location.", file=sys.stderr)
        sys.exit(1)

    return backlog_path


def handle_list_providers(args):
    """Handle 'ralph list-providers' command."""
    available = list_available_providers()
    if available:
        print("Available providers:")
        for provider in available:
            print(f"  - {provider}")
    else:
        print("No providers are available on this system")
    return 0


def handle_doctor(args):
    """Handle 'ralph doctor' command."""
    from ralph.doctor import run_doctor

    project_dir = None
    if hasattr(args, 'project') and args.project:
        project_dir = Path(args.project).resolve()
        if not project_dir.exists():
            print(f"Warning: Project directory does not exist: {project_dir}", file=sys.stderr)
            project_dir = None

    return run_doctor(project_dir)


def handle_analyze(args):
    """Handle 'ralph analyze' command."""
    from ralph.analyzer import BacklogAnalyzer

    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    analyzer = BacklogAnalyzer(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        dry_run=args.dry_run,
        save_analysis=args.save_analysis
    )

    return analyzer.analyze()


def handle_refine(args):
    """Handle 'ralph refine PROMPT' command."""
    from ralph.refiner import BacklogRefiner

    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    refiner = BacklogRefiner(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        dry_run=args.dry_run
    )

    return refiner.refine(args.prompt)


def handle_refine_architecture(args):
    """Handle 'ralph refine-architecture PROMPT' command."""
    from ralph.architecture_refiner import ArchitectureRefiner

    project_dir = resolve_project_dir(args)

    refiner = ArchitectureRefiner(
        project_dir=project_dir,
        provider=args.provider,
        dry_run=args.dry_run
    )

    return refiner.refine(args.prompt)


def handle_improve(args):
    """Handle 'ralph improve' command."""
    from ralph.improver import BacklogImprover

    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    improver = BacklogImprover(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        threshold=args.threshold,
        max_iterations=args.max_improve_iterations,
        dry_run=args.dry_run
    )

    return improver.improve()


def handle_mark_complete(args):
    """Handle 'ralph mark-complete ITEM_ID' command."""
    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    orchestrator = BacklogOrchestrator(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        auto_push=False,
        dry_run=False,
        continue_on_error=False
    )

    backlog = orchestrator.load_backlog()
    orchestrator.mark_item_done(backlog, args.item_id)
    orchestrator.save_backlog(backlog)
    print(f"✓ Marked {args.item_id} as complete")
    return 0


def handle_mark_ready(args):
    """Handle 'ralph mark-ready ITEM_ID' command."""
    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    orchestrator = BacklogOrchestrator(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        auto_push=False,
        dry_run=False,
        continue_on_error=False
    )

    backlog = orchestrator.load_backlog()
    orchestrator.mark_work_complete(backlog, args.item_id)
    orchestrator.save_backlog(backlog)
    print(f"✓ Marked {args.item_id} as ready for validation")
    return 0


def handle_reset_item(args):
    """Handle 'ralph reset-item ITEM_ID' command."""
    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    orchestrator = BacklogOrchestrator(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        auto_push=False,
        dry_run=False,
        continue_on_error=False
    )

    backlog = orchestrator.load_backlog()
    items = backlog.get('items', [])
    found = False
    for item in items:
        if item['id'] == args.item_id:
            item['status'] = 'todo'
            item.pop('startedAt', None)
            item.pop('workCompletedAt', None)
            item.pop('completedAt', None)
            for deliverable in item.get('deliverables', []):
                deliverable['done'] = False
            for criterion in item.get('exitCriteria', []):
                criterion['done'] = False
            found = True
            break

    if not found:
        print(f"Error: Item not found: {args.item_id}", file=sys.stderr)
        return 1

    orchestrator.save_backlog(backlog)
    print(f"✓ Reset {args.item_id} to todo status")
    return 0


def handle_init(args):
    """Handle 'ralph init PROMPT' command."""
    from ralph.initializer import BacklogInitializer

    project_dir = resolve_project_dir(args)

    # Check git repository exists
    if not (project_dir / ".git").exists():
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("Error: Not a git repository", file=sys.stderr)
            print("\nRalph Loop requires a git repository to be initialized first.", file=sys.stderr)
            print("Initialize one with: git init", file=sys.stderr)
            return 1

    backlog_path = resolve_backlog_path(args, project_dir, check_exists=False)

    initializer = BacklogInitializer(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        dry_run=args.dry_run
    )

    return initializer.initialize(args.prompt)


def handle_validate(args):
    """Handle 'ralph validate' command."""
    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    orchestrator = BacklogOrchestrator(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        auto_push=False,
        dry_run=False,
        continue_on_error=False
    )

    if orchestrator.validate_backlog():
        print("✓ Backlog is valid")
        return 0
    else:
        return 1


def handle_show_next(args):
    """Handle 'ralph show-next' command."""
    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    orchestrator = BacklogOrchestrator(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        auto_push=False,
        dry_run=False,
        continue_on_error=False
    )

    if not orchestrator.validate_backlog():
        return 1

    backlog = orchestrator.load_backlog()
    next_item = orchestrator.select_next_item(backlog)

    if next_item:
        print(f"Next item: {next_item['id']}")
        print(f"  Title: {next_item['title']}")
        print(f"  Priority: {next_item['priority']}")
        print(f"  Order: {next_item['order']}")
    else:
        print("No eligible items to execute")

    return 0


def handle_run(args):
    """Handle 'ralph run' command (main orchestration loop)."""
    project_dir = resolve_project_dir(args)
    backlog_path = resolve_backlog_path(args, project_dir)

    orchestrator = BacklogOrchestrator(
        project_dir=project_dir,
        backlog_path=backlog_path,
        provider=args.provider,
        auto_push=args.auto_push,
        dry_run=args.dry_run,
        continue_on_error=args.continue_on_error
    )

    # Check git repository exists
    if not orchestrator.check_git_repo():
        print("Error: Not a git repository", file=sys.stderr)
        print("\nRalph Loop requires a git repository to track changes.", file=sys.stderr)
        print("Initialize one with: git init", file=sys.stderr)
        return 1

    # Check git status
    if not orchestrator.check_git_clean():
        print("Error: Working tree is not clean. Commit or stash changes first.", file=sys.stderr)
        return 1

    # Acquire lock
    if not orchestrator.acquire_lock():
        print("Error: Another ralph-loop instance is running (lock exists)", file=sys.stderr)
        return 1

    try:
        # Git fetch
        if not orchestrator.git_fetch():
            return 1

        # Run main loop
        return orchestrator.run_loop(max_iterations=args.max_iterations)

    finally:
        orchestrator.release_lock()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ralph Loop - Provider-agnostic orchestration for agent-driven development",
        epilog="""
Examples:
  ralph init "Build a web scraper in Python"
  ralph run --max-iterations 10 --auto-push
  ralph analyze --save-analysis
  ralph improve --threshold 80
  ralph doctor
  ralph item show-next
  ralph item mark-complete ITEM-1

For detailed help on a specific command:
  ralph COMMAND --help
  ralph item --help

YOLO mode (auto-approve all actions) is always enabled.
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global arguments
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
        choices=['qwen', 'claude', 'codex', 'mock'],
        help='Agent provider to use (default: qwen)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    # Create subparsers
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # ralph run
    run_parser = subparsers.add_parser(
        'run',
        help='Run main orchestration loop (default). Options: --max-iterations N, --auto-push, --continue-on-error'
    )
    run_parser.add_argument(
        '--max-iterations',
        type=int,
        default=100,
        metavar='N',
        help='Maximum number of loop iterations (default: 100)'
    )
    run_parser.add_argument(
        '--auto-push',
        action='store_true',
        help='Automatically push commits to remote after each completed item'
    )
    run_parser.add_argument(
        '--continue-on-error',
        action='store_true',
        help='Continue to next iteration even if work phase fails'
    )

    # ralph init
    init_parser = subparsers.add_parser(
        'init',
        help='Initialize backlog from natural language prompt. Usage: ralph init PROMPT'
    )
    init_parser.add_argument('prompt', type=str, help='Project description (e.g., "Build a web scraper in Python")')

    # ralph doctor
    subparsers.add_parser('doctor', help='Run health checks for providers and system dependencies')

    # ralph analyze
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze backlog for automation readiness. Options: --save-analysis'
    )
    analyze_parser.add_argument(
        '--save-analysis',
        action='store_true',
        help='Save analysis to .ralph/backlog-analysis.json'
    )

    # ralph refine
    refine_parser = subparsers.add_parser(
        'refine',
        help='Refine backlog using AI agent. Usage: ralph refine PROMPT'
    )
    refine_parser.add_argument('prompt', type=str, help='Refinement instructions')

    # ralph refine-architecture
    refine_arch_parser = subparsers.add_parser(
        'refine-architecture',
        help='Refine architecture document using AI agent. Usage: ralph refine-architecture PROMPT'
    )
    refine_arch_parser.add_argument('prompt', type=str, help='Architecture refinement instructions')

    # ralph improve
    improve_parser = subparsers.add_parser(
        'improve',
        help='Iteratively improve backlog until threshold is met. Options: --threshold SCORE, --max-improve-iterations N'
    )
    improve_parser.add_argument(
        '--threshold',
        type=int,
        default=75,
        metavar='SCORE',
        help='Target quality score (1-100, default: 75)'
    )
    improve_parser.add_argument(
        '--max-improve-iterations',
        type=int,
        default=10,
        metavar='N',
        help='Maximum improvement iterations (default: 10)'
    )

    # ralph validate
    subparsers.add_parser('validate', help='Validate backlog.json and exit')

    # ralph item (group for item management commands)
    item_parser = subparsers.add_parser(
        'item',
        help='Manage backlog items (show-next, mark-complete, mark-ready, reset)'
    )
    item_subparsers = item_parser.add_subparsers(dest='item_command', help='Item operations')

    # ralph item show-next
    item_subparsers.add_parser(
        'show-next',
        help='Show next item that would be executed'
    )

    # ralph item mark-complete
    item_mark_complete_parser = item_subparsers.add_parser(
        'mark-complete',
        help='Mark an item as complete (bypasses validation)'
    )
    item_mark_complete_parser.add_argument('item_id', type=str, metavar='ITEM_ID', help='Item ID to mark as complete')

    # ralph item mark-ready
    item_mark_ready_parser = item_subparsers.add_parser(
        'mark-ready',
        help='Mark an item as ready for validation'
    )
    item_mark_ready_parser.add_argument('item_id', type=str, metavar='ITEM_ID', help='Item ID to mark as ready')

    # ralph item reset
    item_reset_parser = item_subparsers.add_parser(
        'reset',
        help='Reset an item back to todo status'
    )
    item_reset_parser.add_argument('item_id', type=str, metavar='ITEM_ID', help='Item ID to reset')

    # ralph list-providers
    subparsers.add_parser('list-providers', help='List available providers and exit')

    args = parser.parse_args()

    # Default to 'run' if no subcommand given
    if args.command is None:
        args.command = 'run'
        # Set default values for run command when invoked without subcommand
        if not hasattr(args, 'max_iterations'):
            args.max_iterations = 100
        if not hasattr(args, 'auto_push'):
            args.auto_push = False
        if not hasattr(args, 'continue_on_error'):
            args.continue_on_error = False

    # Dispatch to handlers
    if args.command == 'item':
        # Handle item subcommands
        if not hasattr(args, 'item_command') or args.item_command is None:
            print("Error: 'ralph item' requires a subcommand", file=sys.stderr)
            print("Run 'ralph item --help' for available commands", file=sys.stderr)
            sys.exit(1)

        item_handlers = {
            'show-next': handle_show_next,
            'mark-complete': handle_mark_complete,
            'mark-ready': handle_mark_ready,
            'reset': handle_reset_item,
        }
        exit_code = item_handlers[args.item_command](args)
    else:
        # Handle top-level commands
        handlers = {
            'run': handle_run,
            'init': handle_init,
            'doctor': handle_doctor,
            'analyze': handle_analyze,
            'refine': handle_refine,
            'refine-architecture': handle_refine_architecture,
            'improve': handle_improve,
            'validate': handle_validate,
            'list-providers': handle_list_providers,
        }
        exit_code = handlers[args.command](args)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
