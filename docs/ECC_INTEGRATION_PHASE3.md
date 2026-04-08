# ECC Integration Phase 3: Code Review Phase

## Overview

**Goal**: Add optional pre-validation code review using ECC language-specific reviewer agents to catch quality issues before validation.

**Priority**: P2 (Quality Assurance)  
**Effort**: 3-4 days  
**Risk**: Medium (new pipeline phase, complex error handling)

**Prerequisites**: 
- Phase 1 complete (ECC rules in ARCHITECTURE.md)
- Phase 2 complete (Skills + Build resolution)

## Context

Phases 1-2 provide guidance and resilience. Phase 3 adds quality assurance through automated code review before validation runs. This catches issues like:
- Empty catch blocks
- Hardcoded secrets
- SQL injection vulnerabilities
- Missing async/await
- Type safety issues

**Key Design Decision**: Code review is **opt-in** (disabled by default) to avoid breaking existing workflows.

## What Gets Integrated

Copy from `~/projects/everything-claude-code/agents/`:

```
ralph/
  ecc_resources/
    agents/
      # Already bundled in Phase 2:
      # - csharp-build-resolver.md
      # - python-build-resolver.md
      # - go-build-resolver.md
      # - rust-build-resolver.md
      # - java-build-resolver.md
      # - kotlin-build-resolver.md
      
      # NEW for Phase 3:
      csharp-reviewer.md
      python-reviewer.md
      go-reviewer.md
      typescript-reviewer.md
      java-reviewer.md
      kotlin-reviewer.md
      rust-reviewer.md
      code-reviewer.md          # Generic reviewer (fallback)
```

**Size**: ~200KB for 8 agents

## Implementation Steps

### Step 1: Bundle ECC Reviewer Agents

```bash
# From ralph-loop root
# agents/ directory already exists from Phase 2

# Copy reviewer agents
for agent in csharp-reviewer python-reviewer go-reviewer typescript-reviewer java-reviewer kotlin-reviewer rust-reviewer code-reviewer; do
  cp ~/projects/everything-claude-code/agents/$agent.md ralph/ecc_resources/agents/
done
```

**Verification**:
```bash
ls ralph/ecc_resources/agents/ | grep reviewer
# Should show 8 reviewer .md files
```

### Step 2: Update Backlog Schema

**File**: `ralph/schemas/backlog.schema.json`

**Add new status** to enum (around line 45):

```json
{
  "status": {
    "type": "string",
    "enum": [
      "todo",
      "in_progress",
      "ready_for_review",     // NEW
      "ready_for_validation",
      "done",
      "blocked",
      "deferred",
      "cancelled"
    ]
  }
}
```

### Step 3: Create Code Reviewer

**File**: `ralph/code_reviewer.py`

