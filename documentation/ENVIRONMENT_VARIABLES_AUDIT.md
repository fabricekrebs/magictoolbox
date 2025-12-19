# Environment Variables Audit

**Date**: 2025-12-18  
**Status**: Complete audit of all environment variables across Azure Functions and Container Apps

## Summary

This document audits all environment variables used in the Azure Functions and Django Container Apps to identify which are **actively used**, **deprecated**, or **can be removed**.

---

## Azure Functions (function_app.py)

### ✅ **ACTIVELY USED** - Keep These

| Variable | Purpose | Used In | Required |
|----------|---------|---------|----------|
| `AZURE_STORAGE_CONNECTION_STRING` | Blob storage access (local Azurite) | function_app.py:36 | Dev only |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name (Managed Identity) | function_app.py:42, :129, :150 | Production |
| `DB_HOST` | PostgreSQL server hostname | function_app.py:62, :152 | Yes |
| `DB_NAME` | PostgreSQL database name | function_app.py:63 | Yes |
| `DB_USER` | PostgreSQL username | function_app.py:64 | Yes |
| `DB_PASSWORD` | PostgreSQL password | function_app.py:65 | Yes |
| `DB_PORT` | PostgreSQL port | function_app.py:66 | Yes (default: 5432) |
| `DB_SSLMODE` | PostgreSQL SSL mode | function_app.py:67 | Yes (default: require) |
| `FUNCTIONS_WORKER_RUNTIME` | Azure Functions runtime | Bicep config | Yes |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights telemetry | Bicep config | Recommended |

### ❌ **NOT USED IN CODE** - Can Remove

| Variable | Currently Set In | Reason to Remove |
|----------|------------------|------------------|
| `APPINSIGHTS_INSTRUMENTATIONKEY` | function-app.bicep:128 | Deprecated - use connection string instead |
| `ApplicationInsightsAgent_EXTENSION_VERSION` | function-app.bicep:132 | Not used by Python Functions |
| `XDT_MicrosoftApplicationInsights_Mode` | function-app.bicep:136 | Not used by Python Functions |
| `InstrumentationEngine_EXTENSION_VERSION` | function-app.bicep:140 | Explicitly disabled |
| `APPLICATIONINSIGHTS_ENABLE_AGENT` | function-app.bicep:144 | Redundant with connection string |
| `APPLICATIONINSIGHTS_SAMPLING_PERCENTAGE` | function-app.bicep:148 | Not referenced in code |

---

## Django Container App (Container Apps)

### ✅ **ACTIVELY USED** - Keep These

| Variable | Purpose | Used In | Required |
|----------|---------|---------|----------|
| `SECRET_KEY` | Django secret key | base.py:24 | Yes |
| `DEBUG` | Debug mode toggle | base.py:27 | Yes |
| `ALLOWED_HOSTS` | Allowed HTTP hosts | base.py:29 | Yes |
| `DB_NAME` | PostgreSQL database | base.py:97 | Yes |
| `DB_USER` | PostgreSQL username | base.py:98 | Yes |
| `DB_PASSWORD` | PostgreSQL password | base.py:99 | Yes |
| `DB_HOST` | PostgreSQL hostname | base.py:100 | Yes |
| `DB_PORT` | PostgreSQL port | base.py:101 | Yes (default: 5432) |
| `DB_SSLMODE` | PostgreSQL SSL mode | base.py:105 | Yes (default: prefer) |
| `DB_CONN_MAX_AGE` | Connection pool timeout | base.py:102 | Optional (default: 600) |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | production.py:56, tools | Yes |
| `AZURE_STORAGE_CONNECTION_STRING` | Storage connection (dev) | base.py:267, tools | Dev only |
| `AZURE_FUNCTION_BASE_URL` | Azure Functions base URL | base.py:252, tools | Yes (async tools) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights telemetry | production.py:134 | Recommended |
| `ENVIRONMENT` | Environment name (dev/prod) | production.py:21 | Yes |
| `CORS_ALLOWED_ORIGINS` | CORS origins | base.py:227 | Yes |
| `CACHE_TIMEOUT` | Cache timeout | base.py:230 | Optional |
| `SESSION_COOKIE_AGE` | Session timeout | base.py:237 | Optional |
| `MAX_UPLOAD_SIZE` | Max file upload size | base.py:241 | Optional |
| `USE_AZURE_FUNCTIONS_PDF_CONVERSION` | Enable async PDF | production.py:192 | Optional |

### ⚠️ **CONFIGURED BUT NOT ACTIVELY USED** - Review These

| Variable | Currently Set In | Status | Recommendation |
|----------|------------------|--------|----------------|
| `AZURE_STORAGE_ACCOUNT_KEY` | container-apps.bicep:218 | Using Managed Identity | **Remove** - not needed with Managed Identity |
| `AZURE_STORAGE_CONTAINER_UPLOADS` | container-apps.bicep:222 | Hardcoded in tools | **Remove** - tools use hardcoded "uploads" |
| `AZURE_STORAGE_CONTAINER_PROCESSED` | container-apps.bicep:226 | Hardcoded in tools | **Remove** - tools use hardcoded "processed" |
| `AZURE_STORAGE_CONTAINER_STATIC` | container-apps.bicep:230 | Not used | **Remove** - static files use WhiteNoise |
| `WEBSITES_PORT` | container-apps.bicep:238 | Not needed for Container Apps | **Remove** - Container Apps use targetPort |
| `GUNICORN_WORKERS` | container-apps.bicep:242 | Not read by code | **Keep** - used in Dockerfile CMD |
| `GUNICORN_THREADS` | container-apps.bicep:246 | Not read by code | **Keep** - used in Dockerfile CMD |
| `GUNICORN_TIMEOUT` | container-apps.bicep:250 | Not read by code | **Keep** - used in Dockerfile CMD |

