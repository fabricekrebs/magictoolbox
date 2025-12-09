# Azurite Local Testing Issues - Summary

## Problem
During local testing setup for the video rotation tool, we encountered persistent issues with Azurite 3.x (both 3.28.0 and 3.35.0) refusing to recognize the well-known `devstorageaccount1` account.

## Symptoms
- All container creation requests return HTTP 404 "ResourceNotFound"
- Error message: "Invalid storage account devstorageaccount1"
- Occurs even with `--loose` and `--skipApiVersionCheck` flags
- Affects both Python Azure SDK and Azure CLI tools

## Root Cause
Azurite 3.x versions have stricter account validation that requires accounts to exist in the internal database (`__azurite_db_blob__.json`). The well-known `devstorageaccount1` account is not automatically created/recognized even though it's part of the Azurite specification.

## Attempted Solutions
1. ✗ Using `--loose` mode
2. ✗ Using `--disableProductStyleUrl` flag  
3. ✗ Creating `accounts.json` file manually
4. ✗ Using `--skipApiVersionCheck`
5. ✗ Downgrading to Azurite 3.28.0
6. ✗ Using Docker container instead of NPM package
7. ✗ Different connection string formats
8. ✗ REST API direct calls with/without authentication

## Recommended Solutions

### Option 1: Use Actual Azure Storage (RECOMMENDED)
For local testing, use the dev Azure Storage Account instead of Azurite:
- More reliable
- Closer to production environment
- All containers already exist
- No compatibility issues

Update `function_app/local.settings.json`:
```json
{
  "Values": {
    "STORAGE_CONNECTION_STRING": "<actual-azure-storage-connection-string>",
    "AZURE_STORAGE_ACCOUNT_NAME": "sawemagictoolboxdev01"
  }
}
```

### Option 2: Use Azurite 2.x
Downgrade to Azurite 2.x which doesn't have account validation issues:
```bash
npm install -g azurite@2.7.1
azurite -l /tmp/azurite
```

### Option 3: Use MinIO
MinIO is S3-compatible but can work with Azure SDK using compatibility layer:
```bash
docker compose up -d minio
# Then configure with MinIO credentials
```

### Option 4: Skip Local Blob Testing
Test the workflow without actual blob storage:
- Mock the blob operations in tests
- Deploy directly to Azure for integration testing

## Current Status
- Azurite Docker container is running but non-functional for container operations
- Video rotation code is complete and ready for testing
- Need to decide on storage approach before proceeding with local tests

## Next Steps
1. **Decide on storage approach** (Azure dev storage recommended)
2. Update `function_app/local.settings.json` with chosen connection string
3. Update Django `.env.development` with same connection string
4. Start Azure Functions locally: `cd function_app && func start`
5. Start Django server: `python manage.py runserver`
6. Test video rotation end-to-end workflow

## References
- Azurite GitHub Issues: Multiple reports of account validation problems in 3.x
- Azure Storage Emulator (deprecated) had similar issues before EOL
- MinIO vs Azurite comparison: MinIO more stable but S3-focused

## Date
December 9, 2025
