# Redis Connection Fix for Azure Container Apps

## Issue
Container Apps were unable to connect to Azure Cache for Redis, resulting in connection errors in the logs.

## Root Cause
The Redis Cache has `publicNetworkAccess: 'Disabled'` (configured in `infra/modules/redis.bicep`), which means it's only accessible via private endpoints. 

The Container Apps were configured with the correct VNet integration and could reach Redis through the private endpoint, but the connection string was **missing the authentication password**.

The original `REDIS_URL` format was:
```
rediss://default@{hostname}:6380/0?ssl_cert_reqs=required
```

This format doesn't include the access key (password), causing authentication failures.

## Solution
Updated the Redis connection strings to include the access key in the proper format:
```
rediss://:{access_key}@{hostname}:6380/0?ssl_cert_reqs=required
```

### Changes Made

#### 1. `/infra/modules/container-apps.bicep`
- **Added new secrets** for Redis URLs with embedded access keys:
  - `redis-url` - Main cache connection (database 0)
  - `celery-broker-url` - Celery broker (database 1)
  - `celery-result-backend` - Celery results (database 1)
  
- **Updated environment variables** to use secret references instead of plain values:
  ```bicep
  {
    name: 'REDIS_URL'
    secretRef: 'redis-url'  // Changed from value to secretRef
  }
  {
    name: 'CELERY_BROKER_URL'
    secretRef: 'celery-broker-url'  // Changed from value to secretRef
  }
  {
    name: 'CELERY_RESULT_BACKEND'
    secretRef: 'celery-result-backend'  // Changed from value to secretRef
  }
  ```

- **Secret definitions** (both for Key Vault and direct secrets):
  ```bicep
  {
    name: 'redis-url'
    value: 'rediss://:${redisAccessKey}@${redisHostName}:6380/0?ssl_cert_reqs=required'
  }
  {
    name: 'celery-broker-url'
    value: 'rediss://:${redisAccessKey}@${redisHostName}:6380/1?ssl_cert_reqs=required'
  }
  {
    name: 'celery-result-backend'
    value: 'rediss://:${redisAccessKey}@${redisHostName}:6380/1?ssl_cert_reqs=required'
  }
  ```

#### 2. `/magictoolbox/settings/production.py`
- **Simplified Redis configuration** to use the complete connection string from environment variables
- **Removed** the conditional logic that tried to reconstruct the Redis URL from components
- The settings now simply use `REDIS_URL` from the environment (which is populated from the secret)

## How It Works

### Network Flow
1. Container Apps → VNet Integration → Container Apps Subnet
2. Container Apps Subnet → Private Endpoint → Redis Cache
3. DNS Resolution via Private DNS Zone (`privatelink.redis.cache.windows.net`)
4. Connection authenticated using access key embedded in connection string

### Authentication Flow
1. Redis access key is retrieved from Key Vault (or passed directly during deployment)
2. Access key is embedded in the connection string format: `rediss://:{key}@{host}:6380/db`
3. Connection string is stored as a secret in Container Apps configuration
4. Django reads `REDIS_URL` environment variable and uses it to configure `django-redis`
5. `django-redis` establishes SSL connection (port 6380) with password authentication

## Deployment Steps

### Option 1: Full Redeployment
```bash
# Deploy infrastructure with the updated Bicep templates
cd infra
az deployment group create \
  --resource-group rg-westeurope-magictoolbox-dev \
  --template-file main.bicep \
  --parameters environment=dev \
  --parameters useKeyVaultReferences=true
```

### Option 2: Update Container App Only
```bash
# Update just the Container App secrets
az containerapp secret set \
  --name app-we-magictoolbox-01 \
  --resource-group rg-westeurope-magictoolbox-dev \
  --secrets redis-url="rediss://:YOUR_REDIS_ACCESS_KEY@YOUR_REDIS_HOST:6380/0?ssl_cert_reqs=required"

# Update environment variable to use the secret reference
az containerapp update \
  --name app-we-magictoolbox-01 \
  --resource-group rg-westeurope-magictoolbox-dev \
  --set-env-vars REDIS_URL=secretref:redis-url
```

## Verification

### 1. Check Container App Logs
```bash
az containerapp logs show \
  --name app-we-magictoolbox-01 \
  --resource-group rg-westeurope-magictoolbox-dev \
  --follow
```

Look for:
- ✅ `Redis connection successful - using cache-based sessions`
- ❌ `Redis connection failed: ...` (should not appear)

### 2. Test Health Endpoints
```bash
# Readiness check (includes Redis connectivity test)
curl https://YOUR_APP_URL/api/health/readiness/

# Expected response:
{
  "status": "ready",
  "checks": {
    "database": true,
    "cache": true
  }
}
```

### 3. Verify in Azure Portal
1. Navigate to Container Apps → Secrets
2. Confirm `redis-url`, `celery-broker-url`, `celery-result-backend` secrets exist
3. Navigate to Container Apps → Environment Variables
4. Confirm `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` use secret references

## Related Files
- `/infra/modules/container-apps.bicep` - Container Apps configuration
- `/infra/modules/redis.bicep` - Redis Cache configuration
- `/infra/modules/private-endpoints.bicep` - Private endpoint for Redis
- `/magictoolbox/settings/production.py` - Django production settings
- `/magictoolbox/settings/base.py` - Base cache configuration

## Security Considerations
✅ Access key is stored as a secret (not exposed in environment variables)  
✅ Connection uses TLS 1.2 (`rediss://` protocol)  
✅ SSL certificate validation enabled (`ssl_cert_reqs=required`)  
✅ Redis only accessible via private endpoint (no public access)  
✅ VNet integration ensures traffic stays within Azure backbone

## Troubleshooting

### Issue: Connection timeout
**Check**: VNet integration is properly configured
```bash
az containerapp show \
  --name app-we-magictoolbox-01 \
  --resource-group rg-westeurope-magictoolbox-dev \
  --query "properties.configuration.ingress.fqdn"
```

### Issue: Authentication failed
**Check**: Access key is correct in the secret
```bash
# Get Redis access key
az redis list-keys \
  --name red-westeurope-magictoolbox-01 \
  --resource-group rg-westeurope-magictoolbox-dev
```

### Issue: DNS resolution failed
**Check**: Private DNS zone link to VNet
```bash
az network private-dns link vnet list \
  --resource-group rg-westeurope-magictoolbox-dev \
  --zone-name privatelink.redis.cache.windows.net
```

## References
- [Azure Cache for Redis - Private Link](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-private-link)
- [django-redis documentation](https://github.com/jazzband/django-redis)
- [Redis connection string format](https://redis-py.readthedocs.io/en/stable/#redis.Redis.from_url)
