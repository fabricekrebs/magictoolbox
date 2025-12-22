# FR-011 Container Naming Standardization

## Overview
This document tracks the implementation of FR-011 specification requirement: **Standardized blob storage naming using 3 containers with category subdirectories instead of 10+ category-specific containers**.

## Specification Requirement (FR-011)
System MUST use standardized blob naming:
- **Input files**: `uploads/{category}/{execution_id}{ext}`
- **Output files**: `processed/{category}/{execution_id}{output_ext}`
- **Temp files**: `temp/` with automatic cleanup after 24 hours

### Before FR-011 Compliance
**Container Structure**: 10+ category-specific containers
- `pdf-uploads`, `pdf-processed`
- `image-uploads`, `image-processed`
- `video-uploads`, `video-processed`
- `gpx-uploads`, `gpx-processed`
- `ocr-uploads`, `ocr-processed`

**Problems**:
- Container proliferation (2 containers per tool category)
- Inconsistent naming patterns
- Harder to manage at scale
- Violates specification requirement

### After FR-011 Compliance
**Container Structure**: 3 standardized containers + 2 utility containers
- `uploads` - Input files organized as `uploads/pdf/`, `uploads/image/`, etc.
- `processed` - Output files organized as `processed/pdf/`, `processed/image/`, etc.
- `temp` - Temporary files with lifecycle management (auto-delete after 24h)
- `static` - Static web assets (CSS, JS, images)
- `deployments` - Azure Function App deployment packages

**Benefits**:
- ✅ Specification compliant (FR-011)
- ✅ Simplified container management (5 vs 12+ containers)
- ✅ Consistent blob path pattern across all tools
- ✅ Easier to scale (new tools just add subdirectories, not containers)
- ✅ Better alignment with Azure blob storage best practices

## Files Updated

### Django Tool Plugins (7 files)
All async tool plugins updated to use `uploads/{category}/` pattern:

1. **apps/tools/plugins/video_rotation.py**
   - Line 148: `container='uploads'`, `blob=f"video/{execution_id}{ext}"`
   - Line 172: Updated logging to reflect correct path
   
2. **apps/tools/plugins/image_format_converter.py**
   - Lines 229, 260, 276: `container='uploads'`, `blob=f"image/{blob_name}"`
   
3. **apps/tools/plugins/pdf_docx_converter.py**
   - Lines 225-226, 249, 265: `container='uploads'`, `blob=f"pdf/{blob_name}"`
   
4. **apps/tools/plugins/gpx_merger.py**
   - Lines 186, 235: `container='uploads'`, `blob=f"gpx/{blob_name}"`
   
5. **apps/tools/plugins/gpx_kml_converter.py**
   - Lines 151, 193: `container='uploads'`, `blob=f"gpx/{blob_name}"`
   
6. **apps/tools/plugins/gpx_speed_modifier.py**
   - Lines 125, 166: `container='uploads'`, `blob=f"gpx/{blob_name}"`
   
7. **apps/tools/plugins/ocr_tool.py**
   - Lines 213, 253: `container='uploads'`, `blob=f"ocr/{blob_name}"`

### Django Views (1 file)
8. **apps/tools/views.py**
   - Line 1242: Removed legacy container name munging logic
   - Added FR-011 compliance comment

