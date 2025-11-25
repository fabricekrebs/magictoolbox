---
description: Backend-specific development guidelines for MagicToolbox
applyTo: 'backend/**'
---

# Backend Development Guidelines

## Django + Django REST Framework Best Practices

### Application Structure
- Use Django apps for modular organization (one app per major feature)
- Django project structure with split settings (base, development, production)
- Use Django REST Framework (DRF) ViewSets and Routers for API endpoints
- Configure CORS middleware using django-cors-headers
- Implement custom middleware for request ID tracking and logging
- Use Django's built-in admin for data management

### Request/Response Handling
```python
# Use DRF Serializers for request/response validation
from rest_framework import serializers

class ToolProcessRequestSerializer(serializers.Serializer):
    file_data = serializers.FileField()
    options = serializers.JSONField(default=dict, required=False)
    
    def validate_file_data(self, value):
        # Add validation logic
        if value.size > 50 * 1024 * 1024:  # 50MB
            raise serializers.ValidationError("File too large")
        return value

class ToolProcessResponseSerializer(serializers.Serializer):
    task_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=['pending', 'processing', 'completed', 'failed'])
    result_url = serializers.URLField(required=False, allow_null=True)
```

### Error Handling
- Use DRF's APIException for client errors (4xx)
- Create custom exceptions inheriting from APIException
- Implement custom exception handler in settings
- Log all exceptions with appropriate context
- Never expose internal error details to clients

```python
from rest_framework.exceptions import APIException
from rest_framework import status

class ToolProcessingError(APIException):
    """Custom exception for tool processing errors"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Tool processing failed'
    default_code = 'tool_processing_error'

# In settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}

# In apps/core/exceptions.py
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            'message': response.data.get('detail', 'An error occurred'),
            'code': getattr(exc, 'default_code', 'error'),
            'details': response.data
        }
    return response
```

### Authentication & Authorization
- Use Django REST Framework SimpleJWT for token-based authentication
- Implement custom permissions for role-based access control (RBAC)
- Use Django's built-in User model or extend it
- Store hashed passwords only (Django handles this automatically)
- Implement token refresh mechanism

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Custom permission in apps/core/permissions.py
from rest_framework import permissions

class IsToolOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff
```

### Database Operations
- Use Django ORM for all database operations
- Always use transactions with atomic() for multi-step operations
- Implement QuerySet optimization with select_related() and prefetch_related()
- Use Django migrations for schema changes
- Add indexes via Meta class in models or migrations
- Use database transactions for data consistency

```python
from django.db import models, transaction
from django.contrib.auth import get_user_model

User = get_user_model()

class ToolExecution(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tool_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
        ]

# Use transactions for multi-step operations
@transaction.atomic
def create_tool_execution(tool_id: str, user: User) -> ToolExecution:
    execution = ToolExecution.objects.create(
        tool_id=tool_id,
        user=user,
        status='pending'
    )
    # Additional operations...
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
- Implement processing methods (can be async if needed)
- Add proper cleanup for temporary files
- Tools are Django apps in `apps/tools/plugins/`

```python
from abc import ABC, abstractmethod
from typing import Any, Dict
from django.core.files.uploadedfile import UploadedFile

class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    name: str
    description: str
    input_formats: list[str]
    output_formats: list[str]
    max_file_size: int = 50 * 1024 * 1024  # 50MB default
    
    @abstractmethod
    def validate(self, input_file: UploadedFile, options: Dict[str, Any]) -> bool:
        """Validate input before processing"""
        pass
    
    @abstractmethod
    def process(self, input_file: UploadedFile, options: Dict[str, Any]) -> Any:
        """Main processing logic - returns processed file path or data"""
        pass
    
    @abstractmethod
    def cleanup(self, temp_files: list[str]) -> None:
        """Clean up temporary files"""
        pass
    
    def get_output_filename(self, input_filename: str, output_format: str) -> str:
        """Generate output filename based on input"""
        base_name = input_filename.rsplit('.', 1)[0]
        return f"{base_name}_converted.{output_format}"
```

### File Upload Processing
- Use Django's UploadedFile for file handling
- Stream large files to avoid memory issues
- Validate file type using magic numbers, not just extensions
- Store files temporarily with unique identifiers
- Upload to Azure Blob Storage for permanent storage
- Clean up local temporary files after upload

```python
import os
import uuid
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
import magic

def validate_file_type(uploaded_file: UploadedFile, allowed_mimes: list[str]) -> bool:
    """Validate file type using magic numbers"""
    mime = magic.from_buffer(uploaded_file.read(1024), mime=True)
    uploaded_file.seek(0)  # Reset file pointer
    return mime in allowed_mimes

def save_temp_file(uploaded_file: UploadedFile) -> str:
    """Save uploaded file to temporary location"""
    temp_dir = settings.MEDIA_ROOT / 'temp'
    temp_dir.mkdir(exist_ok=True)
    
    filename = f"{uuid.uuid4()}_{uploaded_file.name}"
    temp_path = temp_dir / filename
    
    with open(temp_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    return str(temp_path)
```

### Background Tasks (Celery)
- Use Celery for asynchronous task processing
- Configure Azure Storage Queues as broker
- Store task status in Azure Cache for Redis
- Provide status endpoint for task polling
- Set appropriate task timeouts and retries

