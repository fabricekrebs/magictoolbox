# MagicToolbox Improvement Todo List

**Generated:** November 27, 2025  
**Branch:** develop  
**Status:** Ready for implementation

---

## 🔴 **CRITICAL - Do These First**

### Security & Stability
- [ ] **Sanitize file names** to prevent directory traversal attacks
  - Add filename validation in `apps/core/utils.py`
  - Apply to all file upload handlers
  
- [ ] **Re-enable API authentication** for production
  - Remove `permission_classes = []` from `ToolViewSet` in `apps/tools/views.py`
  - Add proper permission classes for each endpoint
  
- [ ] **Fix skipped tests**
  - Unskip tests in `tests/test_authentication.py`
  - Unskip tests in `tests/test_tools.py`
  - Ensure all tests pass before deployment

---

## 🟠 **HIGH PRIORITY - Configuration & Cleanup**

### Configuration Consolidation
- [ ] **Remove `setup.cfg`** (duplicates `pyproject.toml`)
  - Verify all settings are in `pyproject.toml`
  - Delete `setup.cfg`
  - Test that pytest still works

- [ ] **Update `.env.example`** with all current variables
  - Add missing Azure-specific variables
  - Add comments explaining each variable
  - Ensure it matches what's used in `settings/base.py` and `settings/production.py`

- [ ] **Consolidate documentation files**
  - Remove `GITHUB_SECRETS_SETUP.md` from root (keep in `documentation/`)
  - Remove or populate empty `static/README.md` and `templates/README.md`
  - Update root `README.md` with links to all docs

### Dependency Management
- [ ] **Review and loosen version constraints** in requirements files
  - Change strict versions (e.g., `>=5.0,<5.1`) to more flexible (e.g., `>=5.0,<6.0`)
  - Review `requirements/base.txt`, `requirements/development.txt`, `requirements/production.txt`
  
- [ ] **Remove whitenoise duplication**
  - Check if whitenoise appears in both base and production requirements
  - Keep only in production with `[brotli]` extra

---

## 🟡 **MEDIUM PRIORITY - Code Quality**

### Type Hints & Code Quality
- [ ] **Add complete type hints to `apps/tools/base.py`**
  - Use `Tuple[str, str]` for return types
  - Use `Optional[str]` consistently
  - Import `Tuple` from `typing`

- [ ] **Add type hints to all view functions**
  - `apps/core/views.py`
  - `apps/tools/views.py`
  - `apps/authentication/views.py`

- [ ] **Add module-level docstrings** to files missing them
  - Check all Python files in `apps/`
  - Follow Google docstring style

### Database Models
- [ ] **Review `ToolExecution` model structure**
  - Consider inheriting from `SoftDeleteModel` if soft deletes are needed
  - Add database-level constraints for status transitions
  
- [ ] **Add composite database indexes** for common queries
  - Add index on `(user, tool_name, created_at)` in `ToolExecution`
  - Add index on `(user, status, created_at)` in `ToolExecution`
  - Create and run migrations

- [ ] **Add model-level file validators**
  - Add max file size validator to `FileField`s
  - Add file type validators

### Error Handling
- [ ] **Standardize error handling across tool plugins**
  - Ensure all plugins use `ToolExecutionError` and `ToolValidationError`
  - Add more specific exception types if needed
  
- [ ] **Add request IDs to all log messages**
  - Extend logging formatters to include request ID from middleware
  - Update log format in `settings/base.py`

- [ ] **Consider structured logging**
  - Evaluate `python-json-logger` for better log parsing
  - Update Application Insights integration

---

## 🟢 **NORMAL PRIORITY - Features & UX**

### API Improvements
- [ ] **Split bulk conversion endpoint**
  - Create `/api/v1/tools/{tool_name}/convert/` for single files
  - Create `/api/v1/tools/{tool_name}/convert/batch/` for bulk uploads
  - Update documentation

