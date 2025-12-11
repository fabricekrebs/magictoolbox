"""
Development settings for MagicToolbox project.

These settings are optimized for local development with relaxed security
and additional debugging tools.
"""

from decouple import config

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use SQLite for development if PostgreSQL is not configured
if not config("DB_NAME", default=""):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Use dummy cache if Redis is not available
if not config("REDIS_URL", default=""):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# Development-specific apps (django_extensions is optional)
# INSTALLED_APPS += [
#     'django_extensions',  # Useful development tools
# ]

# Disable template caching in development
for template_engine in TEMPLATES:
    template_engine["OPTIONS"]["debug"] = True

# Use console email backend in development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Use local file storage in development
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Disable HTTPS redirect in development
SECURE_SSL_REDIRECT = False

# Enable Azure Functions for PDF conversion in development (if configured)
# Set USE_AZURE_FUNCTIONS_PDF_CONVERSION=True in .env to enable
# Also set AZURE_FUNCTION_BASE_URL to your local function app URL
# Example: http://localhost:7071/api
# Example: http://localhost:7071/api/convert/pdf-to-docx

# Additional logging in development
LOGGING["loggers"]["django.db.backends"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}

# Django Debug Toolbar (optional - uncomment if needed)
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
# INTERNAL_IPS = ['127.0.0.1']
