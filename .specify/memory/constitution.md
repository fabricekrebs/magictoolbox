<!--
Sync Impact Report - Version 1.0.0
==================================
Version Change: INITIAL → 1.0.0
Constitution Type: MINOR (initial constitution establishment)

Principles Established:
1. Code Quality & Type Safety - Enforces Python type hints, PEP 8, 80%+ test coverage
2. Test-First Development - Mandatory TDD with pytest-django, red-green-refactor cycle
3. User Experience Consistency - Bootstrap 5, responsive design, accessibility WCAG 2.1 AA
4. Performance Requirements - Response times, file processing limits, database optimization
5. Security by Design - Azure Key Vault, input validation, HTTPS, least privilege

Sections Added:
- Core Principles (5 principles)
- Development Standards
- Quality Gates
- Governance

Templates Status:
✅ plan-template.md - Constitution Check section aligns with 5 principles
✅ spec-template.md - User Scenarios support independent testing requirement
✅ tasks-template.md - Task categorization supports TDD and phased implementation
⚠ PENDING: Review command files in .specify/templates/commands/*.md (if any)

Follow-up TODOs:
- None - All placeholders filled based on project context
-->

# MagicToolbox Constitution

**Project Description**: MagicToolbox is a comprehensive web-based utility platform that provides users with a curated collection of powerful file conversion, GPS/fitness tracking, text processing, image manipulation, and document transformation tools. Built with Django and deployed on Azure Container Apps, it offers both synchronous and asynchronous processing capabilities for handling everything from quick text encoding to complex video rotation. The platform features a plugin-based architecture allowing easy addition of new tools while maintaining consistent user experience through Bootstrap 5 responsive design.

**Current Tools Portfolio**:
- **Document Processing**: PDF to DOCX conversion with layout preservation
- **Image Tools**: Format conversion (15+ formats), EXIF metadata extraction, OCR text extraction (14+ languages)
- **Video Tools**: Rotation and transformation
- **GPS/Fitness**: GPX track analysis, GPX/KML bidirectional conversion, GPX merger (3 modes), GPX speed modification
- **Text Utilities**: Base64 encoder/decoder, hash generators, JSON formatter
- **Unit Conversion**: 160+ units across 18 categories with bidirectional conversion

---

## Core Principles

### I. Code Quality & Type Safety (NON-NEGOTIABLE)

**Rules**:
- Python type hints MUST be used for all function signatures and class attributes
- Code MUST follow PEP 8 style guide (enforced via Black formatter, line length 100)
- Import organization MUST use isort with standard configuration
- Linting with pylint/ruff MUST pass with no errors before commit
- Minimum 80% test coverage required for all new code
- Docstrings (Google style) MUST document all public functions, classes, and modules

**Rationale**: Type safety catches bugs at development time rather than runtime. Consistent formatting reduces cognitive load during code review and enables faster collaboration. High test coverage ensures reliability and confidence in refactoring.

### II. Test-First Development (NON-NEGOTIABLE)

**Rules**:
- TDD workflow MUST be followed: Write test → Test fails (red) → Implement → Test passes (green) → Refactor
- Tests MUST be written and approved by stakeholders BEFORE implementation begins
- pytest-django framework MUST be used for all backend tests
- Unit tests required for business logic; integration tests for API endpoints; E2E tests for critical user flows
- Mock external services (Azure services, third-party APIs) in unit and integration tests
- Test fixtures MUST be used for common setup to avoid duplication
- CI/CD pipeline MUST pass all tests before merge approval

**Rationale**: Test-first development ensures requirements are clear before coding begins, reduces defects, enables confident refactoring, and serves as living documentation. External service mocking ensures fast, reliable test execution.

### III. User Experience Consistency

**Rules**:
- Bootstrap 5 MUST be used for all frontend components (responsive grid, utilities)
- Django Templates for server-side rendering; vanilla JavaScript or minimal jQuery only
- Mobile-first responsive design MUST be implemented (test on mobile, tablet, desktop)
- Two-column layout pattern for file processing tools: Upload/Status (8 cols) + History sidebar (4 cols)
- History sections MUST display last 10 items with download, delete, and refresh actions
- WCAG 2.1 Level AA accessibility MUST be met: semantic HTML, ARIA labels, keyboard navigation
- Forms MUST use django-crispy-forms with crispy-bootstrap5 for consistent styling
- Status polling MUST occur every 2-3 seconds for async operations with visual feedback
- Error messages MUST be clear, actionable, and user-friendly (not raw stack traces)

**Rationale**: Consistent UI patterns reduce learning curve, increase productivity, and improve user satisfaction. Accessibility ensures the application is usable by all users. Real-time feedback builds trust during long-running operations.

### IV. Performance Requirements

**Rules**:
- API response time MUST be <200ms p95 for synchronous endpoints
- File processing MUST use async pattern: Upload to blob → Azure Function processes → Client polls status
- Database queries MUST use select_related/prefetch_related to avoid N+1 queries
- Azure Cache for Redis MUST be used for: sessions, frequently accessed data, API response caching
- Static assets MUST be served via CDN with browser caching headers
- File uploads: Maximum 50MB default, 500MB for video files (configurable per tool)
- Large file operations MUST stream data rather than loading entirely into memory
- Azure Functions MUST have timeout handling and temp file cleanup in try/finally blocks
- Database migrations MUST be tested for performance impact on large datasets before production

**Rationale**: Performance directly impacts user satisfaction and operational costs. Async processing prevents blocking the web server during long-running operations. Caching reduces database load and improves response times.

### V. Security by Design (NON-NEGOTIABLE)

**Rules**:
- Secrets, API keys, credentials MUST NEVER be committed to version control
- Azure Key Vault MUST be used for all production secrets; .env files for local development only
- Input validation MUST occur on both client (UX) and server (security) sides
- File uploads MUST be validated: whitelist allowed types, enforce size limits, scan content
- HTTPS MUST be enforced in production (handled by Azure Container Apps)
- Rate limiting MUST be implemented on all API endpoints using DRF throttling
- Principle of least privilege MUST be applied to all Azure resource permissions
- Azure Managed Identity MUST be used for service-to-service authentication (no connection strings)
- CORS policies MUST be explicitly configured (no wildcard origins in production)
- SQL injection protection via Django ORM parameterized queries (no raw SQL without sanitization)

**Rationale**: Security breaches damage user trust, cause legal liability, and compromise data integrity. Defense-in-depth approach ensures multiple layers of protection. Managed Identity eliminates credential management risks.

## Development Standards

### Code Organization
- **Backend**: Django apps in `apps/` (core, authentication, tools, api)
- **Frontend**: Django templates in `templates/` with Bootstrap 5, static assets in `static/`
- **Infrastructure**: Bicep templates in `infra/` for all Azure resources
- **Documentation**: Comprehensive docs in `documentation/` (guides, troubleshooting, architecture)
- **Tests**: Mirror source structure in `tests/` directory

### Async File Processing (MANDATORY for file manipulation tools)
All file conversion, transformation, and manipulation tools MUST follow the async pattern:
1. User uploads file → Django validates and uploads to Azure Blob Storage (`uploads/{category}/{execution_id}{ext}`)
2. Django triggers Azure Function via HTTP POST to `{base_url}/{category}/{action}`
3. Azure Function processes file and uploads result to `processed/{category}/` container
4. Client polls status endpoint every 2-3 seconds until completion
5. Blob Storage authentication: Connection string (local Azurite) or Managed Identity (Azure)

Reference implementations: PDF to DOCX Converter, Video Rotation tool

### API Conventions
- **Endpoint Naming**: Noun-based, plural resources (e.g., `/api/v1/tools/image-converter/`)
- **HTTP Methods**: GET (read), POST (create/process), PUT (update), PATCH (partial), DELETE (remove)
- **Status Codes**: 200 (success), 201 (created), 400 (validation), 401 (auth), 403 (forbidden), 404 (not found), 500 (server error)
- **Request/Response Format**: JSON with camelCase keys (DRF camelCase renderer)
- **Pagination**: PageNumberPagination with `page` and `page_size` parameters
- **Error Format**: Consistent structure with `message`, `code`, `details` (camelCase)

### Environment Configuration
- **Local Development**: `.env.development` (not committed, template in `.env.example`)
- **Production**: Azure Key Vault + Azure App Configuration
- **Required Variables**: DATABASE_URL, REDIS_URL, AZURE_STORAGE_CONNECTION_STRING, SECRET_KEY, JWT_SECRET, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, MAX_UPLOAD_SIZE, AZURE_FUNCTION_BASE_URL

### Database Migrations
- Use Django migrations for all schema changes
- Never edit migration files after commit
- Test migrations both forward (apply) and backward (rollback)
- Keep migrations atomic and reversible
- Document breaking changes in migration comments

## Quality Gates

### Pre-Commit Checks
- [ ] Code formatted with Black (line length 100)
- [ ] Imports sorted with isort
- [ ] Linting passes (pylint/ruff with no errors)
- [ ] Type checking passes (mypy)
- [ ] All tests pass locally (pytest)

### Pull Request Requirements
- [ ] All pre-commit checks pass
- [ ] Test coverage ≥80% for new code
- [ ] Code review approval from at least one team member
- [ ] No security vulnerabilities identified
- [ ] Documentation updated (README, API docs, architecture diagrams as needed)
- [ ] Error handling implemented with proper logging
- [ ] Constitution compliance verified (all 5 principles)
- [ ] CI/CD pipeline passes (tests, linting, builds)

### Deployment Checklist
- [ ] All tests pass in staging environment
- [ ] Performance benchmarks meet requirements (p95 <200ms)
- [ ] Security scan completed (no critical vulnerabilities)
- [ ] Database migrations tested with production-like data volumes
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured (Azure Monitor, Application Insights)
- [ ] Secrets migrated to Azure Key Vault
- [ ] Infrastructure as Code (Bicep) validated

## Governance

### Amendment Process
1. Propose constitution change via Pull Request to `.specify/memory/constitution.md`
2. Include rationale, impact analysis, and affected templates/docs
3. Team review and discussion (minimum 2 approvals required)
4. Update version following semantic versioning:
   - **MAJOR**: Backward-incompatible principle removals or redefinitions
   - **MINOR**: New principle/section added or materially expanded guidance
   - **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements
5. Propagate changes to dependent artifacts (templates, docs, CI/CD)
6. Update LAST_AMENDED_DATE to amendment date

### Compliance Review
- Constitution supersedes all other development practices and guidelines
- All PRs MUST verify compliance with Core Principles (automated checks where possible)
- Complexity or deviations MUST be justified in PR description and approved by team
- Quarterly constitution review to ensure alignment with evolving project needs
- Use `.github/copilot-instructions.md` for runtime development guidance and best practices

### Enforcement
- CI/CD pipeline configured to enforce quality gates automatically
- Code reviews MUST explicitly verify principle compliance
- Non-compliance blocks merge approval
- Retrospectives include constitution effectiveness review

**Version**: 1.0.0 | **Ratified**: 2025-12-20 | **Last Amended**: 2025-12-20
