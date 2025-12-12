---
description: MagicToolbox development guidelines and best practices
applyTo: '**'
---

# MagicToolbox Development Guidelines

## Project Overview
MagicToolbox is a modular web application that hosts multiple tools for file and image conversion. The application is built with Django for both backend and frontend, using Django templates with Bootstrap for a responsive UI. The application is deployed on Azure Container Apps.

## Architecture Principles

### Backend (Python)
- **Framework**: Use Django 5.0+ for both backend logic and frontend rendering
- **Structure**: Modular plugin-based architecture for tools using Django apps
- **API Design**: RESTful principles with Django REST Framework (DRF) for API endpoints, versioned at `/api/v1/`
- **Authentication**: Django's built-in authentication system with session-based auth for web UI, JWT for API access
- **File Handling**: Django file upload handling, Azure Blob Storage for permanent storage
- **Database**: Azure Database for PostgreSQL Flexible Server for persistent data
- **Cache**: Azure Cache for Redis for caching and sessions
- **Type Safety**: Use Python type hints throughout
- **Testing**: pytest-django with minimum 80% coverage for new code

### Frontend (Django Templates + Bootstrap)
- **Template Engine**: Django Templates for server-side rendering
- **Styling**: Bootstrap 5 for responsive, consistent design
- **JavaScript**: Vanilla JavaScript or minimal jQuery for interactivity
- **AJAX**: Fetch API for asynchronous operations
- **Forms**: Django Forms with Bootstrap styling using django-crispy-forms and crispy-bootstrap5
- **Icons**: Bootstrap Icons or Font Awesome
- **Responsive Design**: Mobile-first approach with Bootstrap grid system

### Deployment (Azure)
- **Platform**: Azure Container Apps for container orchestration
- **Container Registry**: Azure Container Registry for Docker images
- **Database**: Azure Database for PostgreSQL Flexible Server
- **Cache**: Azure Cache for Redis
- **Storage**: Azure Blob Storage for file uploads and processing
- **Secrets**: Azure Key Vault for secure configuration
- **Monitoring**: Azure Monitor and Application Insights
- **IaC**: Bicep templates for infrastructure as code

### Security Requirements
- Never commit secrets, API keys, or credentials
- Use Azure Key Vault for all secrets
- Implement CORS policies appropriately
- Validate all user inputs on both client and server
- Sanitize file uploads (type, size, content validation)
- Use HTTPS in production (enforced by Azure Container Apps)
- Implement rate limiting on all endpoints
- Apply principle of least privilege for permissions
- Use Azure Managed Identity for service-to-service authentication

### Code Organization

#### Backend Structure (Django)
```
backend/
├── magictoolbox/              # Django project root
│   ├── settings/
│   │   ├── base.py           # Base settings
│   │   ├── development.py    # Development settings
│   │   └── production.py     # Production settings
│   ├── urls.py               # Root URL configuration
│   ├── wsgi.py              # WSGI application
│   └── asgi.py              # ASGI application
├── apps/
│   ├── core/                 # Core functionality
│   │   ├── models.py        # Base models
│   │   ├── permissions.py   # Custom permissions
│   │   ├── middleware.py    # Custom middleware
│   │   └── exceptions.py    # Custom exceptions
│   ├── authentication/       # Auth & user management
│   │   ├── models.py        # User models
│   │   ├── serializers.py   # DRF serializers
│   │   └── views.py         # Auth endpoints
│   ├── tools/               # Tool plugin system
│   │   ├── models.py        # Tool execution models
│   │   ├── base.py          # BaseTool abstract class
│   │   ├── registry.py      # Tool registration
│   │   ├── serializers.py   # Tool serializers
│   │   └── views.py         # Tool API endpoints
│   └── api/                 # API versioning
│       └── v1/
│           ├── urls.py      # API v1 routes
│           └── views.py     # API v1 views
├── tests/                   # Test suite
├── requirements/
│   ├── base.txt            # Base dependencies
│   ├── development.txt     # Dev dependencies
│   └── production.txt      # Prod dependencies
└── manage.py
```

