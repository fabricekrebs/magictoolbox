# Research & Technical Decisions

**Feature**: Async Tool Framework & Plugin System  
**Date**: 2025-12-21  
**Status**: Complete

## Executive Summary

This research document consolidates technical decisions for implementing a plugin-based tool framework with async processing capabilities for MagicToolbox. Key decisions include: Django's built-in plugin discovery via app auto-discovery, abstract base classes for tool standardization, Azure Blob Storage for file handling with Managed Identity authentication, and Azure Functions for async processing with HTTP triggers.

---

## 1. Plugin Discovery & Registration Mechanism

### Decision: Django AppConfig-based Auto-Discovery

**Rationale**:
- Leverages Django's existing app discovery mechanism (`INSTALLED_APPS` + `AppConfig.ready()`)
- Tools register themselves during Django startup via metaclass pattern
- No manual registration needed - drop file in `apps/tools/plugins/`, app auto-discovers
- Django's initialization order guarantees registry is populated before URL resolution

**How It Works**:
```python
# apps/tools/base.py
class ToolMeta(type):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        if name != 'BaseTool':  # Don't register abstract base
            ToolRegistry.register(cls())
        return cls

class BaseTool(metaclass=ToolMeta):
    # Abstract base class
```

**Alternatives Considered**:
- **Manual registration decorators**: Rejected - requires developers to remember decorator
- **Entry points (setuptools)**: Rejected - overkill for internal plugins, adds packaging complexity
- **File system scanning**: Rejected - fragile, doesn't respect Python module system

**Implementation References**:
- Django signals: `apps/tools/apps.py` `ready()` method triggers registry population
- Similar pattern used in Django's admin auto-discovery

---

## 2. Tool Base Class Design

### Decision: Abstract Base Class with Required Properties & Methods

**Rationale**:
- Python's `abc.ABC` enforces interface contract at class definition time
- Type hints enable IDE autocomplete and static type checking
- Clear separation between sync (`process() returns (result, None)`) and async (`process() returns (execution_id, None)`)
- Properties (name, category, etc.) as class attributes for metadata discoverability

**Interface Definition**:
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, Optional