```python
"""
Code review using ECC reviewer agents.
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ReviewIssue:
    """Represents a code review issue."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    title: str
    file_path: str
    line_number: Optional[int]
    description: str
    fix_suggestion: str


@dataclass
class ReviewResult:
    """Result of code review."""
    approved: bool
    issues: List[ReviewIssue]
    summary: str


class CodeReviewer:
    """Reviews code changes using language-specific ECC agents."""
    
    def __init__(self, project_dir: Path, provider, ecc_dir: Path):
        self.project_dir = project_dir
        self.provider = provider
        self.agents_dir = ecc_dir / "agents"
    
    def review_changes(
        self,
        item: Dict,
        tech_stack: Dict
    ) -> ReviewResult:
        """
        Review code changes for item.
        
        Args:
            item: Backlog item
            tech_stack: Detected tech stack
        
        Returns:
            ReviewResult with issues and approval status
        """
        # Get git diff
        diff = self._get_git_diff()
        
        if not diff:
            return ReviewResult(
                approved=True,
                issues=[],
                summary="No changes to review"
            )
        
        # Detect language
        language = self._detect_language(tech_stack)
        
        # Load reviewer agent
        agent_path = self._get_reviewer_agent_path(language)
        
        if not agent_path or not agent_path.exists():
            return ReviewResult(
                approved=True,
                issues=[],
                summary=f"No reviewer agent available for {language}"
            )
        
        agent_content = agent_path.read_text(encoding='utf-8')
        
        # Build review prompt
        prompt = self._build_review_prompt(agent_content, diff, item)
        
        # Invoke provider
        print(f"\n🔍 Running code review using {agent_path.stem}...")
        
        try:
            cmd = self.provider.build_command(prompt, self.project_dir, yolo=True)
            
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                return ReviewResult(
                    approved=True,  # Don't block on reviewer failure
                    issues=[],
                    summary=f"Reviewer agent failed: {result.stderr[:200]}"
                )
            
            # Parse review output
            issues = self._parse_review_output(result.stdout)
            
            # Determine approval
            critical_or_high = [i for i in issues if i.severity in ['CRITICAL', 'HIGH']]
            approved = len(critical_or_high) == 0
            
            summary = self._build_summary(issues)
            
            return ReviewResult(
                approved=approved,
                issues=issues,
                summary=summary
            )
        
        except subprocess.TimeoutExpired:
            return ReviewResult(
                approved=True,  # Don't block on timeout
                issues=[],
                summary="Code review timed out"
            )
        except Exception as e:
            return ReviewResult(
                approved=True,  # Don't block on error
                issues=[],
                summary=f"Code review error: {e}"
            )
    
    def _get_git_diff(self) -> str:
        """Get git diff of uncommitted changes."""
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        return result.stdout
    
    def _detect_language(self, tech_stack: Dict) -> Optional[str]:
        """Detect language from tech stack."""
        backend = tech_stack.get('backend', '').lower()
        frontend = tech_stack.get('frontend', '').lower()
        
        # Backend language detection
        if '.net' in backend or 'c#' in backend:
            return 'csharp'
        elif 'python' in backend:
            return 'python'
        elif 'go' in backend:
            return 'go'
        elif 'java' in backend:
            return 'java'
        elif 'rust' in backend:
            return 'rust'
        elif 'kotlin' in backend:
            return 'kotlin'
        elif 'node' in backend or 'typescript' in backend:
            return 'typescript'
        
        # Frontend language detection (fallback)
        if 'typescript' in frontend or 'react' in frontend:
            return 'typescript'
        
        return None
    
    def _get_reviewer_agent_path(self, language: Optional[str]) -> Optional[Path]:
        """Get path to reviewer agent."""
        if not language:
            # Fallback to generic reviewer
            return self.agents_dir / "code-reviewer.md"
        
        agent_path = self.agents_dir / f"{language}-reviewer.md"
        
        if agent_path.exists():
            return agent_path
        
        # Fallback to generic reviewer
        return self.agents_dir / "code-reviewer.md"
    
    def _build_review_prompt(self, agent_content: str, diff: str, item: Dict) -> str:
        """Build prompt for code reviewer agent."""
        return f"""{agent_content}

# Code Review Request

Review the following changes for backlog item: {item['title']}

## Git Diff

```diff
{diff}
```

## Review Instructions

1. Analyze the changes for security, quality, and best practices
2. Report issues in this format:

[SEVERITY] Issue title
File: path/to/file.ext:line
Issue: Description of the problem
Fix: Suggested fix

Where SEVERITY is one of: CRITICAL, HIGH, MEDIUM, LOW

3. Provide a summary at the end

Begin your review now.
"""
    
    def _parse_review_output(self, output: str) -> List[ReviewIssue]:
        """Parse review output into structured issues."""
        issues = []
        
        # Pattern: [SEVERITY] Title
        # File: path:line
        # Issue: description
        # Fix: suggestion
        
        pattern = r'\[(CRITICAL|HIGH|MEDIUM|LOW)\]\s+(.+?)\n\s*File:\s+(.+?)(?::(\d+))?\n\s*Issue:\s+(.+?)\n\s*Fix:\s+(.+?)(?=\n\[|$)'
        
        matches = re.finditer(pattern, output, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            severity = match.group(1)
            title = match.group(2).strip()
            file_path = match.group(3).strip()
            line_number = int(match.group(4)) if match.group(4) else None
            description = match.group(5).strip()
            fix_suggestion = match.group(6).strip()
            
            issues.append(ReviewIssue(
                severity=severity,
                title=title,
                file_path=file_path,
                line_number=line_number,
                description=description,
                fix_suggestion=fix_suggestion
            ))
        
        return issues
    
    def _build_summary(self, issues: List[ReviewIssue]) -> str:
        """Build summary of review results."""
        if not issues:
            return "✓ No issues found"
        
        by_severity = {
            'CRITICAL': [i for i in issues if i.severity == 'CRITICAL'],
            'HIGH': [i for i in issues if i.severity == 'HIGH'],
            'MEDIUM': [i for i in issues if i.severity == 'MEDIUM'],
            'LOW': [i for i in issues if i.severity == 'LOW']
        }
        
        parts = []
        for severity, items in by_severity.items():
            if items:
                parts.append(f"{len(items)} {severity}")
        
        return f"Found {len(issues)} issue(s): " + ", ".join(parts)
```

