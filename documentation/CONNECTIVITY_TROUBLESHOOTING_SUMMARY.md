# Azure Function App Connectivity Troubleshooting Summary

## Date: December 3, 2025

## Overview
This document summarizes the comprehensive troubleshooting and resolution of connectivity issues between Azure Function Apps, Blob Storage, Key Vault, and PostgreSQL Database within a private network environment.

## Problem Statement
The Azure Function App (FlexConsumption plan) was unable to:
1. ✅ **RESOLVED**: Access Azure Blob Storage using Managed Identity
2. ✅ **RESOLVED**: Resolve Key Vault secret references for database password
3. ✅ **RESOLVED**: Connect to PostgreSQL database

## Root Causes

### Issue 1: Blob Storage Access Denied
**Symptom**: Function App couldn't initialize BlobServiceClient
```python
AttributeError: 'NoneType' object has no attribute 'rstrip'
```

**Root Cause**: 
- Function Apps subnet (snet-function-apps) lacked Microsoft.Storage service endpoint
- Storage Account network ACLs didn't include Function Apps subnet

**Solution**:
```bash
# Add Microsoft.Storage service endpoint
az network vnet subnet update \
  --name snet-function-apps \
  --vnet-name vnet-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --service-endpoints Microsoft.Storage

# Add subnet to Storage Account network rules
az storage account network-rule add \
  --account-name sawemagictoolboxdev01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --subnet /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/snet-function-apps
```

### Issue 2: Key Vault Secret Reference Not Resolving
**Symptom**: Database connection failing with password authentication error
```
FATAL: password authentication failed for user "magictoolbox"
```

**Root Cause**: 
- Function Apps subnet (snet-function-apps) lacked Microsoft.KeyVault service endpoint
- Key Vault network ACLs didn't include Function Apps subnet
- Key Vault secret references require network access to resolve, not just RBAC permissions

**Solution**:
```bash
# Add Microsoft.KeyVault service endpoint
az network vnet subnet update \
  --name snet-function-apps \
  --vnet-name vnet-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --service-endpoints Microsoft.Storage Microsoft.KeyVault

# Add subnet to Key Vault network rules
az keyvault network-rule add \
  --name kvwemagictoolboxdev01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --subnet /subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/snet-function-apps
```

## Infrastructure Code Updates

### 1. Network Module (`infra/modules/network.bicep`)
Added Microsoft.KeyVault service endpoint to Function Apps subnet:

```bicep
{
  name: 'snet-function-apps'
  properties: {
    addressPrefix: '10.0.3.0/24'
    delegations: [
      {
        name: 'delegation'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
    serviceEndpoints: [
      {
        service: 'Microsoft.Storage'
        locations: [location]
      }
      {
        service: 'Microsoft.KeyVault'
        locations: ['*']
      }
    ]
  }
}
```

### 2. Key Vault Module (`infra/modules/keyvault.bicep`)
Added Function Apps subnet to virtualNetworkRules:

```bicep
@description('Subnet ID for Function Apps to access Key Vault')
param functionAppsSubnetId string = ''

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  properties: {
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      ipRules: []
      virtualNetworkRules: !empty(functionAppsSubnetId) ? [
        {
          id: functionAppsSubnetId
          ignoreMissingVnetServiceEndpoint: false
        }
      ] : []
    }
  }
}
```

### 3. Main Template (`infra/main.bicep`)
Pass Function Apps subnet ID to Key Vault module:

```bicep
module keyVault './modules/keyvault.bicep' = {
  params: {
    functionAppsSubnetId: network.outputs.functionAppsSubnetId
  }
}
```

## Function App Code Updates

### Managed Identity Storage Client (`function_app/function_app.py`)
Updated to detect AzureWebJobsStorage__blobServiceUri format:

