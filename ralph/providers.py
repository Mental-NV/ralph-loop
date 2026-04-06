#!/usr/bin/env python3
"""
Provider abstraction for Ralph Loop.

Supports Qwen, Claude Code, and Codex backends.
"""

import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple


class AgentProvider(ABC):
    """Abstract base class for agent providers."""

    @abstractmethod
    def get_name(self) -> str:
        """Return provider name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider CLI is available."""
        pass

    @abstractmethod
    def build_command(
        self,
        prompt: str,
        project_dir: Path,
        yolo: bool = False
    ) -> List[str]:
        """Build command to execute agent with prompt."""
        pass

    @abstractmethod
    def supports_rich_progress(self) -> bool:
        """Return True if provider supports structured progress output."""
        pass

    @abstractmethod
    def get_progress_renderer(self, project_dir: Path) -> Optional[List[str]]:
        """
        Return command to pipe output through for progress rendering.
        Returns None if no renderer needed.
        """
        pass

    @abstractmethod
    def check_authentication(self) -> Tuple[bool, str]:
        """
        Check if provider is authenticated and ready to use.
        Returns (is_authenticated, message).
        """
        pass


class QwenProvider(AgentProvider):
    """Qwen agent provider."""

    def get_name(self) -> str:
        return "qwen"

    def is_available(self) -> bool:
        try:
            subprocess.run(
                ["qwen", "--version"],
                capture_output=True,
                check=False
            )
            return True
        except FileNotFoundError:
            return False

    def build_command(
        self,
        prompt: str,
        project_dir: Path,
        yolo: bool = False
    ) -> List[str]:
        cmd = [
            "qwen",
            "--output-format", "stream-json",
            "--include-partial-messages",
            "--prompt", prompt
        ]
        if yolo:
            cmd.insert(1, "--yolo")
        return cmd

    def supports_rich_progress(self) -> bool:
        return True

    def get_progress_renderer(self, project_dir: Path) -> Optional[List[str]]:
        # Use bundled renderer via python -m
        from ralph.paths import RalphPaths
        paths = RalphPaths(project_dir)
        paths.ensure_dirs(paths.qwen_stream_logs)

        return [
            sys.executable, "-m", "ralph.renderers.qwen_renderer",
            "--mode", "normal",
            "--stream-mode", "complete",
            "--raw-log-dir", str(paths.qwen_stream_logs)
        ]

    def check_authentication(self) -> Tuple[bool, str]:
        """Check Qwen authentication by running a minimal test command."""
        if not self.is_available():
            return False, "Qwen CLI not installed"

        try:
            result = subprocess.run(
                ["qwen", "--prompt", "test", "--output-format", "stream-json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return True, "Authenticated successfully"

            # Check for auth-related errors
            stderr_lower = result.stderr.lower()
            if any(word in stderr_lower for word in ["auth", "login", "token", "credential"]):
                return False, "Not authenticated. Run: qwen auth"

            return False, f"Test command failed: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            return False, "Test command timed out"
        except Exception as e:
            return False, f"Error checking authentication: {e}"


class ClaudeCodeProvider(AgentProvider):
    """Claude Code agent provider."""

    def get_name(self) -> str:
        return "claude"

    def is_available(self) -> bool:
        try:
            subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                check=False
            )
            return True
        except FileNotFoundError:
            return False

    def build_command(
        self,
        prompt: str,
        project_dir: Path,
        yolo: bool = False
    ) -> List[str]:
        cmd = [
            "claude",
            "--print",
            "--output-format", "stream-json",
            "--include-partial-messages",
            prompt
        ]
        if yolo:
            cmd.insert(1, "--dangerously-skip-permissions")
        return cmd

    def supports_rich_progress(self) -> bool:
        return False  # Best-effort line-based progress

    def get_progress_renderer(self, project_dir: Path) -> Optional[List[str]]:
        # Use bundled renderer via python -m
        return [sys.executable, "-m", "ralph.renderers.simple_renderer"]

    def check_authentication(self) -> Tuple[bool, str]:
        """Check Claude Code authentication by running a minimal test command."""
        if not self.is_available():
            return False, "Claude Code CLI not installed"

        try:
            result = subprocess.run(
                ["claude", "--print", "--dangerously-skip-permissions", "test"],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                return True, "Authenticated successfully"

            # Check for auth-related errors
            stderr_lower = result.stderr.lower()
            if any(word in stderr_lower for word in ["authentication", "api key", "login", "unauthorized"]):
                return False, "Not authenticated. Set ANTHROPIC_API_KEY or configure authentication"

            return False, f"Test command failed: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            return False, "Test command timed out"
        except Exception as e:
            return False, f"Error checking authentication: {e}"


class CodexProvider(AgentProvider):
    """Codex agent provider."""

    def get_name(self) -> str:
        return "codex"

    def is_available(self) -> bool:
        try:
            subprocess.run(
                ["codex", "--version"],
                capture_output=True,
                check=False
            )
            return True
        except FileNotFoundError:
            return False

    def build_command(
        self,
        prompt: str,
        project_dir: Path,
        yolo: bool = False
    ) -> List[str]:
        cmd = [
            "codex", "exec",
            prompt
        ]
        if yolo:
            cmd.insert(2, "--dangerously-bypass-approvals-and-sandbox")
        return cmd

    def supports_rich_progress(self) -> bool:
        return False  # Best-effort line-based progress

    def get_progress_renderer(self, project_dir: Path) -> Optional[List[str]]:
        # Use bundled renderer via python -m
        return [sys.executable, "-m", "ralph.renderers.simple_renderer"]

    def check_authentication(self) -> Tuple[bool, str]:
        """Check Codex authentication by running a minimal test command."""
        if not self.is_available():
            return False, "Codex CLI not installed"

        try:
            result = subprocess.run(
                ["codex", "exec", "test", "--dangerously-bypass-approvals-and-sandbox"],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode == 0:
                return True, "Authenticated successfully"

            # Check for auth-related errors
            stderr_lower = result.stderr.lower()
            if any(word in stderr_lower for word in ["auth", "login", "token", "not logged in"]):
                return False, "Not authenticated. Run: codex login"

            return False, f"Test command failed: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            return False, "Test command timed out"
        except Exception as e:
            return False, f"Error checking authentication: {e}"


def get_provider(name: str) -> AgentProvider:
    """Get provider by name."""
    providers = {
        "qwen": QwenProvider(),
        "claude": ClaudeCodeProvider(),
        "codex": CodexProvider(),
    }

    provider = providers.get(name.lower())
    if not provider:
        raise ValueError(f"Unknown provider: {name}. Available: {', '.join(providers.keys())}")

    return provider


def list_available_providers() -> List[str]:
    """Return list of available provider names."""
    all_providers = [
        QwenProvider(),
        ClaudeCodeProvider(),
        CodexProvider(),
    ]
    return [p.get_name() for p in all_providers if p.is_available()]
