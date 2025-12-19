# Conventional Commits Guide for MagicToolbox

## Overview

This project uses **Conventional Commits** to automatically generate semantic versions and deploy to production. When you merge a pull request to `main`, the system automatically analyzes your commits, determines the version bump, creates a release, and deploys to production.

## Commit Message Format

```
<type>[(scope)]: <description>

[optional body]

[optional footer]
```

### Types and Version Impact

| Type | Version Bump | Example | When to Use |
|------|-------------|---------|-------------|
| `feat` | **Minor** (1.2.0 → 1.3.0) | `feat: add GPX merger tool` | New features |
| `fix` | **Patch** (1.2.0 → 1.2.1) | `fix: correct PDF conversion timeout` | Bug fixes |
| `perf` | **Patch** (1.2.0 → 1.2.1) | `perf: optimize image processing` | Performance improvements |
| `refactor` | **Patch** (1.2.0 → 1.2.1) | `refactor: simplify file upload logic` | Code refactoring |
| `revert` | **Patch** (1.2.0 → 1.2.1) | `revert: remove broken feature` | Revert changes |
| `docs` | **None** | `docs: update README` | Documentation only |
| `style` | **None** | `style: format code with Black` | Code style changes |
| `test` | **None** | `test: add unit tests for OCR` | Test changes |
| `chore` | **None** | `chore: update dependencies` | Maintenance tasks |
| `ci` | **None** | `ci: update GitHub Actions` | CI/CD changes |
| `build` | **None** | `build: update Docker config` | Build system changes |

### Breaking Changes → Major Version

Add `!` after type or `BREAKING CHANGE:` in footer to trigger **Major** version bump (1.2.0 → 2.0.0):

```bash
feat!: change API response format

BREAKING CHANGE: API now returns camelCase instead of snake_case
```

## Examples

### ✅ Good Commit Messages

```bash
# New feature (minor version bump)
feat: add video rotation tool with Azure Functions support

# Bug fix (patch version bump)
fix: resolve download button not appearing after PDF conversion

# Performance improvement (patch version bump)
perf: reduce memory usage in image converter

# Breaking change (major version bump)
feat!: migrate to PostgreSQL from SQLite

BREAKING CHANGE: Database schema changed, requires migration
```

### ❌ Bad Commit Messages

```bash
# Too vague
fix: bug fix

# No type
Added new feature

# Wrong type
feat: fixed typo in documentation  # Should be 'docs:'
```

## Scopes (Optional but Recommended)

Add scope to provide more context:

```bash
feat(tools): add GPX speed modifier
fix(auth): resolve session timeout issue
perf(storage): optimize blob upload performance
docs(api): update API documentation
```

Common scopes:
- `tools` - Tool plugins
- `auth` - Authentication
- `api` - API endpoints
- `frontend` - Templates and UI
- `infra` - Infrastructure/Bicep
- `ci` - CI/CD workflows
- `storage` - Blob storage operations
- `database` - Database operations

## Workflow: PR to Production

### Step 1: Create Feature Branch
```bash
git checkout -b feature/gpx-merger
```

### Step 2: Make Changes with Conventional Commits
```bash
# First commit
git add apps/tools/plugins/gpx_merger.py
git commit -m "feat(tools): add GPX file merger plugin"

# Bug fix during development
git add templates/tools/gpx_merger.html
git commit -m "fix(frontend): correct file upload validation"

# Documentation
git add documentation/GPX_MERGER_TOOL.md
git commit -m "docs(tools): add GPX merger documentation"
```

### Step 3: Push and Create PR
```bash
git push origin feature/gpx-merger
# Create PR on GitHub targeting 'main' branch
```

### Step 4: Merge PR (Automatic Process)
When PR is merged to `main`:

1. ✅ **Semantic Release** analyzes commits since last release
2. ✅ Determines version: `feat:` commits → Minor bump (v1.2.0 → v1.3.0)
3. ✅ Creates git tag: `v1.3.0`
4. ✅ Updates `CHANGELOG.md`
5. ✅ Pushes tag to repository
6. ✅ **GitHub Actions** builds Docker image with tags: `v1.3.0`, `v1.3`, `v1`, `latest`
7. ✅ Deploys to **production** Azure Container Apps
8. ✅ Creates GitHub Release

**No manual intervention required! 🎉**

## Version Calculation Examples

### Example 1: New Feature
```
Current version: v1.2.5

Commits in PR:
- feat: add OCR tool
- docs: update README

Result: v1.3.0 (minor bump from 'feat')
```

### Example 2: Multiple Commits
```
Current version: v1.2.5

Commits in PR:
- feat: add GPX analyzer
- feat: add GPX merger  
- fix: correct file validation
- docs: update documentation

Result: v1.3.0 (highest is 'feat' = minor)
```

### Example 3: Breaking Change
```
Current version: v1.2.5

Commits in PR:
- feat!: migrate to new authentication system
- refactor: update all auth endpoints

Result: v2.0.0 (major bump from '!')
```

### Example 4: No Version Bump
```
Current version: v1.2.5

Commits in PR:
- docs: fix typo in README
- style: format code with Black
- chore: update .gitignore

Result: No new version (no release)
```

## Tips for Success

1. **Be Specific**: `feat: add GPX merger` is better than `feat: new tool`
2. **One Concern Per Commit**: Separate features and fixes into different commits
3. **Use Scopes**: Helps organize changelog and understand impact
4. **Breaking Changes**: Always document in commit footer what breaks and how to migrate
5. **Squash Carefully**: When squashing PR commits, ensure the final commit message is conventional

## Checking Your Release

After your PR is merged, check:

1. **GitHub Releases**: https://github.com/your-org/magictoolbox/releases
2. **CHANGELOG.md**: View auto-generated changelog
3. **Production URL**: Verify deployment at your Container App URL
4. **Container Image**: Check Azure Container Registry for new version tags

## Questions?

- **Q: What if I make a typo in commit message?**
  - A: Fix it before merging: `git commit --amend` or squash commits in PR

- **Q: Can I skip automatic release?**
  - A: Yes! Use only `docs:`, `style:`, `test:`, `chore:` types

- **Q: What if semantic-release fails?**
  - A: Check GitHub Actions logs; it won't deploy if release fails

- **Q: How do I rollback a version?**
  - A: Manually deploy previous version tag or revert the PR and merge to main

## References

- [Conventional Commits Specification](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Semantic Release Documentation](https://semantic-release.gitbook.io/)

---

**Remember**: Every merge to `main` can trigger a production release. Write clear, conventional commits! 🚀