```python
def get_blob_service_client():
    """Get blob service client with Managed Identity support."""
    storage_connection = os.environ.get("AzureWebJobsStorage")
    storage_uri = os.environ.get("AzureWebJobsStorage__blobServiceUri")
    
    if storage_uri:
        # FlexConsumption with Managed Identity
        return BlobServiceClient(
            account_url=storage_uri.rstrip('/'),
            credential=DefaultAzureCredential()
        )
    elif storage_connection:
        # Connection string (local dev)
        return BlobServiceClient.from_connection_string(storage_connection)
    else:
        raise ValueError("No storage configuration found")
```

### HTTP Connectivity Check Endpoint
Created comprehensive validation endpoint at `/api/health/connectivity`:

**Capabilities**:
- ✅ Storage Account connectivity (write/read/delete blob)
- ✅ PostgreSQL connectivity (connect/insert/select/delete)
- ✅ Performance metrics for each operation
- ✅ Returns HTTP 200 (healthy), 207 (degraded), or 503 (unhealthy)

**Test Results** (after fixes):
```
Storage Account Connectivity:
  ✅ WRITE     : SUCCESS (157.33ms)
  ✅ READ      : SUCCESS (12.84ms)
  ✅ DELETE    : SUCCESS (18.8ms)

PostgreSQL Database Connectivity:
  ✅ CONNECT   : SUCCESS (73.27ms)
  ✅ WRITE     : SUCCESS (8.34ms)
  ✅ READ      : SUCCESS (2.92ms)
  ✅ DELETE    : SUCCESS (4.99ms)

Overall Status: ✅ HEALTHY
```

## Network Architecture

### Virtual Network: vnet-westeurope-magictoolbox-dev-01 (10.0.0.0/16)

| Subnet | Address Space | Delegation | Service Endpoints | Purpose |
|--------|---------------|------------|-------------------|---------|
| snet-container-apps | 10.0.0.0/23 | Microsoft.App/environments | Microsoft.Storage | Container Apps hosting Django |
| snet-private-endpoints | 10.0.2.0/24 | None | Microsoft.Storage | Private endpoints for services |
| snet-function-apps | 10.0.3.0/24 | Microsoft.App/environments | Microsoft.Storage, Microsoft.KeyVault | Function Apps PDF conversion |

### Azure Resources Network Configuration

**Storage Account (sawemagictoolboxdev01)**:
- Network: defaultAction "Deny", publicNetworkAccess "Disabled"
- VNet Rules: snet-container-apps, snet-function-apps
- Access: Managed Identity with Storage Blob Data Contributor role

**Key Vault (kvwemagictoolboxdev01)**:
- Network: defaultAction "Deny", publicNetworkAccess "Disabled", bypass "AzureServices"
- VNet Rules: snet-function-apps
- Private Endpoint: pe-westeurope-magictoolbox-dev-kv-01 (10.0.2.4)
- Access: RBAC with Key Vault Secrets User role for Function App

**PostgreSQL (psql-westeurope-magictoolbox-dev-01)**:
- Network: Private endpoint only
- Private Endpoint: 10.0.2.6 in snet-private-endpoints
- Firewall: AllowAllAzureServicesAndResourcesWithinAzureIps enabled
- Access: Password authentication from Key Vault secret

**Function App (func-magictoolbox-dev-rze6cb73hmijy)**:
- Plan: FlexConsumption (serverless)
- Subnet: snet-function-apps (10.0.3.0/24)
- Managed Identity: da1e662e-07d5-4f88-9289-17947993ea3a
- Role Assignments:
  - Storage Blob Data Contributor (storage account)
  - Key Vault Secrets User (key vault)

## Key Learnings

### 1. FlexConsumption Function Apps Network Requirements
FlexConsumption Function Apps require **service endpoints** on their subnet to access Azure PaaS services behind network restrictions, even with Managed Identity authentication.

### 2. Key Vault Secret References in Function Apps
Function App Key Vault references (`@Microsoft.KeyVault(SecretUri=...)`) require:
1. ✅ Managed Identity with "Key Vault Secrets User" RBAC role
2. ✅ **Network access** from Function Apps subnet to Key Vault
3. ✅ Microsoft.KeyVault service endpoint on Function Apps subnet

