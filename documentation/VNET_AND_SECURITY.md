# Virtual Network and Security Configuration

**Last Updated:** December 23, 2025  
**Status:** ✅ Production-ready with private endpoints and VNet integration

## Overview

MagicToolbox uses a comprehensive security architecture with:
- **Virtual Network integration** for Container Apps and Function Apps
- **Private endpoints** for all Azure PaaS services
- **Managed identities** for keyless authentication
- **RBAC** for fine-grained access control
- **Key Vault** for secrets management (private endpoint only)

## Network Architecture

### Virtual Network: `vnet-westeurope-magictoolbox-dev-01`
**Address Space:** `10.0.0.0/16`

#### Subnets

| Subnet | CIDR | Purpose | Delegation |
|--------|------|---------|------------|
| `snet-container-apps` | `10.0.0.0/23` (512 IPs) | Container Apps Environment | Auto-delegated by Container Apps |
| `snet-private-endpoints` | `10.0.2.0/24` (256 IPs) | Private endpoints for all PaaS services | None |
| `snet-function-apps` | `10.0.3.0/24` (256 IPs) | Function App VNet integration | `Microsoft.Web/serverFarms` |

## Private Endpoints

All Azure PaaS services are accessed through private endpoints in the `snet-private-endpoints` subnet:

| Service | Private Endpoint Name | Internal IP | DNS Zone |
|---------|----------------------|-------------|----------|
| Storage Account (Blob) | `pe-westeurope-magictoolbox-dev-blob-01` | 10.0.2.x | `privatelink.blob.core.windows.net` |
| Key Vault | `pe-westeurope-magictoolbox-dev-kv-01` | 10.0.2.x | `privatelink.vaultcore.azure.net` |
| PostgreSQL | `pe-westeurope-magictoolbox-dev-psql-01` | 10.0.2.x | `privatelink.postgres.database.azure.com` |
| Redis Cache | `pe-westeurope-magictoolbox-dev-redis-01` | 10.0.2.x | `privatelink.redis.cache.windows.net` |
| Container Registry | `pe-westeurope-magictoolbox-dev-acr-01` | 10.0.2.x | `privatelink.azurecr.io` |

### Benefits of Private Endpoints
- ✅ **No public internet exposure** for sensitive services
- ✅ **Traffic stays within Azure backbone** network
- ✅ **Private DNS resolution** for seamless connectivity
- ✅ **Enhanced security** with network segmentation

## Security Configuration

### 1. Storage Account
- **Public Network Access:** Enabled (required for Azure services)
- **Default Action:** Deny all
- **Bypass:** Azure Services
- **Shared Key Access:** Disabled (uses managed identity only)
- **IP Rules:** None (removed temporary testing rules)
- **Access Method:** Managed Identity with RBAC roles

### 2. Key Vault
- **Public Network Access:** **Disabled** (private endpoint only)
- **Default Action:** Deny all
- **Bypass:** Azure Services
- **IP Rules:** None
- **Access Method:** RBAC (Key Vault Secrets User role)

### 3. PostgreSQL Flexible Server
- **Public Network Access:** Enabled
- **Firewall Rules:** AllowAzureServices (0.0.0.0-0.0.0.0)
- **SSL Mode:** Required
- **Database Name:** `magictoolbox` (not `magictoolbox_dev`)
- **Access Method:** Username/password from Key Vault

### 4. Redis Cache
- **Public Network Access:** Enabled
- **Access Method:** Access key from Key Vault
- **TLS:** Enabled (minimum TLS 1.2)

### 5. Container Registry
- **Public Network Access:** Enabled
- **Access Method:** Managed identity with AcrPull role

## VNet Integration

### Container Apps
- **Subnet:** `snet-container-apps` (10.0.0.0/23)
- **Integration Type:** Internal only (workload profiles)
- **Outbound:** All traffic routes through VNet
- **Managed Identity:** System-assigned
- **RBAC Roles:**
  - Storage Blob Data Contributor
  - AcrPull
  - Key Vault Secrets User

### Function App
- **Subnet:** `snet-function-apps` (10.0.3.0/24)
- **Integration Type:** VNet integration with delegation
- **Setting:** `WEBSITE_VNET_ROUTE_ALL=1` (all traffic through VNet)
- **Managed Identity:** System-assigned
- **RBAC Roles:**
  - Storage Blob Data Contributor
  - Storage Queue Data Contributor
  - Storage Table Data Contributor
  - Storage File Data Privileged Contributor
  - Key Vault Secrets User