#### Frontend Structure (Django Templates)
```
backend/
├── templates/                # Django templates
│   ├── base.html            # Base template with Bootstrap
│   ├── includes/            # Reusable template fragments
│   │   ├── navbar.html      # Navigation bar
│   │   ├── footer.html      # Footer
│   │   └── messages.html    # Flash messages
│   ├── home.html            # Homepage
│   ├── tools/               # Tool-specific templates
│   │   ├── tool_list.html   # List of all tools
│   │   └── tool_detail.html # Individual tool interface
│   ├── authentication/      # Auth templates
│   │   ├── login.html
│   │   ├── register.html
│   │   └── profile.html
│   └── errors/              # Error pages
│       ├── 404.html
│       └── 500.html
├── static/                  # Static assets
│   ├── css/
│   │   └── custom.css       # Custom styles
│   ├── js/
│   │   └── main.js          # Custom JavaScript
│   └── images/
```

## Development Guidelines

### Python Virtual Environment
- **Always use `.venv` virtual environment** for all Python operations
- Activate before running any Python commands: `source .venv/bin/activate`
- Install dependencies inside `.venv`: `pip install -r requirements/development.txt`
- Run Django commands with activated `.venv`: `python manage.py <command>`
- Run tests with activated `.venv`: `pytest`

### ⭐ GOLD STANDARD - Async File Processing Tools

**CRITICAL**: All file processing tools (conversion, transformation, manipulation) **MUST** follow the async pattern.

#### Before Creating Any New Tool
1. **READ** `documentation/ASYNC_FILE_PROCESSING_GOLD_STANDARD.md` - This is **MANDATORY**
2. Study reference implementations:
   - PDF to DOCX Converter: `apps/tools/plugins/pdf_docx_converter.py`
   - Video Rotation: `apps/tools/plugins/video_rotation.py`
3. Follow the compliance checklist in the gold standard document

#### Async Tool Architecture Pattern (MANDATORY)
```
User Upload → Django validates & uploads to blob → Azure Function processes → Client polls status
```

**Key Requirements**:
- ✅ Tool's `process()` method returns `(execution_id, None)` for async
- ✅ Upload to standardized blob path: `uploads/{category}/{execution_id}{ext}`
- ✅ Azure Function endpoint: `/{category}/{action}` (e.g., `/pdf/convert`, `/video/rotate`)
- ✅ Database status tracking: `pending` → `processing` → `completed`/`failed`
- ✅ **Frontend Layout**: Two-column with upload/status (left 8 cols) and history sidebar (right 4 cols)
- ✅ **History Features**: Download, re-download, delete actions; shows last 10 items; auto-refreshes
- ✅ **Status Polling**: Client polls every 2-3 seconds until completion
- ✅ Support both Azurite (local) and Azure (Managed Identity) auth
- ✅ Comprehensive logging with emojis for easy scanning
- ✅ Azure Function endpoint: `/{category}/{action}` (e.g., `/pdf/convert`, `/video/rotate`)
- ✅ Database status tracking: `pending` → `processing` → `completed`/`failed`
- ✅ Frontend must have: upload form, status polling, **history section**
- ✅ Support both Azurite (local) and Azure (Managed Identity) auth
- ✅ Comprehensive logging with emojis for easy scanning

#### Container & Blob Naming Standards
**Containers**:
- `uploads` - Input files (organized by category: pdf/, video/, image/)
- `processed` - Output files (organized by category)
- `temp` - Temporary files (auto-cleanup)

**Blob Paths**:
- Input: `uploads/{category}/{execution_id}{original_ext}`
- Output: `processed/{category}/{execution_id}{output_ext}`

#### Configuration Naming Convention
**Django Settings**:
```python
# Single base URL for all Azure Functions
AZURE_FUNCTION_BASE_URL = config("AZURE_FUNCTION_BASE_URL", default="")

# Tool constructs full URL: f"{AZURE_FUNCTION_BASE_URL}/{category}/{action}"
# Examples:
#   {base_url}/pdf/convert
#   {base_url}/video/rotate
#   {base_url}/image/resize
```

**Benefits**: Single configuration point, easier maintenance

#### Frontend Template Requirements (MANDATORY)
**Two-Column Layout**:
- **Left Column (8 cols)**: Upload form, status section, instructions
- **Right Column (4 cols)**: History sidebar (sticky on desktop)

**MANDATORY Sections**:
1. **Upload Form** - File selection with tool-specific parameters
2. **Status Section** - Real-time progress with polling (every 2-3 seconds)
3. **History Sidebar** - Right-aligned, shows last 10 executions

