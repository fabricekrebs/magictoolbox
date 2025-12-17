# Redis Resource Cleanup Guide for Azure

## Overview

After removing Redis from the infrastructure code, the existing Redis resources in Azure need to be manually deleted. This guide provides the commands to clean up Redis resources from both development and production environments.

## Current State

### Development Environment
- **Subscription**: `fec3a155-e384-43cd-abc7-9c20391a3fd4` (ME-MngEnvMCAP380572-fabricekrebs-1)
- **Resource Group**: `rg-westeurope-magictoolbox-dev-01`
- **Redis Cache**: `red-westeurope-magictoolbox-dev-01` (Basic SKU, West Europe)
- **Private Endpoint**: `pe-westeurope-magictoolbox-dev-redis-01`

### Production Environment
- **Subscription**: `b83b5bd5-c04f-4965-bb3d-89ffdb75cbcc` (Visual Studio Enterprise)
- **Resource Group**: `rg-italynorth-magictoolbox-prod-01`
- **Redis Cache**: `red-italynorth-magictoolbox-prod-01` (Basic SKU, Italy North)
- **Private Endpoint**: None (deployment may not have completed)

## Manual Deletion Steps

### Option 1: Azure Portal (Recommended for Visual Confirmation)

#### Development Environment
1. Navigate to Azure Portal: https://portal.azure.com
2. Switch to subscription: **ME-MngEnvMCAP380572-fabricekrebs-1**
3. Go to resource group: **rg-westeurope-magictoolbox-dev-01**
4. Delete resources in this order:
   - **Private Endpoint**: `pe-westeurope-magictoolbox-dev-redis-01`
     - Click → Delete → Confirm
     - Wait 1-2 minutes for deletion
   - **Redis Cache**: `red-westeurope-magictoolbox-dev-01`
     - Click → Delete → Type resource name to confirm
     - Wait 5-10 minutes for deletion (Redis takes time)

#### Production Environment
1. Switch to subscription: **Visual Studio Enterprise Subscription**
2. Go to resource group: **rg-italynorth-magictoolbox-prod-01**
3. Delete resources:
   - Check for any Redis private endpoint (name contains "redis")
   - **Redis Cache**: `red-italynorth-magictoolbox-prod-01`
     - Click → Delete → Type resource name to confirm
     - Wait 5-10 minutes

### Option 2: Azure CLI (Automated)

#### Development Environment

```bash
# Set subscription
az account set --subscription fec3a155-e384-43cd-abc7-9c20391a3fd4

# Delete private endpoint (fast)
az network private-endpoint delete \
  --name pe-westeurope-magictoolbox-dev-redis-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01

# Delete Redis cache (takes 5-10 minutes)
az redis delete \
  --name red-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01
```

#### Production Environment

```bash
# Set subscription
az account set --subscription b83b5bd5-c04f-4965-bb3d-89ffdb75cbcc

# Check for and delete private endpoint if exists
PROD_PE=$(az network private-endpoint list \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --query "[?contains(name, 'redis')].name" -o tsv)

if [ -n "$PROD_PE" ]; then
  az network private-endpoint delete \
    --name "$PROD_PE" \
    --resource-group rg-italynorth-magictoolbox-prod-01
fi

# Delete Redis cache
az redis delete \
  --name red-italynorth-magictoolbox-prod-01 \
  --resource-group rg-italynorth-magictoolbox-prod-01
```

### Option 3: All-in-One Cleanup Script

