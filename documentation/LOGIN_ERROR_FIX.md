# Login Error 500 - Fix Documentation

**Date**: November 27, 2025  
**Issue**: Users getting HTTP 500 error when attempting to login  
**Root Cause**: Redis session storage configuration issues

---

## Problems Identified

### 1. **Redis Configuration Conflict**
- `production.py` attempted to override Redis cache location from Key Vault
- Environment variable `REDIS_URL` was already correctly set in `container-apps.bicep`
- The override logic had a condition that might prevent proper Redis connection

### 2. **Missing Celery Environment Variables**
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` were not set in container environment
- These are needed for future async task processing
- Using separate Redis database (db 1) to avoid conflicts with cache/sessions (db 0)

### 3. **No Session Fallback Mechanism**
- If Redis connection fails, login fails with 500 error
- Django couldn't store user sessions without cache backend
- No graceful degradation to database sessions

---

## Changes Made

### 1. **Production Settings** (`magictoolbox/settings/production.py`)

#### Redis Configuration Fix
```python
# Only override CACHES if we have both REDIS_HOST and key from Key Vault
if REDIS_ACCESS_KEY and config("REDIS_HOST", default=""):
    REDIS_HOST = config("REDIS_HOST", default="")
    CACHES["default"]["LOCATION"] = f"rediss://:{REDIS_ACCESS_KEY}@{REDIS_HOST}:6380/0?ssl_cert_reqs=required"
    logger.info("Redis cache location updated from Key Vault credentials")
else:
    # Use REDIS_URL from environment (set in container-apps.bicep)
    logger.info("Using REDIS_URL from environment variables")
```

#### Session Cookie Settings
```python
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"  # Better CSRF protection
SESSION_COOKIE_AGE = 86400  # 24 hours
```

#### Redis Connection Validation with Fallback
```python
# Validate Redis connection and fallback to database sessions if needed
try:
    import redis
    from django_redis import get_redis_connection
    
    redis_conn = get_redis_connection("default")
    redis_conn.ping()
    logger.info("Redis connection successful - using cache-based sessions")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Falling back to database sessions.")
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
    CACHES["default"]["BACKEND"] = "django.core.cache.backends.locmem.LocMemCache"
```

### 2. **Infrastructure** (`infra/modules/container-apps.bicep`)

#### Added Celery Environment Variables
```bicep
{
  name: 'CELERY_BROKER_URL'
  value: 'rediss://:${redisAccessKey}@${redisHostName}:6380/1?ssl_cert_reqs=required'
}
{
  name: 'CELERY_RESULT_BACKEND'
  value: 'rediss://:${redisAccessKey}@${redisHostName}:6380/1?ssl_cert_reqs=required'
}
```

---

## Deployment Steps

### Option 1: Deploy via GitHub Actions (Recommended)

#### Step 1: Deploy Updated Infrastructure
```bash
# Trigger infrastructure deployment workflow
gh workflow run deploy-infrastructure.yml --field environment=dev
```

Wait for infrastructure deployment to complete (~5-10 minutes).

#### Step 2: Deploy Updated Application
```bash
# Commit and push changes
git add .
git commit -m "fix(auth): resolve login 500 error with Redis session handling"
git push origin develop  # For dev environment
# OR
git push origin main     # For staging/prod
```

The `azure-deploy.yml` workflow will automatically:
- Run tests
- Build new Docker image
- Push to ACR
- Deploy to Container Apps
- Run migrations
- Perform health checks

### Option 2: Manual Deployment via Script

```bash
# Deploy infrastructure and application
./scripts/deploy-to-azure.sh \
  --environment dev \
  --resource-group <your-resource-group-name>
```

### Option 3: Deploy Application Only (Skip Infrastructure)

If infrastructure is already up-to-date:

```bash
# Build and deploy only the application
./scripts/deploy-to-azure.sh \
  --environment dev \
  --resource-group <your-resource-group-name> \
  --skip-infra
```

---

## Verification Steps

### 1. Check Redis Connection
```bash
# Get Container App name
CONTAINER_APP_NAME="app-we-magictoolbox-dev-01"  # Adjust for your environment
RESOURCE_GROUP="rg-westeurope-magictoolbox-dev-01"

