# Implementation Plan: Async Tool Framework & Plugin System

**Branch**: `001-async-tool-framework` | **Date**: 2025-12-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-async-tool-framework/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature implements a comprehensive plugin-based tool framework for MagicToolbox that enables developers to add new tools (both synchronous and asynchronous) with minimal boilerplate code. The framework provides automatic tool discovery via Django's AppConfig metaclass pattern, standardized interfaces through abstract base classes, Azure Blob Storage integration for file handling, and Azure Functions for async processing. The technical approach leverages Django's built-in mechanisms for plugin registration, PostgreSQL with JSON fields for flexible execution tracking, and a polling-based status update pattern for real-time user feedback during long-running operations.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Django 5.0+, Django REST Framework, azure-storage-blob SDK, azure-functions Python runtime, Bootstrap 5, pytest-django  
**Storage**: Azure Database for PostgreSQL Flexible Server (production), SQLite (local dev); Azure Blob Storage (uploads, processed, temp containers)  
**Testing**: pytest-django with 80%+ coverage, mocked external services (Azure SDK), integration tests with test database  
**Target Platform**: Azure Container Apps (Django), Azure Functions Flex Consumption (async processing), Linux-based containers  
**Project Type**: Web application (backend: Django, frontend: Django Templates + Bootstrap)  
**Performance Goals**: API response <200ms p95 for sync endpoints, status polling <3s latency, support 50 concurrent async jobs  
**Constraints**: File uploads max 500MB, async processing timeout 30min (video), blob retention policies (7d/30d/24h), WCAG 2.1 AA accessibility  
**Scale/Scope**: 20+ tool plugins at launch, 10k users anticipated, 100k executions/month target, extensible to 100+ tools

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with MagicToolbox Constitution v1.0.0:

- [x] **I. Code Quality & Type Safety**: ✅ Python type hints required in BaseTool interface and all tool implementations; PEP 8 enforced via Black formatter; 80%+ test coverage mandated for all tool plugins; docstrings (Google style) required for all public methods
- [x] **II. Test-First Development**: ✅ TDD workflow documented in quickstart.md; test utilities provided for tool isolation; pytest-django framework with fixtures; external Azure services mocked in unit tests; CI/CD pipeline validates all tests pass before merge
- [x] **III. User Experience Consistency**: ✅ Bootstrap 5 used for all frontend components; two-column layout pattern enforced (8 cols main, 4 cols sidebar); history sections display last 10 items with actions; WCAG 2.1 AA accessibility compliance verified; status polling every 2-3 seconds with visual feedback; django-crispy-forms with crispy-bootstrap5 for consistent form styling
- [x] **IV. Performance Requirements**: ✅ Async pattern mandatory for file processing (upload → Azure Function → poll); Azure Cache for Redis used for sessions; database query optimization via composite indexes; static assets served via CDN; file streaming for large uploads; timeout handling in Azure Functions with temp file cleanup
- [x] **V. Security by Design**: ✅ Azure Key Vault for production secrets; input validation on client and server; file upload validation (whitelist, size, MIME type); HTTPS enforced in Azure Container Apps; rate limiting via DRF throttling; Managed Identity for service-to-service auth; no raw SQL without parameterization

**Violations**: None - fully compliant

**Post-Phase 1 Re-check**: ✅ All principles remain satisfied. Data model uses composite indexes for performance (Principle IV). API contracts include validation error schemas (Principle V). Quickstart guide emphasizes TDD workflow (Principle II).

## Project Structure

### Documentation (this feature)