### Step 4: Add Review Phase to Orchestrator

**File**: `ralph/orchestrator.py`

**Add new method** after `mark_work_complete()`:

```python
def mark_ready_for_review(self, backlog: Dict[str, Any], item_id: str) -> None:
    """Mark work phase complete and transition to ready_for_review."""
    items = backlog.get('items', [])
    for item in items:
        if item['id'] == item_id:
            item['status'] = 'ready_for_review'
            item['workCompletedAt'] = datetime.now(timezone.utc).isoformat()
            break
```

**Modify** `run_loop()` method to add review phase (around line 661):

```python
def run_loop(self, max_iterations: Optional[int] = None) -> int:
    """
    Main execution loop with multi-phase execution.
    Returns exit code: 0 if all items done, 1 on error, 2 if work remains.
    """
    iteration = 0

    while True:
        iteration += 1
        if max_iterations and iteration > max_iterations:
            print(f"\nReached max iterations ({max_iterations}), stopping")
            return 2

        print(f"\n{'='*80}")
        print(f"Ralph Loop - Iteration {iteration}")
        print(f"{'='*80}")

        # Validate backlog
        if not self.validate_backlog():
            return 1

        # Load backlog
        backlog = self.load_backlog()
        items = backlog.get('items', [])

        # Check for items in ready_for_review status (NEW)
        if self.enable_code_review:
            ready_for_review = [i for i in items if i['status'] == 'ready_for_review']
            
            if ready_for_review:
                item = ready_for_review[0]
                print(f"\nCode review phase for: {item['title']}")
                print(f"ID: {item['id']}")
                
                # Run code review
                review_result = self._run_code_review(item)
                
                # Handle review results
                if not review_result.approved and not self.auto_fix_review:
                    # Report-only mode: log issues, continue
                    print(f"\n⚠️  Code review found issues (report-only mode):")
                    self._print_review_issues(review_result.issues)
                    print(f"\nContinuing to validation (--auto-fix-review not enabled)")
                elif not review_result.approved and self.auto_fix_review:
                    # Auto-fix mode: attempt to fix issues
                    print(f"\n⚠️  Code review found issues (auto-fix mode):")
                    self._print_review_issues(review_result.issues)
                    print(f"\nAttempting to fix issues...")
                    
                    # Invoke agent to fix issues
                    fix_success = self._fix_review_issues(item, review_result.issues)
                    
                    if not fix_success:
                        print(f"\nFailed to fix review issues", file=sys.stderr)
                        return 1
                    
                    # Re-review after fixes
                    print(f"\nRe-reviewing after fixes...")
                    review_result = self._run_code_review(item)
                    
                    if not review_result.approved:
                        print(f"\nStill have issues after auto-fix", file=sys.stderr)
                        self._print_review_issues(review_result.issues)
                        return 1
                
                # Transition to ready_for_validation
                backlog = self.load_backlog()
                self.mark_work_complete(backlog, item['id'])
                self.save_backlog(backlog)
                
                print(f"\n✓ Code review complete: {item['title']}")
                continue

        # Check for items in ready_for_validation status
        ready_items = [i for i in items if i['status'] == 'ready_for_validation']

        if ready_items:
            # Process validation phase for ready items
            item = ready_items[0]
            print(f"\nValidation phase for: {item['title']}")
            print(f"ID: {item['id']}")
            print(f"Work completed at: {item.get('workCompletedAt', 'unknown')}")

            # Run validation
            if not self.run_validation_commands(item):
                print(f"\nValidation failed for {item['id']}", file=sys.stderr)
                return 1

            # Mark item as done
            backlog = self.load_backlog()
            self.mark_item_done(backlog, item['id'])
            self.save_backlog(backlog)

            print(f"\n✓ Completed: {item['title']}")

            # Create git commit
            commit_message = self.build_commit_message(item)
            if not self.git_commit(commit_message):
                print("Warning: git commit failed", file=sys.stderr)

            # Git push if auto-push enabled
            if self.auto_push:
                if not self.git_push():
                    print("Warning: git push failed", file=sys.stderr)

            continue

        # Select next item to start
        next_item = self.select_next_item(backlog)

        if not next_item:
            # Check if any items are in_progress or ready_for_review
            in_progress = [i for i in items if i['status'] in ['in_progress', 'ready_for_review']]

            if in_progress:
                print("\nNo new items to start, but items in progress remain:")
                for item in in_progress:
                    print(f"  - {item['id']}: {item['status']}")
                return 2

            # Check if all items are done
            todo_count = sum(1 for i in items if i['status'] == 'todo')
            done_count = sum(1 for i in items if i['status'] == 'done')

            if todo_count == 0:
                print(f"\n✓ All items complete! ({done_count} done)")
                return 0
            else:
                print(f"\nNo eligible items to execute ({todo_count} todo, {done_count} done)")
                print("Remaining items may have unsatisfied dependencies or be blocked")
                return 2

        # Mark item as started
        self.mark_item_started(backlog, next_item['id'])
        self.save_backlog(backlog)

        # Execute work phase
        print(f"\nWork phase for: {next_item['title']}")
        success = self.execute_item(next_item)

        if not success:
            print(f"\nWork phase failed for {next_item['id']}", file=sys.stderr)

            if self.continue_on_error:
                print(f"Continuing to next iteration (--continue-on-error enabled)", file=sys.stderr)
                continue

            return 1

        # Mark work complete and transition
        backlog = self.load_backlog()
        
        if self.enable_code_review:
            # Transition to ready_for_review
            self.mark_ready_for_review(backlog, next_item['id'])
            self.save_backlog(backlog)
            print(f"\n✓ Work phase complete: {next_item['title']}")
            print(f"Status: ready_for_review (will review on next iteration)")
        else:
            # Skip review, go directly to validation
            self.mark_work_complete(backlog, next_item['id'])
            self.save_backlog(backlog)
            print(f"\n✓ Work phase complete: {next_item['title']}")
            print(f"Status: ready_for_validation (will validate on next iteration)")

def _run_code_review(self, item: Dict[str, Any]) -> 'ReviewResult':
    """Run code review for item."""
    from ralph.code_reviewer import CodeReviewer
    from ralph.ecc_loader import ECCRuleLoader
    
    # Load tech stack
    tech_stack = self._load_tech_stack_from_architecture()
    
    # Create reviewer
    ecc_loader = ECCRuleLoader()
    reviewer = CodeReviewer(
        self.project_dir,
        self.provider,
        ecc_loader.ecc_dir
    )
    
    # Run review
    return reviewer.review_changes(item, tech_stack)

def _print_review_issues(self, issues: List['ReviewIssue']) -> None:
    """Print review issues."""
    for issue in issues:
        print(f"\n[{issue.severity}] {issue.title}")
        print(f"  File: {issue.file_path}" + (f":{issue.line_number}" if issue.line_number else ""))
        print(f"  Issue: {issue.description}")
        print(f"  Fix: {issue.fix_suggestion}")

def _fix_review_issues(self, item: Dict[str, Any], issues: List['ReviewIssue']) -> bool:
    """Attempt to fix review issues using agent."""
    # Build fix prompt
    issues_text = "\n\n".join([
        f"[{i.severity}] {i.title}\nFile: {i.file_path}\nIssue: {i.description}\nFix: {i.fix_suggestion}"
        for i in issues
    ])
    
    prompt = f"""Fix the following code review issues for: {item['title']}

{issues_text}

Please fix all issues and verify the fixes.
"""
    
    # Invoke provider
    try:
        cmd = self.provider.build_command(prompt, self.project_dir, yolo=True)
        
        result = subprocess.run(
            cmd,
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return result.returncode == 0
    
    except Exception as e:
        print(f"Fix attempt failed: {e}", file=sys.stderr)
        return False
```