**History Features** (ALL REQUIRED):
- ✅ Display input/output filenames
- ✅ Show status with color-coded badges
- ✅ Time ago display (e.g., "2m ago", "1h ago")
- ✅ Download button for completed items
- ✅ Delete button with confirmation modal
- ✅ Auto-refresh after upload completion
- ✅ Refresh button for manual updates
- ✅ Empty state message when no history
- ✅ Loading spinner during fetch

**Status Polling Pattern**:
```javascript
async function checkStatus() {
  const response = await fetch(`/api/v1/executions/${executionId}/status/`);
  const data = await response.json();
  if (data.status === 'completed') { 
    showDownloadButton(data.downloadUrl);
    loadHistory(); // Refresh history
  }
  else if (data.status === 'failed') { showError(data.error); }
  // Continue polling for 'pending' or 'processing'
}
```

**API Endpoints Required**:
- `POST /api/v1/tools/{tool-name}/convert/` - Upload & convert
- `GET /api/v1/executions/{id}/status/` - Check status
- `GET /api/v1/executions/{id}/download/` - Download result
- `GET /api/v1/executions/?tool_name={name}&limit=10` - Get history
- `DELETE /api/v1/executions/{id}/` - Delete item (with blob cleanup)

#### Azure Function Handler Pattern
```python
@app.route(route="{category}/{action}", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def process_file(req: func.HttpRequest) -> func.HttpResponse:
    execution_id = None
    temp_input = temp_output = None
    try:
        # 1. Parse request & validate
        # 2. Update DB: status='processing'
        # 3. Download from blob
        # 4. Process file
        # 5. Upload result to 'processed' container
        # 6. Update DB: status='completed'
        # 7. Cleanup temp files
        return func.HttpResponse(json.dumps({"status": "success"}), status_code=200)
    except Exception as e:
        # Update DB: status='failed'
        # Cleanup temp files
        return func.HttpResponse(json.dumps({"status": "error", "error": str(e)}), status_code=500)
```

#### Testing Requirements for Async Tools
- Unit tests with mocked blob storage
- Integration tests with local Azurite
- E2E tests in staging with real Azure resources
- Minimum 80% code coverage

#### Common Pitfalls to Avoid
- ❌ Don't use synchronous processing for file manipulation
- ❌ Don't skip the history section in templates
- ❌ Don't forget to cleanup temp files in Azure Functions
- ❌ Don't hardcode container names or blob paths
- ❌ Don't forget timeout handling in Azure Functions
- ❌ Don't skip comprehensive logging

---

### Adding New Non-Async Tools (Simple Tools)
For simple tools that don't require file processing (e.g., calculators, formatters):
1. **Backend Django App**: Create in `apps/tools/plugins/`
2. **Tool Interface**: Inherit from `BaseTool`, implement `validate()`, `process()`
3. **API Endpoint**: Add DRF ViewSet
4. **URL Registration**: Register in `apps/api/v1/urls.py`
5. **Frontend Template**: Create in `templates/tools/`
6. **Tests**: Write unit tests using pytest-django

### Code Style

#### Python
- Follow PEP 8 style guide
- **Naming Convention**: snake_case for variables/functions, PascalCase for classes
- **Indentation**: 4 spaces (no tabs)
- Use Black formatter (line length: 100)
- Use isort for import sorting
- Use pylint/ruff for linting
- Docstrings: Google style for all public functions/classes
- Async/await for I/O operations
- Type hints required for all function signatures

#### JavaScript/Templates
- **Naming Convention**: camelCase for JavaScript variables/functions
- **Indentation**: 2 spaces for JavaScript/HTML (no tabs)
- Use vanilla JavaScript or jQuery sparingly
- Keep JavaScript modular and minimal
- Use Django template tags and filters appropriately
- Follow Bootstrap conventions for class names
- Use data attributes for JavaScript hooks
- Validate forms on both client and server side

### API Conventions
- **Endpoints**: Noun-based, plural resources (e.g., `/api/v1/tools/image-converter/`)
- **Methods**: GET (read), POST (create/process), PUT (update), PATCH (partial update), DELETE (remove)
- **Status Codes**: 200 (success), 201 (created), 400 (validation), 401 (auth), 403 (forbidden), 404 (not found), 500 (server error)
- **Request/Response**: JSON API uses camelCase keys via DRF's camelCase renderer
- **Pagination**: Use DRF's PageNumberPagination with `page` and `page_size` parameters
- **Filtering**: Use django-filter for complex filtering
- **Error Format**: Consistent error response structure with `message`, `code`, `details` (camelCase)

