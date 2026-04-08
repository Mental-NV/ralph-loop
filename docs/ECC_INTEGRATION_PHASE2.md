# ECC Integration Phase 2: Skills Reference + Build Error Resolution

## Overview

**Goal**: Provide AI agents with detailed implementation patterns (skills) and auto-resolve build failures using ECC build-resolver agents.

**Priority**: P1 (Guidance + Resilience)  
**Effort**: 3-4 days  
**Risk**: Low (well-defined scope, additive changes)

**Prerequisites**: Phase 1 must be complete (ECC rules integrated into ARCHITECTURE.md)

## Context

Phase 1 provides high-level coding standards in ARCHITECTURE.md. Phase 2 adds:
1. **Skills as Reference**: Detailed implementation patterns injected into execution prompts
2. **Build Error Resolution**: Auto-detect and fix build failures using specialized agents

## Part A: Skills as Reference Material

### What Gets Integrated

Copy from `~/projects/everything-claude-code/skills/`:

```
ralph/
  ecc_resources/
    skills/
      # Core patterns (all projects)
      api-design/SKILL.md              # REST API patterns, pagination, versioning
      testing-patterns/SKILL.md        # TDD workflow, test organization
      security-review/SKILL.md         # Security checklist, OWASP
      
      # Language-specific patterns
      python-patterns/SKILL.md         # Pythonic idioms, type hints
      typescript-patterns/SKILL.md     # TS best practices, React patterns
      csharp-patterns/SKILL.md         # .NET patterns, async/await
      golang-patterns/SKILL.md         # Go idioms, error handling
      java-patterns/SKILL.md           # Spring patterns, JPA
      
      # Framework-specific
      backend-patterns/SKILL.md        # API design, caching, database
      frontend-patterns/SKILL.md       # React, component composition
      database-patterns/SKILL.md       # Migrations, query optimization
```

**Size**: ~2MB for 12 skills

### Implementation Steps

#### Step 1: Bundle ECC Skills

```bash
# From ralph-loop root
mkdir -p ralph/ecc_resources/skills

# Copy core skills
for skill in api-design testing-patterns security-review backend-patterns frontend-patterns database-patterns; do
  cp -r ~/projects/everything-claude-code/skills/$skill ralph/ecc_resources/skills/
done

# Copy language-specific skills
for skill in python-patterns typescript-patterns csharp-patterns golang-patterns java-patterns; do
  cp -r ~/projects/everything-claude-code/skills/$skill ralph/ecc_resources/skills/
done
```

**Verification**:
```bash
ls ralph/ecc_resources/skills/
# Should show 11 directories

ls ralph/ecc_resources/skills/api-design/
# Should show: SKILL.md
```

#### Step 2: Add Skill Selection to ECC Loader

**File**: `ralph/ecc_loader.py`

**Add new method**:

```python
def select_skills_for_item(self, item: Dict, tech_stack: Dict) -> List[str]:
    """
    Select relevant skills based on item deliverables and tech stack.
    
    Args:
        item: Backlog item with deliverables
        tech_stack: Detected tech stack
    
    Returns:
        List of skill markdown content
    """
    skills = []
    skills_dir = self.ecc_dir / "skills"
    
    if not skills_dir.exists():
        return skills
    
    # Detect language
    language = self._detect_language(tech_stack)
    
    # Always include language-specific patterns
    if language:
        skill_path = skills_dir / f"{language}-patterns" / "SKILL.md"
        if skill_path.exists():
            skills.append(skill_path.read_text(encoding='utf-8'))
    
    # Select skills based on deliverables
    deliverables_text = " ".join([d.get('text', '') for d in item.get('deliverables', [])])
    deliverables_lower = deliverables_text.lower()
    
    # API-related
    if any(keyword in deliverables_lower for keyword in ['api', 'endpoint', 'rest', 'http', 'route']):
        skill_path = skills_dir / "api-design" / "SKILL.md"
        if skill_path.exists():
            skills.append(skill_path.read_text(encoding='utf-8'))
    
    # Database-related
    if any(keyword in deliverables_lower for keyword in ['database', 'persistence', 'storage', 'query', 'migration']):
        skill_path = skills_dir / "database-patterns" / "SKILL.md"
        if skill_path.exists():
            skills.append(skill_path.read_text(encoding='utf-8'))
    
    # Frontend-related
    if any(keyword in deliverables_lower for keyword in ['ui', 'component', 'frontend', 'react', 'vue', 'interface']):
        skill_path = skills_dir / "frontend-patterns" / "SKILL.md"
        if skill_path.exists():
            skills.append(skill_path.read_text(encoding='utf-8'))
    
    # Backend-related
    if any(keyword in deliverables_lower for keyword in ['backend', 'service', 'business logic', 'controller']):
        skill_path = skills_dir / "backend-patterns" / "SKILL.md"
        if skill_path.exists():
            skills.append(skill_path.read_text(encoding='utf-8'))
    
    # Testing-related (always include if tests mentioned)
    if any(keyword in deliverables_lower for keyword in ['test', 'testing', 'coverage']):
        skill_path = skills_dir / "testing-patterns" / "SKILL.md"
        if skill_path.exists():
            skills.append(skill_path.read_text(encoding='utf-8'))
    
    # Security-related
    if any(keyword in deliverables_lower for keyword in ['security', 'auth', 'authentication', 'authorization']):
        skill_path = skills_dir / "security-review" / "SKILL.md"
        if skill_path.exists():
            skills.append(skill_path.read_text(encoding='utf-8'))
    
    return skills
```

#### Step 3: Enhance Execution Prompt Template

**File**: `ralph/prompts/execution.txt`

**Add new section** after "**Architecture Context:**":

```
**Reference Patterns:**
{ecc_skills}
```

**Full updated template**:

```
Execute backlog item: {title}

**Why:** {why}

**Architecture Context:**
See docs/ARCHITECTURE.md for tech stack, patterns, and best practices to follow.

**Reference Patterns:**
{ecc_skills}

**Deliverables:**
{deliverables}

**Exit Criteria:**
{exit_criteria}

**Risks:**
{risks}

**Validation Approach:**
{validation_commands}

Please implement this milestone following the deliverables, exit criteria, architectural guidelines, and reference patterns.
```

#### Step 4: Update Orchestrator to Load Skills

**File**: `ralph/orchestrator.py`

**Modify** `build_execution_prompt()` method (around line 578):

