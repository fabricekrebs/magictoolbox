# Deployment Instructions - Tool-Specific Containers Migration

**Date**: December 16, 2025  
**Branch**: `develop`  
**Commit**: `feat: implement tool-specific blob storage containers`

## Overview

This deployment migrates from generic blob storage containers (`uploads`, `processed`) to tool-specific containers (`pdf-uploads`, `image-uploads`, etc.) for better isolation, security, and management.

---

## Pre-Deployment Checklist

- [ ] Code committed to `develop` branch
- [ ] All tests passing locally
- [ ] Azure CLI authenticated: `az login`
- [ ] Correct subscription selected: `az account show`
- [ ] Review changes in [documentation/NAMING_CONSISTENCY_AUDIT.md](documentation/NAMING_CONSISTENCY_AUDIT.md)

---

## Deployment Steps

### Step 1: Deploy Infrastructure (Create New Containers)

```bash
cd /home/azureuser/magictoolbox

# Navigate to infrastructure folder
cd infra

# Deploy to create new tool-specific containers
# This will create: pdf-uploads, pdf-processed, image-uploads, image-processed, 
# gpx-uploads, gpx-processed, ocr-uploads, ocr-processed
# (video-uploads and video-processed already exist)
az deployment sub create \
  --location westeurope \
  --template-file main.bicep \
  --parameters @main.parameters.dev.json

# Wait for deployment to complete (~5-10 minutes)
# Verify containers were created
az storage container list \
  --account-name <your-storage-account> \
  --auth-mode login \
  --query "[].name" -o table
```

**Expected containers**:
- ✅ `pdf-uploads`
- ✅ `pdf-processed`
- ✅ `image-uploads`
- ✅ `image-processed`
- ✅ `gpx-uploads`
- ✅ `gpx-processed`
- ✅ `video-uploads` (existing)
- ✅ `video-processed` (existing)
- ✅ `ocr-uploads`
- ✅ `ocr-processed`
- ⚠️ `uploads` (deprecated - keep for now)
- ⚠️ `processed` (deprecated - keep for now)

---

### Step 2: Deploy Azure Functions

```bash
cd /home/azureuser/magictoolbox/function_app

# Publish updated functions to Azure
func azure functionapp publish func-magictoolbox-dev-<suffix> --python

# Wait for deployment (~2-3 minutes)

# Verify deployment
az functionapp list --query "[].{name:name, state:state}" -o table

# Test health endpoint
curl https://func-magictoolbox-dev-<suffix>.azurewebsites.net/api/health?detailed=true
```

**Expected Response**:
```json
{
  "status": "healthy",
  "blob_storage": {"status": "connected"},
  "database": {"status": "connected"}
}
```

---

### Step 3: Deploy Django Container App

```bash
cd /home/azureuser/magictoolbox

# Build and push Docker image to ACR
az acr build \
  --registry <your-acr-name> \
  --image magictoolbox:latest \
  --file Dockerfile .

# Update Container App with new image
az containerapp update \
  --name app-<location>-<prefix>-01 \
  --resource-group rg-<env>-<location>-<prefix> \
  --image <your-acr-name>.azurecr.io/magictoolbox:latest

# Wait for deployment (~3-5 minutes)

# Check Container App status
az containerapp show \
  --name app-<location>-<prefix>-01 \
  --resource-group rg-<env>-<location>-<prefix> \
  --query "properties.runningStatus" -o tsv
```

---

### Step 4: Verification Testing

#### Test Each Tool

1. **PDF to DOCX Converter**
   ```bash
   # Upload a test PDF through the UI
   # Check blob appears in: pdf-uploads/{uuid}.pdf
   # After processing, check: pdf-processed/{uuid}.docx
   ```

2. **Image Converter**
   ```bash
   # Upload a test image
   # Check blob appears in: image-uploads/{uuid}.jpg
   # After processing, check: image-processed/{uuid}.png
   ```

3. **Video Rotation**
   ```bash
   # Upload a test video
   # Check blob appears in: video-uploads/{uuid}.mp4
   # After processing, check: video-processed/{uuid}.mp4
   ```

4. **GPX Tools** (Converter, Merger, Speed Modifier)
   ```bash
   # Upload test GPX files
   # Check blob appears in: gpx-uploads/{uuid}.gpx
   # After processing, check: gpx-processed/{uuid}.kml (or .gpx)
   ```

5. **OCR Tool**
   ```bash
   # Upload a test image with text
   # Check blob appears in: ocr-uploads/{uuid}.jpg
   # After processing, check: ocr-processed/{uuid}.txt
   ```

#### Verify in Azure Portal

1. Navigate to Storage Account → Containers
2. Confirm all tool-specific containers exist
3. Spot-check blob paths (should be simplified - no subdirectories)
4. Verify old containers (`uploads`, `processed`) still exist but unused

---

### Step 5: Monitor and Validate