### Step 5: Update CLI

**File**: `ralph/cli.py`

**Modify** `BacklogOrchestrator.__init__()` to accept new flags:

```python
def __init__(
    self,
    project_dir: Path,
    backlog_path: Path,
    provider: str = "qwen",
    auto_push: bool = False,
    dry_run: bool = False,
    continue_on_error: bool = False,
    enable_code_review: bool = False,      # NEW
    auto_fix_review: bool = False          # NEW
):
    self.project_dir = project_dir
    self.backlog_path = backlog_path
    self.provider_name = provider
    self.auto_push = auto_push
    self.dry_run = dry_run
    self.continue_on_error = continue_on_error
    self.enable_code_review = enable_code_review      # NEW
    self.auto_fix_review = auto_fix_review            # NEW
    
    # ... rest of __init__
```

**Add CLI flags** to `run_parser` (around line 412):

```python
run_parser.add_argument(
    '--enable-code-review',
    action='store_true',
    help='Enable code review phase before validation'
)
run_parser.add_argument(
    '--auto-fix-review',
    action='store_true',
    help='Automatically fix code review issues (requires --enable-code-review)'
)
```

**Update** `handle_run()` to pass new flags (around line 311):

```python
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
        continue_on_error=args.continue_on_error,
        enable_code_review=args.enable_code_review,      # NEW
        auto_fix_review=args.auto_fix_review             # NEW
    )
    
    # ... rest of handle_run
```

