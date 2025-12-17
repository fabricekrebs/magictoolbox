# MagicToolbox Naming Consistency Audit

**Date**: December 16, 2025  
**Status**: ⚠️ **INCONSISTENCIES FOUND - ACTION REQUIRED**

## Executive Summary

This audit examines naming consistency across three critical areas:
1. **Environment Variables** - Configuration across Django app, Container Apps, Azure Functions, and Key Vault
2. **Blob Storage** - Container names and blob paths between Django app and Azure Functions
3. **Database Tables** - Table names between Django models, Container Apps, and Azure Functions

---

## 1. Environment Variables Analysis

### ✅ CONSISTENT Variables

The following environment variables are **consistently named** across all components:

| Variable | Django App | Container Apps | Azure Functions | Key Vault Secret | PostgreSQL |
|----------|-----------|----------------|-----------------|------------------|------------|
| `DB_NAME` | ✅ | ✅ | ✅ | N/A | ✅ `magictoolbox` |
| `DB_USER` | ✅ | ✅ | ✅ | N/A | N/A |
| `DB_PASSWORD` | ✅ | ✅ | ✅ | ✅ `postgres-password` | N/A |
| `DB_HOST` | ✅ | ✅ | ✅ | N/A | N/A |
| `DB_PORT` | ✅ | ✅ | ✅ | N/A | N/A |
| `DB_SSLMODE` | ✅ | ✅ | ✅ | N/A | N/A |
| `SECRET_KEY` | ✅ | ✅ | N/A | ✅ `django-secret-key` | N/A |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | ✅ | ✅ | ✅ | N/A | N/A |

### ⚠️ INCONSISTENT Variables - Azure Storage Account Name

**CRITICAL ISSUE**: Multiple variable names are used for the Azure Storage Account:

