# Private Endpoints Migration Guide

## Overview

This guide covers the migration from public network access to private endpoints for all Azure resources in the MagicToolbox infrastructure.

## What Changed

### Network Architecture

**Before:**
- All services (ACR, PostgreSQL, Redis, Storage, Key Vault) were accessible via public endpoints
- Network security relied on firewall rules and Azure service tags
- Container Apps communicated with services over the public internet

**After:**
- Virtual Network (VNet) with dedicated subnets for Container Apps and private endpoints
- All services use private endpoints for secure, internal communication
- Public network access disabled for ACR, PostgreSQL, Redis, Storage, and Key Vault
- Container Apps integrated with VNet for private connectivity

### Infrastructure Components

#### New Resources

1. **Virtual Network (`network.bicep`)**
   - Address space: `10.0.0.0/16`
   - Subnet for Container Apps: `10.0.0.0/23` (512 IPs) - delegated to `Microsoft.App/environments`
   - Subnet for Private Endpoints: `10.0.2.0/24` (256 IPs)

2. **Private Endpoints (`private-endpoints.bicep`)**
   - ACR private endpoint with DNS zone `privatelink.azurecr.io`
   - PostgreSQL private endpoint with DNS zone `privatelink.postgres.database.azure.com`
   - Redis private endpoint with DNS zone `privatelink.redis.cache.windows.net`
   - Storage Blob private endpoint with DNS zone `privatelink.blob.core.windows.net`
   - Key Vault private endpoint with DNS zone `privatelink.vaultcore.azure.net`

#### Modified Resources

1. **Azure Container Registry**
   - `publicNetworkAccess: 'Disabled'`
   - Accessible only via private endpoint

2. **PostgreSQL Flexible Server**
   - Public network access disabled via network configuration
   - Firewall rules removed (not needed with private endpoints)

3. **Azure Cache for Redis**
   - `publicNetworkAccess: 'Disabled'`
   - Accessible only via private endpoint

4. **Azure Storage Account**
   - `defaultAction: 'Deny'` in network ACLs
   - Accessible only via private endpoint

5. **Azure Key Vault**
   - `publicNetworkAccess: 'Disabled'`
   - `defaultAction: 'Deny'` in network ACLs
   - Accessible only via private endpoint

6. **Container Apps Environment**
   - VNet integration with `infrastructureSubnetId`
   - `internal: false` (allows external ingress, but services are private)

## Deployment Order

The infrastructure deployment follows this sequence:

1. **Virtual Network** - Creates VNet and subnets
2. **Monitoring** - Log Analytics and Application Insights
3. **Services** (parallel):
   - Azure Container Registry (with private access disabled)
   - Azure Storage Account (with network ACLs set to Deny)
   - Azure Cache for Redis (with public access disabled)
   - Azure Database for PostgreSQL (with public access disabled)
4. **Key Vault** - Stores secrets (with public access disabled)
5. **Container Apps** - With VNet integration
6. **Private Endpoints** - Creates private endpoints and DNS zones
7. **RBAC** - Role assignments for Managed Identity

## Benefits

### Security
- ✅ All traffic stays within Azure backbone network
- ✅ No exposure to public internet for backend services
- ✅ Network isolation at VNet level
- ✅ Private DNS resolution prevents DNS hijacking

### Performance
- ✅ Reduced latency with private network paths
- ✅ No NAT gateway or public IP overhead
- ✅ Direct connectivity within Azure region

### Compliance
- ✅ Meets requirements for private connectivity
- ✅ Network traffic audit trail via Azure Monitor
- ✅ PCI-DSS, HIPAA, and other compliance frameworks supported

## Migration Steps

### Prerequisites

- Existing deployment with public endpoints
- Azure CLI or Azure Portal access
- Permissions to create VNet and private endpoints

### Step 1: Update Infrastructure Code

All changes are already in the Bicep templates:
- `infra/modules/network.bicep` (new)
- `infra/modules/private-endpoints.bicep` (new)
- `infra/modules/acr.bicep` (modified)
- `infra/modules/postgresql.bicep` (modified)
- `infra/modules/redis.bicep` (modified)
- `infra/modules/storage.bicep` (modified)
- `infra/modules/keyvault.bicep` (modified)
- `infra/modules/container-apps.bicep` (modified)
- `infra/main.bicep` (modified)

### Step 2: Deploy Infrastructure

