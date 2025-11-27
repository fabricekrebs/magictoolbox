# Azure Resources Usage Analysis

**Generated**: November 26, 2025  
**Resource Group**: magictoolbox-demo-rg  
**Environment**: Development

## Summary

This document analyzes which Azure resources are **actively used** by the deployed application versus which are **deployed but not yet utilized**.

---

## ✅ Actively Used Resources

### 1. **Azure Container Apps** 
- **Resource**: `app-magictoolboxdevgrrafkow`
- **Status**: ✅ **ACTIVELY USED**
- **Usage**: Hosts the Django application (revision 0000006, Healthy)
- **Evidence**: Application is running and serving traffic
- **Configuration**: 
  - Image: `magictoolboxdevacrgrrafkow6cceq.azurecr.io/magictoolbox:static-files-fix`
  - Scaling: 1-3 replicas
  - Resources: 0.5 CPU, 1Gi memory

### 2. **Azure Container Registry (ACR)**
- **Resource**: `magictoolboxdevacrgrrafkow6cceq`
- **Status**: ✅ **ACTIVELY USED**
- **Usage**: Stores Docker images for the application
- **Evidence**: Container App pulls images from this registry
- **Authentication**: Managed Identity (System Assigned)

### 3. **PostgreSQL Flexible Server**
- **Resource**: `magictoolbox-dev-psql-grrafkow6cceq`
- **Status**: ✅ **ACTIVELY USED**
- **Usage**: Primary database for Django application
- **Evidence**: 
  - Environment variable `DB_HOST` configured: `magictoolbox-dev-psql-grrafkow6cceq.postgres.database.azure.com`
  - Django uses PostgreSQL engine in `settings/base.py`
  - Migrations run successfully during container startup
- **Configuration**:
  - Database: `magictoolbox`
  - Connection pooling: CONN_MAX_AGE=600s

### 4. **Azure Cache for Redis**
- **Resource**: `magictoolbox-dev-redis-grrafkow6cceq`
- **Status**: ✅ **ACTIVELY USED**
- **Usage**: Django cache backend and session storage
- **Evidence**:
  - Environment variable `REDIS_URL` configured: `rediss://...@magictoolbox-dev-redis-grrafkow6cceq.redis.cache.windows.net:6380/0`
  - Django settings use `django_redis.cache.RedisCache`
  - Session engine uses cache backend
- **Configuration**:
  - SSL enabled (port 6380)
  - Max connections: 50
  - Used for: Session storage, caching

### 5. **Azure Storage Account (Blob Storage)**
- **Resource**: `magictoolboxdevstgrrafko`
- **Status**: ✅ **ACTIVELY USED**
- **Usage**: Stores user-uploaded files (media files)
- **Evidence**:
  - Environment variable `AZURE_STORAGE_ACCOUNT_NAME` configured
  - Django `DEFAULT_FILE_STORAGE` uses Azure Storage backend
  - Managed Identity authentication configured
- **Containers**:
  - `uploads`: User uploaded files (GPX, images, etc.)
  - `processed`: Converted/processed files
  - `static`: NOT USED (static files served via WhiteNoise from container)
- **Note**: Public access is **disabled** (security best practice)

### 6. **Log Analytics Workspace**
- **Resource**: `magictoolbox-dev-logs-grrafkow6cceq`
- **Status**: ✅ **ACTIVELY USED**
- **Usage**: Collects logs from Container Apps environment
- **Evidence**: Container Apps automatically sends logs here
- **Access**: Via `az containerapp logs show` or Azure Portal

### 7. **Container Apps Environment**
- **Resource**: `env-magictoolboxdevgrrafkow`
- **Status**: ✅ **ACTIVELY USED**
- **Usage**: Provides infrastructure for Container Apps
- **Features**: Networking, load balancing, health probes

---

## ⚠️ Deployed But NOT Actively Used