- [ ] **Standardize API response format**
  - Always return JSON with `{status, data, message}` structure
  - Provide download URLs instead of raw file data
  - Update serializers

- [ ] **Implement rate limiting**
  - Add `@ratelimit` decorators to API endpoints
  - Configure in `settings/production.py`
  - Document rate limits in API docs

- [ ] **Add pagination to executions endpoint**
  - Ensure `ToolExecutionViewSet` uses DRF pagination
  - Add pagination parameters to API docs

### Template & UI Improvements
- [ ] **Make home page tools dynamic**
  - Load tools from registry instead of hardcoding
  - Update `templates/home.html`
  - Add fallback for when no tools are available

- [ ] **Create missing error templates**
  - Create `templates/errors/400.html`
  - Create `templates/errors/403.html`
  - Update existing `404.html` and `500.html` for consistency

- [ ] **Add tool execution results template**
  - Create template to show conversion results
  - Include download link and metadata
  - Add "Convert Another" button

- [ ] **Add client-side file validation**
  - Validate file size before upload
  - Validate file type before upload
  - Show validation errors immediately
  - Update `static/js/main.js`

- [ ] **Implement upload progress indicators**
  - Add progress bar during file upload
  - Show processing status
  - Add loading spinners

- [ ] **Add drag-and-drop file upload**
  - Implement drop zone in tool detail pages
  - Add visual feedback for drag-over
  - Update JavaScript

---

## 🔵 **LOW PRIORITY - Advanced Features**

### File Handling & Storage
- [ ] **Use context managers for temporary files**
  - Replace `tempfile.NamedTemporaryFile` with `tempfile.TemporaryDirectory`
  - Ensure automatic cleanup on exceptions
  - Update all tool plugins

- [ ] **Add Celery periodic task for cleanup**
  - Create task to delete old executions (>7 days)
  - Create task to delete orphaned files
  - Configure in `apps/tools/tasks.py`
  - Add to Celery beat schedule

- [ ] **Implement storage quota tracking**
  - Update `User` model with storage limit field
  - Add quota check before file upload
  - Add admin interface to manage quotas

- [ ] **Add file checksum/deduplication**
  - Generate SHA-256 hash for uploaded files
  - Store in `ToolExecution` model
  - Skip processing if duplicate detected

### Async Processing
- [ ] **Complete Celery task implementation**
  - Finish `process_tool_async` in `apps/tools/tasks.py`
  - Add task progress reporting with `update_state`
  - Test with long-running conversions

- [ ] **Implement task retry logic**
  - Add exponential backoff for failed tasks
  - Configure max retries
  - Log retry attempts

- [ ] **Add task status polling endpoint**
  - Create `/api/v1/executions/{id}/status/` endpoint
  - Return current processing status
  - Include progress percentage if available

### Plugin System Enhancement
- [ ] **Add plugin metadata system**
  - Add `version`, `author`, `dependencies` to `BaseTool`
  - Update `get_metadata()` method
  - Display in admin interface

- [ ] **Implement plugin compatibility checking**
  - Check Python version requirements
  - Check dependency versions
  - Warn on incompatibilities

- [ ] **Add admin interface to enable/disable tools**
  - Create Django admin interface for tool management
  - Add `enabled` flag to tool registry
  - Filter disabled tools from API responses

### Testing Improvements
- [ ] **Add tests for middleware**
  - Test `HealthCheckMiddleware` with internal IPs
  - Test `RequestIDMiddleware` functionality
  - Mock Azure health probe requests

- [ ] **Add integration tests with mocked Azure services**
  - Mock Azure Blob Storage
  - Mock Azure Key Vault
  - Mock Application Insights

- [ ] **Add fixture factories using `factory_boy`**
  - Create factory for `User`
  - Create factory for `ToolExecution`
  - Update existing tests to use factories

- [ ] **Add tests for file upload limits**
  - Test max file size enforcement
  - Test file type validation
  - Test multiple file upload limits