```bash
#!/bin/bash
set -e

echo "🧹 Cleaning up Redis resources from all environments..."
echo ""

# Development
echo "📍 Development Environment"
az account set --subscription fec3a155-e384-43cd-abc7-9c20391a3fd4

echo "  Deleting private endpoint..."
az network private-endpoint delete \
  --name pe-westeurope-magictoolbox-dev-redis-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  2>/dev/null || echo "  ⚠️ Already deleted"

echo "  Deleting Redis cache..."
az redis delete \
  --name red-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  2>/dev/null || echo "  ⚠️ Already deleted"

echo ""

# Production
echo "📍 Production Environment"
az account set --subscription b83b5bd5-c04f-4965-bb3d-89ffdb75cbcc

PROD_PE=$(az network private-endpoint list \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --query "[?contains(name, 'redis')].name" -o tsv 2>/dev/null)

if [ -n "$PROD_PE" ]; then
  echo "  Deleting private endpoint: $PROD_PE..."
  az network private-endpoint delete \
    --name "$PROD_PE" \
    --resource-group rg-italynorth-magictoolbox-prod-01 \
    2>/dev/null || echo "  ⚠️ Failed to delete"
fi

echo "  Deleting Redis cache..."
az redis delete \
  --name red-italynorth-magictoolbox-prod-01 \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  2>/dev/null || echo "  ⚠️ Already deleted"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Note: Redis deletion can take 5-10 minutes."
echo "Verify deletion with: az redis list --output table"
```

## Verification

### Check if Redis resources are deleted

```bash
# Development
az account set --subscription fec3a155-e384-43cd-abc7-9c20391a3fd4
az redis list --resource-group rg-westeurope-magictoolbox-dev-01 --output table

# Production
az account set --subscription b83b5bd5-c04f-4965-bb3d-89ffdb75cbcc
az redis list --resource-group rg-italynorth-magictoolbox-prod-01 --output table
```

Expected output: Empty table or "No resources found"

### Check Private DNS Zones

Redis private DNS zones may still exist:

```bash
# Development
az network private-dns zone list \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "[?contains(name, 'redis')]" --output table

# Production
az network private-dns zone list \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --query "[?contains(name, 'redis')]" --output table
```

If Redis DNS zones exist (`privatelink.redis.cache.windows.net`), they will be automatically removed on the next infrastructure deployment since they're not in the Bicep templates anymore.

## After Cleanup

### Redeploy Infrastructure

Once Redis resources are deleted, redeploy the infrastructure to ensure clean state:

#### Development Environment

```bash
cd infra

az account set --subscription fec3a155-e384-43cd-abc7-9c20391a3fd4

az deployment group create \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --template-file main.bicep \
  --parameters parameters.dev.json
```

#### Production Environment

```bash
cd infra

az account set --subscription b83b5bd5-c04f-4965-bb3d-89ffdb75cbcc

az deployment group create \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --template-file main.bicep \
  --parameters parameters.prod.json
```

Or use GitHub Actions:

```bash
# Trigger workflow via GitHub UI
# Navigate to: Actions → Deploy Infrastructure → Run workflow
# Select branch: develop (for dev) or main (for prod)
# Set environment: dev or prod
```

## Cost Impact

**Before Removal**:
- Redis Basic C0: ~$16/month per environment
- Total: ~$32/month (dev + prod)

**After Removal**:
- $0 for cache (using database-backed cache)
- Minimal database cost increase (negligible for low traffic)

**Savings**: ~$32/month (~$384/year)

## Troubleshooting

### Redis deletion fails with "Cannot delete"

If Redis is in a failed state or has locks:
```bash
# Check resource locks
az lock list --resource-group rg-westeurope-magictoolbox-dev-01

# Remove lock if exists
az lock delete --name <lock-name> --resource-group <rg-name>

# Try deletion again
```

### Private endpoint deletion fails

Delete via Azure Portal if CLI fails:
1. Navigate to Private Endpoint resource
2. Check "Network Interfaces" and delete them first if needed
3. Then delete the Private Endpoint

### Redis DNS zone remains

The DNS zone will be automatically cleaned up on next deployment, or manually delete:

```bash
az network private-dns zone delete \
  --name privatelink.redis.cache.windows.net \
  --resource-group <resource-group-name>
```

## Related Documentation

- [Redis Removal Migration Guide](REDIS_REMOVAL_MIGRATION.md)
- [Azure Deployment README](AZURE_DEPLOYMENT_README.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
