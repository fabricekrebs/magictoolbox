"""
Production settings for MagicToolbox project.

These settings are optimized for Azure Container Apps deployment with
enhanced security and Azure service integrations.
"""
from .base import *
from decouple import config

# SECURITY
DEBUG = False

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True

# Azure Blob Storage for media files
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
AZURE_ACCOUNT_NAME = config('AZURE_STORAGE_ACCOUNT_NAME', default='')
AZURE_ACCOUNT_KEY = config('AZURE_STORAGE_ACCOUNT_KEY', default='')
AZURE_CONTAINER = config('AZURE_STORAGE_CONTAINER', default='media')
AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_CONTAINER}/'

# Use Azure Key Vault for secrets (optional - requires azure-identity package)
try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    
    AZURE_KEY_VAULT_URL = config('AZURE_KEY_VAULT_URL', default='')
    if AZURE_KEY_VAULT_URL:
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=AZURE_KEY_VAULT_URL, credential=credential)
        
        # Override SECRET_KEY from Key Vault
        try:
            SECRET_KEY = secret_client.get_secret('django-secret-key').value
        except Exception as e:
            print(f"Warning: Could not retrieve django-secret-key from Key Vault: {e}")
except ImportError:
    print("Warning: azure-identity not installed. Using environment variables for secrets.")

# Application Insights for monitoring and logging
try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
    from opencensus.ext.azure.trace_exporter import AzureExporter
    from opencensus.trace.samplers import ProbabilitySampler
    
    APPLICATIONINSIGHTS_CONNECTION_STRING = config('APPLICATIONINSIGHTS_CONNECTION_STRING', default='')
    
    if APPLICATIONINSIGHTS_CONNECTION_STRING:
        # Add Application Insights middleware
        MIDDLEWARE += [
            'opencensus.ext.django.middleware.OpencensusMiddleware',
        ]
        
        # OpenCensus Configuration
        OPENCENSUS = {
            'TRACE': {
                'SAMPLER': ProbabilitySampler(rate=1.0),
                'EXPORTER': AzureExporter(
                    connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING
                ),
            }
        }
        
        # Add Azure Log Handler to logging
        LOGGING['handlers']['azure'] = {
            'level': 'INFO',
            'class': 'opencensus.ext.azure.log_exporter.AzureLogHandler',
            'connection_string': APPLICATIONINSIGHTS_CONNECTION_STRING,
        }
        
        # Add azure handler to loggers
        LOGGING['root']['handlers'].append('azure')
        LOGGING['loggers']['django']['handlers'].append('azure')
        LOGGING['loggers']['apps']['handlers'].append('azure')
except ImportError:
    print("Warning: opencensus-ext-azure not installed. Application Insights logging disabled.")

# Email Configuration (configure based on your email service)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.sendgrid.net')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@magictoolbox.com')

# Admin notification emails
ADMINS = [
    ('Admin', config('ADMIN_EMAIL', default='admin@magictoolbox.com')),
]
MANAGERS = ADMINS

# Database connection pooling (optional - requires django-db-connection-pool)
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes
DATABASES['default']['ATOMIC_REQUESTS'] = True
