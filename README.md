# MagicToolbox Backend

Django backend for the MagicToolbox file conversion application.

📚 **[Complete Documentation →](documentation/)**

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 17 (optional for development, SQLite used by default)
- Redis 7+ (optional for development)

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements/development.txt
```

3. Configure environment:
```bash
cp .env.example .env.development
# Edit .env.development with your settings
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Run development server:
```bash
python manage.py runserver
```

### Running Tests

```bash
pytest
```

### Code Quality

Format code:
```bash
black apps/
isort apps/
```

Run linters:
```bash
flake8 apps/
pylint apps/
mypy apps/
```

## Project Structure

```
magictoolbox/
├── .github/            # GitHub workflows and copilot instructions
├── apps/
│   ├── core/           # Base models, middleware, utilities
│   ├── authentication/ # User management and JWT auth
│   ├── tools/          # Tool plugin system
│   └── api/            # API versioning
├── magictoolbox/
│   ├── settings/       # Split settings (base, dev, prod)
│   ├── urls.py         # Root URL configuration
│   └── celery.py       # Celery configuration
├── templates/          # Django templates with Bootstrap
├── static/             # CSS, JavaScript, images
├── requirements/       # Split requirements files
├── tests/              # Test suite
├── manage.py
└── README.md
```

## Architecture

### Application Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Browser                                 │
│                    (Bootstrap 5 Frontend)                            │
└────────────────┬────────────────────────────────────────────────────┘
                 │ HTTPS
                 ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Django Application                                │
│                  (Azure Container Apps)                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Django Views & Templates                                     │  │
│  │  - File upload forms                                          │  │
│  │  - Status polling (JavaScript)                                │  │
│  │  - History sidebar                                            │  │
│  └────────────────────┬──────────────────────────────────────────┘  │
│                       │                                              │
│  ┌────────────────────▼──────────────────────────────────────────┐  │
│  │  Tool Plugin System (apps/tools/plugins/)                     │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │  │
│  │  │ Image    │ │ PDF      │ │ Video    │ │ GPX/KML  │         │  │
│  │  │Converter │ │Converter │ │Rotation  │ │Converter │         │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘         │  │
│  │                                                                │  │
│  │  Each tool:                                                    │  │
│  │  1. Validates uploaded file                                   │  │
│  │  2. Uploads to Azure Blob Storage (uploads container)         │  │
│  │  3. Triggers Azure Function via HTTP POST                     │  │
│  │  4. Returns execution_id for status polling                   │  │
│  └────────────────────┬──────────────────────────────────────────┘  │
│                       │                                              │
│  ┌────────────────────▼──────────────────────────────────────────┐  │
│  │  Django REST Framework API                                    │  │
│  │  - POST /api/v1/tools/{tool}/convert/   (upload & trigger)    │  │
│  │  - GET  /api/v1/executions/{id}/status/ (polling endpoint)    │  │
│  │  - GET  /api/v1/executions/{id}/download/ (download result)   │  │
│  │  - DELETE /api/v1/executions/{id}/      (cleanup)             │  │
│  └────────────────────┬──────────────────────────────────────────┘  │
└─────────────────────┬─┴──────────────────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ↓            ↓            ↓
    ┌─────────┐ ┌──────────┐ ┌─────────────┐
    │ Blob    │ │PostgreSQL│ │   Redis     │
    │ Storage │ │ Database │ │   Cache     │
    │ (Files) │ │(Metadata)│ │ (Sessions)  │
    └────┬────┘ └──────────┘ └─────────────┘
         │
         │ HTTP POST (background thread)
         ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Azure Functions (Flex Consumption)                      │
│                     Python 3.11 Runtime                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  HTTP Triggered Functions:                                    │  │
│  │  - POST /image/convert   (image conversion)                   │  │
│  │  - POST /pdf/convert     (PDF to DOCX)                        │  │
│  │  - POST /video/rotate    (video rotation)                     │  │
│  │  - POST /gpx/convert     (GPX/KML conversion)                 │  │
│  │  - POST /gpx/speed       (GPX speed modification)             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Processing Flow (per function):                                    │
│  1. Parse HTTP request (execution_id, parameters)                   │
│  2. Update DB: status='processing'                                  │
│  3. Download file from 'uploads' container                          │
│  4. Process file (convert/rotate/modify)                            │
│  5. Upload result to 'processed' container                          │
│  6. Update DB: status='completed', output_blob_path                 │
│  7. Cleanup temp files                                              │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ↓
                ┌─────────────┐
                │   Blob      │
                │  Storage    │
                │ (processed) │
                └─────────────┘
                       ↑
                       │
            Client polls & downloads when complete
