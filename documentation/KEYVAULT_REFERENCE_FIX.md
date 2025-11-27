# Key Vault Reference Fix

**Date**: November 27, 2025  
**Status**: ✅ Completed

## Problem Identified

The Container Apps infrastructure was storing sensitive secrets in the Container App environment configuration instead of referencing them directly from Azure Key Vault. This violated security best practices by duplicating secrets unnecessarily.

### Previous Implementation Issues

1. **Secrets duplicated**: Secrets were stored in both Key Vault AND Container Apps environment
2. **Unnecessary parameters**: Sensitive values were passed through Bicep parameters
3. **Reduced security**: Secrets visible in Container Apps configuration instead of only in Key Vault

## Solution Implemented

### Changes to `infra/modules/container-apps.bicep`

1. **Updated secret references** to use Key Vault URLs with Managed Identity:
   ```bicep
   secrets: [
     {
       name: 'django-secret-key'
       keyVaultUrl: 'https://${keyVaultName}.${az.environment().suffixes.keyvaultDns}/secrets/django-secret-key'
       identity: 'system'
     }
     // ... other secrets
   ]
   ```

2. **Removed secure parameters** that are now fetched from Key Vault:
   - `djangoSecretKey`
   - `postgresAdminPassword`
   - `redisAccessKey`
   - `storageAccountKey`
   - `applicationInsightsConnectionString`

3. **Updated environment variables** to use `secretRef` instead of direct values:
   - `DB_PASSWORD`: Now uses `secretRef: 'postgres-password'`
   - `REDIS_ACCESS_KEY`: Now uses `secretRef: 'redis-access-key'`
   - Redis URLs updated to use hostname with authentication handled separately

4. **Used `az.environment()` function** for multi-cloud compatibility instead of hardcoded `.vault.azure.net`

### Changes to `infra/main.bicep`

1. **Removed unnecessary parameters** from Container Apps module invocation:
   - `applicationInsightsConnectionString`
   - `storageAccountKey`
   - `redisAccessKey`
   - `postgresAdminPassword`
   - `djangoSecretKey`

2. **Kept required infrastructure parameters**:
   - `keyVaultName` (needed to construct Key Vault URLs)
   - `postgresAdminUsername` (non-sensitive, needed for DB connection)
   - Resource hostnames and names

## Security Improvements

### Before
```
GitHub Secrets → Bicep Parameters → Container Apps Secrets → Container
                                   ↓
                              Key Vault (redundant storage)
```

### After
```
GitHub Secrets → Bicep Parameters → Key Vault (single source of truth)
                                   ↓
Container Apps → References Key Vault via Managed Identity → Container
```

## Benefits

1. **Single Source of Truth**: Secrets stored only in Key Vault
2. **Managed Identity**: Container Apps uses system-assigned identity to access secrets
3. **No Secret Duplication**: Secrets not stored in Container Apps environment configuration
4. **Easier Rotation**: Update secrets in Key Vault without redeploying Container Apps
5. **Audit Trail**: Key Vault provides comprehensive audit logs for secret access
6. **Multi-cloud Support**: Uses `az.environment()` function for proper cloud environment handling

## RBAC Configuration

The existing RBAC configuration in `infra/modules/rbac.bicep` already grants the Container App's Managed Identity the **Key Vault Secrets User** role, which allows reading secrets from Key Vault. No changes needed.

## Deployment Notes

### First-Time Deployment
When deploying for the first time, ensure:
1. Secrets are stored in Key Vault via the KeyVault module (already configured)
2. RBAC role assignments complete before Container Apps deployment (dependency handled in main.bicep)
3. Container App's Managed Identity has sufficient permissions

### Re-deployment of Existing Environment
For existing deployments, this change will:
1. Remove secret values from Container Apps environment configuration
2. Replace with Key Vault references
3. Container Apps will fetch secrets from Key Vault at runtime

**No manual intervention required** - the deployment will handle the transition automatically.

## Validation

After deployment, verify:
1. Container Apps starts successfully
2. Application can connect to PostgreSQL (DB_PASSWORD from Key Vault)
3. Redis connection works (REDIS_ACCESS_KEY from Key Vault)
4. Storage operations succeed (AZURE_STORAGE_ACCOUNT_KEY from Key Vault)
5. Check Key Vault access logs to confirm secrets are being accessed

## Exception: ACR Password

The ACR (Azure Container Registry) password is **intentionally NOT** stored in Key Vault because:
1. It's generated during ACR module deployment
2. It's needed immediately for container image pulls
3. ACR is a service principal credential, not an application secret
4. It's passed directly from the ACR module output

## Related Documentation

- [Azure Container Apps Secrets](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets)
- [Key Vault References in Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets#reference-secret-from-key-vault)
- [Managed Identity with Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/managed-identity)

## Impact

- **Security**: ✅ Improved (single source of truth, no duplication)
- **Maintainability**: ✅ Improved (easier secret rotation)
- **Deployment**: ✅ No breaking changes
- **Runtime Performance**: ✅ No impact (secrets cached by Container Apps)