- [ ] **Increase test coverage to 90%+**
  - Identify untested code paths
  - Add missing test cases
  - Generate coverage report

---

## ⚪ **FUTURE - Long-term Improvements**

### Monitoring & Observability
- [ ] **Add custom Application Insights metrics**
  - Track conversion times per tool
  - Track file sizes processed
  - Track user activity metrics
  - Add custom events for important actions

- [ ] **Add Celery health check endpoint**
  - Create `/health/celery/` endpoint
  - Check worker availability
  - Check queue depth

- [ ] **Create Azure Monitor alerts**
  - Alert on error rate threshold
  - Alert on performance degradation
  - Alert on storage quota issues
  - Document alert configuration

### Performance Optimization
- [ ] **Add database query optimization**
  - Add `select_related` and `prefetch_related` where needed
  - Enable Django Debug Toolbar in development
  - Add query count assertions in tests
  - Document optimization patterns

- [ ] **Implement caching strategy**
  - Cache tool registry results (5 minutes TTL)
  - Cache user execution statistics
  - Cache API responses with ETags
  - Document cache invalidation

- [ ] **Configure Azure CDN for static files**
  - Set up CDN in Bicep templates
  - Update static files URL configuration
  - Test CDN delivery
  - Document CDN setup

### Advanced Features
- [ ] **Add WebSocket support for real-time updates**
  - Install Django Channels
  - Create WebSocket consumer for task status
  - Update frontend to use WebSockets
  - Document WebSocket API

- [ ] **Implement external plugin system**
  - Support loading plugins from pip packages
  - Define plugin interface/protocol
  - Add plugin discovery mechanism
  - Document plugin development

- [ ] **Add multi-language support**
  - Install Django i18n
  - Mark strings for translation
  - Add language files
  - Update templates

### Infrastructure & DevOps
- [ ] **Add Snyk/Dependabot for dependency scanning**
  - Configure in GitHub repository settings
  - Set up automated PR creation
  - Define security policy

- [ ] **Create staging environment**
  - Create `infra/parameters.staging.json`
  - Update GitHub Actions workflow
  - Document staging deployment process

- [ ] **Add smoke tests after deployment**
  - Create post-deployment test suite
  - Test critical endpoints
  - Add to CI/CD pipeline

- [ ] **Optimize Docker image**
  - Consider using Alpine base image
  - Implement proper image tagging (git SHA + version)
  - Add comprehensive `.dockerignore`
  - Document image optimization

### Documentation
- [ ] **Add `CHANGELOG.md`**
  - Follow semantic versioning
  - Document all notable changes
  - Update with each release

- [ ] **Add `CONTRIBUTING.md`**
  - Document contribution process
  - Include code style guidelines
  - Add PR template

- [ ] **Add `LICENSE` file**
  - Choose appropriate license
  - Add to repository root

- [ ] **Add `.editorconfig`**
  - Define coding styles
  - Support multiple IDEs
  - Ensure consistent formatting

- [ ] **Create architecture decision records (ADRs)**
  - Document important technical decisions
  - Store in `documentation/adr/`
  - Follow ADR template

- [ ] **Add API usage examples to README**
  - Include curl examples
  - Include Python client examples
  - Add authentication examples

---

## 📋 **How to Use This List**

1. **Pick a section** based on priority and available time
2. **Tell me which items** you want to implement (e.g., "Implement items 1, 2, and 3 from Critical")
3. **I'll implement them** without changing anything else
4. **Review and test** the changes before moving to the next items

**Example command to start:**
```
Implement the first 3 items from the CRITICAL section
```

or

```
Implement all HIGH PRIORITY configuration cleanup tasks
```

---

## 📊 **Progress Tracking**

- ✅ Use checkboxes to track completed items
- 🔄 Mark items as in-progress with `[🔄]`
- ❌ Mark blocked items with `[❌]` and add notes

---

**Last Updated:** November 27, 2025  
**Total Items:** 95  
**Completed:** 0  
**In Progress:** 0