### 1. **Azure Key Vault**
- **Resource**: `kvmagictoolboxgrrafk`
- **Status**: ⚠️ **DEPLOYED BUT NOT ACTIVELY USED**
- **Current State**: 
  - Environment variable `KEY_VAULT_NAME` is set: `kvmagictoolboxgrrafk`
  - Code has Key Vault integration (commented out in `production.py`)
  - Secrets are currently passed via Container Apps secrets (not pulled from Key Vault)
- **Potential Usage**:
  ```python
  # Currently commented out in production.py:
  # SECRET_KEY = secret_client.get_secret('django-secret-key').value
  ```
- **Recommendation**: 
  - **Keep deployed** - Good practice for future secret management
  - **Cost**: ~$0.03/month (minimal)
  - **Future use**: Rotate secrets, additional API keys, certificates

### 2. **Application Insights**
- **Resource**: `magictoolbox-dev-ai-grrafkow6cceq`
- **Status**: ⚠️ **DEPLOYED BUT NOT FULLY UTILIZED**
- **Current State**:
  - Environment variable `APPLICATIONINSIGHTS_CONNECTION_STRING` is set (secret)
  - Code attempts to configure Application Insights
  - **BUT**: `opencensus-ext-azure` may not be installed (warning in logs)
- **Evidence**:
  ```python
  # In production.py - wrapped in try/except
  from opencensus.ext.azure.log_exporter import AzureLogHandler
  # Falls back to: "Warning: opencensus-ext-azure not installed"
  ```
- **Impact**: 
  - Basic telemetry might be collected
  - Advanced features (traces, dependencies) likely not working
- **Recommendation**:
  - **Verify if opencensus packages are installed** in requirements
  - **Check** `requirements/production.txt` for:
    - `opencensus-ext-azure>=1.1,<1.2`
    - `opencensus-ext-django>=0.8,<0.9`
  - **Cost**: ~$2-5/month for dev environment

### 3. **Celery (Background Tasks)**
- **Status**: ⚠️ **CONFIGURED BUT NOT RUNNING**
- **Current State**:
  - Celery settings configured in `base.py`
  - Uses Redis as broker/backend
  - **BUT**: No Celery worker container deployed
  - Environment variables `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` **NOT set**
- **Evidence**:
  - No Celery worker in Container Apps
  - `celery.py` exists but not utilized
- **Impact**: 
  - Synchronous file processing (blocking requests)
  - No background tasks
  - Long-running conversions may timeout
- **Recommendation**:
  - **Deploy Celery worker** as separate Container App for async processing
  - **Or**: Remove Celery configuration if not needed

---

## 📊 Cost Analysis

### Current Monthly Costs (Estimated - Dev Environment)

| Resource | Status | Est. Monthly Cost | Notes |
|----------|--------|-------------------|-------|
| **Container Apps** | ✅ Used | $20-30 | Based on CPU/memory usage |
| **ACR** | ✅ Used | $5 | Basic tier |
| **PostgreSQL Flexible** | ✅ Used | $15-25 | Burstable tier |
| **Redis Cache** | ✅ Used | $15 | Basic C0 |
| **Storage Account** | ✅ Used | $5 | Based on usage |
| **Log Analytics** | ✅ Used | $5 | Based on ingestion |
| **Key Vault** | ⚠️ Minimal | $0.03 | Very low cost |
| **Application Insights** | ⚠️ Partial | $2-5 | If telemetry working |
| **Container Apps Env** | ✅ Used | Included | No separate charge |
| **Total** | | **$67-85/month** | |

---

## 🔧 Recommendations

### Immediate Actions

1. **✅ Keep All Deployed Resources**
   - All resources serve a purpose (even if not fully utilized yet)
   - Costs are reasonable for a functional application
   - Better to have infrastructure ready than deploy later

2. **🔍 Verify Application Insights**
   ```bash
   # Check if opencensus packages are in the image
   az containerapp exec \
     --name app-magictoolboxdevgrrafkow \
     --resource-group magictoolbox-demo-rg \
     --command "pip list | grep opencensus"
   ```
   
   If missing, add to `requirements/production.txt`:
   ```txt
   opencensus-ext-azure>=1.1,<1.2
   opencensus-ext-django>=0.8,<0.9
   ```

