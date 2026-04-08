# ECC Integration Phase 1: Enhanced Architecture Generation

## Overview

**Goal**: Inject ECC language-specific rules into ARCHITECTURE.md generation to provide AI agents with proven coding standards from day one.

**Priority**: P0 (Foundation)  
**Effort**: 1-2 days  
**Risk**: Low (additive change, doesn't break existing flow)

## Context

Ralph Loop currently generates generic ARCHITECTURE.md documents without leveraging battle-tested best practices from Everything Claude Code (ECC). This phase integrates ECC's proven rules (10+ months of production use) into architecture generation.

## What Gets Integrated

### ECC Rules to Bundle

Copy from `~/projects/everything-claude-code/rules/`:

```
ralph/
  ecc_resources/
    rules/
      common/
        coding-style.md      # Universal principles
        testing.md           # TDD, 80% coverage
        security.md          # Secret detection, OWASP
        git-workflow.md      # Commit format, PR process
        patterns.md          # Design patterns
      
      # Top 5 languages (start here)
      csharp/
        coding-style.md      # Nullable types, async patterns
        testing.md           # xUnit, test organization
        security.md          # SQL injection, CSRF prevention
      
      python/
        coding-style.md      # PEP 8, type hints
        testing.md           # pytest patterns
        security.md          # Input validation
      
      typescript/
        coding-style.md      # ESLint, immutability
        testing.md           # Jest, React Testing Library
        security.md          # XSS prevention
      
      golang/
        coding-style.md      # Go idioms, error handling
        testing.md           # table-driven tests
        security.md          # Input sanitization
      
      java/
        coding-style.md      # Spring conventions
        testing.md           # JUnit patterns
        security.md          # OWASP for Java
```

**Size**: ~500KB for 5 languages

## Implementation Steps

### Step 1: Bundle ECC Rules

**Action**: Copy ECC rules into Ralph Loop repository

```bash
# From ralph-loop root
mkdir -p ralph/ecc_resources/rules

# Copy common rules
cp -r ~/projects/everything-claude-code/rules/common ralph/ecc_resources/rules/

# Copy language-specific rules (top 5)
for lang in csharp python typescript golang java; do
  cp -r ~/projects/everything-claude-code/rules/$lang ralph/ecc_resources/rules/
done
```

**Verification**:
```bash
ls ralph/ecc_resources/rules/
# Should show: common/ csharp/ python/ typescript/ golang/ java/

ls ralph/ecc_resources/rules/common/
# Should show: coding-style.md testing.md security.md git-workflow.md patterns.md
```

### Step 2: Create ECC Rule Loader

**File**: `ralph/ecc_loader.py`

```python
"""
ECC resource loader for Ralph Loop.

Loads rules, skills, and agents from bundled ECC resources.
"""

from pathlib import Path
from typing import Dict, List, Optional


class ECCRuleLoader:
    """Loads ECC rules based on tech stack."""
    
    def __init__(self):
        self.ecc_dir = Path(__file__).parent / "ecc_resources"
        self.rules_dir = self.ecc_dir / "rules"
    
    def load_rules_for_stack(self, tech_stack: Dict) -> Dict[str, str]:
        """
        Load common + language-specific rules based on tech stack.
        
        Args:
            tech_stack: Dict with 'backend', 'frontend', 'database', etc.
        
        Returns:
            Dict mapping rule category to markdown content:
            {
                "coding-style": "...",
                "testing": "...",
                "security": "...",
                "git-workflow": "...",
                "patterns": "..."
            }
        """
        rules = {}
        
        # Detect primary language from tech stack
        language = self._detect_language(tech_stack)
        
        # Load common rules (always included)
        rules.update(self._load_common_rules())
        
        # Load language-specific rules (if available)
        if language:
            rules.update(self._load_language_rules(language))
        
        return rules
    
    def _detect_language(self, tech_stack: Dict) -> Optional[str]:
        """
        Detect primary language from tech stack.
        
        Returns language key (csharp, python, typescript, golang, java) or None.
        """
        backend = tech_stack.get('backend', '').lower()
        frontend = tech_stack.get('frontend', '').lower()
        
        # Backend language detection
        if '.net' in backend or 'asp.net' in backend or 'c#' in backend:
            return 'csharp'
        elif 'python' in backend or 'django' in backend or 'fastapi' in backend or 'flask' in backend:
            return 'python'
        elif 'go' in backend or 'golang' in backend:
            return 'golang'
        elif 'java' in backend or 'spring' in backend:
            return 'java'
        elif 'node' in backend or 'express' in backend or 'nestjs' in backend:
            return 'typescript'
        
        # Frontend language detection (fallback)
        if 'typescript' in frontend or 'react' in frontend or 'next.js' in frontend or 'vue' in frontend:
            return 'typescript'
        
        return None
    
    def _load_common_rules(self) -> Dict[str, str]:
        """Load common rules (language-agnostic)."""
        rules = {}
        common_dir = self.rules_dir / "common"
        
        if not common_dir.exists():
            return rules
        
        for rule_file in ["coding-style.md", "testing.md", "security.md", "git-workflow.md", "patterns.md"]:
            rule_path = common_dir / rule_file
            if rule_path.exists():
                category = rule_file.replace('.md', '')
                rules[f"common_{category}"] = rule_path.read_text(encoding='utf-8')
        
        return rules
    
    def _load_language_rules(self, language: str) -> Dict[str, str]:
        """Load language-specific rules."""
        rules = {}
        lang_dir = self.rules_dir / language
        
        if not lang_dir.exists():
            return rules
        
        for rule_file in ["coding-style.md", "testing.md", "security.md"]:
            rule_path = lang_dir / rule_file
            if rule_path.exists():
                category = rule_file.replace('.md', '')
                rules[f"{language}_{category}"] = rule_path.read_text(encoding='utf-8')
        
        return rules
```

**Verification**:
```python
# Test in Python REPL
from ralph.ecc_loader import ECCRuleLoader

loader = ECCRuleLoader()
tech_stack = {"backend": ".NET 10", "frontend": "React"}
rules = loader.load_rules_for_stack(tech_stack)

print(rules.keys())
# Should show: dict_keys(['common_coding-style', 'common_testing', 'common_security', 
#                         'common_git-workflow', 'common_patterns', 
#                         'csharp_coding-style', 'csharp_testing', 'csharp_security'])
```

### Step 3: Enhance Architecture Prompt Template

**File**: `ralph/prompts/architecture.txt`

**Add new section** after "# Your Task":

```
# Best Practices and Coding Standards

Follow these proven patterns and standards for this tech stack:

{ecc_rules}

These standards should be reflected in the architecture document you generate.
```

**Full updated template**:

```
You are a software architect defining the technical architecture for a project.

# Project Description
{user_prompt}

# Detected Tech Stack
```json
{tech_stack}
```

# Best Practices and Coding Standards

Follow these proven patterns and standards for this tech stack:

{ecc_rules}

These standards should be reflected in the architecture document you generate.

# Your Task
Generate a comprehensive ARCHITECTURE.md document following best practices for this specific tech stack and application type.

Write the architecture document to: {output_file}

# Document Structure

The ARCHITECTURE.md should include:

1. **Overview**
   - Application type and purpose
   - Technology stack summary

2. **Technology Stack**
   - Backend framework and version
   - Frontend framework (if applicable)
   - Database
   - Testing frameworks
   - Additional tools and libraries

3. **Project Structure**
   - Folder organization following best practices for this stack
   - Key directories and their purposes
   - File naming conventions

4. **Architectural Patterns**
   - Design patterns appropriate for this stack
   - Layering strategy (e.g., MVC, Clean Architecture, etc.)
   - Dependency management approach

5. **Coding Standards**
   - Language-specific conventions
   - Code organization principles
   - Error handling patterns

6. **Testing Strategy**
   - Unit testing approach
   - Integration testing approach
   - Test organization and naming

7. **Development Guidelines**
   - How to add new features
   - How to structure components/modules
   - Configuration management

# Guidelines
- Tailor everything to the specific tech stack detected
- Be specific about versions and tools
- Follow industry best practices for this stack
- Make it actionable for AI agents implementing features
- Include concrete examples where helpful
- Consider the application type when defining structure
- Incorporate the coding standards and patterns provided above

Write the markdown document to the specified file now.
```

### Step 4: Update Prompt Builder

**File**: `ralph/prompts.py`

**Modify** `build_architecture_prompt()` function:

```python
def build_architecture_prompt(user_prompt: str, tech_stack: Dict[str, Any], output_file: Path) -> str:
    """
    Build prompt for architecture document generation.
    
    Args:
        user_prompt: User's project description
        tech_stack: Detected tech stack
        output_file: Path where ARCHITECTURE.md should be written
    
    Returns:
        Rendered prompt string
    """
    from ralph.ecc_loader import ECCRuleLoader
    
    loader = PromptLoader()
    
    # Load ECC rules for tech stack
    ecc_loader = ECCRuleLoader()
    rules = ecc_loader.load_rules_for_stack(tech_stack)
    
    # Format rules for prompt
    ecc_rules = _format_ecc_rules(rules)
    
    return loader.load(
        'architecture',
        user_prompt=user_prompt,
        tech_stack=json.dumps(tech_stack, indent=2),
        output_file=str(output_file),
        ecc_rules=ecc_rules
    )


def _format_ecc_rules(rules: Dict[str, str]) -> str:
    """
    Format ECC rules for inclusion in prompt.
    
    Args:
        rules: Dict mapping rule category to markdown content
    
    Returns:
        Formatted markdown string
    """
    if not rules:
        return "No specific coding standards loaded."
    
    sections = []
    
    # Group by category
    categories = {
        'coding-style': 'Coding Style',
        'testing': 'Testing Standards',
        'security': 'Security Guidelines',
        'git-workflow': 'Git Workflow',
        'patterns': 'Design Patterns'
    }
    
    for category_key, category_title in categories.items():
        # Check for language-specific rule first, then common
        content = None
        for rule_key, rule_content in rules.items():
            if category_key in rule_key and not rule_key.startswith('common_'):
                content = rule_content
                break
        
        # Fallback to common rule
        if not content:
            common_key = f"common_{category_key}"
            content = rules.get(common_key)
        
        if content:
            sections.append(f"## {category_title}\n\n{content}")
    
    return "\n\n".join(sections)
```

### Step 5: Update Initializer

**File**: `ralph/initializer.py`

**No changes needed** - `build_architecture_prompt()` already handles ECC loading internally.

**Verification**: The existing code in `initializer.py` (lines 168-184) already calls `build_architecture_prompt()` with the correct parameters.

## Testing

### Test 1: C# Project

```bash
cd ~/projects/test-ralph-csharp
git init
ralph init "Build a REST API with ASP.NET Core and Entity Framework"
```

**Expected**: `docs/ARCHITECTURE.md` should contain:
- C# coding standards (nullable reference types, async patterns)
- xUnit testing patterns
- Security guidelines (SQL injection prevention, CSRF)
- Git workflow conventions

**Verify**:
```bash
grep -i "nullable reference" docs/ARCHITECTURE.md
grep -i "async" docs/ARCHITECTURE.md
grep -i "xUnit" docs/ARCHITECTURE.md
```

### Test 2: Python Project

```bash
cd ~/projects/test-ralph-python
git init
ralph init "Build a web scraper with Python and BeautifulSoup"
```

**Expected**: `docs/ARCHITECTURE.md` should contain:
- PEP 8 conventions
- Type hints
- pytest patterns
- Security guidelines (input validation)

**Verify**:
```bash
grep -i "PEP 8" docs/ARCHITECTURE.md
grep -i "type hint" docs/ARCHITECTURE.md
grep -i "pytest" docs/ARCHITECTURE.md
```

### Test 3: TypeScript Project

```bash
cd ~/projects/test-ralph-typescript
git init
ralph init "Build a React dashboard with TypeScript and Vite"
```

**Expected**: `docs/ARCHITECTURE.md` should contain:
- TypeScript conventions
- ESLint configuration
- Jest/React Testing Library patterns
- XSS prevention

**Verify**:
```bash
grep -i "typescript" docs/ARCHITECTURE.md
grep -i "eslint" docs/ARCHITECTURE.md
grep -i "jest" docs/ARCHITECTURE.md
```

## Rollback Plan

If issues arise:

1. **Remove ECC resources**:
   ```bash
   rm -rf ralph/ecc_resources
   ```

2. **Revert prompt changes**:
   ```bash
   git checkout ralph/prompts/architecture.txt
   ```

3. **Revert code changes**:
   ```bash
   git checkout ralph/prompts.py
   rm ralph/ecc_loader.py
   ```

## Success Criteria

- [ ] ECC rules bundled in `ralph/ecc_resources/rules/`
- [ ] `ECCRuleLoader` class created and tested
- [ ] Architecture prompt template enhanced
- [ ] Prompt builder updated to load ECC rules
- [ ] Test 1 (C#) passes
- [ ] Test 2 (Python) passes
- [ ] Test 3 (TypeScript) passes
- [ ] Generated ARCHITECTURE.md includes language-specific standards

## Next Steps

After Phase 1 is complete and validated:
- **Phase 2**: Skills as reference material + Build error resolution
- **Phase 3**: Code review phase

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| ECC rules too verbose, bloat prompts | Select only 3 most important rules per language (coding-style, testing, security) |
| Language detection fails | Fallback to common rules only (still valuable) |
| Prompt becomes too long | Truncate rules to first 500 lines per category |
| Breaking existing workflows | Phase 1 is purely additive, doesn't change existing behavior |

## Estimated Timeline

- **Step 1** (Bundle rules): 30 minutes
- **Step 2** (Create loader): 2 hours
- **Step 3** (Update prompt template): 30 minutes
- **Step 4** (Update prompt builder): 1 hour
- **Step 5** (Testing): 2 hours

**Total**: 6 hours (1 day)