```python
def build_execution_prompt(self, item: Dict[str, Any]) -> str:
    """Build execution prompt for item."""
    from ralph.prompt_loader import PromptLoader
    from ralph.ecc_loader import ECCRuleLoader
    import json

    loader = PromptLoader()
    ecc_loader = ECCRuleLoader()

    # Load tech stack from ARCHITECTURE.md
    tech_stack = self._load_tech_stack_from_architecture()

    # Select relevant skills
    skills = ecc_loader.select_skills_for_item(item, tech_stack)
    ecc_skills = self._format_skills(skills)

    # Format deliverables
    deliverables = "\n".join([
        f"  {'✓' if d.get('done') else '○'} {d['text']}"
        for d in item.get('deliverables', [])
    ])

    # Format exit criteria
    exit_criteria = "\n".join([
        f"  {'✓' if c.get('done') else '○'} {c['text']}"
        for c in item.get('exitCriteria', [])
    ])

    # Format risks
    if item.get('risks'):
        risks = "\n".join([
            f"  - {self._format_risk(risk)}"
            for risk in item['risks']
        ])
    else:
        risks = "None specified"

    # Format validation commands
    validation = item.get('validation', {})
    if validation.get('commands'):
        validation_commands = "\n".join([
            f"  - {cmd}"
            for cmd in validation['commands']
        ])
    else:
        validation_commands = "None specified"

    return loader.load('execution',
                      title=item['title'],
                      why=item.get('why', 'No rationale provided'),
                      ecc_skills=ecc_skills,
                      deliverables=deliverables,
                      exit_criteria=exit_criteria,
                      risks=risks,
                      validation_commands=validation_commands)

def _load_tech_stack_from_architecture(self) -> Dict[str, Any]:
    """Load tech stack from ARCHITECTURE.md."""
    arch_path = self.project_dir / "docs" / "ARCHITECTURE.md"
    
    if not arch_path.exists():
        return {}
    
    # Simple extraction: look for "Technology Stack" section
    content = arch_path.read_text(encoding='utf-8')
    
    # Default fallback
    tech_stack = {
        "backend": "",
        "frontend": "",
        "database": "",
        "testing": ""
    }
    
    # Extract backend
    if '.NET' in content or 'ASP.NET' in content:
        tech_stack['backend'] = '.NET'
    elif 'Python' in content or 'Django' in content or 'FastAPI' in content:
        tech_stack['backend'] = 'Python'
    elif 'Go' in content or 'Golang' in content:
        tech_stack['backend'] = 'Go'
    elif 'Java' in content or 'Spring' in content:
        tech_stack['backend'] = 'Java'
    elif 'Node' in content or 'Express' in content or 'NestJS' in content:
        tech_stack['backend'] = 'Node.js'
    
    # Extract frontend
    if 'React' in content:
        tech_stack['frontend'] = 'React'
    elif 'Vue' in content:
        tech_stack['frontend'] = 'Vue'
    elif 'Angular' in content:
        tech_stack['frontend'] = 'Angular'
    
    return tech_stack

def _format_skills(self, skills: List[str]) -> str:
    """Format skills for inclusion in prompt."""
    if not skills:
        return "No specific patterns loaded for this milestone."
    
    # Truncate each skill to first 1000 lines to avoid prompt bloat
    truncated_skills = []
    for skill in skills:
        lines = skill.split('\n')
        if len(lines) > 1000:
            truncated_skills.append('\n'.join(lines[:1000]) + "\n\n[... truncated for brevity ...]")
        else:
            truncated_skills.append(skill)
    
    return "\n\n---\n\n".join(truncated_skills)
```

### Testing Part A

```bash
cd ~/projects/test-ralph-csharp
ralph run --dry-run
```

**Expected**: Execution prompt should include:
- `csharp-patterns` skill
- `api-design` skill (if deliverables mention API)
- `testing-patterns` skill (if deliverables mention tests)

**Verify**: Check dry-run output for "Reference Patterns:" section

---

## Part B: Build Error Resolution

### What Gets Integrated

Copy from `~/projects/everything-claude-code/agents/`:

```
ralph/
  ecc_resources/
    agents/
      csharp-build-resolver.md
      python-build-resolver.md
      go-build-resolver.md
      rust-build-resolver.md
      java-build-resolver.md
      kotlin-build-resolver.md
```

**Size**: ~100KB for 6 agents

### Implementation Steps

#### Step 1: Bundle ECC Build-Resolver Agents

```bash
# From ralph-loop root
mkdir -p ralph/ecc_resources/agents

# Copy build-resolver agents
for agent in csharp-build-resolver python-build-resolver go-build-resolver rust-build-resolver java-build-resolver kotlin-build-resolver; do
  cp ~/projects/everything-claude-code/agents/$agent.md ralph/ecc_resources/agents/
done
```

**Verification**:
```bash
ls ralph/ecc_resources/agents/
# Should show 6 .md files
```

#### Step 2: Create Build Resolver

**File**: `ralph/build_resolver.py`