```bash
# Check Container App logs
az containerapp logs show \
  --name app-<location>-<prefix>-01 \
  --resource-group rg-<env>-<location>-<prefix> \
  --tail 50

# Check Azure Function logs
func azure functionapp logstream func-magictoolbox-dev-<suffix>

# Check Application Insights for errors
az monitor app-insights query \
  --app <app-insights-name> \
  --analytics-query "traces | where severityLevel >= 3 | top 20 by timestamp desc"
```

---

### Step 6: Cleanup (After Successful Migration)

**⚠️ ONLY AFTER CONFIRMING ALL TOOLS WORK CORRECTLY**

```bash
# Remove deprecated containers (optional - can keep for rollback)
# az storage container delete --name uploads --account-name <storage-account> --auth-mode login
# az storage container delete --name processed --account-name <storage-account> --auth-mode login

# Remove legacy containers from storage.bicep
# Edit infra/modules/storage.bicep and remove uploadsContainer and processedContainer resources
# Re-deploy infrastructure
```

---

## Rollback Plan (If Needed)

If issues occur during deployment:

1. **Revert Code**
   ```bash
   git revert HEAD
   git push origin develop
   ```

2. **Redeploy Previous Version**
   ```bash
   # Redeploy previous Container App revision
   az containerapp revision list \
     --name app-<location>-<prefix>-01 \
     --resource-group rg-<env>-<location>-<prefix>

   az containerapp revision set-mode \
     --name app-<location>-<prefix>-01 \
     --resource-group rg-<env>-<location>-<prefix> \
     --mode single \
     --revision <previous-revision-name>

   # Redeploy previous Azure Functions
   git checkout <previous-commit>
   cd function_app
   func azure functionapp publish func-magictoolbox-dev-<suffix> --python
   ```

3. **Verify Rollback**
   - Test all tools with previous configuration
   - Check logs for errors
   - Verify blob storage access

---

## Post-Deployment Tasks

- [ ] Update `.env.development` if using local Azurite (no changes needed)
- [ ] Notify team about container structure changes
- [ ] Update monitoring dashboards if necessary
- [ ] Schedule cleanup of deprecated containers (optional, after 1 week)

---

## Environment Variables Reference

### Required Variables (Unchanged)

| Variable | Container Apps | Azure Functions | Django App |
|----------|----------------|-----------------|------------|
| `AZURE_STORAGE_ACCOUNT_NAME` | ✅ | ✅ | ✅ |
| `DB_NAME` | ✅ | ✅ | ✅ |
| `DB_USER` | ✅ | ✅ | ✅ |
| `DB_PASSWORD` | ✅ | ✅ | ✅ |
| `DB_HOST` | ✅ | ✅ | ✅ |
| `AZURE_FUNCTION_BASE_URL` | ✅ | ❌ | ✅ |

### Deprecated Variables (Removed)

| Variable | Status |
|----------|--------|
| ~~`AZURE_ACCOUNT_NAME`~~ | ❌ Removed |
| ~~`AZURE_STORAGE_CONTAINER_UPLOADS`~~ | ❌ Not needed (hardcoded per tool) |

---

## Container Naming Reference

| Tool | Upload Container | Processed Container | Blob Path Format |
|------|------------------|---------------------|------------------|
| PDF Converter | `pdf-uploads` | `pdf-processed` | `{uuid}.pdf` → `{uuid}.docx` |
| Image Converter | `image-uploads` | `image-processed` | `{uuid}.{ext}` → `{uuid}.{ext}` |
| GPX Converter | `gpx-uploads` | `gpx-processed` | `{uuid}.gpx` → `{uuid}.kml` |
| GPX Merger | `gpx-uploads` | `gpx-processed` | `{uuid}_000.gpx` → `{uuid}.gpx` |
| GPX Speed Modifier | `gpx-uploads` | `gpx-processed` | `{uuid}.gpx` → `{uuid}.gpx` |
| Video Rotation | `video-uploads` | `video-processed` | `{uuid}.mp4` → `{uuid}.mp4` |
| OCR Tool | `ocr-uploads` | `ocr-processed` | `{uuid}.{ext}` → `{uuid}.txt` |

---

## Troubleshooting

### Issue: Containers not created after infrastructure deployment
**Solution**: 
```bash
# Manually create missing containers
az storage container create --name <container-name> --account-name <storage-account> --auth-mode login
```

### Issue: Functions can't access new containers
**Solution**: Check managed identity RBAC roles:
```bash
az role assignment list --assignee <function-app-principal-id> --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<storage-account>
```

### Issue: Tools still uploading to old containers
**Solution**: Verify code deployment succeeded, check logs for old container references

### Issue: Blob not found errors
**Solution**: Verify blob path format matches new simplified structure (no subdirectories)

---

## Support

For issues or questions:
- Check [documentation/NAMING_CONSISTENCY_AUDIT.md](documentation/NAMING_CONSISTENCY_AUDIT.md)
- Review commit message for detailed changes
- Check Application Insights logs
- Contact DevOps team

---

**Deployment completed successfully?** ✅  
**All tools tested?** ✅  
**No errors in logs?** ✅  

🎉 **Migration Complete!** 🎉
