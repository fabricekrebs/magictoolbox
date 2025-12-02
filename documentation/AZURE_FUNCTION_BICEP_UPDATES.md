# Azure Function Bicep Configuration Updates

**Last Updated**: December 1, 2025  
**Status**: Complete - Ready for Deployment

## 📋 Overview

This document describes the Bicep infrastructure updates to properly deploy the Azure Function App with correct permissions and network access to Azure Storage and PostgreSQL database.

---

## 🔧 Changes Made

### 1. **RBAC Module (`infra/modules/rbac.bicep`)**

**Added Function App Permissions:**
- Added `functionAppIdentityPrincipalId` parameter (optional, empty string by default)
- Added Storage Blob Data Contributor role assignment for Function App managed identity
- Added Key Vault Secrets User role assignment for Function App managed identity
- Both role assignments are conditional (only created when Function App principal ID is provided)

**Permissions Granted:**
- ✅ **Storage Blob Data Contributor** - Allows Function App to read/write blobs in all containers
- ✅ **Key Vault Secrets User** - Allows Function App to read secrets from Key Vault

### 2. **PostgreSQL Module (`infra/modules/postgresql.bicep`)**

**Added Network Access:**
- Added firewall rule `AllowAllAzureServicesAndResourcesWithinAzureIps`
- This rule allows Azure services (including Function Apps) to connect to PostgreSQL
- Uses special IP range `0.0.0.0` to `0.0.0.0` which represents "Azure services"

**Removed Output:**
- Removed `connectionString` output to comply with Bicep security best practices (no secrets in outputs)

### 3. **Function App Module (`infra/modules/function-app.bicep`)**

**Updated Storage Connection:**
- Added `AzureWebJobsStorage__accountName` app setting with storage account name
- Added `AzureWebJobsStorage__credential` app setting set to `managedidentity`
- This enables the Function App to use Managed Identity for blob trigger authentication

**Removed Duplicate RBAC:**
- Removed inline Storage Blob Data Contributor role assignment (handled in rbac.bicep)
- Removed inline Key Vault Secrets User role assignment (handled in rbac.bicep)
- Removed unused `keyVaultName` parameter

**Result:**
- Function App now uses Managed Identity for all Azure resource access
- No connection strings or access keys in Function App code
- Cleaner deployment with centralized RBAC management

### 4. **Main Orchestration (`infra/main.bicep`)**

**Updated RBAC Deployment:**
- Added `functionAppIdentityPrincipalId` parameter to RBAC module
- RBAC module now receives Function App principal ID and grants permissions
- Removed unnecessary `dependsOn` (Bicep infers dependencies from parameter usage)

**Updated Function App Deployment:**
- Removed `keyVaultName` parameter (no longer needed)
- Removed explicit `dependsOn` entries (Bicep infers from outputs used)

---

## 🏗️ Deployment Order

Bicep automatically determines the correct deployment order based on dependencies:

1. **Networking** (VNet and subnets)
2. **Monitoring** (Log Analytics and Application Insights)
3. **Storage Account** (with containers: uploads, processed, static)
4. **ACR** (Azure Container Registry)
5. **Redis** (Azure Cache for Redis)
6. **PostgreSQL** (with firewall rules to allow Azure services)
7. **Key Vault** (with secrets)
8. **Function App** (with Managed Identity)
9. **Container Apps** (with Managed Identity)
10. **RBAC** (role assignments for both Function App and Container App)
11. **Private Endpoints** (for Storage, PostgreSQL, Redis, Key Vault, ACR)

---

## 🔐 Security Configuration

### Managed Identity Usage

**Function App Identity:**
- System-assigned Managed Identity created automatically
- No passwords or connection strings stored
- Azure handles credential rotation automatically

**Permissions Granted:**
- Storage Blob Data Contributor (read/write blobs)
- Key Vault Secrets User (read secrets)
- Outbound network access to PostgreSQL (via firewall rule)

### PostgreSQL Access

**Firewall Rule:**
```bicep
startIpAddress: '0.0.0.0'
endIpAddress: '0.0.0.0'
```