### Environment Configuration
- **Development**: `.env.development` (not committed)
- **Production**: Azure Key Vault + Azure App Configuration
- **Template**: `.env.example` (committed as reference)
- **Required Variables**:
  - `DATABASE_URL` (Azure PostgreSQL connection string)
  - `REDIS_URL` (Azure Cache for Redis connection string)
  - `AZURE_STORAGE_CONNECTION_STRING` (Azure Blob Storage)
  - `SECRET_KEY`, `JWT_SECRET`
  - `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
  - `MAX_UPLOAD_SIZE`
  - Tool-specific API keys (prefixed with `TOOL_`)

### File Upload Handling
- Maximum file size: Configurable per tool (default 50MB, up to 500MB for video)
- Allowed types: Whitelist approach (reject by default)
- **Async Processing Pattern** (MANDATORY for file manipulation):
  - Upload to Azure Blob Storage (`uploads/{category}/{execution_id}{ext}`)
  - Trigger Azure Function via HTTP POST
  - Azure Function processes and uploads to `processed/{category}/` container
  - Client polls status endpoint every 2-3 seconds
- **Blob Storage Authentication**:
  - Local: Connection string to Azurite
  - Azure: Managed Identity (DefaultAzureCredential)
- Cleanup: Automatic cleanup of temp files in Azure Functions (try/finally blocks)
- Progress tracking: Polling endpoints for status (not webhooks)

### Database Migrations
- Use Django migrations for all schema changes
- Never edit migration files after commit
- Test migrations both forward and backward
- Keep migrations atomic and reversible
- Document breaking changes

### Testing Requirements
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user flows
- Mock external services in tests
- Use test fixtures for common setup
- CI/CD must pass all tests before merge

### Deployment (Azure)
- **Django App**: Azure Container Apps (Linux containers, automatic scaling)
- **Azure Functions**: Flex Consumption plan (Python 3.11, HTTP triggers)
- **Container Registry**: Azure Container Registry (ACR)
- **Infrastructure as Code**: Bicep templates for all Azure resources
- **Blob Storage Containers** (auto-created by Bicep):
  - `uploads` - Input files for async processing
  - `processed` - Output files from Azure Functions
  - `temp` - Temporary files (lifecycle management: auto-delete after 24h)
- **CI/CD**: GitHub Actions with Azure integration
- **Monitoring**: Azure Monitor, Application Insights for telemetry
- **Secrets Management**: Azure Key Vault with managed identity
- **Authentication**: Managed Identity for all service-to-service auth
- **Network Security**: Private endpoints, VNet integration, no public internet access

### Documentation
- README.md: Project overview, setup instructions
- API documentation: DRF's browsable API + drf-spectacular for OpenAPI/Swagger
- Architecture diagrams: In `docs/architecture/`
- Tool documentation: Each tool has usage examples
- Changelog: Keep updated with notable changes
- **All project documentation**: Create/update in `documentation/` folder (deployment guides, Azure docs, troubleshooting, etc.)
  - Use clear, descriptive filenames (e.g., `AZURE_DEPLOYMENT_README.md`, `TROUBLESHOOTING_GUIDE.md`)
  - Include cross-references to related documentation
  - Follow the existing documentation structure and style

## Commit Conventions
- Use conventional commits format: `type(scope): message`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Example: `feat(tools): add PDF to image converter`
- Reference issues: Include issue number in commit body

## Code Review Guidelines
- All changes require PR review before merge
- Check for security vulnerabilities
- Verify test coverage meets requirements
- Ensure documentation is updated
- Validate error handling
- Confirm proper logging is in place

## Performance Considerations
- Backend: Use database query optimization, Django QuerySet select_related/prefetch_related
- Templates: Use template fragment caching, minimize database queries in templates
- Static Files: Use Django's collectstatic, compress CSS/JS, leverage browser caching
- File Processing: Stream large files, use chunked processing, implement timeout handling
- API: Implement rate limiting with Django REST Framework throttling
- Caching: Use Azure Cache for Redis for sessions, query results, and API responses
- CDN: Use Azure CDN for static assets

## Accessibility
- Frontend components must meet WCAG 2.1 Level AA
- Use semantic HTML
- Proper ARIA labels for interactive elements
- Keyboard navigation support
- Screen reader testing for critical flows

---

**Note**: These guidelines are living documents. Propose changes via PR to the `.github/copilot-instructions.md` file.
