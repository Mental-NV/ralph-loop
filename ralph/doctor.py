#!/usr/bin/env python3
"""
Health check system for Ralph Loop.

Validates provider installation, authentication, system dependencies,
and project setup.
"""

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional


class CheckStatus(Enum):
    """Status of a health check."""
    PASS = "✓"
    FAIL = "✗"
    WARN = "⚠"
    SKIP = "○"


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: CheckStatus
    message: str
    suggestion: Optional[str] = None


class HealthChecker:
    """Performs health checks for Ralph Loop."""

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir
        self.results: List[CheckResult] = []

    def run_all_checks(self) -> bool:
        """Run all health checks. Returns True if all critical checks pass."""
        self.check_system_dependencies()
        self.check_provider_installation()
        self.check_provider_authentication()

        if self.project_dir:
            self.check_project_setup()

        return self.print_results()

    def check_system_dependencies(self) -> None:
        """Check system-level dependencies."""
        # Python version check
        py_version = sys.version_info
        if py_version >= (3, 9):
            self.results.append(CheckResult(
                name="Python version",
                status=CheckStatus.PASS,
                message=f"Python {py_version.major}.{py_version.minor}.{py_version.micro} (>= 3.9 required)"
            ))
        else:
            self.results.append(CheckResult(
                name="Python version",
                status=CheckStatus.FAIL,
                message=f"Python {py_version.major}.{py_version.minor}.{py_version.micro} (< 3.9)",
                suggestion="Python 3.9+ required. Upgrade Python."
            ))

        # Git installation check
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                version = result.stdout.strip().replace("git version ", "")
                self.results.append(CheckResult(
                    name="Git installed",
                    status=CheckStatus.PASS,
                    message=f"Git {version}"
                ))

                # Git user.name check
                result = subprocess.run(
                    ["git", "config", "--global", "user.name"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    self.results.append(CheckResult(
                        name="Git user.name",
                        status=CheckStatus.PASS,
                        message="Configured"
                    ))
                else:
                    self.results.append(CheckResult(
                        name="Git user.name",
                        status=CheckStatus.FAIL,
                        message="Not configured",
                        suggestion="Run: git config --global user.name 'Your Name'"
                    ))

                # Git user.email check
                result = subprocess.run(
                    ["git", "config", "--global", "user.email"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    self.results.append(CheckResult(
                        name="Git user.email",
                        status=CheckStatus.PASS,
                        message="Configured"
                    ))
                else:
                    self.results.append(CheckResult(
                        name="Git user.email",
                        status=CheckStatus.FAIL,
                        message="Not configured",
                        suggestion="Run: git config --global user.email 'you@example.com'"
                    ))
            else:
                self.results.append(CheckResult(
                    name="Git installed",
                    status=CheckStatus.FAIL,
                    message="Git not found",
                    suggestion="Install git to use Ralph Loop"
                ))
        except FileNotFoundError:
            self.results.append(CheckResult(
                name="Git installed",
                status=CheckStatus.FAIL,
                message="Git not found",
                suggestion="Install git to use Ralph Loop"
            ))

        # jsonschema library check
        try:
            import jsonschema
            self.results.append(CheckResult(
                name="jsonschema library",
                status=CheckStatus.PASS,
                message="Installed"
            ))
        except ImportError:
            self.results.append(CheckResult(
                name="jsonschema library",
                status=CheckStatus.FAIL,
                message="Not found",
                suggestion="Run: pip install jsonschema"
            ))

    def check_provider_installation(self) -> None:
        """Check if provider CLIs are installed."""
        from ralph.providers import QwenProvider, ClaudeCodeProvider, CodexProvider

        providers = [
            (QwenProvider(), "Qwen"),
            (ClaudeCodeProvider(), "Claude Code"),
            (CodexProvider(), "Codex")
        ]

        for provider, name in providers:
            if provider.is_available():
                # Try to get version info
                try:
                    result = subprocess.run(
                        [provider.get_name(), "--version"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=5
                    )
                    version_info = ""
                    if result.returncode == 0 and result.stdout.strip():
                        version_info = f" ({result.stdout.strip()})"
                    self.results.append(CheckResult(
                        name=f"{name} CLI",
                        status=CheckStatus.PASS,
                        message=f"Installed{version_info}"
                    ))
                except (subprocess.TimeoutExpired, Exception):
                    self.results.append(CheckResult(
                        name=f"{name} CLI",
                        status=CheckStatus.PASS,
                        message="Installed"
                    ))
            else:
                suggestion = f"Install {name} CLI"
                if name == "Claude Code":
                    suggestion = "Install from: https://docs.anthropic.com/claude-code"
                self.results.append(CheckResult(
                    name=f"{name} CLI",
                    status=CheckStatus.FAIL,
                    message="Not found",
                    suggestion=suggestion
                ))

    def check_provider_authentication(self) -> None:
        """Check if providers are authenticated."""
        from ralph.providers import QwenProvider, ClaudeCodeProvider, CodexProvider

        providers = [
            (QwenProvider(), "Qwen"),
            (ClaudeCodeProvider(), "Claude Code"),
            (CodexProvider(), "Codex")
        ]

        for provider, name in providers:
            if not provider.is_available():
                self.results.append(CheckResult(
                    name=f"{name} authentication",
                    status=CheckStatus.SKIP,
                    message="Skipped (not installed)"
                ))
                continue

            is_authenticated, message = provider.check_authentication()
            if is_authenticated:
                self.results.append(CheckResult(
                    name=f"{name} authentication",
                    status=CheckStatus.PASS,
                    message="Authenticated"
                ))
            else:
                self.results.append(CheckResult(
                    name=f"{name} authentication",
                    status=CheckStatus.FAIL,
                    message="Not authenticated",
                    suggestion=message
                ))

    def check_project_setup(self) -> None:
        """Check project-specific setup (optional)."""
        if not self.project_dir:
            return

        # Check git repository
        git_dir = self.project_dir / ".git"
        if git_dir.exists() and git_dir.is_dir():
            self.results.append(CheckResult(
                name="Git repository",
                status=CheckStatus.PASS,
                message="Initialized"
            ))
        else:
            self.results.append(CheckResult(
                name="Git repository",
                status=CheckStatus.FAIL,
                message="Not a git repository",
                suggestion="Run: git init"
            ))

        # Check backlog.json exists
        backlog_path = self.project_dir / "docs" / "backlog.json"
        if backlog_path.exists():
            self.results.append(CheckResult(
                name="Backlog file",
                status=CheckStatus.PASS,
                message="Found at docs/backlog.json"
            ))

            # Validate backlog.json
            from ralph.validator import validate_backlog
            try:
                if validate_backlog(backlog_path):
                    self.results.append(CheckResult(
                        name="Backlog validation",
                        status=CheckStatus.PASS,
                        message="Valid"
                    ))
                else:
                    self.results.append(CheckResult(
                        name="Backlog validation",
                        status=CheckStatus.FAIL,
                        message="Validation failed",
                        suggestion="Run: ralph --validate-only"
                    ))
            except Exception as e:
                self.results.append(CheckResult(
                    name="Backlog validation",
                    status=CheckStatus.FAIL,
                    message=f"Error: {str(e)[:100]}",
                    suggestion="Run: ralph --validate-only"
                ))
        else:
            self.results.append(CheckResult(
                name="Backlog file",
                status=CheckStatus.FAIL,
                message="Not found at docs/backlog.json",
                suggestion="Run: ralph --init 'Project description'"
            ))

    def print_results(self) -> bool:
        """Print formatted results. Returns True if all critical checks pass."""
        print("Ralph Loop Health Check")
        print("=======================")
        print()

        # Group results by category
        categories = {
            "System Dependencies": [],
            "Provider Installation": [],
            "Provider Authentication": [],
            "Project Setup": []
        }

        for result in self.results:
            if "Python" in result.name or "Git" in result.name or "jsonschema" in result.name:
                categories["System Dependencies"].append(result)
            elif "CLI" in result.name:
                categories["Provider Installation"].append(result)
            elif "authentication" in result.name:
                categories["Provider Authentication"].append(result)
            else:
                categories["Project Setup"].append(result)

        # Print each category
        for category, results in categories.items():
            if not results:
                continue

            print(category)
            for result in results:
                status_icon = result.status.value
                print(f"  {status_icon} {result.name}: {result.message}")
                if result.suggestion:
                    print(f"    → {result.suggestion}")
            print()

        # Print summary
        fail_count = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        warn_count = sum(1 for r in self.results if r.status == CheckStatus.WARN)

        print("Summary")
        print("-------")
        if fail_count == 0 and warn_count == 0:
            print("All checks passed!")
        else:
            if warn_count > 0:
                print(f"{warn_count} warning(s) found.")
            if fail_count > 0:
                print(f"{fail_count} error(s) found.")
                print()
                print("Critical issues:")
                for result in self.results:
                    if result.status == CheckStatus.FAIL:
                        print(f"  - {result.name}: {result.message}")

        if not self.project_dir:
            print()
            print("Run with --project <path> to check project-specific setup.")

        return fail_count == 0


def run_doctor(project_dir: Optional[Path] = None) -> int:
    """
    Run health checks and return exit code.
    Returns 0 if all critical checks pass, 1 otherwise.
    """
    checker = HealthChecker(project_dir)
    success = checker.run_all_checks()
    return 0 if success else 1
