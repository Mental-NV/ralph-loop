#!/usr/bin/env python3
"""
Backlog improver for Ralph Loop.

Handles iterative improvement of backlog.json until quality threshold is met.
"""

import contextlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ralph.paths import RalphPaths
from ralph.providers import get_provider, list_available_providers


class BacklogImprover:
    """Iteratively improves backlog until quality threshold is met."""

    def __init__(
        self,
        project_dir: Path,
        backlog_path: Path,
        provider: str = "qwen",
        threshold: int = 75,
        max_iterations: int = 10,
        dry_run: bool = False
    ):
        """
        Initialize BacklogImprover.

        Args:
            project_dir: Target project directory
            backlog_path: Path to backlog.json
            provider: Agent provider name (qwen, claude, codex)
            threshold: Target quality score (1-100)
            max_iterations: Maximum improvement iterations
            dry_run: If True, preview without making changes
        """
        self.project_dir = project_dir
        self.backlog_path = backlog_path
        self.provider_name = provider
        self.threshold = threshold
        self.max_iterations = max_iterations
        self.dry_run = dry_run

        # Validate threshold
        if not 1 <= threshold <= 100:
            print(f"Error: Threshold must be between 1 and 100 (got {threshold})", file=sys.stderr)
            sys.exit(1)

        # Validate max_iterations
        if not 0 <= max_iterations <= 100:
            print(f"Error: Max iterations must be between 0 and 100 (got {max_iterations})", file=sys.stderr)
            sys.exit(1)

        # Initialize paths
        self.paths = RalphPaths(project_dir)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.improvement_log = self.paths.logs_dir / "improve" / f"improvement-{timestamp}.log"

        # Initialize provider
        try:
            self.provider = get_provider(provider)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            available = list_available_providers()
            if available:
                print(f"Available providers: {', '.join(available)}", file=sys.stderr)
            else:
                print("No providers are available on this system", file=sys.stderr)
            sys.exit(1)

        if not self.provider.is_available():
            print(f"Error: Provider '{provider}' is not available", file=sys.stderr)
            available = list_available_providers()
            if available:
                print(f"Available providers: {', '.join(available)}", file=sys.stderr)
            sys.exit(1)

    def improve(self) -> int:
        """
        Run improvement cycle.

        Returns:
            0: Success (threshold met)
            1: Error
            2: Max iterations reached without meeting threshold
        """
        print(f"Starting backlog improvement cycle", file=sys.stderr)
        print(f"Target threshold: {self.threshold}/100", file=sys.stderr)
        print(f"Max iterations: {self.max_iterations}", file=sys.stderr)
        print(f"Provider: {self.provider_name}", file=sys.stderr)
        print(file=sys.stderr)

        iteration_history = []

        for iteration in range(1, self.max_iterations + 1):
            print(f"{'='*80}", file=sys.stderr)
            print(f"Iteration {iteration}/{self.max_iterations}", file=sys.stderr)
            print(f"{'='*80}", file=sys.stderr)

            # Step 1: Run analysis
            analysis = self._run_analysis()
            if not analysis:
                return 1

            score = analysis['overall_score']
            ready = analysis['ready_for_auto']

            # Log progress
            self._log_progress(iteration, score, ready, analysis)
            iteration_history.append({'iteration': iteration, 'score': score})

            # Step 2: Check threshold
            if score >= self.threshold:
                print(f"\n✓ Backlog meets threshold! (score: {score}/100)", file=sys.stderr)
                self._print_summary(iteration_history)
                return 0

            # Step 3: Check for stalled progress
            if self._is_stalled(iteration_history):
                print(f"\n⚠ Progress stalled (same score for 3 iterations)", file=sys.stderr)
                print(f"Current score: {score}/100, Target: {self.threshold}/100", file=sys.stderr)
                self._print_summary(iteration_history)
                return 2

            # Step 4: Extract follow-up prompt
            follow_up_prompt = analysis.get('follow_up_prompt')
            if not follow_up_prompt:
                print("Error: No follow-up prompt in analysis", file=sys.stderr)
                return 1

            print(f"\nCurrent score: {score}/100 (target: {self.threshold}/100)", file=sys.stderr)
            print(f"Applying refinements...", file=sys.stderr)

            # Step 5: Run refinement
            if not self._run_refinement(follow_up_prompt):
                return 1

            print(f"✓ Refinement complete", file=sys.stderr)
            print(file=sys.stderr)

        # Max iterations reached
        print(f"\n⚠ Max iterations reached ({self.max_iterations})", file=sys.stderr)
        print(f"Final score: {iteration_history[-1]['score']}/100", file=sys.stderr)
        print(f"Target: {self.threshold}/100", file=sys.stderr)
        self._print_summary(iteration_history)
        return 2

    def _run_analysis(self) -> Optional[Dict[str, Any]]:
        """Run analysis and return parsed JSON."""
        from ralph.analyzer import BacklogAnalyzer

        analyzer = BacklogAnalyzer(
            project_dir=self.project_dir,
            backlog_path=self.backlog_path,
            provider=self.provider_name,
            dry_run=self.dry_run,
            save_analysis=True,
            threshold=self.threshold
        )

        # Run analysis (no stdout capture needed)
        exit_code = analyzer.analyze()

        if exit_code != 0:
            print("Error: Analysis failed", file=sys.stderr)
            return None

        # Read analysis from saved file
        analysis_path = self.paths.analysis_file
        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Analysis file not found: {analysis_path}", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse analysis JSON: {e}", file=sys.stderr)
            return None

    def _run_refinement(self, prompt: str) -> bool:
        """Run refinement with given prompt."""
        from ralph.refiner import BacklogRefiner

        refiner = BacklogRefiner(
            project_dir=self.project_dir,
            backlog_path=self.backlog_path,
            provider=self.provider_name,
            dry_run=self.dry_run
        )

        exit_code = refiner.refine(prompt)
        return exit_code == 0

    def _is_stalled(self, history: List[Dict[str, Any]]) -> bool:
        """Check if progress has stalled (same score for 3+ iterations)."""
        if len(history) < 3:
            return False

        last_three = history[-3:]
        scores = [h['score'] for h in last_three]
        return len(set(scores)) == 1  # All same score

    def _log_progress(self, iteration: int, score: float, ready: bool, analysis: Dict[str, Any]) -> None:
        """Log iteration progress to file."""
        self.paths.ensure_dirs(self.improvement_log.parent)

        with open(self.improvement_log, 'a', encoding='utf-8') as f:
            f.write(f"Iteration {iteration}:\n")
            f.write(f"  Score: {score}/100\n")
            f.write(f"  Ready: {ready}\n")
            f.write(f"  Recommendations: {len(analysis.get('recommendations', []))}\n")
            f.write(f"  Issues: {len(analysis.get('issues', []))}\n")
            f.write("\n")

    def _print_summary(self, history: List[Dict[str, Any]]) -> None:
        """Print improvement summary."""
        print(f"\n{'='*80}", file=sys.stderr)
        print("Improvement Summary", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)

        for h in history:
            print(f"  Iteration {h['iteration']}: {h['score']}/100", file=sys.stderr)

        if len(history) > 1:
            improvement = history[-1]['score'] - history[0]['score']
            print(f"\nTotal improvement: {improvement:+.1f} points", file=sys.stderr)

        print(f"\nDetailed log: {self.improvement_log}", file=sys.stderr)