```python
"""
Build error resolution using ECC build-resolver agents.
"""

import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple


class BuildResolver:
    """Resolves build errors using language-specific ECC agents."""
    
    def __init__(self, project_dir: Path, provider, ecc_dir: Path):
        self.project_dir = project_dir
        self.provider = provider
        self.agents_dir = ecc_dir / "agents"
    
    def resolve_build_error(
        self,
        error_output: str,
        tech_stack: Dict,
        max_retries: int = 2
    ) -> Tuple[bool, str]:
        """
        Attempt to resolve build error using appropriate agent.
        
        Args:
            error_output: Build error output
            tech_stack: Detected tech stack
            max_retries: Maximum resolution attempts
        
        Returns:
            Tuple of (success, message)
        """
        # Detect language
        language = self._detect_language(tech_stack)
        
        if not language:
            return False, "Could not detect language for build resolution"
        
        # Load agent
        agent_path = self.agents_dir / f"{language}-build-resolver.md"
        
        if not agent_path.exists():
            return False, f"No build resolver agent for {language}"
        
        agent_content = agent_path.read_text(encoding='utf-8')
        
        # Build resolution prompt
        prompt = self._build_resolution_prompt(agent_content, error_output)
        
        # Invoke provider
        print(f"\n🔧 Attempting to resolve build error using {language}-build-resolver...")
        
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
                return False, f"Build resolver agent failed: {result.stderr}"
            
            return True, "Build error resolved by agent"
        
        except subprocess.TimeoutExpired:
            return False, "Build resolver timed out"
        except Exception as e:
            return False, f"Build resolver error: {e}"
    
    def _detect_language(self, tech_stack: Dict) -> Optional[str]:
        """Detect language from tech stack."""
        backend = tech_stack.get('backend', '').lower()
        
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
        
        return None
    
    def _build_resolution_prompt(self, agent_content: str, error_output: str) -> str:
        """Build prompt for build resolver agent."""
        return f"""{agent_content}

# Build Error to Resolve

The following build error occurred:

```
{error_output}
```

Please analyze the error and fix it. Run the build command again to verify the fix.
"""
```

#### Step 3: Detect Build Failures in Orchestrator

**File**: `ralph/orchestrator.py`

**Modify** `run_validation_commands()` method (around line 369):

```python
def run_validation_commands(self, item: Dict[str, Any]) -> bool:
    """Run validation commands for item with build error resolution. Returns True if all critical commands pass."""
    validation = item.get('validation', {})
    commands = validation.get('commands', [])

    if not commands:
        print("No validation commands defined, skipping validation")
        return True

    # Classify commands
    critical_commands = []
    cleanup_commands = []
    background_commands = []
    build_commands = []  # NEW: Track build commands

    for cmd in commands:
        if self.is_background_command(cmd):
            background_commands.append(cmd)
        elif self.is_cleanup_command(cmd):
            cleanup_commands.append(cmd)
        elif self.is_build_command(cmd):  # NEW
            build_commands.append(cmd)
            critical_commands.append(cmd)
        else:
            critical_commands.append(cmd)

    # Run background commands first
    if background_commands:
        print(f"Starting {len(background_commands)} background process(es)...")
        for i, cmd in enumerate(background_commands, 1):
            print(f"  [{i}/{len(background_commands)}] {cmd}")
            if not self.run_background_command(cmd):
                print(f"  FAILED to start background process", file=sys.stderr)
                return False
            print(f"  STARTED")

    # Run critical validation with build error resolution
    if critical_commands:
        print(f"Running {len(critical_commands)} critical validation command(s)...")

        for i, cmd in enumerate(critical_commands, 1):
            print(f"  [{i}/{len(critical_commands)}] {cmd}")

            if self.dry_run:
                print("  [DRY RUN] Would run command")
                continue

            # Run command
            success, error_output = self._run_command_with_retry(cmd, is_build=cmd in build_commands)
            
            if not success:
                print(f"  FAILED", file=sys.stderr)
                if error_output:
                    print(f"  Error: {error_output[:500]}", file=sys.stderr)
                return False
            
            print(f"  PASSED")

    # Run cleanup commands (best-effort)
    if cleanup_commands:
        print(f"\nRunning {len(cleanup_commands)} cleanup command(s) (best-effort)...")
        for i, cmd in enumerate(cleanup_commands, 1):
            print(f"  [{i}/{len(cleanup_commands)}] {cmd}")
            if self.dry_run:
                print("  [DRY RUN] Would run command")
                continue
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode != 0:
                    print(f"  WARNING: Cleanup failed (non-critical, continuing)", file=sys.stderr)
                else:
                    print(f"  PASSED")
            except Exception as e:
                print(f"  WARNING: Cleanup error: {e} (non-critical, continuing)", file=sys.stderr)

    return True

def is_build_command(self, cmd: str) -> bool:
    """Identify build commands."""
    build_patterns = [
        'dotnet build', 'npm run build', 'yarn build', 'pnpm build',
        'go build', 'cargo build', 'mvn compile', 'gradle build',
        'make', 'cmake --build'
    ]
    return any(pattern in cmd for pattern in build_patterns)

def _run_command_with_retry(self, cmd: str, is_build: bool, max_retries: int = 2) -> Tuple[bool, str]:
    """
    Run command with build error resolution retry.
    
    Args:
        cmd: Command to run
        is_build: Whether this is a build command
        max_retries: Maximum retry attempts
    
    Returns:
        Tuple of (success, error_output)
    """
    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, ""
            
            # Build failed
            error_output = result.stderr or result.stdout
            
            # If this is a build command and we have retries left, attempt resolution
            if is_build and attempt < max_retries:
                print(f"\n  Build failed (attempt {attempt + 1}/{max_retries + 1})")
                
                # Load tech stack
                tech_stack = self._load_tech_stack_from_architecture()
                
                # Attempt resolution
                from ralph.build_resolver import BuildResolver
                from ralph.ecc_loader import ECCRuleLoader
                
                ecc_loader = ECCRuleLoader()
                resolver = BuildResolver(
                    self.project_dir,
                    self.provider,
                    ecc_loader.ecc_dir
                )
                
                success, message = resolver.resolve_build_error(error_output, tech_stack)
                
                if success:
                    print(f"  ✓ {message}")
                    print(f"  Retrying build...")
                    continue  # Retry
                else:
                    print(f"  ✗ {message}", file=sys.stderr)
                    return False, error_output
            
            # No more retries or not a build command
            return False, error_output
        
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
    
    return False, "Max retries exceeded"
```

