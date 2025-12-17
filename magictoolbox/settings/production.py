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

# Azure Key Vault for secrets management
# Use Managed Identity for secure, keyless authentication
# Set KEY_VAULT_ENABLED=true to enable Key Vault integration
try:
    from azure.core.exceptions import AzureError
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    KEY_VAULT_ENABLED = config("KEY_VAULT_ENABLED", default=False, cast=bool)
    KEY_VAULT_NAME = config("KEY_VAULT_NAME", default="")
    if KEY_VAULT_ENABLED and KEY_VAULT_NAME:
        AZURE_KEY_VAULT_URL = f"https://{KEY_VAULT_NAME}.vault.azure.net/"
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=AZURE_KEY_VAULT_URL, credential=credential)

        # Retrieve secrets from Key Vault with fallback to environment variables
        def get_secret_or_env(secret_name: str, env_var_name: str, required: bool = True) -> str:
            """Retrieve secret from Key Vault or fall back to environment variable."""
            try:
                secret_value = secret_client.get_secret(secret_name).value
                logger.info(f"Retrieved {secret_name} from Key Vault")
                return secret_value
            except AzureError as e:
                logger.warning(
                    f"Could not retrieve {secret_name} from Key Vault: {e}. Using environment variable."
                )
                value = config(env_var_name, default="")
                if required and not value:
                    raise ValueError(
                        f"Secret {secret_name} not found in Key Vault or environment variable {env_var_name}"
                    )
                return value

        # Override secrets with Key Vault values (with fallback to env vars)
        try:
            SECRET_KEY = get_secret_or_env("django-secret-key", "SECRET_KEY", required=True)

            # Database credentials
            DB_PASSWORD = get_secret_or_env("postgres-password", "DB_PASSWORD", required=True)
            DATABASES["default"]["PASSWORD"] = DB_PASSWORD

            # Redis URL is passed as a complete connection string in environment variables
            # No need to reconstruct it from individual components
            logger.info("Using REDIS_URL from environment variables (with embedded access key)")

            # Storage credentials (for non-Managed Identity scenarios)
            STORAGE_ACCOUNT_KEY = get_secret_or_env(
                "storage-account-key", "AZURE_STORAGE_ACCOUNT_KEY", required=False
            )

            logger.info("Successfully configured secrets from Key Vault")
        except Exception as e:
            logger.error(f"Error configuring secrets from Key Vault: {e}")
            raise
    else:
        logger.info("KEY_VAULT_NAME not set. Using environment variables for secrets.")
except ImportError as e:
    logger.warning(
        f"Azure Key Vault packages not installed: {e}. Using environment variables for secrets."
    )

# Validate Redis connection and fallback to database sessions if needed
try:
    import redis
    from django_redis import get_redis_connection

    # Test Redis connection
    redis_conn = get_redis_connection("default")
    redis_conn.ping()
    logger.info("Redis connection successful - using cache-based sessions")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Falling back to database sessions.")
    # Fallback to database-backed sessions if Redis is unavailable
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
    # Also update cache to use dummy backend as fallback
    CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"

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

# Email Configuration (configure based on your email service)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.sendgrid.net")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@magictoolbox.com")

# Admin notification emails
ADMINS = [
    ("Admin", config("ADMIN_EMAIL", default="admin@magictoolbox.com")),
]
MANAGERS = ADMINS

# Database connection pooling (optional - requires django-db-connection-pool)
DATABASES["default"]["CONN_MAX_AGE"] = 600  # 10 minutes
DATABASES["default"]["ATOMIC_REQUESTS"] = True
