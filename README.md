# MagicToolbox Backend

Django backend for the MagicToolbox file conversion application.

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

## Environment Variables

See `.env.example` for all available configuration options.