## Authentication Flow

### Container App → Storage Account
1. Container App uses system-assigned managed identity
2. Requests token for storage resource
3. Azure AD validates identity
4. Storage Account validates token via RBAC
5. Access granted with Blob Data Contributor permissions

### Function App → Key Vault
1. Function App uses system-assigned managed identity
2. Request routes through VNet (snet-function-apps)
3. Traffic reaches Key Vault via private endpoint (10.0.2.x)
4. Key Vault validates identity via RBAC
5. Secret value returned (e.g., `DB_PASSWORD`)

### Function App → PostgreSQL
1. Function App reads `DB_PASSWORD` from Key Vault (via private endpoint)
2. Connection string constructed with credentials
3. Connection routes through VNet to PostgreSQL private endpoint
4. PostgreSQL validates credentials
5. Database connection established

## Key Vault Secret References

Environment variables can reference Key Vault secrets using this format:
```
@Microsoft.KeyVault(SecretUri=https://kvwemagictoolboxdev01.vault.azure.net/secrets/SECRET_NAME/)
```

The Azure platform automatically resolves these references using the managed identity.

### Currently Used References
- `DB_PASSWORD` in Function App (resolves to PostgreSQL password)
- Container App can also use references when `useKeyVaultReferences=true` in Bicep

## Deployed Configuration Summary

### ✅ What's Working
- Container App accesses all services via private endpoints
- Function App accesses Key Vault via private endpoint (VNet integrated)
- Function App accesses Storage via managed identity
- Function App connects to PostgreSQL using resolved password from Key Vault
- Database name is `magictoolbox` (correct)
- All temporary IP rules removed
- Key Vault is private endpoint only

### 🔒 Security Status
- ✅ No public IP access to Key Vault
- ✅ No shared key access to Storage Account
- ✅ All secrets in Key Vault
- ✅ RBAC roles properly assigned
- ✅ Managed identities for all service-to-service auth
- ✅ TLS 1.2+ enforced everywhere
- ✅ Network segmentation with subnets

### 📊 Network Traffic Flow
```
Internet → Container App Ingress (HTTPS)
  ↓
Container App (10.0.0.x)
  ↓
Private Endpoint (10.0.2.x) → Storage/PostgreSQL/Redis/Key Vault/ACR

Internet → Function App (HTTPS with function key)
  ↓
Function App (10.0.3.x via VNet integration)
  ↓
Private Endpoint (10.0.2.x) → Key Vault/Storage
  ↓
Private Endpoint (10.0.2.x) → PostgreSQL
```

## Troubleshooting

### Check VNet Integration
```bash
# Container App
az containerapp show --name <app-name> --resource-group <rg> \
  --query "properties.configuration.{vnetConfig:infrastructureSubnetId}"

# Function App
az functionapp vnet-integration list --name <func-name> --resource-group <rg>
```

### Test Private Endpoint Connectivity
```bash
# From Container App
az containerapp exec --name <app-name> --resource-group <rg> \
  --command "nslookup <service>.privatelink.azure.service"

# Function App - use diagnostic endpoint
curl "https://<func-name>.azurewebsites.net/api/db-diagnostic"
```

### Verify RBAC Roles
```bash
# Check managed identity
PRINCIPAL_ID=$(az containerapp show --name <app-name> --resource-group <rg> \
  --query "identity.principalId" -o tsv)

# List role assignments
az role assignment list --assignee $PRINCIPAL_ID -o table
```

## Best Practices

1. **Always use managed identities** - Avoid storing credentials
2. **Private endpoints for PaaS services** - Keep traffic within Azure
3. **RBAC over access keys** - Granular permissions and audit trails
4. **Key Vault for secrets** - Centralized secrets management
5. **VNet integration** - Network segmentation and security
6. **Least privilege** - Grant minimum required permissions
7. **Monitor and audit** - Use Log Analytics and Application Insights

## References

- [Azure Container Apps VNet integration](https://learn.microsoft.com/en-us/azure/container-apps/networking)
- [Azure Functions VNet integration](https://learn.microsoft.com/en-us/azure/azure-functions/functions-networking-options)
- [Azure Private Endpoints](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview)
- [Managed Identities](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)
- [Key Vault references](https://learn.microsoft.com/en-us/azure/app-service/app-service-key-vault-references)