3. **🚀 Consider Celery Worker for Production**
   - File conversions can be time-consuming
   - Background processing improves user experience
   - Prevents request timeouts
   
   Add to Bicep templates:
   ```bicep
   // Additional Container App for Celery worker
   container {
     name: 'celery-worker'
     image: '${acrLoginServer}/magictoolbox:latest'
     command: ['celery', '-A', 'magictoolbox', 'worker', '-l', 'info']
   }
   ```

### Future Enhancements

4. **🔐 Migrate Secrets to Key Vault**
   - Currently: Secrets in Container Apps environment
   - Future: Rotate secrets regularly via Key Vault
   - Better secret lifecycle management

5. **📈 Enable Application Insights Fully**
   - Track request performance
   - Monitor dependencies (PostgreSQL, Redis, Storage)
   - Set up alerts for failures
   - Use KQL queries for diagnostics

6. **⚡ Add Celery Beat (Optional)**
   - Schedule periodic tasks (cleanup old files, etc.)
   - Requires another small container

---

## 🎯 Current Architecture Status

```
✅ FULLY FUNCTIONAL (No Async Processing)
┌─────────────────────────────────────────────────────────────┐
│                      Azure Resource Group                    │
│                                                              │
│  ✅ Container Apps ──────────✅ Container Registry (ACR)    │
│      (Django App)                 (Docker Images)            │
│           │                                                  │
│           ├──────► ✅ PostgreSQL (Database)                 │
│           ├──────► ✅ Redis (Cache + Sessions)              │
│           ├──────► ✅ Storage Account (User Uploads)        │
│           ├──────► ⚠️ Key Vault (Not actively fetching)     │
│           └──────► ⚠️ Application Insights (Partial)        │
│                                                              │
│  ✅ Log Analytics Workspace (Logs from Container Apps)      │
│                                                              │
│  ❌ NOT DEPLOYED: Celery Worker (Async Tasks)               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Environment Variables Status

| Variable | Purpose | Status | Used By |
|----------|---------|--------|---------|
| `DB_HOST` | PostgreSQL connection | ✅ Set | Django ORM |
| `DB_NAME` | Database name | ✅ Set | Django ORM |
| `DB_USER` | Database user | ✅ Set | Django ORM |
| `DB_PASSWORD` | Database password | ✅ Set (secret) | Django ORM |
| `REDIS_URL` | Redis connection | ✅ Set | Django Cache, Sessions |
| `AZURE_STORAGE_ACCOUNT_NAME` | Blob Storage | ✅ Set | File uploads |
| `KEY_VAULT_NAME` | Key Vault name | ⚠️ Set but unused | None (commented code) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights | ⚠️ Set (secret) | Telemetry (if installed) |
| `CELERY_BROKER_URL` | Celery broker | ❌ Not set | N/A - No Celery |
| `CELERY_RESULT_BACKEND` | Celery results | ❌ Not set | N/A - No Celery |

---

## ✅ Conclusion

**Overall Assessment**: Your Azure deployment is **well-structured and functional**. 

### What's Working:
- ✅ Core application infrastructure (Container Apps, ACR, Database, Cache, Storage)
- ✅ Proper security (Managed Identity, private storage, SSL termination)
- ✅ Monitoring infrastructure (Log Analytics)
- ✅ Static files served efficiently via WhiteNoise

### What's Prepared But Not Fully Used:
- ⚠️ Key Vault (infrastructure ready, not actively fetching secrets)
- ⚠️ Application Insights (might need packages installed)
- ⚠️ Celery configuration (Redis ready, no worker deployed)

### Recommendation:
**Keep all deployed resources.** The additional costs for Key Vault and Application Insights are minimal (~$5/month total), and they provide valuable capabilities when you need them. Focus on:
1. Verifying Application Insights telemetry works
2. Deciding if async processing (Celery) is needed for your workload

**Current setup is production-ready for synchronous workloads.**