class BaseTool(ABC):
    # Required class attributes (metadata)
    name: str
    display_name: str
    description: str
    category: str  # DOCUMENT, IMAGE, VIDEO, GPS, TEXT, CONVERSION
    supported_formats: list[str]
    max_file_size: int  # bytes
    is_async: bool = False  # Override to True for async tools
    
    @abstractmethod
    def validate(self, input_data: Dict[str, Any]) -> bool:
        """Validate input, raise ValidationError if invalid"""
        pass
    
    @abstractmethod
    def process(self, input_data: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
        """
        Process input.
        Returns: (result, None) for sync OR (execution_id, None) for async
        """
        pass
```

**Alternatives Considered**:
- **Protocol (PEP 544)**: Rejected - less explicit, no enforcement at definition time
- **Multiple inheritance**: Rejected - creates diamond problem complexity
- **Dataclass**: Rejected - dataclasses don't support abstract methods well

**Best Practices**:
- Use `@property` for computed metadata (e.g., URL slug from name)
- Keep validation logic in `validate()` separate from processing logic
- Document expected input/output formats in docstrings

---

## 3. Azure Blob Storage Integration

### Decision: BlobServiceClient with DefaultAzureCredential (Managed Identity)

**Rationale**:
- **Local Development**: Uses connection string to Azurite (local emulator)
- **Production**: Uses Azure Managed Identity via `DefaultAzureCredential` (no secrets)
- Standardized container naming: `uploads`, `processed`, `temp`
- Blob path convention: `{container}/{category}/{execution_id}{ext}`

**Authentication Pattern**:
```python
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

def get_blob_service_client() -> BlobServiceClient:
    connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
    if connection_string:
        # Local development (Azurite)
        return BlobServiceClient.from_connection_string(connection_string)
    else:
        # Production (Managed Identity)
        account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
        return BlobServiceClient(account_url, credential=DefaultAzureCredential())
```

**Container Lifecycle Management**:
- **uploads**: Input files, 7-day lifecycle policy (auto-delete after 7 days)
- **processed**: Output files, 30-day lifecycle policy
- **temp**: Temporary processing files, 24-hour lifecycle policy

**Alternatives Considered**:
- **Shared Access Signatures (SAS)**: Rejected - adds complexity, tokens expire
- **Storage Account Keys**: Rejected - security risk, violates principle of least privilege
- **Service Principal**: Rejected - Managed Identity is simpler, no secret rotation

**Implementation Best Practices**:
- Use async client (`BlobServiceClient` supports async operations)
- Implement retry logic with exponential backoff (Azure SDK has built-in retry policies)
- Log blob operations for debugging (include execution_id)

---

## 4. Async Processing Architecture

### Decision: Azure Functions with HTTP Triggers + Database Status Tracking

**Rationale**:
- **HTTP Trigger Pattern**: Django POST to Azure Function endpoint, function processes and updates DB
- **Status Polling**: Client polls Django API every 2-3 seconds until completion
- **Database as Source of Truth**: `ToolExecution` model tracks status (pending → processing → completed/failed)
- **Function Idempotency**: Execution ID ensures duplicate triggers don't cause double-processing

**Workflow**:
1. User uploads file → Django uploads to blob storage (`uploads/{category}/{execution_id}{ext}`)
2. Django creates `ToolExecution` record with status="pending"
3. Django POSTs to Azure Function: `{base_url}/{category}/{action}` with execution_id
4. Azure Function:
   - Updates status to "processing"
   - Downloads from `uploads/` container
   - Processes file
   - Uploads result to `processed/` container
   - Updates status to "completed" or "failed"
5. Client JavaScript polls `/api/v1/executions/{execution_id}/status/` every 2-3 seconds
6. On completion, client displays download button

**Azure Function Configuration**:
- **Plan**: Flex Consumption (auto-scaling, pay-per-execution)
- **Runtime**: Python 3.11
- **Auth Level**: Function (requires function key in production, anonymous for local dev)
- **Timeout**: Configurable per category (5 min default, 30 min for video)

**Alternatives Considered**:
- **Message Queue (Service Bus)**: Rejected - adds complexity, HTTP trigger is simpler for low-medium volume
- **Webhooks**: Rejected - requires public endpoint from Azure Function to Django (networking complexity)
- **Durable Functions**: Rejected - overkill for single-step processing
- **Event Grid**: Rejected - blob trigger pattern has cold start issues, HTTP is more predictable

**Implementation Best Practices**:
```python
# Django trigger
import requests

def trigger_azure_function(category: str, action: str, execution_id: str, params: dict):
    url = f"{settings.AZURE_FUNCTION_BASE_URL}/{category}/{action}"
    payload = {
        "execution_id": execution_id,
        "input_blob_path": f"uploads/{category}/{execution_id}",
        "params": params
    }
    response = requests.post(url, json=payload, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Function trigger failed: {response.text}")
```

---

## 5. Database Schema for Tool Execution Tracking

### Decision: Single ToolExecution Model with JSON Parameters

**Rationale**:
- Single table for all tool executions (polymorphic pattern)
- JSON field for tool-specific parameters (flexible schema)
- UUID primary key for execution_id (URL-safe, no sequential guessing)
- Indexed fields for common queries (status, created_at, tool_name)

**Schema**:
```python
from django.db import models
import uuid

class ToolExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    execution_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tool_name = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    
    input_file_name = models.CharField(max_length=255)
    input_blob_path = models.CharField(max_length=500)
    output_file_name = models.CharField(max_length=255, blank=True)
    output_blob_path = models.CharField(max_length=500, blank=True)
    
    parameters = models.JSONField(default=dict, blank=True)  # Tool-specific params
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tool_executions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tool_name', 'status', '-created_at']),
        ]
```

**Alternatives Considered**:
- **Separate table per tool**: Rejected - creates schema management complexity, harder to query across tools
- **Generic relations**: Rejected - Django's GenericForeignKey adds query overhead
- **NoSQL (Cosmos DB)**: Rejected - relational model fits use case, PostgreSQL JSON queries are performant

**Query Optimization**:
- Composite index on (tool_name, status, created_at) for history queries
- Separate index on execution_id (primary key already indexed)
- Use `select_related('user')` when fetching with user info

---

## 6. Frontend Status Polling Pattern

### Decision: JavaScript setInterval with Exponential Backoff (Capped)

**Rationale**:
- Simple implementation with vanilla JavaScript (no external dependencies)
- Exponential backoff reduces server load for long-running jobs
- Capped at 5-second intervals to maintain responsiveness
- Stops polling on completion or after max duration (60 minutes)

**Implementation**:
```javascript
class StatusPoller {
    constructor(executionId, onUpdate, onComplete, onError) {
        this.executionId = executionId;
        this.onUpdate = onUpdate;
        this.onComplete = onComplete;
        this.onError = onError;
        this.interval = 2000;  // Start at 2 seconds
        this.maxInterval = 5000;  // Cap at 5 seconds
        this.maxDuration = 60 * 60 * 1000;  // 60 minutes
        this.startTime = Date.now();
        this.timerId = null;
    }
    
    start() {
        this.poll();
    }
    
    async poll() {
        if (Date.now() - this.startTime > this.maxDuration) {
            this.onError('Processing timeout exceeded');
            return;
        }
        
        try {
            const response = await fetch(`/api/v1/executions/${this.executionId}/status/`);
            const data = await response.json();
            
            this.onUpdate(data.status, data.progress);
            
            if (data.status === 'completed') {
                this.onComplete(data.downloadUrl);
            } else if (data.status === 'failed') {
                this.onError(data.error);
            } else {
                // Continue polling with exponential backoff
                this.interval = Math.min(this.interval * 1.2, this.maxInterval);
                this.timerId = setTimeout(() => this.poll(), this.interval);
            }
        } catch (error) {
            this.onError(`Network error: ${error.message}`);
        }
    }
    
    stop() {
        if (this.timerId) clearTimeout(this.timerId);
    }
}
```

**Alternatives Considered**:
- **WebSockets**: Rejected - adds infrastructure complexity (Redis pub/sub), overkill for status updates
- **Server-Sent Events (SSE)**: Rejected - not well supported in all browsers, stateful connections
- **Long polling**: Rejected - complex server-side implementation, doesn't work well with load balancers

**Best Practices**:
- Display progress bar during polling (visual feedback)
- Show elapsed time (builds trust for long operations)
- Provide "cancel" button (updates status to "cancelled" in DB)
- Handle page refresh gracefully (check URL param for execution_id, resume polling)

---

## 7. URL Routing & API Endpoint Auto-Generation

### Decision: Dynamic URL Pattern Registration in AppConfig.ready()

**Rationale**:
- Tools automatically get URL routes without manual configuration
- Consistent URL patterns: `/tools/{tool-name}/` for web UI, `/api/v1/tools/{tool-name}/process/` for API
- Django's URL resolver efficiently handles dynamic routes
- SEO-friendly URLs (tool name as slug)

**Implementation Pattern**:
```python
# apps/tools/urls.py
from django.urls import path
from apps.tools.views import ToolDetailView, ToolProcessView

def get_tool_urls():
    """Generate URL patterns for all registered tools"""
    urlpatterns = []
    for tool in ToolRegistry.get_all_tools():
        urlpatterns.extend([
            # Web UI
            path(f'{tool.name}/', ToolDetailView.as_view(), {'tool_name': tool.name}, name=f'tool-{tool.name}'),
            # API endpoint
            path(f'api/v1/tools/{tool.name}/process/', ToolProcessView.as_view(), {'tool_name': tool.name}, name=f'api-tool-{tool.name}'),
        ])
    return urlpatterns

# Called during Django initialization
urlpatterns = get_tool_urls()
```

**Alternatives Considered**:
- **Django REST Framework routers**: Rejected - ViewSets are overkill for simple endpoints
- **Class-based URL patterns**: Rejected - less flexible for tool-specific customization
- **URL include() with namespace**: Considered - may use for better organization later

**Best Practices**:
- Tool names must be URL-safe (validated in BaseTool)
- Use `reverse('tool-{name}')` for URL generation in templates
- Add OpenAPI schema generation for auto-documentation

---

## 8. Error Handling & Logging Strategy

### Decision: Structured Logging with Emoji Prefixes + Azure Application Insights

**Rationale**:
- Emojis make logs scannable in terminal during development
- Structured JSON logging in production for Application Insights query efficiency
- Correlation IDs (execution_id) link logs across Django + Azure Functions
- Different log levels for different audiences (DEBUG for devs, ERROR for ops alerts)

**Logging Pattern**:
```python
import logging
import structlog

logger = structlog.get_logger(__name__)

# In tool processing
logger.info("🚀 Starting async processing", 
            execution_id=execution_id, 
            tool_name=tool_name,
            input_file=input_file_name)

try:
    # Process file
    logger.info("✅ Processing completed", 
                execution_id=execution_id,
                processing_time=elapsed_seconds)
except Exception as e:
    logger.error("❌ Processing failed",
                 execution_id=execution_id,
                 error=str(e),
                 exc_info=True)
```

**Error Categorization**:
- **User Errors**: Invalid input, unsupported format → 400 Bad Request, user-friendly message
- **System Errors**: Blob storage failure, function timeout → 500 Internal Server Error, generic message + log detail
- **Integration Errors**: Azure Function unreachable → Retry with exponential backoff, alert ops team

**Alternatives Considered**:
- **Sentry for error tracking**: Considered - good for production, may add later
- **ELK stack**: Rejected - overkill, Azure Monitor + Application Insights is sufficient
- **Plain text logs**: Rejected - hard to query and analyze

**Best Practices**:
- Always include execution_id in log messages (enables request tracing)
- Use Python's `logging.exception()` to capture stack traces
- Set up Application Insights alerts for error rate spikes

---

## 9. Testing Strategy for Plugin Architecture

### Decision: Layered Testing with Mocked External Services

**Rationale**:
- **Unit Tests**: Test tool logic in isolation with mocked dependencies
- **Integration Tests**: Test tool + Django framework interaction with test database
- **Contract Tests**: Verify Azure Function contracts match Django expectations
- **E2E Tests**: End-to-end workflow in staging environment with real Azure resources

**Testing Layers**:

**Unit Tests** (Fast, No I/O):
```python
# tests/unit/tools/test_my_tool.py
import pytest
from unittest.mock import Mock, patch
from apps.tools.plugins.my_tool import MyTool

def test_validate_valid_input():
    tool = MyTool()
    assert tool.validate({"text": "valid input"}) is True

def test_validate_invalid_input():
    tool = MyTool()
    with pytest.raises(ValidationError):
        tool.validate({"text": ""})

@patch('apps.tools.plugins.my_tool.BlobServiceClient')
def test_async_process_uploads_to_blob(mock_blob_client):
    tool = MyAsyncTool()
    execution_id, _ = tool.process(uploaded_file, rotation=90)
    assert mock_blob_client.upload_blob.called
```

**Integration Tests** (Medium Speed, Test DB):
```python
# tests/integration/test_tool_api.py
import pytest
from django.test import Client
from apps.tools.models import ToolExecution

@pytest.mark.django_db
def test_async_tool_creates_execution_record():
    client = Client()
    response = client.post('/api/v1/tools/video-rotation/process/', 
                          {'file': uploaded_file, 'rotation': 90})
    assert response.status_code == 200
    execution = ToolExecution.objects.get(execution_id=response.json()['executionId'])
    assert execution.status == 'pending'
```

**E2E Tests** (Slow, Real Azure):
```python
# tests/e2e/test_video_rotation_workflow.py
import pytest
import time

@pytest.mark.e2e
def test_video_rotation_end_to_end():
    # Upload video
    response = client.post('/api/v1/tools/video-rotation/process/', ...)
    execution_id = response.json()['executionId']
    
    # Poll status until completed
    for _ in range(60):  # Max 2 minutes
        status_response = client.get(f'/api/v1/executions/{execution_id}/status/')
        if status_response.json()['status'] == 'completed':
            break
        time.sleep(2)
    
    # Download and verify result
    download_url = status_response.json()['downloadUrl']
    result_file = client.get(download_url)
    assert result_file.status_code == 200
```

**Alternatives Considered**:
- **BDD with Behave**: Rejected - adds learning curve, pytest is sufficient
- **Snapshot testing**: Considered - useful for API response schemas, may add later
- **Load testing**: Considered - important for production, separate concern

**Test Coverage Requirements**:
- Minimum 80% code coverage for all tool plugins
- 100% coverage for BaseTool abstract methods
- E2E tests for at least 3 representative tools (sync, async small file, async large file)

---

## 10. Template System & UI Component Library

### Decision: Django Templates + Bootstrap 5 + Minimal Custom CSS

**Rationale**:
- Server-side rendering reduces JavaScript complexity
- Bootstrap 5 provides comprehensive component library (grid, forms, alerts, modals)
- Django template inheritance enables consistent layouts
- Progressive enhancement: core functionality works without JavaScript, polling enhances UX

**Template Structure**:
```django
{# templates/base.html #}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}MagicToolbox{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="{% static 'css/custom.css' %}" rel="stylesheet">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% include 'includes/navbar.html' %}
    <div class="container mt-4">
        {% include 'includes/messages.html' %}
        {% block content %}{% endblock %}
    </div>
    {% include 'includes/footer.html' %}
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>

{# templates/tools/tool_detail.html #}
{% extends "base.html" %}
{% block content %}
<div class="row">
    <div class="col-md-8">
        <h2>{{ tool.display_name }}</h2>
        <p>{{ tool.description }}</p>
        {% include 'tools/includes/upload_form.html' %}
        {% if tool.is_async %}
            {% include 'tools/includes/status_section.html' %}
        {% endif %}
    </div>
    <div class="col-md-4">
        {% if tool.is_async %}
            {% include 'tools/includes/history_sidebar.html' %}
        {% endif %}
        {% include 'tools/includes/instructions.html' %}
    </div>
</div>
{% endblock %}
```

**Component Reusability**:
- `templates/tools/includes/upload_form.html` - File upload widget (configurable accepted types)
- `templates/tools/includes/status_section.html` - Progress bar + status messages
- `templates/tools/includes/history_sidebar.html` - Last 10 executions with actions
- `templates/includes/messages.html` - Django messages as Bootstrap alerts

**Alternatives Considered**:
- **React SPA**: Rejected - adds build complexity, SSR is simpler for content-heavy pages
- **HTMX**: Considered - may add for partial page updates in future iterations
- **Tailwind CSS**: Rejected - Bootstrap is more comprehensive out-of-box

**Accessibility Checklist**:
- All form inputs have `<label>` with `for` attribute
- ARIA attributes for dynamic content (`aria-live` for status updates)
- Keyboard navigation (tab order, escape to close modals)
- Color contrast ratio ≥4.5:1 for text
- Screen reader tested with NVDA/VoiceOver

---

## 11. Configuration Management

### Decision: Environment-based Settings with Azure Key Vault in Production

**Rationale**:
- **Local Development**: `.env.development` file (not committed, template in `.env.example`)
- **Production**: Azure Key Vault + Azure App Configuration for secrets and non-secrets
- Django settings split into `base.py`, `development.py`, `production.py`
- Use `python-decouple` for `.env` parsing (type-safe, with defaults)

**Settings Structure**:
```python
# magictoolbox/settings/base.py
from decouple import config

AZURE_STORAGE_ACCOUNT_NAME = config('AZURE_STORAGE_ACCOUNT_NAME', default='')
AZURE_STORAGE_CONNECTION_STRING = config('AZURE_STORAGE_CONNECTION_STRING', default='')  # Local only
AZURE_FUNCTION_BASE_URL = config('AZURE_FUNCTION_BASE_URL', default='http://localhost:7071')

# magictoolbox/settings/production.py
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Fetch secrets from Key Vault
credential = DefaultAzureCredential()
key_vault_url = config('AZURE_KEYVAULT_URL')
client = SecretClient(vault_url=key_vault_url, credential=credential)

SECRET_KEY = client.get_secret('django-secret-key').value
DATABASE_URL = client.get_secret('database-url').value
```

**Environment Variables Required**:
- `DJANGO_SETTINGS_MODULE` - Which settings file to use
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account name
- `AZURE_STORAGE_CONNECTION_STRING` - For local dev only
- `AZURE_FUNCTION_BASE_URL` - Base URL for Azure Functions
- `AZURE_KEYVAULT_URL` - Key Vault URL (production only)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

**Alternatives Considered**:
- **Hardcoded settings**: Rejected - security risk, not environment-agnostic
- **Environment variables only**: Rejected - secrets leak in logs/process lists
- **Consul/Vault**: Rejected - Azure Key Vault is native, simpler

---

## 12. Deployment & Infrastructure

### Decision: Azure Container Apps with Bicep IaC

**Rationale**:
- Azure Container Apps provides serverless container orchestration (based on Kubernetes)
- Bicep templates ensure reproducible infrastructure
- Auto-scaling based on HTTP traffic and CPU
- Integrated with Azure Monitor and Application Insights

**Key Infrastructure Components**:
- **Azure Container Registry (ACR)**: Docker image storage
- **Azure Container Apps**: Django application hosting
- **Azure Functions**: Async processing
- **Azure Blob Storage**: File storage (3 containers)
- **Azure Database for PostgreSQL Flexible Server**: Primary database
- **Azure Cache for Redis**: Session and caching
- **Azure Key Vault**: Secret management
- **Azure Monitor + Application Insights**: Observability

**Bicep Template Highlights**:
```bicep
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'magictoolbox-webapp'
  location: resourceGroup().location
  identity: {
    type: 'SystemAssigned'  // Managed Identity
  }
  properties: {
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      secrets: []  // Secrets from Key Vault via reference
    }
    template: {
      containers: [
        {
          name: 'django-app'
          image: '${acr.properties.loginServer}/magictoolbox:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}
```

**CI/CD Pipeline** (GitHub Actions):
1. Lint + Test on PR
2. Build Docker image on merge to main
3. Push to ACR
4. Deploy to staging (automatic)
5. Manual approval for production deploy
6. Deploy to production
7. Run smoke tests

**Alternatives Considered**:
- **Azure App Service**: Rejected - Container Apps has better scaling characteristics
- **AKS (Azure Kubernetes Service)**: Rejected - overkill for this scale, more operational overhead
- **Terraform**: Rejected - Bicep is Azure-native, better integration

---

## Summary of Key Decisions

| Area | Decision | Primary Benefit |
|------|----------|----------------|
| Plugin Discovery | Django AppConfig metaclass | Zero-config tool registration |
| Tool Interface | Abstract Base Class (ABC) | Enforced contract at definition time |
| Blob Storage Auth | Managed Identity + DefaultAzureCredential | No secrets, automatic credential rotation |
| Async Processing | HTTP-triggered Azure Functions | Simple, reliable, auto-scaling |
| Status Tracking | Database with polling | Stateless, works with load balancers |
| Frontend | Django Templates + Bootstrap 5 | Server-side rendering, consistent UI |
| Testing | Layered (unit/integration/E2E) | Fast feedback + production confidence |
| Configuration | Key Vault + environment split | Secure, environment-agnostic |
| Deployment | Container Apps + Bicep | Serverless scaling, reproducible infra |

---

## Next Steps (Phase 1)

1. ✅ Research completed - all technical unknowns resolved
2. ⏭️ Create `data-model.md` - Entity definitions and relationships
3. ⏭️ Generate API contracts in `contracts/` directory
4. ⏭️ Write `quickstart.md` - Developer onboarding guide
5. ⏭️ Update agent context with new technologies
