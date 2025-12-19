"""
Production settings for MagicToolbox project.

These settings are optimized for Azure Container Apps deployment with
enhanced security and Azure service integrations.
"""

import logging

from decouple import config

from .base import *

# Configure logging first
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get environment name
ENVIRONMENT = config("ENVIRONMENT", default="dev")

# SECURITY
DEBUG = False

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Azure Container Apps handles SSL termination at ingress
# Don't redirect to HTTPS in Django, trust the X-Forwarded-Proto header
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"  # Better CSRF protection
SESSION_COOKIE_AGE = 86400  # 24 hours

# Static files - served by WhiteNoise from container
# Use WhiteNoise to serve static files efficiently from the container
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Azure Blob Storage for media files (uploads) using Managed Identity
from azure.identity import DefaultAzureCredential

DEFAULT_FILE_STORAGE = "storages.backends.azure_storage.AzureStorage"
AZURE_STORAGE_ACCOUNT_NAME = config("AZURE_STORAGE_ACCOUNT_NAME", default="")
# Use Managed Identity instead of account key
AZURE_TOKEN_CREDENTIAL = DefaultAzureCredential()
AZURE_CONTAINER = config("AZURE_STORAGE_CONTAINER_UPLOADS", default="uploads")
AZURE_CUSTOM_DOMAIN = f"{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
MEDIA_URL = f"https://{AZURE_CUSTOM_DOMAIN}/{AZURE_CONTAINER}/"

# Secrets are managed via Container Apps secret references in Bicep
# No additional Key Vault integration code needed

# Enforce SSL for production database connections
DATABASES["default"]["OPTIONS"]["sslmode"] = "require"

# Use persistent connections for production (better performance)
DATABASES["default"]["CONN_MAX_AGE"] = None  # Persistent connections
DATABASES["default"]["ATOMIC_REQUESTS"] = True  # Wrap each request in a transaction

# Application Insights for monitoring, logging, and telemetry
try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
    from opencensus.ext.azure.metrics_exporter import MetricsExporter
    from opencensus.ext.azure.trace_exporter import AzureExporter
    from opencensus.trace.samplers import ProbabilitySampler

    APPLICATIONINSIGHTS_CONNECTION_STRING = config(
        "APPLICATIONINSIGHTS_CONNECTION_STRING", default=""
    )

    if APPLICATIONINSIGHTS_CONNECTION_STRING:
        logger.info("Configuring Application Insights telemetry")

        # Add Application Insights middleware for request tracing
        MIDDLEWARE += [
            "opencensus.ext.django.middleware.OpencensusMiddleware",
        ]

        # OpenCensus Configuration for distributed tracing
        # Sample rate: 1.0 (100%) for dev/staging, 0.1-0.5 (10-50%) for production
        sample_rate = 1.0 if ENVIRONMENT in ["dev", "staging"] else 0.5

        OPENCENSUS = {
            "TRACE": {
                "SAMPLER": ProbabilitySampler(rate=sample_rate),
                "EXPORTER": AzureExporter(connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING),
            },
            "METRICS": {
                "EXPORTER": MetricsExporter(
                    connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING
                ),
            },
        }

        # Add Azure Log Handler to logging configuration
        LOGGING["handlers"]["azure"] = {
            "level": "INFO",
            "class": "opencensus.ext.azure.log_exporter.AzureLogHandler",
            "connection_string": APPLICATIONINSIGHTS_CONNECTION_STRING,
            "formatter": "verbose",
        }

        # Add azure handler to loggers for comprehensive telemetry
        LOGGING["root"]["handlers"].append("azure")
        LOGGING["loggers"]["django"]["handlers"].append("azure")
        LOGGING["loggers"]["apps"]["handlers"].append("azure")

        # Track exceptions automatically
        LOGGING["loggers"]["django.request"] = {
            "handlers": ["console", "file", "azure"],
            "level": "ERROR",
            "propagate": False,
        }

        logger.info(f"Application Insights enabled with {sample_rate*100}% sampling rate")
    else:
        logger.warning(
            "APPLICATIONINSIGHTS_CONNECTION_STRING not set. Application Insights disabled."
        )
except ImportError as e:
    logger.warning(f"Application Insights packages not installed: {e}. Telemetry disabled.")

# Azure Functions Configuration
# PDF conversion is handled via blob triggers - no HTTP endpoint needed
USE_AZURE_FUNCTIONS_PDF_CONVERSION = config(
    "USE_AZURE_FUNCTIONS_PDF_CONVERSION", default=False, cast=bool
)