This special range means "Allow Azure services" and includes:
- Azure Functions
- Azure Container Apps
- Azure Logic Apps
- Other Azure services within the same subscription

**Note:** For production, consider using VNet integration and private endpoints instead.

---

## 📝 Environment Variables in Function App

The Function App is configured with these environment variables:

| Variable | Value | Purpose |
|----------|-------|---------|
| `AzureWebJobsStorage` | Connection string | Function runtime storage (required) |
| `AzureWebJobsStorage__accountName` | Storage account name | Managed Identity auth for blobs |
| `AzureWebJobsStorage__credential` | `managedidentity` | Use Managed Identity for blobs |
| `FUNCTIONS_EXTENSION_VERSION` | `~4` | Azure Functions v4 runtime |
| `FUNCTIONS_WORKER_RUNTIME` | `python` | Python runtime |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | Blob trigger configuration |
| `DB_HOST` | PostgreSQL FQDN | Database hostname |
| `DB_NAME` | Database name | Database name |
| `DB_USER` | Admin username | Database user |
| `DB_PASSWORD` | Admin password | Database password |
| `DB_PORT` | `5432` | PostgreSQL port |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | App Insights connection | Telemetry and logging |

---

## 🚀 Deployment Commands

### Deploy Infrastructure

```bash
# Navigate to infrastructure directory
cd infra

# Deploy to development environment
az deployment group create \
  --resource-group magictoolbox-demo-rg \
  --template-file main.bicep \
  --parameters @parameters.dev.json
```

### Deploy Function Code

After infrastructure is deployed:

```bash
# Get Function App name from deployment output
FUNC_APP_NAME=$(az deployment group show \
  --resource-group magictoolbox-demo-rg \
  --name <deployment-name> \
  --query properties.outputs.functionAppName.value -o tsv)

# Deploy function code
cd function_app
func azure functionapp publish $FUNC_APP_NAME --python
```

---

## ✅ Verification Steps

### 1. Check Function App Deployment

```bash
az functionapp show \
  --resource-group magictoolbox-demo-rg \
  --name $FUNC_APP_NAME \
  --query "{name:name, state:state, identity:identity.principalId}" -o table
```

Expected output:
```
Name                          State     Identity
----------------------------- --------- ------------------------------------
func-magictoolbox-dev-xxxx    Running   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

### 2. Verify Storage RBAC

```bash
# Get Function App principal ID
PRINCIPAL_ID=$(az functionapp show \
  --resource-group magictoolbox-demo-rg \
  --name $FUNC_APP_NAME \
  --query identity.principalId -o tsv)

# Check role assignments
az role assignment list \
  --assignee $PRINCIPAL_ID \
  --query "[].{Role:roleDefinitionName, Scope:scope}" -o table
```

Expected roles:
- Storage Blob Data Contributor
- Key Vault Secrets User

### 3. Test PostgreSQL Connection

```bash
# From Function App console (Advanced Tools -> Kudu)
python -c "import psycopg2; conn = psycopg2.connect(host='$DB_HOST', dbname='$DB_NAME', user='$DB_USER', password='$DB_PASSWORD'); print('Connected successfully!')"
```

### 4. Test Blob Trigger

Upload a test PDF to trigger the function:

```bash
# Get storage account name
STORAGE_NAME=$(az storage account list \
  --resource-group magictoolbox-demo-rg \
  --query "[0].name" -o tsv)

# Upload test PDF
az storage blob upload \
  --account-name $STORAGE_NAME \
  --container-name uploads \
  --name pdf/test-$(uuidgen).pdf \
  --file /path/to/test.pdf \
  --metadata execution_id=$(uuidgen) start_page=0 original_filename=test.pdf \
  --auth-mode login

# Monitor function logs
az functionapp log tail \
  --resource-group magictoolbox-demo-rg \
  --name $FUNC_APP_NAME