**Option A: Fresh Deployment**
```bash
# Set variables
RESOURCE_GROUP="rg-westeurope-magictoolbox-dev-01"
LOCATION="westeurope"
ENVIRONMENT="dev"
APP_NAME="magictoolbox"

# Deploy infrastructure (two-phase approach for Key Vault)
# Phase 1: Deploy with direct secrets
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters environment=$ENVIRONMENT \
               appName=$APP_NAME \
               postgresAdminUsername="<admin-username>" \
               postgresAdminPassword="<secure-password>" \
               djangoSecretKey="<django-secret>" \
               useKeyVaultReferences=false

# Wait 60 seconds for RBAC propagation
sleep 60

# Phase 2: Deploy with Key Vault references
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters environment=$ENVIRONMENT \
               appName=$APP_NAME \
               postgresAdminUsername="<admin-username>" \
               postgresAdminPassword="<secure-password>" \
               djangoSecretKey="<django-secret>" \
               useKeyVaultReferences=true
```

**Option B: Update Existing Deployment**

⚠️ **Warning**: This will cause temporary downtime during VNet integration and private endpoint creation.

```bash
# Deploy infrastructure update
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters environment=$ENVIRONMENT \
               appName=$APP_NAME \
               postgresAdminUsername="<admin-username>" \
               postgresAdminPassword="<secure-password>" \
               djangoSecretKey="<django-secret>" \
               useKeyVaultReferences=true
```

### Step 3: Verify Private Connectivity

```bash
# Check VNet
az network vnet show \
  --resource-group $RESOURCE_GROUP \
  --name vnet-westeurope-${APP_NAME}-${ENVIRONMENT}-01

# Check private endpoints
az network private-endpoint list \
  --resource-group $RESOURCE_GROUP \
  --output table

# Check private DNS zones
az network private-dns zone list \
  --resource-group $RESOURCE_GROUP \
  --output table

# Verify Container App is healthy
CONTAINER_APP_NAME="app-we-${APP_NAME}-${ENVIRONMENT}-01"
az containerapp show \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_APP_NAME \
  --query "properties.runningStatus"
```

### Step 4: Test Application

```bash
# Get Container App URL
CONTAINER_APP_URL=$(az containerapp show \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_APP_NAME \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv)

# Test health endpoint
curl -I https://$CONTAINER_APP_URL/api/health/

# Test homepage
curl -I https://$CONTAINER_APP_URL/
```

### Step 5: Monitor Logs

```bash
# Stream Container App logs
az containerapp logs show \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_APP_NAME \
  --follow

# Check for connection errors
az containerapp logs show \
  --resource-group $RESOURCE_GROUP \
  --name $CONTAINER_APP_NAME \
  --tail 100 | grep -E "connection|error|failed"
```

## Troubleshooting

### Issue: Container App Cannot Connect to Services

**Symptoms:**
- Connection timeouts to PostgreSQL, Redis, or Storage
- Errors like "connection refused" or "name resolution failed"

**Resolution:**
1. Verify private endpoints are created:
   ```bash
   az network private-endpoint list --resource-group $RESOURCE_GROUP --output table
   ```

2. Check private DNS zone links:
   ```bash
   az network private-dns link vnet list \
     --resource-group $RESOURCE_GROUP \
     --zone-name privatelink.postgres.database.azure.com \
     --output table
   ```

3. Verify Container Apps VNet integration:
   ```bash
   az containerapp env show \
     --resource-group $RESOURCE_GROUP \
     --name env-we-${APP_NAME}-${ENVIRONMENT}-01 \
     --query "properties.vnetConfiguration"
   ```

### Issue: ACR Pull Fails

**Symptoms:**
- Container App cannot pull images from ACR
- "unauthorized" or "connection refused" errors

**Resolution:**
1. Verify ACR private endpoint:
   ```bash
   az network private-endpoint show \
     --resource-group $RESOURCE_GROUP \
     --name pe-westeurope-${APP_NAME}-${ENVIRONMENT}-acr-01
   ```

2. Check Container App Managed Identity has AcrPull permission:
   ```bash
   az role assignment list \
     --assignee <managed-identity-principal-id> \
     --scope <acr-resource-id>
   ```

3. Test ACR connectivity from Container App:
   ```bash
   az containerapp exec \
     --resource-group $RESOURCE_GROUP \
     --name $CONTAINER_APP_NAME \
     --command "nslookup <acr-name>.azurecr.io"
   ```

### Issue: Key Vault Access Denied