### Testing Part B

#### Test 1: Introduce Build Error

```bash
cd ~/projects/test-ralph-csharp

# Introduce syntax error
echo "public class Broken { invalid syntax }" > src/Broken.cs

# Run validation
ralph run --max-iterations 1
```

**Expected**:
1. Build fails
2. Build resolver detects error
3. Agent attempts to fix
4. Build retries (max 2 times)

#### Test 2: Verify Resolution

```bash
# Check if error was fixed
cat src/Broken.cs
# Should show corrected syntax

# Verify build passes
dotnet build
```

## Success Criteria

### Part A (Skills)
- [ ] ECC skills bundled in `ralph/ecc_resources/skills/`
- [ ] Skill selection logic added to `ECCRuleLoader`
- [ ] Execution prompt template enhanced
- [ ] Orchestrator loads and formats skills
- [ ] Test: API deliverable includes `api-design` skill
- [ ] Test: Test deliverable includes `testing-patterns` skill

### Part B (Build Resolution)
- [ ] ECC build-resolver agents bundled
- [ ] `BuildResolver` class created
- [ ] Build command detection added
- [ ] Retry logic with resolution implemented
- [ ] Test: Build error detected and resolved
- [ ] Test: Max retries respected (2 attempts)

## Rollback Plan

If issues arise:

```bash
# Remove skills
rm -rf ralph/ecc_resources/skills

# Remove agents
rm -rf ralph/ecc_resources/agents

# Revert code changes
git checkout ralph/orchestrator.py
git checkout ralph/prompts/execution.txt
rm ralph/build_resolver.py
```

## Next Steps

After Phase 2 is complete:
- **Phase 3**: Code review phase with language-specific reviewers

## Estimated Timeline

- **Part A** (Skills): 1 day
- **Part B** (Build resolution): 2-3 days

**Total**: 3-4 days