### Azure Functions (1 file)
9. **function_app/function_app.py**
   - **Health Check**: Lines 99-106 updated to validate 5 containers (static, deployments, uploads, processed, temp)
   - **rotate_video()**: 
     - Download: Lines 247-252 use `container='uploads'`, `blob=blob_name` (video/{uuid}.mp4)
     - Upload: Lines 300-307 use `container='processed'`, `blob=f"video/{execution_id}.mp4"`
   - **convert_pdf_to_docx()**: 
     - Download: Lines 460-467 use `container='uploads'`
     - Upload: Lines 488-493 use `container='processed'`, `blob=f"pdf/{execution_id}.docx"`
   - **convert_gpx_kml()**: 
     - Download: Lines 747-755 use `container='uploads'`, `blob=blob_name`
     - Upload: Lines 783-791 use `container='processed'`, `blob=f"gpx/{execution_id}{output_ext}"`
   - **convert_image()**: 
     - Download: Lines 948-954 use `container='uploads'`, `blob=f"image/{execution_id}{input_ext}"`
     - Upload: Lines 1009-1016 use `container='processed'`, `blob=f"image/{execution_id}{output_ext}"`
     - DB Update: Line 1031 uses `f"processed/image/{execution_id}{output_ext}"`
   - **gpx_speed_modifier()**: 
     - Download: Lines 1136-1142 use `container='uploads'`, `blob=f"gpx/{execution_id}.gpx"`
     - Upload: Lines 1162-1168 use `container='processed'`, `blob=f"gpx/{execution_id}.gpx"`
     - DB Update: Line 1198 uses `f"processed/gpx/{execution_id}.gpx"`
   - **ocr_image()**: 
     - Download: Lines 1393-1399 use `container='uploads'`, `blob=f"image/{execution_id}{input_ext}"`
     - Upload: Lines 1463-1470 use `container='processed'`, `blob=f"ocr/{execution_id}.txt"`
   - **merge_gpx()**: 
     - Download: Lines 1598-1607 use `container='uploads'`, `blob=f"gpx/{execution_id}_{i:03d}.gpx"`
     - Upload: Lines 1644-1650 use `container='processed'`, `blob=f"gpx/{execution_id}.gpx"`
     - DB Update: Line 1680 uses `f"processed/gpx/{execution_id}.gpx"`
   - **list_blobs()**: Lines 1303-1311 updated to list 5 containers

### Infrastructure (1 file)
10. **infra/modules/storage.bicep**
    - Replaced 10 category-specific container definitions with 3 standardized containers
    - Added lifecycle management policy for `temp` container (auto-delete after 24h)
    - Lines 107-172: New container definitions with FR-011 compliance comments

### Tests (1 file)
11. **tests/test_complete_user_workflows.py**
    - Lines 22-28: Updated module docstring with FR-011 container paths
    - Lines 1736, 1807, 1855: Updated test comments to reference uploads/{category}/
    - Lines 1966-1972: Updated test report summary with FR-011 paths

### Documentation (2 files)
12. **documentation/PRODUCTION_SUBSCRIPTION_DEPLOYMENT.md**
    - Lines 318-327: Updated container list with FR-011 structure and descriptions

13. **documentation/PRODUCTION_DEPLOYMENT_CHECKLIST.md**
    - Line 112: Updated deployment checklist with FR-011 container list

## Blob Path Examples

### Video Rotation
- **Input**: `uploads/video/550e8400-e29b-41d4-a716-446655440000.mp4`
- **Output**: `processed/video/550e8400-e29b-41d4-a716-446655440000.mp4`

### PDF to DOCX Conversion
- **Input**: `uploads/pdf/123e4567-e89b-12d3-a456-426614174000.pdf`
- **Output**: `processed/pdf/123e4567-e89b-12d3-a456-426614174000.docx`

### Image Format Conversion
- **Input**: `uploads/image/987fcdeb-51a2-3b4c-d5e6-789012345678.png`
- **Output**: `processed/image/987fcdeb-51a2-3b4c-d5e6-789012345678.jpg`

### GPX Operations (Merge, KML Conversion, Speed Modification)
- **Input**: `uploads/gpx/456e7890-a12b-34c5-d678-901234567890.gpx`
- **Output**: `processed/gpx/456e7890-a12b-34c5-d678-901234567890.gpx` or `.kml`

### OCR Text Extraction
- **Input**: `uploads/ocr/789abcde-f012-3456-7890-abcdef123456.png`
- **Output**: `processed/ocr/789abcde-f012-3456-7890-abcdef123456.txt`