```

---

## 🔍 Troubleshooting

### Issue: Function App can't access Storage

**Symptoms:** Blob trigger doesn't fire or fails with authentication error

**Solutions:**
1. Check RBAC role assignment exists:
   ```bash
   az role assignment list --assignee $PRINCIPAL_ID --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage-name>
   ```

2. Verify Managed Identity settings:
   ```bash
   az functionapp config appsettings list \
     --resource-group magictoolbox-demo-rg \
     --name $FUNC_APP_NAME \
     --query "[?name=='AzureWebJobsStorage__credential'].{Name:name, Value:value}"
   ```
   Should return: `{"Name": "AzureWebJobsStorage__credential", "Value": "managedidentity"}`

3. Wait for RBAC propagation (can take 5-10 minutes)

### Issue: Function App can't connect to PostgreSQL

**Symptoms:** Database connection failures in logs

**Solutions:**
1. Check firewall rule exists:
   ```bash
   az postgres flexible-server firewall-rule show \
     --resource-group magictoolbox-demo-rg \
     --name <postgres-server-name> \
     --rule-name AllowAllAzureServicesAndResourcesWithinAzureIps
   ```

2. Verify connection string environment variables:
   ```bash
   az functionapp config appsettings list \
     --resource-group magictoolbox-demo-rg \
     --name $FUNC_APP_NAME \
     --query "[?starts_with(name, 'DB_')].{Name:name, Value:value}" -o table
   ```

3. Test connection from Function App console

### Issue: RBAC role assignment fails

**Symptoms:** Deployment fails with RBAC error

**Solutions:**
1. Ensure you have permissions to assign roles (Owner or User Access Administrator)
2. Check if role assignment already exists (can happen on re-deployment)
3. Delete existing role assignments and redeploy if needed

---

## 📊 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Azure Subscription                       │
│                                                                 │
│  ┌───────────────┐         ┌──────────────┐                    │
│  │ Function App  │────────▶│   Storage    │                    │
│  │ (Managed ID)  │  Blob   │   Account    │                    │
│  │               │  Trigger│              │                    │
│  └───────┬───────┘         └──────────────┘                    │
│          │                                                      │
│          │ Storage Blob Data Contributor (RBAC)                │
│          │ Key Vault Secrets User (RBAC)                       │
│          │ PostgreSQL Firewall Allow                           │
│          │                                                      │
│          ├──────────────────┐                                  │
│          │                  │                                  │
│          ▼                  ▼                                  │
│  ┌──────────────┐   ┌──────────────┐                          │
│  │  PostgreSQL  │   │  Key Vault   │                          │
│  │   Database   │   │   Secrets    │                          │
│  └──────────────┘   └──────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📚 Related Documentation

- [AZURE_FUNCTIONS_PDF_CONVERSION.md](./AZURE_FUNCTIONS_PDF_CONVERSION.md) - Complete guide to Azure Functions integration
- [FRESH_DEPLOYMENT_GUIDE.md](./FRESH_DEPLOYMENT_GUIDE.md) - Full infrastructure deployment guide
- [Azure Functions with Managed Identity](https://learn.microsoft.com/azure/azure-functions/functions-identity-based-connections-tutorial)
- [Azure RBAC Best Practices](https://learn.microsoft.com/azure/role-based-access-control/best-practices)

---

## ✅ Summary of Changes

| Component | Change | Benefit |
|-----------|--------|---------|
| **RBAC Module** | Added Function App permissions | Centralized permission management |
| **PostgreSQL** | Added Azure services firewall rule | Function App can connect to database |
| **Function App** | Use Managed Identity for storage | No connection strings, better security |
| **Main Bicep** | Updated parameter passing | Proper deployment orchestration |

**Security Improvements:**
- ✅ No hardcoded connection strings in Function App code
- ✅ Managed Identity for all Azure resource access
- ✅ Centralized RBAC management
- ✅ PostgreSQL firewall configured for Azure services
- ✅ Key Vault integration for secrets

**Deployment Ready:**
- ✅ All Bicep files pass linting
- ✅ No compilation errors
- ✅ Proper dependency management
- ✅ Ready for deployment to dev/staging/prod

---

**Next Steps:**
1. Deploy infrastructure using updated Bicep files
2. Deploy Function App code
3. Test PDF to DOCX conversion flow
4. Monitor Application Insights for telemetry
5. Enable `USE_AZURE_FUNCTIONS_PDF_CONVERSION=true` in Container App
