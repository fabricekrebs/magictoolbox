---
description: MagicToolbox development guidelines and best practices
applyTo: '**'
---

# MagicToolbox Development Guidelines

## Project Overview
MagicToolbox is a modular web application that hosts multiple tools for file and image conversion. The application follows a microservices architecture with a Python backend and React frontend, fully API-driven and secure.

## Architecture Principles

### Backend (Python)
- **Framework**: Use FastAPI for the REST API backend
- **Structure**: Modular plugin-based architecture for tools
- **API Design**: RESTful principles, versioned endpoints (e.g., `/api/v1/`)
- **Authentication**: JWT-based authentication with secure token handling
- **File Handling**: Async file operations, proper cleanup, size limits
- **Database**: PostgreSQL for persistent data, Redis for caching
- **Type Safety**: Use Python type hints throughout
- **Testing**: pytest with minimum 80% coverage for new code

### Frontend (React + TypeScript)
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **State Management**: React Query for server state, Zustand for client state
- **Styling**: Tailwind CSS for consistent, responsive design
- **API Client**: Axios with interceptors for auth and error handling
- **Routing**: React Router v6
- **Forms**: React Hook Form with Zod validation
- **Testing**: Vitest + React Testing Library

### Security Requirements
- Never commit secrets, API keys, or credentials
- Use environment variables for all configuration
- Implement CORS policies appropriately
- Validate all user inputs on both client and server
- Sanitize file uploads (type, size, content validation)
- Use HTTPS in production
- Implement rate limiting on all endpoints
- Apply principle of least privilege for permissions

### Code Organization

#### Backend Structure
```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API route handlers
│   │       └── dependencies.py # Dependency injection
│   ├── core/
│   │   ├── config.py          # Configuration management
│   │   ├── security.py        # Auth & security utilities
│   │   └── exceptions.py      # Custom exception classes
│   ├── models/                # Database models
│   ├── schemas/               # Pydantic schemas
│   ├── services/              # Business logic
│   ├── tools/                 # Tool plugins (one per tool)
│   │   ├── base.py           # Abstract base tool class
│   │   └── registry.py       # Tool registration system
│   └── utils/                 # Shared utilities
├── tests/
├── alembic/                   # Database migrations
├── requirements.txt
└── main.py
```

#### Frontend Structure
```
frontend/
├── src/
│   ├── api/                   # API client & endpoints
│   ├── components/
│   │   ├── common/           # Reusable components
│   │   └── tools/            # Tool-specific components
│   ├── hooks/                # Custom React hooks
│   ├── pages/                # Page components
│   ├── stores/               # State management
│   ├── types/                # TypeScript types
│   ├── utils/                # Helper functions
│   └── App.tsx
├── public/
├── tests/
└── package.json
```

## Development Guidelines

### Adding New Tools
1. **Backend Plugin**: Create a new tool class inheriting from `BaseTool` in `backend/app/tools/`
2. **Tool Interface**: Each tool must implement: `validate()`, `process()`, `cleanup()`
3. **API Endpoint**: Add dedicated endpoint in `backend/app/api/v1/endpoints/`
4. **Frontend Component**: Create tool UI in `frontend/src/components/tools/`
5. **Registration**: Register tool in the tool registry for automatic discovery
6. **Documentation**: Add OpenAPI documentation for all endpoints
7. **Tests**: Write unit tests for backend logic and integration tests for API

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

#### TypeScript/React
- **Naming Convention**: camelCase for variables/functions, PascalCase for components/types
- **Indentation**: 2 spaces (no tabs)
- Use ESLint with recommended TypeScript rules
- Use Prettier formatter (2 spaces, single quotes)
- Functional components with hooks only
- Named exports preferred over default exports
- Props interfaces defined inline or in separate types file
- Avoid `any` type - use `unknown` or proper types
- Use const for immutable values

### API Conventions
- **Endpoints**: Noun-based, plural resources (e.g., `/api/v1/tools/image-converter`)
- **Methods**: GET (read), POST (create/process), PUT (update), DELETE (remove)
- **Status Codes**: 200 (success), 201 (created), 400 (validation), 401 (auth), 404 (not found), 500 (server error)
- **Request/Response**: JSON API uses camelCase keys; backend internally uses snake_case (auto-converted via Pydantic)
- **Pagination**: Use `limit` and `offset` query parameters
- **Filtering**: Use query parameters for filters
- **Error Format**: Consistent error response structure with `message`, `code`, `details` (camelCase)

### Environment Configuration
- **Development**: `.env.development` (not committed)
- **Production**: `.env.production` (not committed)
- **Template**: `.env.example` (committed as reference)
- **Required Variables**:
  - `DATABASE_URL`, `REDIS_URL`
  - `SECRET_KEY`, `JWT_SECRET`
  - `ALLOWED_ORIGINS`
  - `MAX_UPLOAD_SIZE`
  - Tool-specific API keys (prefixed with `TOOL_`)

### File Upload Handling
- Maximum file size: Configurable per tool (default 50MB)
- Allowed types: Whitelist approach (reject by default)
- Temporary storage: Use `/tmp` or configured temp directory
- Cleanup: Automatic cleanup after processing (success or failure)
- Async processing: Use background tasks for large files
- Progress tracking: WebSocket or polling endpoints for status

### Database Migrations
- Use Alembic for all schema changes
- Never edit migration files after commit
- Test migrations both up and down
- Keep migrations atomic and reversible
- Document breaking changes

### Testing Requirements
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user flows
- Mock external services in tests
- Use test fixtures for common setup
- CI/CD must pass all tests before merge

### Deployment
- **Containerization**: Docker for both frontend and backend
- **Orchestration**: Docker Compose for local dev, Kubernetes manifests for production
- **Infrastructure as Code**: Terraform or Pulumi for cloud resources
- **CI/CD**: GitHub Actions or GitLab CI
- **Monitoring**: Structured logging, health check endpoints
- **Secrets Management**: Use proper secret managers (not env files in production)

### Documentation
- README.md: Project overview, setup instructions
- API documentation: Auto-generated from OpenAPI/Swagger
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
- Backend: Use async operations, implement caching, optimize database queries
- Frontend: Code splitting, lazy loading, optimize bundle size, use React.memo strategically
- File Processing: Stream large files, use chunked processing, implement timeout handling
- API: Implement rate limiting, use compression, cache responses where appropriate

## Accessibility
- Frontend components must meet WCAG 2.1 Level AA
- Use semantic HTML
- Proper ARIA labels for interactive elements
- Keyboard navigation support
- Screen reader testing for critical flows

---

**Note**: These guidelines are living documents. Propose changes via PR to the `.github/copilot-instructions.md` file.
