# MagicToolbox Setup Prompt

Use this prompt to instruct an AI agent to scaffold the complete MagicToolbox application structure:

---

## 🚀 Create MagicToolbox Application

Create the complete directory structure and foundational files for MagicToolbox, a modular web application for file and image conversion tools. Follow these requirements:

**PROJECT OVERVIEW:**
- Python Django + Django REST Framework backend with plugin-based tool architecture
- **Django Templates + Bootstrap 5 frontend** (server-side rendering)
- Dual interface: Web UI (templates) + REST API (for future mobile/integrations)
- Azure Database for PostgreSQL Flexible Server
- Azure Cache for Redis
- Azure Blob Storage for file storage
- Fully modular, secure design with comprehensive tool development guide
- Docker containerization with Azure Container Apps deployment
- Complete CI/CD pipeline with GitHub Actions
- Infrastructure as Code using Azure Bicep

**TASKS:**

1. **Create Backend Structure** (backend/)
   - Set up Django project with split settings (base, development, production)
   - Create Django apps: core, authentication, tools, api
   - Implement base tool plugin system (BaseTool abstract class + registry)
   - Create DRF ViewSets and serializers for API v1 endpoints
   - Set up JWT authentication with djangorestframework-simplejwt
   - Configure Django models and migrations
   - Add Celery for background task processing
   - Implement file upload handling with Azure Blob Storage integration
   - Configure Azure Cache for Redis integration
   - Set up structured logging with Application Insights
   - Create health check and readiness endpoints
   - Add requirements files (base.txt, development.txt, production.txt)
   - Create manage.py and WSGI/ASGI configuration

2. **Create Frontend Structure** (Django Templates + Bootstrap)
   - Set up Django template structure with base.html
   - Configure Bootstrap 5.3.2 + Bootstrap Icons
   - Create reusable template includes (navbar, footer, messages)
   - Implement Django Crispy Forms with Bootstrap 5 styling
   - Create authentication templates (login, register, profile)
   - Create tool templates with file upload interface
   - Add custom CSS with animations and hover effects
   - Add custom JavaScript utilities (file validation, notifications, progress)
   - Implement AJAX file upload with progress tracking
   - Add bulk upload support with JSZip for downloads
   - Create error pages (404, 500)
   - Implement flash messages with auto-dismiss
   - Add responsive navigation and layouts
   - Create tool-specific templates with consistent UI patterns

3. **Create Docker Configuration**
   - Multi-stage Dockerfile for backend (Python slim + Gunicorn)
   - Multi-stage Dockerfile for frontend (Node + Nginx)
   - Docker Compose for local development (backend, frontend, postgres, redis)
   - Nginx configuration for frontend serving
   - .dockerignore files for both services
   - Health checks for all services

4. **Create Azure Bicep Templates** (bicep/)
   - Main deployment template (main.bicep)
   - Container Apps Environment
   - Backend and Frontend Container Apps with scaling rules
   - Azure Database for PostgreSQL Flexible Server
   - Azure Cache for Redis
   - Azure Blob Storage account and containers
   - Azure Key Vault for secrets
   - Azure Container Registry
   - Application Insights and Log Analytics
   - Managed Identity configuration
   - Role assignments for Key Vault access

5. **Create CI/CD Pipeline** (.github/workflows/)
   - CI pipeline: lint, test, build, security scan (Trivy)
   - CD pipeline: build images, push to ACR, deploy to Container Apps
   - Separate jobs for backend and frontend
   - Code coverage reporting
   - Automated security scanning
   - Database migration step in deployment

6. **Create Configuration Files**
   - .env.example with all required Azure variables
   - .gitignore (Python, Node, Docker, IDE)
   - README.md with setup instructions and architecture overview
   - CONTRIBUTING.md with development guidelines
   - LICENSE file (MIT)
   - pyproject.toml for Python tooling (Black, isort, pylint)
   - .prettierrc and .eslintrc for frontend
   - renovate.json for dependency updates

7. **Create Documentation**
   - ✅ `.github/copilot-tool-development-instructions.md` - **Comprehensive tool creation guide**
   - ✅ `.github/copilot-instructions.md` - Project guidelines
   - ✅ `.github/copilot-backend-instructions.md` - Backend best practices
   - ✅ `.github/copilot-frontend-instructions.md` - Frontend patterns
   - ✅ `.github/copilot-deployment-instructions.md` - Azure deployment
   - Architecture diagram (in markdown)
   - API documentation structure
   - Azure deployment guide
   - Local development setup guide

**CODING STANDARDS:**
- Backend: Python 3.11+, Django 5.0+, snake_case naming, 4-space indentation, type hints everywhere
- Frontend: TypeScript strict mode, camelCase naming, 2-space indentation, no 'any' types
- API: RESTful, camelCase JSON keys via DRF renderer, snake_case Python internally
- All files must follow the guidelines in .github/copilot-*.md files

**AZURE-SPECIFIC REQUIREMENTS:**
- Use Azure Managed Identity for service-to-service authentication
- All secrets in Azure Key Vault (never hardcoded)
- Azure Blob Storage for media files
- Azure Database for PostgreSQL with connection pooling
- Azure Cache for Redis for sessions and caching
- Application Insights for logging and monitoring
- Azure Container Apps with auto-scaling
- Use Bicep for Infrastructure as Code

**CURRENT STATUS:**
- ✅ Backend structure complete with Django + DRF
- ✅ Frontend complete with Django Templates + Bootstrap 5
- ✅ Two fully functional tools:
  - **Image Format Converter** - 15+ formats, bulk upload, quality control
  - **GPX/KML Converter** - Bidirectional conversion, bulk upload
- ✅ **Tool Development Guide** created (`.github/copilot-tool-development-instructions.md`)
- ✅ Bulk upload support with ZIP downloads
- ✅ Proper temp file cleanup mechanisms
- ✅ Comprehensive error handling and logging

**FOR NEW TOOLS:**
- Follow `.github/copilot-tool-development-instructions.md` for standardized structure
- All tools must support bulk uploads
- All tools must properly clean up temp files
- Use original filename + new extension pattern
- Follow the exact patterns from existing tools

Generate the complete project structure with all files and their initial content. Start with the most critical foundational files first.

---

## Expected File Structure

```
magictoolbox/
├── .github/
│   ├── copilot-instructions.md (already exists)
│   ├── copilot-backend-instructions.md (already exists)
│   ├── copilot-frontend-instructions.md (already exists)
│   ├── copilot-deployment-instructions.md (already exists)
│   ├── copilot-tool-development-instructions.md (already exists)
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── magictoolbox/
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── __init__.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── apps/
│   │   ├── core/
│   │   ├── authentication/
│   │   ├── tools/
│   │   └── api/
│   ├── tests/
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── development.txt
│   │   └── production.txt
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── manage.py
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── stores/
│   │   ├── types/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── .dockerignore
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── bicep/
│   ├── main.bicep
│   ├── container-apps.bicep
│   ├── database.bicep
│   ├── redis.bicep
│   ├── storage.bicep
│   ├── keyvault.bicep
│   └── monitoring.bicep
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── deployment.md
│   └── development.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

This prompt references all the instruction files that have been created and will guide the agent through scaffolding your complete Azure-ready Django application.