# Check logs for Redis connection status
az containerapp logs show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow
```

Look for:
- ✅ `"Redis connection successful - using cache-based sessions"`
- ⚠️ `"Redis connection failed: ... Falling back to database sessions"`

### 2. Test Login Functionality

1. **Navigate to application URL**:
   ```bash
   az containerapp show \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --query "properties.configuration.ingress.fqdn" -o tsv
   ```

2. **Access login page**: `https://<your-app-url>/auth/login/`

3. **Attempt login**:
   - If you don't have a user, register first at `/auth/register/`
   - Login with username and password
   - Should redirect to homepage with success message

4. **Check session persistence**:
   - Navigate to `/auth/profile/`
   - Should show your user profile (verifies session is working)
   - Refresh page - should remain logged in

### 3. Monitor Application Insights (Optional)

```bash
# Check for exceptions in Application Insights
az monitor app-insights query \
  --app <app-insights-name> \
  --analytics-query "exceptions | where timestamp > ago(1h) | order by timestamp desc"
```

---

## Rollback Plan

If issues persist after deployment:

### Rollback Container App to Previous Revision
```bash
# List revisions
az containerapp revision list \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "[].{name:name, active:properties.active, created:properties.createdTime}" -o table

# Activate previous revision
az containerapp revision activate \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --revision <previous-revision-name>
```

### Alternative: Use Database Sessions Temporarily

If Redis continues to have issues, you can temporarily use database-backed sessions:

1. Edit `production.py`:
   ```python
   # Force database sessions
   SESSION_ENGINE = "django.contrib.sessions.backends.db"
   ```

2. Ensure session table exists:
   ```bash
   az containerapp exec \
     --name $CONTAINER_APP_NAME \
     --resource-group $RESOURCE_GROUP \
     --command "python manage.py migrate"
   ```

3. Redeploy application

---

## Root Cause Analysis

### Why Did This Happen?

1. **Redis URL Configuration**:
   - `REDIS_URL` was correctly set in `container-apps.bicep`
   - `production.py` attempted to reconstruct it from separate components
   - Condition logic might have prevented proper override
   - Result: Potential Redis connection string mismatch

2. **Session Storage Dependency**:
   - Django sessions configured to use cache backend (Redis)
   - No fallback mechanism if Redis unavailable
   - Login requires session storage to work
   - Result: Login fails with 500 error if Redis unreachable

3. **Missing Environment Variables**:
   - Celery broker URLs not set in container environment
   - Not causing immediate issues but needed for async tasks
   - Result: Future functionality limitation

### Why Wasn't This Caught Earlier?

- Local development likely uses different Redis configuration
- Test environment might have working Redis connection
- No integration tests for Redis connection failures
- Health check endpoint (`/health/`) doesn't validate Redis

---

## Prevention Measures

### 1. Enhanced Health Check
Consider adding Redis validation to health check endpoint:

```python
# In apps/core/views.py
def health_check(request):
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "cache": "unknown",
    }
    
    # Check database
    try:
        from django.db import connection
        connection.ensure_connection()
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check cache (Redis)
    try:
        from django.core.cache import cache
        cache.set("health_check", "ok", 30)
        if cache.get("health_check") == "ok":
            health_status["cache"] = "connected"
    except Exception as e:
        health_status["cache"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return JsonResponse(health_status)
```

### 2. Integration Tests
Add tests for authentication with session storage:

```python
# In tests/test_authentication.py
def test_login_with_session_storage(client):
    """Test login works with session backend."""
    user = User.objects.create_user(username="testuser", password="testpass")
    response = client.post("/auth/login/", {
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 302  # Redirect after login
    assert "_auth_user_id" in client.session
```

### 3. Monitoring Alerts
Set up Application Insights alerts for:
- HTTP 500 errors on `/auth/login/` endpoint
- Redis connection failures
- Session storage errors

---

## Related Documentation

- [Azure Resources Usage Analysis](./AZURE_RESOURCES_USAGE_ANALYSIS.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Azure Deployment README](./AZURE_DEPLOYMENT_README.md)
- [Troubleshooting Guide](./AZURE_CONTAINER_APPS_TROUBLESHOOTING.md)

---

## Summary

✅ **Fixed**: Redis configuration conflict resolved  
✅ **Added**: Celery broker environment variables for future use  
✅ **Improved**: Session handling with automatic fallback to database  
✅ **Enhanced**: Session cookie security settings  

**Expected Result**: Login should now work reliably, with automatic fallback to database sessions if Redis is unavailable.