## Testing

### Test 1: Report-Only Mode

```bash
cd ~/projects/test-ralph-csharp

# Introduce code quality issues
cat > src/BadCode.cs << 'EOF'
public class BadCode
{
    public void ProcessData()
    {
        try
        {
            // Do something
        }
        catch (Exception)
        {
            // Empty catch block - CRITICAL issue
        }
        
        string apiKey = "sk-1234567890";  // Hardcoded secret - CRITICAL issue
    }
}
EOF

# Run with code review enabled
ralph run --enable-code-review --max-iterations 1
```

**Expected**:
1. Work phase completes
2. Code review phase runs
3. Issues detected: empty catch block, hardcoded secret
4. Issues logged as warnings
5. Continues to validation (report-only mode)

### Test 2: Auto-Fix Mode

```bash
# Same bad code as above
ralph run --enable-code-review --auto-fix-review --max-iterations 1
```

**Expected**:
1. Work phase completes
2. Code review phase runs
3. Issues detected
4. Agent attempts to fix issues
5. Re-review runs
6. If fixed, continues to validation
7. If not fixed, stops with error

### Test 3: No Code Review (Default)

```bash
ralph run --max-iterations 1
```

**Expected**:
1. Work phase completes
2. **No code review phase** (skipped)
3. Goes directly to validation
4. Existing behavior unchanged