```

**Key Architectural Features:**
- **Async Processing Pattern**: Upload → Trigger → Poll → Download
- **Separation of Concerns**: Django handles UI/API, Azure Functions handle heavy processing
- **Scalability**: Azure Functions auto-scale based on load
- **Fault Tolerance**: Status tracking in database, automatic retry on failures
- **Storage Organization**: 
  - `uploads/` - Input files organized by category (pdf/, image/, video/, gpx/)
  - `processed/` - Output files with same organization
  - `temp/` - Temporary files (auto-cleanup after 24h)

### Azure Infrastructure Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Internet (HTTPS)                             │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Azure Front Door (Optional)                       │
│                         CDN + WAF                                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   Azure Container Apps                               │
│                    (Django Application)                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Environment: magictoolbox-env                                │  │
│  │  Container: Django 5.1 + Gunicorn                            │  │
│  │  Scale: 1-10 replicas (CPU/HTTP based)                        │  │
│  │  Resources: 0.5 CPU, 1.0 GB RAM per replica                   │  │
│  │  Ingress: External, HTTPS only                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Managed Identity: System-assigned                                  │
│  VNet Integration: Yes (Private subnet)                             │
└─────┬───────────────────┬───────────────────┬───────────────────────┘
      │                   │                   │
      │                   │                   │
┌─────▼────────┐   ┌──────▼──────┐   ┌───────▼──────────┐
│   Azure      │   │   Azure     │   │  Azure Cache     │
│ Key Vault    │   │ PostgreSQL  │   │   for Redis      │
│              │   │   Flexible  │   │                  │
│ Secrets:     │   │   Server    │   │ - Sessions       │
│ - DB_PASS    │   │             │   │ - Cache          │
│ - REDIS_CONN │   │ Private     │   │                  │
│ - STORAGE_KEY│   │ Endpoint    │   │ Private Endpoint │
│              │   │             │   │                  │
│ Private      │   │ VNet        │   │ VNet Integrated  │
│ Endpoint     │   │ Integrated  │   │                  │
└──────────────┘   └─────────────┘   └──────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   Azure Functions (Flex Consumption)                 │
│                    (File Processing Workers)                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Runtime: Python 3.11                                         │  │
│  │  Triggers: HTTP (POST endpoints)                              │  │
│  │  Scale: 0-1000 instances (event-driven)                       │  │
│  │  Resources: Dynamic allocation                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Managed Identity: System-assigned                                  │
│  VNet Integration: Yes (Functions subnet)                           │
│  Storage: Requires public access for runtime                        │
└─────┬────────────────────────────────────────────────────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Azure Blob Storage (Standard LRS)                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Containers:                                                  │  │
│  │  - uploads/       (input files: pdf/, image/, video/, gpx/)   │  │
│  │  - processed/     (output files: same structure)              │  │
│  │  - video-uploads/ (video-specific inputs)                     │  │
│  │  - video-processed/ (video-specific outputs)                  │  │
│  │  - temp/          (lifecycle: auto-delete after 24h)          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Access: Public blob access (for Functions runtime)                 │
│  Authentication: Managed Identity + Access Keys                     │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│              Azure Container Registry (ACR)                          │
│  - Docker images for Container Apps                                 │
│  - Private endpoint enabled                                         │
│  - Admin user disabled (MI auth only)                               │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│              Application Insights                                    │
│  - Distributed tracing (OpenCensus)                                 │
│  - Custom metrics & events                                          │
│  - Exception tracking                                               │
│  - Performance monitoring                                           │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    Virtual Network (VNet)                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Subnets:                                                     │  │
│  │  - containerapp-subnet    (10.0.0.0/23)   Container Apps     │  │
│  │  - functions-subnet       (10.0.2.0/24)   Azure Functions    │  │
│  │  - private-endpoints      (10.0.3.0/24)   Private Endpoints  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Network Security:                                                   │
│  - Private endpoints for PostgreSQL, Key Vault, Redis, ACR          │
│  - Network isolation for backend services                           │
│  - NSG rules for traffic control                                    │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                                    │
│  GitHub Actions:                                                     │
│  - Build Docker image                                                │
│  - Push to ACR                                                       │
│  - Deploy to Container Apps                                          │
│  - Deploy Functions                                                  │
│  - Run tests & validation                                            │
└──────────────────────────────────────────────────────────────────────┘
```

**Infrastructure Highlights:**

| Component | Service | Purpose | Scaling |
|-----------|---------|---------|---------|
| **Web App** | Azure Container Apps | Django frontend/backend | 1-10 replicas (auto) |
| **Processing** | Azure Functions (Flex) | File conversion workers | 0-1000 instances (event-driven) |
| **Database** | PostgreSQL Flexible | Metadata & executions | Single server (can enable HA) |
| **Cache** | Azure Cache for Redis | Sessions & query cache | Basic/Standard tier |
| **Storage** | Azure Blob Storage | File uploads & results | Standard LRS |
| **Secrets** | Azure Key Vault | Configuration secrets | N/A |
| **Monitoring** | Application Insights | Telemetry & diagnostics | N/A |
| **Registry** | Azure Container Registry | Docker images | Standard tier |
| **Network** | Virtual Network | Network isolation | N/A |

**Security Features:**
- ✅ Managed Identity for all service-to-service auth
- ✅ Private endpoints for PostgreSQL, Key Vault, Redis, ACR
- ✅ VNet integration for Container Apps and Functions
- ✅ HTTPS only (SSL termination at ingress)
- ✅ RBAC-based access control
- ✅ No hardcoded credentials (Key Vault references)
- ✅ Network isolation for backend services