### ❌ **DEPRECATED / NOT USED** - Remove These

| Variable | Currently Set In | Reason to Remove |
|----------|------------------|------------------|
| `KEY_VAULT_ENABLED` | production.py:71 | Not actively used | Code always tries DefaultAzureCredential |
| `KEY_VAULT_NAME` | production.py:72 | Not actively used | Using secretRef in Container Apps |
| `REDIS_URL` | development.py:27 | No Redis integration | Database cache is used instead |
| `EMAIL_HOST` | production.py:198 | Email not implemented | No email functionality |
| `EMAIL_PORT` | production.py:199 | Email not implemented | No email functionality |
| `EMAIL_HOST_USER` | production.py:201 | Email not implemented | No email functionality |
| `EMAIL_HOST_PASSWORD` | production.py:202 | Email not implemented | No email functionality |
| `DEFAULT_FROM_EMAIL` | production.py:203 | Email not implemented | No email functionality |
| `ADMIN_EMAIL` | production.py:207 | Email not implemented | No email functionality |

### 🔄 **DUPLICATED** - Consolidate These

| Variable | Issue | Recommendation |
|----------|-------|----------------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Set twice in container-apps.bicep (lines 218 & 270) | **Remove duplicate** on line 270 |

---

## Recommendations Summary

### **Immediate Actions** - Remove Unused Variables

#### From `infra/modules/function-app.bicep`:
```bicep
# REMOVE these lines (130-148):
- APPINSIGHTS_INSTRUMENTATIONKEY
- ApplicationInsightsAgent_EXTENSION_VERSION
- XDT_MicrosoftApplicationInsights_Mode
- InstrumentationEngine_EXTENSION_VERSION
- APPLICATIONINSIGHTS_ENABLE_AGENT
- APPLICATIONINSIGHTS_SAMPLING_PERCENTAGE
```

#### From `infra/modules/container-apps.bicep`:
```bicep
# REMOVE these environment variables:
- AZURE_STORAGE_ACCOUNT_KEY (line 218 - using Managed Identity)
- AZURE_STORAGE_CONTAINER_UPLOADS (line 222 - hardcoded)
- AZURE_STORAGE_CONTAINER_PROCESSED (line 226 - hardcoded)
- AZURE_STORAGE_CONTAINER_STATIC (line 230 - not used)
- WEBSITES_PORT (line 238 - not needed for Container Apps)
- Duplicate AZURE_STORAGE_ACCOUNT_NAME (line 270)
```

#### From `magictoolbox/settings/production.py`:
```python
# REMOVE these config variables:
- KEY_VAULT_ENABLED (line 71)
- KEY_VAULT_NAME (line 72)
- All email configuration (lines 198-207)
```

#### From `magictoolbox/settings/development.py`:
```python
# REMOVE this check:
- REDIS_URL check (line 27)
```

### **Keep But Document** - These Are Used

#### Gunicorn Variables
These are **not read by Python code** but are **used in Dockerfile CMD**:
- `GUNICORN_WORKERS`
- `GUNICORN_THREADS`
- `GUNICORN_TIMEOUT`

**Action**: Add comment in Bicep explaining they're for Gunicorn startup.

---

## Variable Counts

### Azure Functions
- **Active**: 10 variables
- **Remove**: 6 variables (Application Insights redundancy)
- **Reduction**: 37.5%

### Container Apps
- **Active**: 20 variables
- **Remove**: 15 variables (duplicates, unused features, deprecated)
- **Keep but unused in Python**: 3 variables (Gunicorn config)
- **Reduction**: 42.9%

### Total Cleanup
- **Before**: 41 environment variables
- **After**: 23 environment variables
- **Removed**: 18 variables (43.9% reduction)

---

## Implementation Checklist

- [ ] Remove 6 Application Insights variables from `function-app.bicep`
- [ ] Remove 6 storage/web variables from `container-apps.bicep`
- [ ] Remove duplicate `AZURE_STORAGE_ACCOUNT_NAME` from `container-apps.bicep`
- [ ] Remove Key Vault config from `production.py`
- [ ] Remove all email configuration from `production.py`
- [ ] Remove Redis check from `development.py`
- [ ] Add comments for Gunicorn variables in `container-apps.bicep`
- [ ] Test deployment after cleanup
- [ ] Update documentation to reflect cleaned variables

---

## Notes

1. **Managed Identity**: We're using Managed Identity for all Azure service auth, so connection strings and keys are not needed in production
2. **Container Naming**: Tools hardcode container names ("uploads", "processed", "temp"), so environment variables for these are redundant
3. **Email**: No email functionality is implemented, so all email config can be removed
4. **Redis**: Using database-backed cache, not Redis
5. **Key Vault**: Using Container Apps secret references directly, not the Django Key Vault integration code
6. **Application Insights**: Only connection string is needed; other settings are for .NET apps

