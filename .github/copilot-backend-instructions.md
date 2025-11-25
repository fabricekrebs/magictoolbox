---
description: Backend-specific development guidelines for MagicToolbox
applyTo: 'backend/**'
---

# Backend Development Guidelines

## FastAPI Best Practices

### Application Structure
- Use APIRouter for modular endpoint organization
- Implement dependency injection for database sessions, authentication
- Use lifespan events for startup/shutdown operations
- Configure CORS middleware with explicit allowed origins
- Enable request ID middleware for tracing

### Request/Response Handling
```python
# Always use Pydantic models for request/response
from pydantic import BaseModel, Field, validator

class ToolProcessRequest(BaseModel):
    file_data: str = Field(..., description="Base64 encoded file")
    options: dict[str, Any] = Field(default_factory=dict)
    
    @validator('file_data')
    def validate_file_data(cls, v):
        # Add validation logic
        return v

class ToolProcessResponse(BaseModel):
    task_id: str
    status: str
    result_url: Optional[str] = None
```

### Error Handling
- Use HTTPException for client errors (4xx)
- Use custom exceptions for business logic errors
- Implement global exception handler for consistent error responses
- Log all exceptions with appropriate context
- Never expose internal error details to clients

```python
from fastapi import HTTPException, status

class ToolProcessingError(Exception):
    """Custom exception for tool processing errors"""
    pass

@app.exception_handler(ToolProcessingError)
async def tool_processing_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Tool processing failed",
            "code": "TOOL_PROCESSING_ERROR",
            "details": str(exc)
        }
    )
```

### Authentication & Authorization
- Implement JWT token-based authentication
- Use OAuth2PasswordBearer for token extraction
- Create dependency for current user validation
- Implement role-based access control (RBAC)
- Store hashed passwords only (use bcrypt or argon2)

```python
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Token validation logic
    pass
```

### Database Operations
- Use SQLAlchemy 2.0+ with async support
- Always use sessions with context managers
- Implement repository pattern for data access
- Use Alembic for migrations
- Add indexes for frequently queried fields
- Use database transactions for multi-step operations

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def create_tool_execution(
    db: AsyncSession,
    tool_id: str,
    user_id: str
) -> ToolExecution:
    async with db.begin():
        execution = ToolExecution(tool_id=tool_id, user_id=user_id)
        db.add(execution)
        await db.flush()
        return execution
```

### Code Style Guidelines
- **Naming Convention**: Use snake_case for all variables, functions, and methods; PascalCase for classes
- **Indentation**: 4 spaces (no tabs) - strictly enforced
- Follow PEP 8 style guide
- Use Black formatter (line length: 100)
- Use isort for import sorting
- Type hints required for all function signatures
- Module names: lowercase with underscores (e.g., `tool_processor.py`)
- Constants: UPPER_CASE with underscores (e.g., `MAX_FILE_SIZE`)

### Tool Plugin System
- All tools inherit from `BaseTool` abstract class
- Tools register themselves in the tool registry
- Each tool defines supported input/output formats
- Implement async methods for processing
- Add proper cleanup for temporary files

```python
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    name: str
    description: str
    input_formats: list[str]
    output_formats: list[str]
    
    @abstractmethod
    async def validate(self, input_data: Any, options: Dict) -> bool:
        """Validate input before processing"""
        pass
    
    @abstractmethod
    async def process(self, input_data: Any, options: Dict) -> Any:
        """Main processing logic"""
        pass
    
    @abstractmethod
    async def cleanup(self, temp_files: list[str]) -> None:
        """Clean up temporary files"""
        pass
```

### File Upload Processing
- Use UploadFile from FastAPI for file handling
- Stream large files to avoid memory issues
- Validate file type using magic numbers, not extensions
- Implement virus scanning for uploaded files
- Store files temporarily with unique identifiers
- Clean up failed/completed processing files

```python
from fastapi import UploadFile, File
import aiofiles

