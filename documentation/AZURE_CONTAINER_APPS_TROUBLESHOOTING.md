# Azure Container Apps Troubleshooting Guide

This guide documents common issues encountered when deploying Django applications to Azure Container Apps and their solutions.

## Table of Contents

- [Health Check Failures](#health-check-failures)
- [Redirect Loop Issues](#redirect-loop-issues)
- [Static Files Not Loading](#static-files-not-loading)
- [Database Connection Issues](#database-connection-issues)
- [Environment Variables](#environment-variables)
- [Revision Management](#revision-management)

---

## Health Check Failures

### Issue: Container App Revision Shows "Unhealthy"

**Symptoms:**
- Container App revision health state is "Unhealthy"
- Health probes fail with HTTP 400 errors
- Logs show: `Invalid HTTP_HOST header: '100.100.0.153:8000'. You may need to add '100.100.0.153' to ALLOWED_HOSTS.`

**Root Cause:**
Azure Container Apps uses internal IP addresses (from subnet 100.100.0.0/16) for health probes. Django's ALLOWED_HOSTS validation rejects these internal IPs because they don't match your public FQDN.

**Solution:**

Create a custom middleware to detect and allow health check requests from internal Azure IPs:

1. **Create `apps/core/middleware.py`:**

```python
import logging
import ipaddress
from django.conf import settings
from django.http import HttpResponse

logger = logging.getLogger(__name__)

class HealthCheckMiddleware:
    """
    Middleware to handle health check requests from Azure Container Apps.
    
    Azure Container Apps health probes come from internal IP addresses
    (100.100.0.0/16 and private ranges) that don't match ALLOWED_HOSTS.
    This middleware detects health check requests from these internal IPs
    and bypasses host validation.
    """
    
    # Azure Container Apps uses these internal subnets for health probes
    INTERNAL_SUBNETS = [
        ipaddress.ip_network('100.100.0.0/16'),  # Azure Container Apps
        ipaddress.ip_network('10.0.0.0/8'),      # Private network
        ipaddress.ip_network('172.16.0.0/12'),   # Private network
        ipaddress.ip_network('192.168.0.0/16'),  # Private network
    ]
    
    HEALTH_CHECK_PATHS = ['/health/', '/readiness/', '/liveness/']
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is a health check request
        if request.path in self.HEALTH_CHECK_PATHS:
            # Get the client IP (could be behind proxy)
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0].strip()
            else:
                client_ip = request.META.get('REMOTE_ADDR')
            
            try:
                ip = ipaddress.ip_address(client_ip)
                
                # Check if IP is from internal subnet
                is_internal = any(ip in subnet for subnet in self.INTERNAL_SUBNETS)
                
                if is_internal:
                    logger.debug(f"Health check from internal IP: {client_ip}")
                    # Bypass host validation for internal health checks
                    request.META['HTTP_HOST'] = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
            except ValueError:
                logger.warning(f"Invalid IP address: {client_ip}")
        
        response = self.get_response(request)
        return response
```

2. **Add middleware to `magictoolbox/settings/base.py`:**

```python
MIDDLEWARE = [
    'apps.core.middleware.HealthCheckMiddleware',  # Must be first!
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ... rest of middleware
]
```

**Important**: The `HealthCheckMiddleware` MUST be the first middleware in the list to bypass host validation before `SecurityMiddleware` processes the request.

**Verification:**

```bash
# Check revision health status
az containerapp revision list \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --query "[].{Name:name, Health:properties.healthState, Traffic:properties.trafficWeight}" \
  --output table

# Should show: Health = "Healthy"
```

---

## Redirect Loop Issues

### Issue: Browser Shows "Too Many Redirects"

**Symptoms:**
- Browser error: "This page isn't working... redirected you too many times"
- `curl -I` shows HTTP 301 redirects in a loop
- Website is completely inaccessible

**Root Cause:**
When `SECURE_SSL_REDIRECT = True` is set in Django, it attempts to redirect HTTP to HTTPS. However, Azure Container Apps handles SSL termination at the ingress level, so requests reaching Django are already HTTP (even though they arrived as HTTPS at the ingress). Django sees HTTP and tries to redirect, creating an infinite loop.

**Solution:**

Configure Django to trust the Azure Container Apps proxy headers:

1. **Update `magictoolbox/settings/production.py`:**

```python
# Azure Container Apps handles SSL termination at ingress
# Don't redirect to HTTPS in Django, trust the X-Forwarded-Proto header
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Keep other security settings
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
```

**Explanation:**
- `SECURE_SSL_REDIRECT = False`: Django won't try to redirect HTTP to HTTPS
- `SECURE_PROXY_SSL_HEADER`: Django trusts the `X-Forwarded-Proto` header from Azure's proxy
- This way, Django knows the original request was HTTPS without trying to redirect

**Verification:**

```bash
# Test - should return HTTP 200, not 301
curl -I https://your-app.azurecontainerapps.io/

# Output should show:
# HTTP/2 200
# server: gunicorn
```

---

## Static Files Not Loading

### Issue: CSS/JS Files Return HTTP 409 Error

**Symptoms:**
- Browser console errors: `net::ERR_ABORTED 409 (Public access is not permitted on this storage account.)`
- Static files try to load from: `https://storageaccount.blob.core.windows.net/uploads/css/custom.css`
- Page loads but has no styling or JavaScript functionality

**Root Cause:**
When static files are configured to be served from Azure Blob Storage with public access disabled (security best practice), browsers cannot load CSS/JS files directly. The Django app has access via Managed Identity, but browsers don't.

**Solution:**

Use **WhiteNoise** to serve static files efficiently from the Django container:

1. **Add WhiteNoise to `requirements/production.txt`:**

```txt
# Static files serving
whitenoise[brotli]>=6.6,<7.0
```

2. **Add WhiteNoise middleware to `magictoolbox/settings/base.py`:**

```python
MIDDLEWARE = [
    'apps.core.middleware.HealthCheckMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files
    'corsheaders.middleware.CorsMiddleware',
    # ... rest of middleware
]
```

3. **Update `magictoolbox/settings/production.py`:**

```python
# Static files - served by WhiteNoise from container
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Azure Blob Storage for media files (uploads) using Managed Identity
from azure.identity import DefaultAzureCredential
DEFAULT_FILE_STORAGE = 'storages.backends.azure_storage.AzureStorage'
AZURE_ACCOUNT_NAME = config('AZURE_STORAGE_ACCOUNT_NAME', default='')
AZURE_TOKEN_CREDENTIAL = DefaultAzureCredential()
AZURE_CONTAINER = config('AZURE_STORAGE_CONTAINER_UPLOADS', default='uploads')
AZURE_CUSTOM_DOMAIN = f'{AZURE_ACCOUNT_NAME}.blob.core.windows.net'
MEDIA_URL = f'https://{AZURE_CUSTOM_DOMAIN}/{AZURE_CONTAINER}/'
```

4. **Ensure `scripts/startup.sh` collects static files:**

```bash
# Collect static files (if not already done in Dockerfile)
if [ ! -d "/app/staticfiles" ] || [ -z "$(ls -A /app/staticfiles)" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi
```

**Benefits:**
- ✅ Static files served efficiently from container
- ✅ Brotli compression reduces file sizes
- ✅ Cache-busting hashes prevent stale content
- ✅ Azure Blob Storage stays private (secure)
- ✅ No additional Azure Blob Storage costs for static files

**Verification:**

```bash
# Test CSS file
curl -I https://your-app.azurecontainerapps.io/static/css/custom.css
# Should return: HTTP/2 200, server: gunicorn

# Test JavaScript file
curl -I https://your-app.azurecontainerapps.io/static/js/main.js
# Should return: HTTP/2 200, server: gunicorn

# Check logs for collectstatic
az containerapp logs show \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --tail 100 | grep -i "static"

# Should show: "static files copied to '/app/staticfiles', 784 post-processed."
```

---

## Database Connection Issues

### Issue: Cannot Connect to PostgreSQL

**Symptoms:**
- Container app fails to start
- Logs show: `psycopg2.OperationalError: could not connect to server`
- Health checks fail

**Solutions:**

1. **Check firewall rules:**

```bash
# Add Container Apps outbound IP to PostgreSQL firewall
OUTBOUND_IP=$(az containerapp show \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --query properties.outboundIpAddresses[0] -o tsv)

az postgres flexible-server firewall-rule create \
  --resource-group magictoolbox-demo-rg \
  --name your-postgres-server \
  --rule-name AllowContainerApps \
  --start-ip-address $OUTBOUND_IP \
  --end-ip-address $OUTBOUND_IP
```

2. **Verify connection string format:**

```bash
# Should be:
# postgresql://user:password@hostname:5432/database?sslmode=require
```

3. **Test connection from container:**

```bash
az containerapp exec \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --command "python manage.py check --database default"
```

---

## Environment Variables

### Issue: Missing or Incorrect Environment Variables

**Common Issues:**
- `SECRET_KEY` not set
- Database credentials incorrect
- Storage account name missing

**Solution:**

1. **List current environment variables:**

```bash
az containerapp show \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --query properties.template.containers[0].env
```

2. **Update environment variable:**

```bash
az containerapp update \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --set-env-vars "VARIABLE_NAME=value"
```

3. **Update secret:**

```bash
az containerapp update \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --replace-env-vars "SECRET_NAME=secretref:secret-name"
```

---

## Revision Management

### Issue: New Revision Not Activating

**Symptoms:**
- Old revision still receiving 100% traffic
- New revision exists but is inactive

**Solution:**

1. **Force new revision with timestamp:**

```bash
az containerapp update \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --image yourregistry.azurecr.io/magictoolbox:latest \
  --set-env-vars DEPLOY_TIMESTAMP=$(date +%s)
```

2. **Manually activate revision:**

```bash
# List revisions
az containerapp revision list \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --output table

# Activate specific revision
az containerapp revision activate \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --revision app-magictoolboxdevgrrafkow--0000006
```

3. **Deactivate old revision:**

```bash
az containerapp revision deactivate \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --revision app-magictoolboxdevgrrafkow--0000005
```

---

## Quick Diagnostic Commands

```bash
# Check overall app status
az containerapp show \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --query "{Status:properties.runningStatus, FQDN:properties.configuration.ingress.fqdn}"

# Check all revisions health
az containerapp revision list \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --query "[].{Name:name, Active:properties.active, Health:properties.healthState, Traffic:properties.trafficWeight}" \
  --output table

# View recent logs
az containerapp logs show \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --tail 100

# Search logs for errors
az containerapp logs show \
  --name app-magictoolboxdevgrrafkow \
  --resource-group magictoolbox-demo-rg \
  --tail 200 | grep -i -E "(error|exception|fail)"

# Test health endpoint
curl https://your-app.azurecontainerapps.io/health/

# Test with verbose output
curl -v https://your-app.azurecontainerapps.io/
```

---

## Summary of Fixes Applied

This repository already has the following fixes implemented:

1. ✅ **HealthCheckMiddleware** - Handles Azure internal health probe IPs
2. ✅ **SECURE_SSL_REDIRECT = False** - Prevents redirect loop with Azure SSL termination
3. ✅ **WhiteNoise** - Serves static files from container, not Blob Storage
4. ✅ **SECURE_PROXY_SSL_HEADER** - Trusts X-Forwarded-Proto from Azure proxy

If you encounter these issues after deployment:
1. Check that all middleware is properly configured
2. Verify production.py settings are correct
3. Ensure static files are collected during container startup
4. Review Container Apps logs for specific errors

---

**Last Updated**: November 26, 2025
**Applies to**: Azure Container Apps with Django 5.0+