| Component | Variable Name Used | File Location |
|-----------|-------------------|---------------|
| **Django Base Settings** | `AZURE_STORAGE_ACCOUNT_NAME` | [magictoolbox/settings/base.py#L331](magictoolbox/settings/base.py#L331) |
| **Django Base Settings** | `AZURE_ACCOUNT_NAME` | [magictoolbox/settings/base.py#L332](magictoolbox/settings/base.py#L332) |
| **Django Production** | `AZURE_STORAGE_ACCOUNT_NAME` | [magictoolbox/settings/production.py#L57](magictoolbox/settings/production.py#L57) |
| **Django Production** | `AZURE_ACCOUNT_NAME` | [magictoolbox/settings/production.py#L58](magictoolbox/settings/production.py#L58) |
| **Container Apps Bicep** | `AZURE_STORAGE_ACCOUNT_NAME` | [infra/modules/container-apps.bicep#L272](infra/modules/container-apps.bicep#L272) |
| **Azure Functions Bicep** | `AZURE_STORAGE_ACCOUNT_NAME` | [infra/modules/function-app.bicep#L152](infra/modules/function-app.bicep#L152) |
| **Azure Functions Code** | `AZURE_STORAGE_ACCOUNT_NAME` | [function_app/function_app.py#L44](function_app/function_app.py#L44) |
| **PDF Converter Tool** | `AZURE_STORAGE_ACCOUNT_NAME` or `AZURE_ACCOUNT_NAME` (fallback) | [apps/tools/plugins/pdf_docx_converter.py#L198](apps/tools/plugins/pdf_docx_converter.py#L198) |
| **Video Rotation Tool** | `AZURE_STORAGE_ACCOUNT_NAME` or `AZURE_ACCOUNT_NAME` (fallback) | [apps/tools/plugins/video_rotation.py#L221](apps/tools/plugins/video_rotation.py#L221) |

**Current State**:
- Django uses both `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_ACCOUNT_NAME` (aliased)
- Tools check for both names as fallback
- Infrastructure (Bicep) uses only `AZURE_STORAGE_ACCOUNT_NAME`

**Recommendation**: 
✅ **Standardize on `AZURE_STORAGE_ACCOUNT_NAME`** (already used in infrastructure)

**Action Required**:
1. Remove `AZURE_ACCOUNT_NAME` alias from Django settings
2. Update `.env.example` to use only `AZURE_STORAGE_ACCOUNT_NAME`
3. Update tool code to remove fallback checks

---

## 2. Blob Storage Naming Conventions

### ⚠️ CRITICAL INCONSISTENCY - Container Names

**MAJOR ISSUE**: Hybrid approach with both generic and tool-specific containers creates confusion:

#### Infrastructure (Bicep) - [infra/modules/storage.bicep](infra/modules/storage.bicep)
```bicep
Container Names Created:
- 'uploads'         (Line 109) - Generic container ⚠️
- 'processed'       (Line 118) - Generic container ⚠️
- 'video-uploads'   (Line 145) - Tool-specific ✅ (correct approach)
- 'video-processed' (Line 154) - Tool-specific ✅ (correct approach)
```

#### Django App - [magictoolbox/settings/production.py#L60](magictoolbox/settings/production.py#L60)
```python
AZURE_CONTAINER = config("AZURE_STORAGE_CONTAINER_UPLOADS", default="uploads")
# Generic container - needs to be tool-specific
```

#### Video Rotation Tool - [apps/tools/plugins/video_rotation.py](apps/tools/plugins/video_rotation.py)
```python
# Line 160: Uses 'video-uploads' container
blob_client = blob_service.get_blob_client(
    container="video-uploads",  # ✅ CORRECT (tool-specific)
    blob=blob_name
)
```

#### Azure Functions - [function_app/function_app.py](function_app/function_app.py)
```python
# Line 214: Video rotation incorrectly falls back to generic 'uploads'
container_name = parts[0] if len(parts) > 1 else 'uploads'  # ⚠️ WRONG

# Line 270: Uploads to generic 'processed' container
output_blob_client = blob_service_client.get_blob_client(
    container='processed',  # ⚠️ Should be 'video-processed'
    blob=f"video/{execution_id}.mp4"
)
```

#### Other Tools (PDF, Image, GPX) - Need Update ⚠️
```python
# Current (generic containers):
blob_client = blob_service.get_blob_client(container="uploads", blob=f"{category}/{uuid}{ext}")
# Output: container="processed", blob=f"{category}/{uuid}{ext}"

# Should be (tool-specific containers):
blob_client = blob_service.get_blob_client(container="pdf-uploads", blob=f"{uuid}.pdf")
# Output: container="pdf-processed", blob=f"{uuid}.docx"
```

### Recommended Blob Storage Architecture

#### ✅ TOOL-SPECIFIC CONTAINERS (Recommended Approach)
**Benefits:**
- Better isolation and security (separate permissions per tool)
- Easier lifecycle management (different retention per tool type)
- Clearer organization in Azure Portal
- Simpler cost tracking per tool
- Avoids potential naming conflicts

**Container Naming Convention:**
```
{tool-category}-uploads    (input files)
{tool-category}-processed  (output files)
```

**Blob Path Structure (simplified - no subdirectories needed):**
```
Input:  {tool}-uploads/{execution_id}{extension}
Output: {tool}-processed/{execution_id}{extension}

Examples:
- pdf-uploads/abc123.pdf         → pdf-processed/abc123.docx
- image-uploads/def456.jpg       → image-processed/def456.png
- gpx-uploads/ghi789.gpx         → gpx-processed/ghi789.kml
- video-uploads/jkl012.mp4       → video-processed/jkl012.mp4
- ocr-uploads/mno345.jpg         → ocr-processed/mno345.txt
```

**Recommendation**:
✅ **Use tool-specific containers** (already partially implemented for video)  
🔄 **UPDATE**: Migrate all tools to use tool-specific containers  
❌ **DEPRECATE**: Generic `uploads` and `processed` containers

---

## 3. Database Table Names

### ✅ FULLY CONSISTENT

The database table name is **consistently used** across all components:

| Component | Table Name | Reference |
|-----------|-----------|-----------|
| **Django Model** | `tool_executions` | [apps/tools/models.py#L67](apps/tools/models.py#L67) `db_table = "tool_executions"` |
| **Azure Functions** | `tool_executions` | [function_app/function_app.py#L196](function_app/function_app.py#L196) `UPDATE tool_executions` |
| **PostgreSQL Database** | `magictoolbox` | [infra/modules/postgresql.bicep#L15](infra/modules/postgresql.bicep#L15) `databaseName = 'magictoolbox'` |

**Schema**:
```sql
-- Defined in apps/tools/models.py
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY,
    user_id INTEGER REFERENCES auth_user(id),
    tool_name VARCHAR(100),
    status VARCHAR(20),
    input_file VARCHAR(100),
    input_filename VARCHAR(255),
    output_file VARCHAR(100),
    output_filename VARCHAR(255),
    parameters JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    error_message TEXT,
    error_traceback TEXT,
    input_size BIGINT,
    output_size BIGINT,
    azure_function_invoked BOOLEAN,
    function_execution_id VARCHAR(255),
    input_blob_path VARCHAR(500),
    output_blob_path VARCHAR(500),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**All SQL Operations Match**:
- Django ORM uses: `ToolExecution` model → `tool_executions` table
- Azure Functions use: `UPDATE tool_executions WHERE id = %s`
- Container Apps use: Django ORM → `tool_executions` table

✅ **No action required** - Database naming is fully consistent!

---

## 4. Summary of Issues & Recommendations

### 🔴 Critical Issues (Must Fix)

1. **Inconsistent Container Strategy**
   - **Issue**: Hybrid approach - video uses tool-specific containers (`video-uploads`, `video-processed`), but other tools use generic containers (`uploads`, `processed`) with subdirectories
   - **Impact**: Confusing architecture, inconsistent patterns, harder to manage permissions and lifecycle policies
   - **Fix**: Standardize ALL tools to use tool-specific containers (extend the video pattern to all tools)
   - **Files to modify**:
     - [function_app/function_app.py](function_app/function_app.py) - Fix video function to use `video-processed` instead of `processed`
     - [apps/tools/plugins/pdf_docx_converter.py](apps/tools/plugins/pdf_docx_converter.py) - Change to `pdf-uploads` / `pdf-processed`
     - [apps/tools/plugins/image_format_converter.py](apps/tools/plugins/image_format_converter.py) - Change to `image-uploads` / `image-processed`
     - [apps/tools/plugins/gpx_kml_converter.py](apps/tools/plugins/gpx_kml_converter.py) - Change to `gpx-uploads` / `gpx-processed`
     - [apps/tools/plugins/gpx_merger.py](apps/tools/plugins/gpx_merger.py) - Change to `gpx-uploads` / `gpx-processed`
     - [apps/tools/plugins/ocr_tool.py](apps/tools/plugins/ocr_tool.py) - Change to `ocr-uploads` / `ocr-processed`
     - [apps/tools/plugins/gpx_speed_modifier.py](apps/tools/plugins/gpx_speed_modifier.py) - Change to `gpx-uploads` / `gpx-processed`
     - [infra/modules/storage.bicep](infra/modules/storage.bicep) - Add all tool-specific containers

2. **Storage Account Variable Duplication**
   - **Issue**: Both `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_ACCOUNT_NAME` are defined
   - **Impact**: Confusion, potential misconfiguration
   - **Fix**: Standardize on `AZURE_STORAGE_ACCOUNT_NAME` everywhere
   - **Files to modify**:
     - [magictoolbox/settings/base.py#L331-332](magictoolbox/settings/base.py#L331-332)
     - [magictoolbox/settings/production.py#L57-58](magictoolbox/settings/production.py#L57-58)
     - [.env.example](/.env.example)
     - Remove fallback logic in tools

### ✅ What's Working Well

1. **Database Configuration**: All database environment variables (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSLMODE`) are consistently named
2. **Table Names**: `tool_executions` table is consistently referenced across Django and Azure Functions
3. **Most Blob Paths**: PDF, Image, GPX tools follow standardized `uploads/{category}/` pattern
4. **Key Vault Secrets**: Secret names match expected patterns (`postgres-password`, `django-secret-key`)

---

## 5. Action Plan

### Phase 1: Update Infrastructure (Create Tool-Specific Containers)

**File to modify**: [infra/modules/storage.bicep](infra/modules/storage.bicep)

Add containers for all tools (keep existing video containers, add others):

```bicep
// PDF tool containers
resource pdfUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'pdf-uploads'
  properties: { publicAccess: 'None' }
}

resource pdfProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'pdf-processed'
  properties: { publicAccess: 'None' }
}

// Image tool containers
resource imageUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'image-uploads'
  properties: { publicAccess: 'None' }
}

resource imageProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'image-processed'
  properties: { publicAccess: 'None' }
}
Update Azure Functions (Fix Video, Add Other Tools)

**File to modify**: [function_app/function_app.py](function_app/function_app.py)

1. **Fix Video Rotation Function** - Use `video-processed` instead of generic `processed`:
   ```python
   # Around Line 270, change:
   output_blob_client = blob_service_client.get_blob_client(
       container='processed',  # ❌ WRONG
       blob=f"video/{execution_id}.mp4"
   )
   
   # To:
   output_blob_client = blob_service_client.get_blob_client(
       container='video-processed',  # ✅ CORRECT
       blob=f"{execution_id}.mp4"  # Simplified path
   )
   ```

2. **Update PDF Conversion Function** - Use `pdf-uploads` / `pdf-processed`:
   ```python
   # Around Line 380, change container names:
   blob_client = blob_service_client.get_blob_client(
       container='pdf-uploads',  # Changed from 'uploads'
       blob=f"{execution_id}.pdf"  # Simplified path (no pdf/ subdirectory)
   )
   
   output_blob_client = blob_service_client.get_blob_client(
       container='pdf-processed',  # Changed from 'processed'
       blob=f"{execution_id}.docx"
   )
   ```

3. **Apply Same Pattern to Image, GPX, OCR Functions** - Update all function endpoints to use tool-specific containers with simplified paths (no subdirectories)

### Phase 3: Update Django Tools

**Files to modify**: All tool plugins in [apps/tools/plugins/](apps/tools/plugins/)

1. **PDF Converter** - [pdf_docx_converter.py](apps/tools/plugins/pdf_docx_converter.py)
   ```python
   # Line 232: Change container
   blob_client = blob_service.get_blob_client(
       container="pdf-uploads",  # Changed from "uploads"
       blob=f"{execution_id}.pdf"  # Simplified (no pdf/ subdirectory)
   )
   ```

2. **Image Converter** - [image_format_converter.py](apps/tools/plugins/image_format_converter.py)
   ```python
   blob_client = blob_service.get_blob_client(
       container="image-uploads",  # Changed from "uploads"
       blob=f"{execution_id}{ext}"
   )
   ```

3. **GPX Tools** - [gpx_kml_converter.py](apps/tools/plugins/gpx_kml_converter.py), [gpx_merger.py](apps/tools/plugins/gpx_merger.py), [gpx_speed_modifier.py](apps/tools/plugins/gpx_speed_modifier.py)
   ```python
   blob_client = blob_service.get_blob_client(
       container="gpx-uploads",  # Changed from "uploads"
       blob=f"{execution_id}.gpx"
   )
   ```

4. **OCR Tool** - [ocr_tool.py](apps/tools/plugins/ocr_tool.py)
   ```python
   blob_client = blob_service.get_blob_client(
       container="ocr-uploads",  # Changed from "uploads"
       blob=f"{execution_id}{ext}"
   )
   ```

5. **Video Rotation** - [video_rotation.py](apps/tools/plugins/video_rotation.py)
   ```python
   # Line 160: Simplify blob path (already uses correct container)
   blob_client = blob_service.get_blob_client(
       container="video-uploads",  # Already correct ✅
       blob=f"{execution_id}{suffix}"  # Simplified (remove video/ subdirectory)
   )
   ```

### Phase 4: 
// GPX tool containers
resource gpxUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'gpx-uploads'
  properties: { publicAccess: 'None' }
}

resource gpxProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'gpx-processed'
  properties: { publicAccess: 'None' }
}

// OCR tool containers
resource ocrUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'ocr-uploads'
  properties: { publicAccess: 'None' }
}

resource ocrProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'ocr-processed'
  properties: { publicAccess: 'None' }
}

// Keep video containers (already exist)
// video-uploads (Line 145)
// video-processed (Line 154)

// DEPRECATED: Remove generic containers after migration
// - uploads (Line 109)
// - processed (Line 118)
```

**Deploy Updated Infrastructure**:
```bash
cd infra
az deployment sub create \
  --location westeurope \
  --template-file main.bicep \
  --parameters @main.parameters.dev.json
```

### Phase 2: Standardize Storage Account Variable

**Files to modify**:

1. **Django Base Settings** - [magictoolbox/settings/base.py](magictoolbox/settings/base.py)
   ```python
   # Remove Line 332:
   # AZURE_ACCOUNT_NAME = config("AZURE_ACCOUNT_NAME", default="")
   
   # Keep only:
   AZURE_STORAGE_ACCOUNT_NAME = config("AZURE_STORAGE_ACCOUNT_NAME", default="")
   ```

2. **Django Production Settings** - [magictoolbox/settings/production.py](magictoolbox/settings/production.py)
   ```python
   # Remove Line 58:
   # AZURE_ACCOUNT_NAME = AZURE_STORAGE_ACCOUNT_NAME
   
   # Keep only:
   AZURE_STORAGE_ACCOUNT_NAME = config("AZURE_STORAGE_ACCOUNT_NAME", default="")
   ```

3. **Environment Template** - [.env.example](/.env.example)
   ```bash
   # Remove:
   # AZURE_ACCOUNT_NAME=
   
   # Keep only (already exists at line 47):
   AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
   ```

4. **Update Tool Fallback Logic**
   - [apps/tools/plugins/pdf_docx_converter.py#L198](apps/tools/plugins/pdf_docx_converter.py#L198)
   - [apps/tools/plugins/video_rotation.py#L221](apps/tools/plugins/video_rotation.py#L221)
   
   ```python
   # Remove fallback:
   storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None) or getattr(settings, "AZURE_ACCOUNT_NAME", None)
   
   # Replace with:
   storage_account_name = getattr(settings, "AZURE_STORAGE_ACCOUNT_NAME", None)
   ```

### Phase 5: Verification

1. **Test Each Tool**:
   - PDF → DOCX: `pdf-uploads/{uuid}.pdf` → `pdf-processed/{uuid}.docx`
   - Image conversion: `image-uploads/{uuid}.jpg` → `image-processed/{uuid}.png`
   - GPX conversion: `gpx-uploads/{uuid}.gpx` → `gpx-processed/{uuid}.kml`
   - Video rotation: `video-uploads/{uuid}.mp4` → `video-processed/{uuid}.mp4`
   - OCR: `ocr-uploads/{uuid}.jpg` → `ocr-processed/{uuid}.txt`

2. **Verify Containers in Azure Portal**:
   - Navigate to Storage Account → Containers
   - Confirm all tool-specific containers exist:
     - `pdf-uploads`, `pdf-processed`
     - `image-uploads`, `image-processed`
     - `gpx-uploads`, `gpx-processed`
     - `video-uploads`, `video-processed`
     - `ocr-uploads`, `ocr-processed`
   - Verify files appear in correct containers without subdirectories

3. **Verify Environment Variables**:
   ```bash
   # Container Apps
   az containerapp show --name <app-name> --query "properties.template.containers[0].env[]"
   
   # Azure Functions
   az functionapp config appsettings list --name <func-name>
   ``` (Tool-Specific Approach)
| Container | Purpose | Used By | Status |
|-----------|---------|---------|--------|
| `pdf-uploads` | PDF input files | PDF Converter | ✅ Required |
| `pdf-processed` | PDF output files | PDF Converter | ✅ Required |
| `image-uploads` | Image input files | Image Converter, OCR | ✅ Required |
| `image-processed` | Image output files | Image Converter | ✅ Required |
| `gpx-uploads` | GPX input files | GPX tools | ✅ Required |
| `gpx-processed` | GPX output files | GPX tools | ✅ Required |
| `video-uploads` | Video input files | Video Rotation | ✅ Exists |
| `video-processed` | Video output files | Video Rotation | ✅ Exists |
| `ocr-uploads` | OCR input files | OCR Tool | ✅ Required |
| `ocr-processed` | OCR output files | OCR Tool | ✅ Required |
| ~~`uploads`~~ | ❌ DEPRECATED | Legacy | 🗑️ Remove after migration |
| ~~`processed`~~ | ❌ DEPRECATED | Legacy | 🗑️ Remove after migration |

### Blob Path Patterns (Simplified - No Subdirectories)
| Tool | Input Container | Input Blob | Output Container | Output Blob |
|------|----------------|-----------|------------------|-------------|
| PDF Converter | `pdf-uploads` | `{uuid}.pdf` | `pdf-processed` | `{uuid}.docx` |
| Image Converter | `image-uploads` | `{uuid}.{ext}` | `image-processed` | `{uuid}.{ext}` |
| GPX Converter | `gpx-uploads` | `{uuid}.gpx` | `gpx-processed` | `{uuid}.kml` |
| GPX Merger | `gpx-uploads` | `{uuid}-{n}.gpx` | `gpx-processed` | `{uuid}.gpx` |
| GPX Speed Modifier | `gpx-uploads` | `{uuid}.gpx` | `gpx-processed` | `{uuid}.gpx` |
| Video Rotation | `video-uploads` | `{uuid}.mp4` | `video-processed` | `{uuid}.mp4` |
| OCR Tool | `ocr-uploads` | `{uuid}.{ext}` | `ocr-processed` | `
| PDF Converter | `uploads/pdf/{uuid}.pdf` | `processed/pdf/{uuid}.docx` |
| Image Converter | `uploads/image/{uuid}.{ext}` | `processed/image/{uuid}.{ext}` |
| GPX Converter | `uploads/gpx/{uuid}.gpx` | `processed/gpx/{uuid}.kml` |
| GPX Merger | `uploads/gpx/{uuid}-{n}.gpx` | `processed/gpx/{uuid}.gpx` |
| Video Rotation | `uploads/video/{uuid}.mp4` | `processed/video/{uuid}.mp4` |
| OCR Tool | `uploads/image/{uuid}.{ext}` | `processed/ocr/{uuid}.txt` |

### Environment Variables Matrix
| Variable | Django | Container Apps | Functions | Key Vault | Required |
|----------|--------|----------------|-----------|-----------|----------|
| `AZURE_STORAGE_ACCOUNT_NAME` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `DB_NAME` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `DB_USER` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `DB_PASSWORD` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `DB_HOST` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `DB_PORT` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `DB_SSLMODE` | ✅ | ✅ | ✅ | Architectural Inconsistency Requiring Standardization**

- ✅ **Database**: Fully consistent
- ✅ **Most Environment Variables**: Fully consistent
- ⚠️ **Storage Account Variable**: Duplicate names need consolidation
- 🔴 **Container Architecture**: Hybrid approach (generic + tool-specific) needs standardization

**Recommendation**: **Adopt tool-specific container strategy** for better isolation, security, and management.

**Priority**: 
1. Create tool-specific containers in infrastructure (Phase 1)
2. Update Azure Functions to use tool-specific containers (Phase 2)
3. Update Django tools to use tool-specific containers (Phase 3)
4. Consolidate storage account variable names (Phase 4)
5. Verify all tools work correctly (Phase 5)

**Estimated Effort**:
- Phase 1 (Infrastructure): 30 minutes + deployment (15 min)
- Phase 2 (Azure Functions): 1 hour + testing (30 min)
- Phase 3 (Django Tools): 1.5 hours + testing (30 min)
- Phase 4 (Variable Cleanup): 15 minutes
- Phase 5 (E2E Testing): 1 hour
- **Total**: ~5-6 hours

**Risk Level**: Medium (requires coordinated updates across infrastructure, functions, and app)

**Benefits of Tool-Specific Containers**:
- ✅ Better security isolation (separate permissions per tool)
- ✅ Independent lifecycle policies (different retention per tool)
- ✅ Clearer organization and easier troubleshooting
- ✅ Simplified cost tracking and monitoring
- ✅ Eliminates subdirectory complexity
- ✅ Prevents cross-tool naming conflictsring immediate fix

**Priority**: Fix video rotation container mismatch first, then consolidate storage account variable names.

**Estimated Effort**:
- Phase 1 (Video Fix): 30 minutes + deployment time
- Phase 2 (Variable Cleanup): 15 minutes
- Phase 3 (Testing): 1 hour

**Risk Level**: Low (changes are isolated and testable)