## Success Criteria

- [ ] ECC reviewer agents bundled
- [ ] `ready_for_review` status added to schema
- [ ] `CodeReviewer` class created
- [ ] Review phase added to orchestration loop
- [ ] CLI flags added (`--enable-code-review`, `--auto-fix-review`)
- [ ] Test 1 (report-only) passes
- [ ] Test 2 (auto-fix) passes
- [ ] Test 3 (disabled) passes - no regression
- [ ] Review detects CRITICAL issues (empty catches, hardcoded secrets)
- [ ] Review detects HIGH issues (missing async, type safety)

## Rollback Plan

If issues arise:

```bash
# Revert schema
git checkout ralph/schemas/backlog.schema.json

# Revert orchestrator
git checkout ralph/orchestrator.py

# Revert CLI
git checkout ralph/cli.py

# Remove code reviewer
rm ralph/code_reviewer.py

# Remove reviewer agents (keep build-resolver agents)
cd ralph/ecc_resources/agents
rm *-reviewer.md
```

## Configuration Options

### Report-Only Mode (Default)

```bash
ralph run --enable-code-review
```

- Reviews code
- Logs issues
- Continues to validation regardless of issues
- **Recommended for initial adoption**

### Auto-Fix Mode

```bash
ralph run --enable-code-review --auto-fix-review
```

- Reviews code
- Attempts to fix CRITICAL/HIGH issues
- Re-reviews after fixes
- Blocks if issues remain
- **Use with caution - agent may introduce bugs**

### Disabled (Default)

```bash
ralph run
```

- No code review
- Existing behavior unchanged
- **Safe for existing users**

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Code review slows execution | Medium | Make opt-in, report-only by default |
| Agent introduces bugs in auto-fix | High | Report-only default, require explicit `--auto-fix-review` |
| Review phase breaks existing workflows | High | Disabled by default, fully backward compatible |
| False positives block progress | Medium | Report-only mode doesn't block, user can disable |
| Reviewer agent fails | Low | Graceful fallback, don't block on reviewer failure |

## Performance Impact

**Report-Only Mode**:
- Adds ~30-60 seconds per item (review time)
- No additional iterations

**Auto-Fix Mode**:
- Adds ~2-5 minutes per item (review + fix + re-review)
- May add 1-2 iterations for fixes

**Recommendation**: Start with report-only mode, enable auto-fix after validating review quality.

## Next Steps

After Phase 3 is complete:
- Monitor review quality and false positive rate
- Collect user feedback on usefulness
- Consider making code review opt-out (enabled by default) if adoption is high
- Add more language-specific reviewers as needed

## Estimated Timeline

- **Step 1** (Bundle agents): 30 minutes
- **Step 2** (Update schema): 15 minutes
- **Step 3** (Create reviewer): 4 hours
- **Step 4** (Add review phase): 4 hours
- **Step 5** (Update CLI): 1 hour
- **Testing**: 2 hours

**Total**: 3-4 days

## Summary

Phase 3 adds optional code review to catch quality issues before validation. Key features:

- **Opt-in**: Disabled by default, no breaking changes
- **Report-only default**: Safe, non-blocking
- **Auto-fix opt-in**: Requires explicit flag
- **Language-specific**: Uses appropriate reviewer for tech stack
- **Graceful degradation**: Failures don't block progress

This completes the ECC integration, providing Ralph Loop with:
1. **Phase 1**: Proven coding standards in ARCHITECTURE.md
2. **Phase 2**: Detailed patterns + build error resolution
3. **Phase 3**: Automated code review for quality assurance

The result is a production-ready autonomous development system with enterprise-level quality standards.