**Symptoms:**
- Container App cannot read secrets from Key Vault
- "403 Forbidden" errors when accessing Key Vault references

**Resolution:**
1. Verify Key Vault private endpoint:
   ```bash
   az network private-endpoint show \
     --resource-group $RESOURCE_GROUP \
     --name pe-westeurope-${APP_NAME}-${ENVIRONMENT}-kv-01
   ```

2. Check Managed Identity has Key Vault Secrets User role:
   ```bash
   az role assignment list \
     --assignee <managed-identity-principal-id> \
     --scope <keyvault-resource-id>
   ```

3. Ensure RBAC has propagated (wait 60 seconds after role assignment)

### Issue: DNS Resolution Fails

**Symptoms:**
- Services resolving to public IPs instead of private IPs
- Intermittent connection issues

**Resolution:**
1. Verify private DNS zone groups are configured:
   ```bash
   az network private-endpoint dns-zone-group list \
     --resource-group $RESOURCE_GROUP \
     --endpoint-name pe-westeurope-${APP_NAME}-${ENVIRONMENT}-psql-01 \
     --output table
   ```

2. Check DNS records in private DNS zones:
   ```bash
   az network private-dns record-set a list \
     --resource-group $RESOURCE_GROUP \
     --zone-name privatelink.postgres.database.azure.com \
     --output table
   ```

3. Restart Container App to refresh DNS cache:
   ```bash
   az containerapp revision restart \
     --resource-group $RESOURCE_GROUP \
     --name $CONTAINER_APP_NAME \
     --revision <revision-name>
   ```

## Rollback Plan

If issues arise, you can temporarily re-enable public access:

### Quick Rollback (Manual)

```bash
# Re-enable public access for ACR
az acr update \
  --name <acr-name> \
  --resource-group $RESOURCE_GROUP \
  --public-network-enabled true

# Re-enable public access for Redis
az redis update \
  --name <redis-name> \
  --resource-group $RESOURCE_GROUP \
  --set publicNetworkAccess=Enabled

# Re-enable public access for Storage
az storage account update \
  --name <storage-name> \
  --resource-group $RESOURCE_GROUP \
  --default-action Allow

# Re-enable public access for Key Vault
az keyvault update \
  --name <keyvault-name> \
  --resource-group $RESOURCE_GROUP \
  --public-network-access Enabled \
  --default-action Allow
```

### Full Rollback (Infrastructure)

1. Revert Bicep templates to previous version
2. Redeploy infrastructure:
   ```bash
   git checkout <previous-commit>
   az deployment group create \
     --resource-group $RESOURCE_GROUP \
     --template-file infra/main.bicep \
     --parameters <parameters>
   ```

## Cost Impact

### Additional Costs

- **Virtual Network**: Free (no additional cost)
- **Private Endpoints**: ~$7.30/endpoint/month × 5 endpoints = **~$36.50/month**
- **Private DNS Zones**: ~$0.50/zone/month × 5 zones = **~$2.50/month**
- **Data Transfer**: Private endpoints use Azure backbone (no internet egress charges)

**Total Additional Monthly Cost**: ~$39/month

### Cost Savings

- Reduced data transfer charges (no internet egress)
- Potential reduction in NAT gateway costs (if previously used)

## References

- [Azure Private Endpoints Overview](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview)
- [Container Apps VNet Integration](https://learn.microsoft.com/en-us/azure/container-apps/vnet-custom)
- [Private DNS Zones](https://learn.microsoft.com/en-us/azure/dns/private-dns-overview)
- [ACR with Private Link](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-private-link)
- [PostgreSQL Private Endpoint](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-networking-private-link)
- [Redis Private Endpoint](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-private-link)
- [Storage Private Endpoints](https://learn.microsoft.com/en-us/azure/storage/common/storage-private-endpoints)
- [Key Vault Private Link](https://learn.microsoft.com/en-us/azure/key-vault/general/private-link-service)

## Next Steps

1. ✅ **Deployment Complete**: Private endpoints deployed for all services
2. ⏭️ **Monitor**: Watch for connection issues in Application Insights
3. ⏭️ **Performance**: Measure latency improvements with private connectivity
4. ⏭️ **Security Audit**: Verify no public endpoints remain exposed
5. ⏭️ **Documentation**: Update team runbooks with new architecture

---

**Last Updated**: December 1, 2025
**Author**: Infrastructure Team
**Status**: Deployed