async def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file to temporary location"""
    temp_path = f"/tmp/{uuid.uuid4()}_{upload_file.filename}"
    async with aiofiles.open(temp_path, 'wb') as f:
        while content := await upload_file.read(1024 * 1024):  # 1MB chunks
            await f.write(content)
    return temp_path
```

### Background Tasks
- Use BackgroundTasks for post-response processing
- Implement Celery for long-running tasks
- Store task status in Redis
- Provide status endpoint for task polling
- Set appropriate task timeouts

```python
from fastapi import BackgroundTasks

def process_tool_background(task_id: str, file_path: str):
    """Background task for tool processing"""
    try:
        # Processing logic
        update_task_status(task_id, "completed")
    except Exception as e:
        update_task_status(task_id, "failed", error=str(e))
    finally:
        cleanup_temp_files(file_path)

@router.post("/process")
async def process_tool(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    task_id = str(uuid.uuid4())
    file_path = await save_upload_file(file)
    background_tasks.add_task(process_tool_background, task_id, file_path)
    return {"task_id": task_id, "status": "processing"}
```

### Caching Strategy
- Use Redis for caching frequently accessed data
- Cache tool metadata and configuration
- Implement cache invalidation strategies
- Use ETags for HTTP caching
- Cache API responses with appropriate TTL

### Logging
- Use structlog for structured logging
- Log all API requests with request ID
- Log tool processing start/end with duration
- Log errors with full context and stack traces
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Never log sensitive data (passwords, tokens, PII)

```python
import structlog

logger = structlog.get_logger()

async def process_tool(tool_id: str, request_id: str):
    logger.info("tool_processing_started", tool_id=tool_id, request_id=request_id)
    try:
        result = await execute_tool(tool_id)
        logger.info("tool_processing_completed", tool_id=tool_id, request_id=request_id)
        return result
    except Exception as e:
        logger.error("tool_processing_failed", tool_id=tool_id, request_id=request_id, error=str(e))
        raise
```

### Configuration Management
- Use Pydantic Settings for configuration
- Load from environment variables
- Validate all configuration on startup
- Provide sensible defaults where appropriate
- Document all configuration options

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    max_upload_size: int = 52428800  # 50MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

### API Versioning
- Version all API endpoints (`/api/v1/`, `/api/v2/`)
- Maintain backward compatibility when possible
- Document breaking changes in changelog
- Deprecate endpoints before removal (with warnings)
- Use semantic versioning for API releases

### Testing Guidelines
- Use pytest with pytest-asyncio
- Test all endpoints with multiple scenarios
- Mock external dependencies
- Use fixtures for common test data
- Test error cases and edge cases
- Aim for >80% code coverage

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_process_tool_success(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/tools/image-converter/process",
        headers=auth_headers,
        files={"file": ("test.jpg", b"fake_image_data", "image/jpeg")}
    )
    assert response.status_code == 200
    assert "task_id" in response.json()
```

### Security Checklist
- [ ] All inputs validated with Pydantic
- [ ] SQL injection prevented (use parameterized queries)
- [ ] File upload restrictions enforced
- [ ] Authentication required for protected endpoints
- [ ] Rate limiting implemented
- [ ] CORS configured properly
- [ ] Secrets not hardcoded
- [ ] Dependencies regularly updated
- [ ] Security headers configured

### Performance Optimization
- Use async/await for I/O operations
- Implement connection pooling for database
- Use Redis for session storage and caching
- Optimize database queries (use EXPLAIN)
- Implement pagination for list endpoints
- Use lazy loading for relationships
- Profile slow endpoints and optimize bottlenecks

### Monitoring & Observability
- Implement health check endpoint (`/health`)
- Add readiness endpoint for K8s (`/ready`)
- Expose metrics endpoint for Prometheus
- Track API response times
- Monitor database connection pool
- Track background task queue size
- Set up alerts for critical errors