**Cost Optimization:**
- Functions scale to zero when idle
- Container Apps scale down to 1 replica minimum
- Storage uses Standard LRS (not Premium)
- Redis uses Basic tier (can upgrade)
- PostgreSQL Burstable tier for development

## Available Tools

### 1. Image Format Converter
- **Path**: `apps/tools/plugins/image_format_converter.py`
- **Features**: Convert between 15+ image formats (JPG, PNG, WEBP, HEIC, BMP, GIF, TIFF, ICO, etc.)
- **Supports**: Quality control, resizing, bulk upload

### 2. GPX/KML Converter
- **Path**: `apps/tools/plugins/gpx_kml_converter.py`
- **Features**: Bidirectional GPS file conversion (GPX ↔ KML)
- **Supports**: Waypoints, tracks, routes, bulk upload

## Adding New Tools

1. Follow the comprehensive guide: **`.github/copilot-tool-development-instructions.md`**
2. Create new tool in `apps/tools/plugins/`:
```python
from apps.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my-tool"
    display_name = "My Tool"
    # ... implement required methods
```

3. Tool will be auto-discovered on startup
4. Both single and bulk file uploads are supported

## API Documentation

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Deployment

### Azure Container Apps (Production-Ready)

MagicToolbox is deployed on Azure Container Apps with a secure, production-grade infrastructure.

**Current Status (Dec 2, 2025)**: ✅ Production-ready with VNet integration, private endpoints, and validated end-to-end functionality.

**Quick Start:**
1. **Review Architecture**: [documentation/AZURE_DEPLOYMENT_README.md](documentation/AZURE_DEPLOYMENT_README.md)
2. **Setup CI/CD Secrets**: [documentation/GITHUB_SECRETS_SETUP.md](documentation/GITHUB_SECRETS_SETUP.md) or run `./scripts/setup-github-secrets.sh`
3. **Deploy Infrastructure**: Use Bicep templates in `infra/`
4. **Verify Deployment**: [documentation/DEPLOYMENT_VERIFICATION.md](documentation/DEPLOYMENT_VERIFICATION.md)

**Key Documentation:**
- 📘 [AZURE_DEPLOYMENT_README.md](documentation/AZURE_DEPLOYMENT_README.md) - Architecture overview and quick start
- 🔐 [VNET_AND_SECURITY.md](documentation/VNET_AND_SECURITY.md) - Network security and private endpoints
- ✅ [DEPLOYMENT_VERIFICATION.md](documentation/DEPLOYMENT_VERIFICATION.md) - Complete verification checklist
- 🔑 [GITHUB_SECRETS_SETUP.md](documentation/GITHUB_SECRETS_SETUP.md) - CI/CD secrets configuration
- 📊 [INFRASTRUCTURE_CLEANUP_SUMMARY.md](documentation/INFRASTRUCTURE_CLEANUP_SUMMARY.md) - Current state

**Infrastructure Highlights:**

1. **Network Security**
   - VNet integration for Container App and Function App
   - Private endpoints for all backend services (Storage, Key Vault, PostgreSQL, Redis, ACR)
   - All traffic routed through VNet with network isolation

2. **Azure Services**
   - Container Apps for web application hosting
   - Function App (FlexConsumption) for PDF to DOCX conversion
   - PostgreSQL Flexible Server with private endpoint
   - Key Vault for secrets management (private endpoint only)
   - Application Insights for monitoring and telemetry
   - Azure Blob Storage for file processing

3. **Security Features**
   - Managed identity authentication (no keys/passwords)
   - RBAC-based access control
   - Key Vault secret references in application settings
   - No public access to Key Vault or Storage (except Functions requirement)

**Important Azure-Specific Configurations:**

1. **Key Vault Integration** ([AZURE_KEYVAULT_APPINSIGHTS.md](documentation/AZURE_KEYVAULT_APPINSIGHTS.md))
   - Managed identity with RBAC roles
   - Secret references: `@Microsoft.KeyVault(SecretUri=...)`
   - Automatic secret refresh

2. **Application Insights** ([AZURE_KEYVAULT_APPINSIGHTS.md](documentation/AZURE_KEYVAULT_APPINSIGHTS.md))
   - OpenCensus integration for distributed tracing
   - Custom metrics and exception logging
   - Performance monitoring

3. **Health Check Middleware** (`apps/core/middleware.py`)
   - Azure health probe IP handling (100.100.0.0/16)
   - ALLOWED_HOSTS bypass for health endpoints
   - Ensures "Healthy" revision status

4. **SSL/TLS Configuration** (`magictoolbox/settings/production.py`)
   - SSL termination at Azure ingress
   - `SECURE_SSL_REDIRECT = False` to prevent redirect loops
   - Proxy headers configured for HTTPS detection

### Local Development

Use Docker Compose for local development with all services:

```bash
docker-compose up -d
```

Includes PostgreSQL, Redis, and MinIO (S3-compatible storage).

## Environment Variables

See `.env.example` for all available configuration options.
# Trigger rebuild - Thu Nov 27 15:58:16 CET 2025