**Bypass "AzureServices" alone is NOT sufficient** - explicit VNet rules are required for FlexConsumption apps.

### 3. Storage Authentication Formats
FlexConsumption Function Apps use different storage config format:
- **Connection String**: `AzureWebJobsStorage=DefaultEndpointsProtocol=https;...`
- **Managed Identity**: `AzureWebJobsStorage__blobServiceUri=https://{account}.blob.core.windows.net/`

The double underscore (`__`) syntax is specific to Azure Functions configuration binding.

### 4. Debugging Private Network Issues
Always check in this order:
1. **Service endpoints** on source subnet
2. **Network ACLs** on target resource (virtualNetworkRules)
3. **RBAC permissions** (Managed Identity role assignments)
4. **Private endpoints** status and DNS resolution

## Testing and Validation

### Test Script: `scripts/testing/test_connectivity_check.py`
Comprehensive test script that validates:
- HTTP endpoint accessibility
- Storage operations (write/read/delete)
- Database operations (connect/insert/select/delete)
- Response time metrics
- Overall system health status

**Usage**:
```bash
source .venv/bin/activate
python scripts/testing/test_connectivity_check.py
```

**Output**: Formatted console display + JSON file with full response

## Deployment Status

### Manual Azure CLI Fixes Applied
1. ✅ Added Microsoft.Storage service endpoint to snet-function-apps
2. ✅ Added snet-function-apps to Storage Account VNet rules
3. ✅ Added Microsoft.KeyVault service endpoint to snet-function-apps
4. ✅ Added snet-function-apps to Key Vault VNet rules
5. ✅ Restarted Function App to refresh connections

### Infrastructure as Code Updated
1. ✅ `infra/modules/network.bicep` - Added Microsoft.KeyVault service endpoint
2. ✅ `infra/modules/keyvault.bicep` - Added functionAppsSubnetId parameter and VNet rules
3. ✅ `infra/main.bicep` - Pass functionAppsSubnetId to keyvault module

### GitHub Deployment
- Commit: `54ce152` - "fix: Add Microsoft.KeyVault service endpoint to Function Apps subnet"
- Branch: `develop`
- Status: Pushed to remote

**Next Step**: Deploy infrastructure to apply Bicep changes to production environment.

## Remaining Work

### 1. Test End-to-End PDF Conversion Workflow
- Upload PDF through Container App API
- Verify Function App blob trigger fires
- Confirm PDF to DOCX conversion completes
- Validate database status updates

**Blocker**: Container App API requires authentication (401 Unauthorized)
**Resolution Needed**: Create test user or authentication bypass for testing

### 2. Infrastructure Deployment
Deploy updated Bicep templates to ensure all manual fixes are codified:

```bash
# Deploy infrastructure
az deployment group create \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --template-file infra/main.bicep \
  --parameters @infra/main.parameters.json
```

### 3. Documentation Updates
- Document authentication setup for API testing
- Create end-to-end testing guide
- Update deployment verification checklist

## References

### Azure Documentation
- [Azure Functions networking options](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)
- [Virtual Network service endpoints](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-network-service-endpoints-overview)
- [Key Vault network security](https://learn.microsoft.com/en-us/azure/key-vault/general/network-security)
- [Storage account network rules](https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security)

### Related Documentation
- [AZURE_DEPLOYMENT_README.md](./AZURE_DEPLOYMENT_README.md) - Deployment procedures
- [VNET_AND_SECURITY.md](./VNET_AND_SECURITY.md) - Network architecture
- [DEPLOYMENT_VERIFICATION.md](./DEPLOYMENT_VERIFICATION.md) - Verification checklist

---

**Last Updated**: December 3, 2025  
**Author**: GitHub Copilot  
**Status**: Connectivity issues resolved, infrastructure code updated, end-to-end testing pending