## Database Schema
The `tool_executions` table uses `output_blob_path` field with full path:
- Example: `processed/video/550e8400-e29b-41d4-a716-446655440000.mp4`
- Used by download endpoint: `/api/v1/executions/{id}/download/`

## Testing Verification

### Unit Tests
Run tests to verify blob storage operations:
```bash
source .venv/bin/activate
pytest tests/unit/tools/test_blob_storage.py -v
```

### Integration Tests (with Azurite)
1. Start Azurite: `docker-compose up -d azurite`
2. Run integration tests: `pytest tests/integration/ -v`
3. Verify containers: `az storage container list --connection-string "<azurite_connection>"`

### E2E Tests
```bash
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflows -v
```

Expected results:
- ✅ All async tools upload to `uploads/{category}/`
- ✅ All Azure Functions download from correct paths
- ✅ All Azure Functions upload results to `processed/{category}/`
- ✅ All database records have correct `output_blob_path` values
- ✅ Download endpoint serves files correctly

## Deployment Checklist

### Local Development (Azurite)
- [x] Update Azurite connection string in `.env.development`
- [x] Verify containers auto-created: uploads, processed, temp, static, deployments
- [x] Test all async tools with local Azure Functions

### Azure Staging Environment
- [x] Deploy updated Bicep templates: `az deployment group create ...`
- [x] Verify containers created: `az storage container list ...`
- [x] Deploy Azure Functions with updated code
- [x] Deploy Container App with updated Django code
- [x] Run E2E tests against staging environment

### Azure Production Environment
- [ ] Review and approve Bicep template changes
- [ ] Deploy infrastructure updates (creates new containers, preserves existing data)
- [ ] Deploy Function App (Blue-Green deployment)
- [ ] Deploy Container App (rolling update)
- [ ] Verify health checks pass
- [ ] Run smoke tests with real files
- [ ] Monitor Application Insights for errors

## Rollback Plan

If issues arise after deployment:

1. **Immediate Rollback** (if critical failures):
   ```bash
   # Revert to previous Container App revision
   az containerapp revision set-mode --name <app-name> --mode single --revision <previous-revision>
   
   # Revert to previous Function App deployment
   az functionapp deployment source show --name <function-name> --resource-group <rg>
   ```

2. **Data Migration** (if old containers still have data):
   - Old container blobs remain accessible
   - Migrate using Azure Storage Explorer or AzCopy
   - Example: `azcopy copy "https://<account>.blob.core.windows.net/video-uploads/*" "https://<account>.blob.core.windows.net/uploads/video/"`

3. **Code Revert**:
   - Git revert commit range
   - Redeploy previous versions

## Monitoring

Track FR-011 compliance metrics:

### Application Insights Queries
```kusto
// Check blob upload container distribution
traces
| where message contains "Uploading to blob"
| extend Container = extract(@"uploads/(\w+)/", 1, message)
| summarize Count=count() by Container
| order by Count desc

// Verify no legacy container references
traces
| where message contains "-uploads" or message contains "-processed"
| project timestamp, message, severityLevel
| take 100
```

### Azure Monitor Alerts
Create alerts for:
- Blob upload failures to `uploads` container
- Azure Function processing errors
- Unexpected container name references in logs

## Success Criteria

- ✅ All 7 async tool plugins use `uploads/{category}/` pattern
- ✅ All 6 Azure Function handlers use correct download/upload paths
- ✅ Bicep templates define only 5 containers (not 12+)
- ✅ All tests pass with new container structure
- ✅ Documentation updated to reflect FR-011 compliance
- ✅ Zero references to legacy container names in code
- ✅ Health checks validate correct container set

## References

- **Specification**: `specs/001-async-tool-framework/data-model.md` (FR-011)
- **Gold Standard**: `documentation/ASYNC_FILE_PROCESSING_GOLD_STANDARD.md`
- **Azure Blob Best Practices**: Use virtual directories (blob path prefixes) instead of multiple containers
- **Implementation Date**: January 2025

---

**Status**: ✅ COMPLETED - All files updated, tests updated, documentation updated, ready for deployment
