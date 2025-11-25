# MagicToolbox Backend

Django backend for the MagicToolbox file conversion application.

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+

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
backend/
├── apps/
│   ├── core/           # Base models, middleware, utilities
│   ├── authentication/ # User management and JWT auth
│   ├── tools/          # Tool plugin system
│   └── api/            # API versioning
├── magictoolbox/
│   ├── settings/       # Split settings (base, dev, prod)
│   ├── urls.py         # Root URL configuration
│   └── celery.py       # Celery configuration
├── requirements/       # Split requirements files
├── manage.py
└── README.md
```

## Adding New Tools

1. Create new tool in `apps/tools/plugins/`:
```python
from apps.tools.base import BaseTool

class MyTool(BaseTool):
    name = "my-tool"
    display_name = "My Tool"
    # ... implement required methods
```

2. Tool will be auto-discovered on startup

## API Documentation

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Environment Variables

See `.env.example` for all available configuration options.
