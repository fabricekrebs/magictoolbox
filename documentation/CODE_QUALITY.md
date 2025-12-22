# Code Quality Guide

This document outlines the code quality standards and tools used in the MagicToolbox project.

## 🎯 Code Quality Standards

### Python Style Guide
- **PEP 8 Compliance**: Follow [PEP 8](https://pep8.org/) style guide
- **Line Length**: Maximum 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Naming Conventions**:
  - `snake_case` for variables, functions, and module names
  - `PascalCase` for class names
  - `UPPER_CASE` for constants
  - `_private_method()` for private methods (single leading underscore)

### Type Hints
- **Required**: All function signatures must include type hints
- **Format**: Use Python 3.11+ type hint syntax
- **Imports**: Use `from typing import` for complex types

```python
from typing import Any, Dict, Optional, Tuple

def process_data(
    input_data: Dict[str, Any],
    parameters: Optional[Dict[str, str]] = None
) -> Tuple[bool, Optional[str]]:
    """Process input data with optional parameters."""
    pass
```

### Docstrings
- **Style**: Google-style docstrings for all public functions and classes
- **Required Sections**: Description, Args, Returns, Raises (when applicable)

```python
def validate_file(file_path: str, max_size: int) -> Tuple[bool, Optional[str]]:
    """
    Validate file existence and size.
    
    Args:
        file_path: Path to the file to validate
        max_size: Maximum allowed file size in bytes
        
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is None.
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    pass
```

---

## 🛠️ Code Quality Tools

### 1. Black - Code Formatter
**Purpose**: Automatic code formatting  
**Configuration**: [pyproject.toml](../pyproject.toml)

```bash
# Format all Python files
black apps/ magictoolbox/ tests/ function_app/

# Check formatting without changes
black --check apps/ magictoolbox/ tests/ function_app/
```

**Settings**:
- Line length: 100
- Target version: Python 3.11
- Excludes: migrations, .venv, build, dist

---

### 2. isort - Import Sorter
**Purpose**: Organize imports alphabetically and by type  
**Configuration**: [pyproject.toml](../pyproject.toml)

```bash
# Sort imports
isort apps/ magictoolbox/ tests/ function_app/

# Check import order
isort --check-only apps/ magictoolbox/ tests/ function_app/
```

**Import Order**:
1. Future imports
2. Standard library
3. Django core
4. Django REST Framework
5. Third-party packages
6. First-party (project) imports
7. Local folder imports

---

### 3. Ruff - Fast Python Linter
**Purpose**: Fast linting for code quality issues  
**Configuration**: [ruff.toml](../ruff.toml)

```bash
# Lint and auto-fix
ruff check apps/ magictoolbox/ tests/ function_app/ --fix

# Lint only (no fixes)
ruff check apps/ magictoolbox/ tests/ function_app/
```

**Enabled Rules**:
- `E`: pycodestyle errors
- `W`: pycodestyle warnings
- `F`: pyflakes (unused imports, variables, etc.)

**Ignored Rules**:
- `E501`: Line too long (handled by Black)
- `E402`: Module import not at top (Django settings pattern)
- `F401`: Unused imports in `__init__.py` (re-exports)

---

### 4. mypy - Type Checker
**Purpose**: Static type checking  
**Configuration**: [pyproject.toml](../pyproject.toml)

```bash
# Type check entire codebase
mypy apps/ magictoolbox/ --config-file=pyproject.toml

# Type check specific module
mypy apps/tools/plugins/pdf_docx_converter.py
```

**Plugins**:
- `mypy_django_plugin`: Django-specific type stubs
- `mypy_drf_plugin`: Django REST Framework stubs

**Settings**:
- `disallow_untyped_defs`: All functions must have type hints
- `warn_return_any`: Warn on `Any` return types
- Migrations are excluded from checking

---

### 5. Bandit - Security Linter
**Purpose**: Identify common security issues  
**Configuration**: [pyproject.toml](../pyproject.toml)

```bash
# Run security scan
bandit -r apps/ magictoolbox/ -f screen

# Generate JSON report
bandit -r apps/ magictoolbox/ -f json -o bandit-report.json
```

**Excluded**:
- Test files (asserts are normal in tests)
- Migrations

---

### 6. Safety - Dependency Vulnerability Scanner
**Purpose**: Check for known vulnerabilities in dependencies

```bash
# Check for vulnerable packages
safety check

# Generate report
safety check --json
```

---

### 7. Radon - Complexity Analyzer
**Purpose**: Measure code complexity

```bash
# Cyclomatic complexity
radon cc apps/ magictoolbox/ -a -nb

# Maintainability index
radon mi apps/ magictoolbox/ -nb

# Raw metrics
radon raw apps/ magictoolbox/ -s
```

**Complexity Grades**:
- **A**: 1-5 (simple)
- **B**: 6-10 (slightly complex)
- **C**: 11-20 (complex)
- **D**: 21-30 (very complex)
- **F**: 31+ (extremely complex - needs refactoring)

---

## 🔄 Pre-commit Hooks

Pre-commit hooks run automatically before each commit to ensure code quality.

### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

### Manual Execution

```bash
# Run all hooks on staged files
pre-commit run

# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

### Hooks Configured
1. **Trailing whitespace removal**
2. **End-of-file fixer**
3. **YAML/JSON/TOML validation**
4. **Large file checker** (max 1MB)
5. **Merge conflict checker**
6. **Black** (code formatting)
7. **isort** (import sorting)
8. **Ruff** (linting with auto-fix)
9. **mypy** (type checking)
10. **Bandit** (security scanning)
11. **Django checks** (system checks)
12. **Django migrations check**

---

## 🚀 CI/CD Integration

### GitHub Actions Workflow

The [code-quality.yml](../.github/workflows/code-quality.yml) workflow runs on every push and pull request.

**Jobs**:
1. **Lint and Format Check**: Black, isort, Ruff
2. **Type Checking**: mypy (currently non-blocking)
3. **Security Scanning**: Bandit, Safety
4. **Django Checks**: System checks, migration checks
5. **Complexity Analysis**: Radon metrics

### Workflow Triggers
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Changes to `.py` files or requirements
- Manual trigger via `workflow_dispatch`

---

## 📋 Code Quality Checklist

Before committing code, ensure:

- [ ] Code is formatted with Black
- [ ] Imports are sorted with isort
- [ ] No Ruff linting errors
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] No security issues reported by Bandit
- [ ] Django system checks pass
- [ ] No missing migrations
- [ ] Tests pass with good coverage
- [ ] Complex functions (grade C+) are documented

---

## 🔧 IDE Integration

### VS Code

Install extensions:
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Ruff** (charliermarsh.ruff)

Add to `.vscode/settings.json`:

```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm

1. **Configure Black**:
   - Settings → Tools → External Tools → Add Black
   
2. **Enable Ruff**:
   - Settings → Tools → External Tools → Add Ruff
   
3. **Configure mypy**:
   - Settings → Tools → External Tools → Add mypy

---

## 📊 Quality Metrics

### Target Metrics
- **Test Coverage**: ≥80% for new code
- **Complexity**: Functions should be grade B or better
- **Type Coverage**: 100% for new code
- **Security Issues**: 0 high/critical issues
- **Linting Errors**: 0 errors (warnings acceptable with justification)

### Measuring Coverage

```bash
# Run tests with coverage
pytest --cov=apps --cov-report=html --cov-report=term-missing

# Open HTML report
open htmlcov/index.html
```

---

## 🚨 Common Issues and Solutions

### Issue: Black and isort conflict

**Solution**: Both tools are configured with `profile = "black"` in isort settings. Run isort before black.

### Issue: mypy import errors

**Solution**: Install type stubs or add to `[tool.mypy]` overrides in pyproject.toml:

```toml
[[tool.mypy.overrides]]
module = "problematic_module.*"
ignore_missing_imports = true
```

### Issue: Bandit false positives

**Solution**: Add `# nosec` comment with justification:

```python
# nosec B101 - Using assert for validation in test helper
assert user.is_active
```

### Issue: Pre-commit is slow

**Solution**: Run specific hooks or skip hooks when needed:

```bash
# Skip all hooks
git commit --no-verify

# Skip specific hook
SKIP=mypy git commit
```

---

## 📚 Additional Resources

- [PEP 8 Style Guide](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)

---

**Last Updated**: December 22, 2025  
**Maintained By**: Development Team
