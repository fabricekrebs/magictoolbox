# Redis Removal Migration Guide

## Overview

Redis has been completely removed from the MagicToolbox infrastructure and replaced with database-backed sessions and cache. This simplifies the architecture for low-traffic scenarios while maintaining all functionality.

## Changes Made

### Infrastructure (Bicep)

1. **Removed Files**:
   - `infra/modules/redis.bicep` - Complete Redis module deleted

2. **Modified Files**:
   - `infra/main.bicep` - Removed Redis module deployment and outputs
   - `infra/modules/keyvault.bicep` - Removed Redis access key secret
   - `infra/modules/container-apps.bicep` - Removed Redis parameters, secrets, and environment variables
   - `infra/modules/private-endpoints.bicep` - Removed Redis private endpoint and DNS zones

### Application Code

1. **Django Settings** (`magictoolbox/settings/base.py`):
   - **Cache**: Changed from `django_redis.cache.RedisCache` to `django.core.cache.backends.db.DatabaseCache`
   - **Sessions**: Changed from `django.contrib.sessions.backends.cache` to `django.contrib.sessions.backends.db`
   - **Removed**: All Celery configuration (no longer needed)

2. **Requirements** (`requirements/base.txt`):
   - Removed packages: `django-redis`, `redis`, `hiredis`, `celery`

3. **Docker Compose** (`docker-compose.yml`):
   - Removed Redis service and volume

## Migration Steps

### Automatic Migration (Recommended)

A custom Django migration (`apps/core/migrations/0002_create_cache_table.py`) has been created that automatically creates the cache table. Simply run:

```bash
python manage.py migrate
```

This migration is **idempotent** - it won't fail if the table already exists, making it safe to run in all environments.

### For All Deployments (New and Existing)

The database cache table is created automatically when you run migrations during deployment. The Container App startup script already includes:

```bash
python manage.py migrate --noinput
```

No manual intervention is required. The cache table will be created on first deployment.

### Manual Creation (If Needed)

If you need to create the cache table manually for any reason:

#### Method 1: Via Django Management Command

```bash
# Connect to the Container App and run:
python manage.py createcachetable

# Or via Azure CLI:
az containerapp exec \
  --name <container-app-name> \
  --resource-group <resource-group-name> \
  --command "python manage.py createcachetable"
```

#### Method 2: Direct SQL (Advanced)

```sql
CREATE TABLE django_cache_table (
    cache_key VARCHAR(255) NOT NULL PRIMARY KEY,
    value TEXT NOT NULL,
    expires TIMESTAMP NOT NULL
);

CREATE INDEX django_cache_table_expires ON django_cache_table (expires);
```

### Environment Variables to Remove

The following environment variables are no longer needed and can be removed from Azure Key Vault or environment configuration:

- `REDIS_URL`
- `REDIS_HOST`
- `REDIS_ACCESS_KEY`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

## Verification

### 1. Verify Infrastructure Deployment

```bash
# Build and validate Bicep templates
cd infra
az bicep build --file main.bicep

# Deploy to development
az deployment group create \
  --resource-group rg-<location>-magictoolbox-dev-01 \
  --template-file main.bicep \
  --parameters parameters.dev.json
```

### 2. Verify Database Cache Table

```bash
# Check if cache table exists
python manage.py dbshell

# In PostgreSQL:
\dt django_cache_table
\d django_cache_table
```

### 3. Test Cache Functionality

```python
# In Django shell or view:
from django.core.cache import cache

# Set a value
cache.set('test_key', 'test_value', 60)

# Get the value
value = cache.get('test_key')
print(value)  # Should print: test_value

# Delete the value
cache.delete('test_key')
```

### 4. Test Session Functionality

1. Log in to the application
2. Verify session is maintained across requests
3. Check database for session records:
   ```sql
   SELECT * FROM django_session LIMIT 5;
   ```

## Performance Considerations

### Database-Backed Cache vs Redis

**Pros**:
- ✅ Simplified infrastructure (one less service to manage)
- ✅ No additional cost for Redis instance
- ✅ Suitable for low-traffic applications
- ✅ Built-in with Django, no external dependencies

**Cons**:
- ❌ Slower than in-memory cache (but acceptable for low traffic)
- ❌ Increased database load (minimal for low traffic)

### When to Consider Re-adding Redis

Consider adding Redis back if:
- You have > 1000 simultaneous users
- Cache hit rate is very high (> 80%)
- Database becomes a bottleneck
- You need pub/sub or real-time features
- You need distributed task queue (Celery)

## Rollback Plan

If you need to restore Redis:

1. **Restore Bicep Files**:
   ```bash
   git revert <commit-hash>
   ```

2. **Restore Requirements**:
   Add back to `requirements/base.txt`:
   ```
   django-redis>=5.4,<5.5
   redis>=5.0,<5.1
   celery>=5.3,<5.4
   ```

3. **Restore Django Settings**:
   ```python
   CACHES = {
       "default": {
           "BACKEND": "django_redis.cache.RedisCache",
           "LOCATION": config("REDIS_URL", default="redis://localhost:6379/0"),
       }
   }
   SESSION_ENGINE = "django.contrib.sessions.backends.cache"
   ```

4. **Redeploy Infrastructure** with Redis module

## Support

If you encounter issues:

1. Check logs: `az containerapp logs show --name <app-name> --resource-group <rg-name>`
2. Verify database connectivity: `python manage.py dbshell`
3. Check cache table exists: `python manage.py createcachetable`
4. Review Application Insights for errors

## Related Documentation

- [Azure Deployment README](AZURE_DEPLOYMENT_README.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Django Cache Framework](https://docs.djangoproject.com/en/5.0/topics/cache/)
- [Django Sessions](https://docs.djangoproject.com/en/5.0/topics/http/sessions/)