```text
specs/001-async-tool-framework/
├── plan.md                  # This file (implementation plan)
├── research.md              # Phase 0 output - technical decisions and alternatives
├── data-model.md            # Phase 1 output - entity definitions and relationships
├── quickstart.md            # Phase 1 output - developer onboarding guide
├── contracts/               # Phase 1 output - API and Azure Function contracts
│   ├── api-spec.yaml        # OpenAPI 3.0 specification
│   └── azure-function-contract.md  # Azure Function interface definition
└── tasks.md                 # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application structure
backend/
├── apps/
│   ├── tools/                         # Core tool framework
│   │   ├── base.py                   # BaseTool abstract class
│   │   ├── registry.py               # ToolRegistry singleton
│   │   ├── models.py                 # ToolExecution model
│   │   ├── views.py                  # Tool detail and process views
│   │   ├── serializers.py            # DRF serializers
│   │   ├── plugins/                  # Tool plugin directory
│   │   │   ├── __init__.py          # Auto-discovery initialization
│   │   │   ├── base64_encoder.py    # Example sync tool
│   │   │   ├── video_rotation.py    # Example async tool
│   │   │   └── pdf_docx_converter.py # Existing async tool
│   │   └── services/                 # Shared services
│   │       ├── blob_storage.py      # BlobStorageClient
│   │       └── async_task.py        # AsyncTaskTrigger
│   ├── api/
│   │   └── v1/
│   │       ├── urls.py              # API v1 routes (includes tool endpoints)
│   │       └── views.py             # API v1 views
│   └── core/
│       └── middleware.py             # Custom middleware (rate limiting, logging)
├── templates/
│   ├── base.html                     # Base template with Bootstrap 5
│   ├── tools/
│   │   ├── tool_list.html           # Tool discovery homepage
│   │   ├── tool_detail.html         # Generic tool template
│   │   ├── base64_encoder.html      # Tool-specific templates
│   │   ├── video_rotation.html
│   │   └── includes/                # Reusable fragments
│   │       ├── upload_form.html     # File upload widget
│   │       ├── status_section.html  # Status polling UI
│   │       └── history_sidebar.html # Execution history
│   └── includes/
│       ├── navbar.html
│       ├── footer.html
│       └── messages.html
├── static/
│   ├── css/
│   │   └── custom.css               # Custom styles
│   └── js/
│       ├── status-poller.js         # Status polling class
│       └── history-manager.js       # History sidebar logic
└── magictoolbox/
    └── settings/
        ├── base.py                   # Base settings
        ├── development.py            # Dev settings (SQLite, Azurite)
        └── production.py             # Prod settings (Azure services)

function_app/                          # Azure Functions
├── function_app.py                   # Function app registration
├── host.json                         # Function host configuration
├── requirements.txt                  # Python dependencies
├── video/
│   └── rotate.py                     # Video rotation handler
├── document/
│   └── convert.py                    # PDF conversion handler
└── shared/                           # Shared utilities
    ├── blob_client.py               # Blob storage operations
    └── database_client.py           # Database status updates

tests/
├── unit/
│   └── tools/
│       ├── test_base_tool.py        # BaseTool tests
│       ├── test_registry.py         # ToolRegistry tests
│       └── plugins/
│           ├── test_base64_encoder.py
│           └── test_video_rotation.py
├── integration/
│   ├── test_tool_api.py             # API endpoint tests
│   └── test_tool_execution.py       # Execution flow tests
└── e2e/
    └── test_async_workflow.py       # End-to-end async tests

infra/
└── bicep/
    ├── storage.bicep                # Blob storage with 3 containers
    └── functions.bicep              # Azure Functions deployment
```

**Structure Decision**: Web application structure selected based on Django backend + template-based frontend. Tool plugins organized in dedicated `apps/tools/plugins/` directory for automatic discovery. Azure Functions separated into category-based subdirectories (`video/`, `document/`, etc.) matching blob storage path conventions. Testing mirrors source structure for easy navigation.

## Complexity Tracking

> **No violations identified - this section intentionally left empty**

All constitutional principles are satisfied by the design:
- Single web application (no multi-project complexity)
- Standard Django patterns (no exotic architecture)
- Established Azure services (no experimental tech)
- Proven async pattern (polling, not WebSockets)

The plugin system adds intentional complexity but is justified by the core requirement for extensibility without code duplication across 20+ tools.
