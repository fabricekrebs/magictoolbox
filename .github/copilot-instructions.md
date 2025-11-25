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

### Adding New Tools
1. **Backend Django App**: Create a new Django app in `apps/tools/plugins/` for the tool
2. **Tool Interface**: Tool class must inherit from `BaseTool` and implement: `validate()`, `process()`, `cleanup()`
3. **API Endpoint**: Add DRF ViewSet in tool's `views.py`
4. **URL Registration**: Register in `apps/api/v1/urls.py`
5. **Frontend Template**: Create tool template in `templates/tools/` for the UI
6. **Registration**: Register tool in the tool registry for automatic discovery
7. **Documentation**: Use DRF's built-in API documentation
8. **Tests**: Write unit tests using pytest-django and integration tests

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
- Maximum file size: Configurable per tool (default 50MB)
- Allowed types: Whitelist approach (reject by default)
- Temporary storage: Local temp directory during processing
- Permanent storage: Azure Blob Storage for processed files
- Cleanup: Automatic cleanup after processing (success or failure)
- Async processing: Use Celery with Azure Storage Queues for background tasks
- Progress tracking: WebSocket or polling endpoints for status

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

### Deployment (Azure Container Apps)
- **Containerization**: Docker for Django application (backend + templates)
- **Container Registry**: Azure Container Registry (ACR)
- **Orchestration**: Azure Container Apps with revision management
- **Infrastructure as Code**: Bicep templates for all Azure resources
- **CI/CD**: GitHub Actions with Azure integration
- **Monitoring**: Azure Monitor, Application Insights for telemetry
- **Secrets Management**: Azure Key Vault with managed identity
- **Scaling**: Automatic scaling based on HTTP traffic and CPU/memory

### Documentation
- README.md: Project overview, setup instructions
- API documentation: DRF's browsable API + drf-spectacular for OpenAPI/Swagger
- Architecture diagrams: In `docs/architecture/`
- Tool documentation: Each tool has usage examples
- Changelog: Keep updated with notable changes

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
