# MagicToolbox Backend

Django backend for the MagicToolbox file conversion application.

📚 **[Complete Documentation →](documentation/)**

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (optional for development, SQLite used by default)
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

### Azure Container Apps

MagicToolbox is designed for deployment on Azure Container Apps with full infrastructure as code support.

**Quick Deploy:**
- See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide
- Infrastructure templates in `infra/` using Azure Bicep
- CI/CD via GitHub Actions (`.github/workflows/`)
- **GitHub Secrets Setup**: [GITHUB_SECRETS_QUICK_REFERENCE.md](GITHUB_SECRETS_QUICK_REFERENCE.md) or run `./scripts/setup-github-secrets.sh`

**Important Azure-Specific Configurations:**

This repository includes comprehensive Azure integration following DevOps best practices:

1. **Azure Key Vault Integration** 
   - Secure secret management with managed identity
   - RBAC-based access control (no access policies)
   - Automatic secret retrieval with fallback to environment variables
   - See [documentation/AZURE_KEYVAULT_APPINSIGHTS.md](documentation/AZURE_KEYVAULT_APPINSIGHTS.md)

2. **Application Insights Telemetry**
   - Distributed tracing with OpenCensus
   - Exception logging and performance metrics
   - Custom sampling rates per environment
   - Comprehensive observability and diagnostics

3. **Health Check Middleware** (`apps/core/middleware.py`)
   - Handles Azure internal health probe IPs (100.100.0.0/16)
   - Bypasses ALLOWED_HOSTS validation for health endpoints
   - Ensures Container App revisions show as "Healthy"

4. **SSL Termination** (`magictoolbox/settings/production.py`)
   - `SECURE_SSL_REDIRECT = False` - Azure handles SSL at ingress
   - `SECURE_PROXY_SSL_HEADER` configured for Azure proxy
   - Prevents infinite redirect loops

5. **Static Files with WhiteNoise**
   - Serves CSS/JS efficiently from container with Brotli compression
   - Azure Blob Storage used only for private user uploads
   - Fixes "Public access not permitted" errors
   - Includes Brotli compression and cache-busting

**Troubleshooting:**
- See [documentation/AZURE_CONTAINER_APPS_TROUBLESHOOTING.md](documentation/AZURE_CONTAINER_APPS_TROUBLESHOOTING.md) for detailed solutions
- Common issues: Unhealthy revisions, redirect loops, static file loading

**Documentation:**
- [documentation/AZURE_NAMING_CONVENTION.md](documentation/AZURE_NAMING_CONVENTION.md) - Azure resource naming standards
- [documentation/AZURE_DEPLOYMENT_README.md](documentation/AZURE_DEPLOYMENT_README.md) - Quick start guide
- [documentation/DEPLOYMENT.md](documentation/DEPLOYMENT.md) - Complete deployment guide with all steps
- [documentation/AZURE_CONTAINER_APPS_TROUBLESHOOTING.md](documentation/AZURE_CONTAINER_APPS_TROUBLESHOOTING.md) - Issue resolution guide

### Local Development

Use Docker Compose for local development with all services:

```bash
docker-compose up -d
```

Includes PostgreSQL, Redis, and MinIO (S3-compatible storage).

## Environment Variables

See `.env.example` for all available configuration options.