```python
# celery.py
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magictoolbox.settings.production')

app = Celery('magictoolbox')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# tasks.py
from celery import shared_task
from apps.tools.registry import tool_registry
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_tool_task(self, task_id: str, tool_name: str, file_path: str, options: dict):
    """Background task for tool processing"""
    try:
        tool = tool_registry.get_tool(tool_name)
        result = tool.process(file_path, options)
        
        # Update task status
        update_task_status(task_id, "completed", result=result)
        return result
    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}")
        update_task_status(task_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)
    finally:
        tool.cleanup([file_path])

# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

class ToolViewSet(viewsets.ViewSet):
    @action(detail=False, methods=['post'])
    def process(self, request):
        serializer = ToolProcessRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        task_id = str(uuid.uuid4())
        file_path = save_temp_file(serializer.validated_data['file_data'])
        
        # Queue task
        process_tool_task.delay(task_id, request.data['tool_name'], file_path, {})
        
        return Response({
            'taskId': task_id,
            'status': 'processing'
        }, status=status.HTTP_202_ACCEPTED)
```

### Caching Strategy
- Use Azure Cache for Redis via django-redis
- Cache tool metadata and configuration
- Implement cache invalidation strategies
- Use Django's cache framework decorators
- Cache API responses with appropriate TTL

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'magictoolbox',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# views.py
from django.views.decorators.cache import cache_page
from django.core.cache import cache

class ToolViewSet(viewsets.ReadOnlyModelViewSet):
    @cache_page(60 * 15)  # Cache for 15 minutes
    def list(self, request):
        # Get list of available tools
        tools = cache.get('available_tools')
        if tools is None:
            tools = tool_registry.get_all_tools()
            cache.set('available_tools', tools, timeout=60 * 60)  # 1 hour
        return Response(tools)
```

### Logging & Monitoring
- Use Django's logging framework with Azure Application Insights
- Log all API requests with request ID (via middleware)
- Log tool processing start/end with duration
- Log errors with full context and stack traces
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR)
- Never log sensitive data (passwords, tokens, PII)

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'azure': {
            'class': 'opencensus.ext.azure.log_exporter.AzureLogHandler',
            'connection_string': os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING'),
        },
    },
    'root': {
        'handlers': ['console', 'azure'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'azure'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# middleware.py
import logging
import uuid
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4()))
        logger.info('request_received', extra={
            'request_id': request.id,
            'method': request.method,
            'path': request.path,
            'user': str(request.user) if request.user.is_authenticated else 'anonymous'
        })
```

### Configuration Management
- Use Django settings with split configuration (base, development, production)
- Load from environment variables using python-decouple or django-environ
- Use Azure Key Vault for production secrets
- Validate all configuration on startup
- Document all configuration options

```python
# settings/base.py
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default=5432, cast=int),
        'CONN_MAX_AGE': 600,
    }
}

# Azure Storage for media files
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
AZURE_ACCOUNT_NAME = config('AZURE_STORAGE_ACCOUNT_NAME')
AZURE_ACCOUNT_KEY = config('AZURE_STORAGE_ACCOUNT_KEY')
AZURE_CONTAINER = config('AZURE_STORAGE_CONTAINER', default='media')

# settings/production.py
from .base import *

# Use Azure Key Vault in production
if not DEBUG:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    
    credential = DefaultAzureCredential()
    vault_url = config('AZURE_KEY_VAULT_URL')
    client = SecretClient(vault_url=vault_url, credential=credential)
    
    SECRET_KEY = client.get_secret('django-secret-key').value
```

### API Versioning & Documentation
- Version all API endpoints (`/api/v1/`, `/api/v2/`)
- Use DRF's built-in versioning
- Maintain backward compatibility when possible
- Document breaking changes in changelog
- Use drf-spectacular for OpenAPI/Swagger documentation

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.NamespaceVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2'],
    'VERSION_PARAM': 'version',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'MagicToolbox API',
    'DESCRIPTION': 'API for file and image conversion tools',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/', include('apps.api.v1.urls', namespace='v1')),
]
```

### Testing Guidelines
- Use pytest-django for all tests
- Test all endpoints with multiple scenarios
- Mock external dependencies (Azure services)
- Use Django test fixtures and factories (factory_boy)
- Test error cases and edge cases
- Aim for >80% code coverage

```python
# conftest.py
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client

# test_tools.py
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.mark.django_db
def test_process_tool_success(authenticated_client):
    file_content = b"fake_image_data"
    uploaded_file = SimpleUploadedFile("test.jpg", file_content, content_type="image/jpeg")
    
    response = authenticated_client.post(
        "/api/v1/tools/process/",
        {"file_data": uploaded_file, "tool_name": "image-converter"},
        format='multipart'
    )
    
    assert response.status_code == 202
    assert "taskId" in response.json()
    assert response.json()["status"] == "processing"
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

### Health Checks & Monitoring
- Implement health check endpoint for Azure Container Apps
- Add readiness check for dependencies (database, Redis, storage)
- Use Azure Application Insights for telemetry
- Track API response times and errors
- Monitor database connection pool
- Track Celery task queue size

```python
# apps/core/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Simple liveness probe"""
    return Response({'status': 'healthy'})

@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """Check all dependencies"""
    checks = {}
    
    # Database check
    try:
        connection.ensure_connection()
        checks['database'] = 'healthy'
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        checks['database'] = 'unhealthy'
    
    # Redis check
    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        checks['redis'] = 'healthy'
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        checks['redis'] = 'unhealthy'
    
    all_healthy = all(v == 'healthy' for v in checks.values())
    status_code = 200 if all_healthy else 503
    
    return Response({
        'status': 'ready' if all_healthy else 'not_ready',
        'checks': checks
    }, status=status_code)
```
