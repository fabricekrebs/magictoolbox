# PDF Conversion Troubleshooting & Resolution Summary

**Date**: December 9, 2025  
**Issue**: Uploaded PDF file remained in "pending" status  
**Resolution**: Azure Function was only reading blob metadata, not performing actual conversion

## Problem Analysis

### Initial Symptoms
- User uploaded a PDF file via the web interface
- File status remained "pending" indefinitely
- No conversion was happening

### Root Cause
The Azure Function (`/api/pdf/convert`) was implemented with only **Step 1** logic:
- ✅ Reading blob from storage
- ✅ Returning metadata
- ❌ **NOT** converting the PDF
- ❌ **NOT** updating database status
- ❌ **NOT** uploading DOCX output

This was intentional during incremental testing but was never completed with the full conversion logic.

## Investigation Process

### 1. Checked Container App Logs
```bash
az containerapp logs show --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 --tail 100
```

**Findings:**
- ✅ PDF uploaded successfully to blob storage
- ✅ Azure Function triggered successfully (HTTP 200)
- ✅ Function returned blob metadata
- ❌ But status remained "pending" (no further processing)

### 2. Checked Database Status
```bash
az containerapp exec --command "python manage.py shell ..."
```

**Findings:**
```
ID: 38f56cbd-2e1e-445b-9137-97e0f675fb5b
Status: pending
Azure Function Invoked: True
Input Blob Path: uploads/pdf/38f56cbd-2e1e-445b-9137-97e0f675fb5b.pdf
Output Blob Path: (empty)
Error Message: (empty)
```

### 3. Analyzed Azure Function Code
The function (`function_app.py`) was simplified for testing:
- Only read blob and returned metadata
- Did not perform PDF → DOCX conversion
- Did not update database
- Did not upload output file

## Solution Implementation

### Changes Made

#### 1. Updated Azure Function (`function_app/function_app.py`)
Added complete conversion workflow:

```python
@app.route(route="pdf/convert", methods=["POST"])
def convert_pdf_to_docx(req: func.HttpRequest) -> func.HttpResponse:
    """Full PDF to DOCX conversion workflow with database tracking."""
    
    # 1. Update database: processing
    cursor.execute(
        "UPDATE tool_executions SET status = %s WHERE id = %s",
        ('processing', execution_id)
    )
    
    # 2. Download PDF from blob storage
    blob_client.download_blob() -> temp_pdf_path
    
    # 3. Convert PDF to DOCX using pdf2docx
    cv = Converter(temp_pdf_path)
    cv.convert(temp_docx_path)
    
    # 4. Upload DOCX to blob storage
    output_blob_client.upload_blob(docx_file)
    
    # 5. Update database: completed
    cursor.execute(
        """UPDATE tool_executions 
           SET status = %s, output_blob_path = %s, output_size = %s,
               completed_at = NOW()
           WHERE id = %s""",
        ('completed', output_blob_path, docx_size, execution_id)
    )
    
    # 6. Cleanup temp files
    Path(temp_pdf_path).unlink()
    Path(temp_docx_path).unlink()
```

#### 2. Preserved Testing Versions
- `function_app_step1.py`: Original simplified version (blob read only)
- `function_app_full_conversion.py`: Full implementation copy
- `function_app.py`: Active version with full conversion

#### 3. Deployed to Azure
```bash
git add function_app/function_app.py function_app/function_app_step1.py
git commit -m "feat: implement full PDF to DOCX conversion in Azure Function"
git push origin develop
```

GitHub Actions automatically deployed the updated function.

## Verification

### 1. Manual Test of Pending Conversion
```bash
curl -X POST https://func-magictoolbox-dev-rze6cb73hmijy.azurewebsites.net/api/pdf/convert \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "38f56cbd-2e1e-445b-9137-97e0f675fb5b",
    "blob_name": "uploads/pdf/38f56cbd-2e1e-445b-9137-97e0f675fb5b.pdf"
  }'
```

**Response:**
```json
{
  "status": "success",
  "execution_id": "38f56cbd-2e1e-445b-9137-97e0f675fb5b",
  "input_blob": "uploads/pdf/38f56cbd-2e1e-445b-9137-97e0f675fb5b.pdf",
  "output_blob": "processed/docx/38f56cbd-2e1e-445b-9137-97e0f675fb5b.docx",
  "output_size_bytes": 39001,
  "output_size_mb": 0.04
}
```

### 2. Database Status Verification
```
Status: completed ✅
Input Size: 49,672 bytes
Output Size: 39,001 bytes
Input Blob Path: uploads/pdf/38f56cbd-2e1e-445b-9137-97e0f675fb5b.pdf
Output Blob Path: processed/docx/38f56cbd-2e1e-445b-9137-97e0f675fb5b.docx
Completed: 2025-12-09 05:00:05+00:00
```

## Full Workflow Now Operational

### End-to-End Process
1. **User uploads PDF** via web interface
2. **Django backend**:
   - Validates file (type, size)
   - Uploads to `uploads/pdf/{execution_id}.pdf`
   - Creates database record (status: `pending`)
   - Triggers Azure Function via HTTP POST
3. **Azure Function**:
   - Updates DB status to `processing`
   - Downloads PDF from blob storage
   - Converts PDF → DOCX using `pdf2docx` library
   - Uploads DOCX to `processed/docx/{execution_id}.docx`
   - Updates DB status to `completed` with output metadata
   - Cleans up temp files
4. **User can download** converted DOCX from web interface

### Error Handling
- If conversion fails, status is updated to `failed`
- Error message is stored in database
- Temp files are cleaned up even on failure
- Comprehensive logging throughout process

## Key Takeaways

### What Worked Well
- ✅ Incremental testing approach (Step 1 first)
- ✅ Comprehensive logging at each step
- ✅ Database tracking fields for Azure Functions
- ✅ Managed Identity for secure blob access

### What Was Missing
- The Step 1 implementation was left in production too long
- Full conversion logic should have been added immediately after Step 1 verification

### Recommendations
1. **Always complete the full workflow** after initial testing
2. **Monitor Azure Function logs** for errors (Application Insights)
3. **Set up alerts** for failed conversions
4. **Add retry logic** for transient failures
5. **Consider timeouts** for large PDF files

## Commands for Future Troubleshooting

### Check Recent Conversions
```bash
az containerapp exec --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --command "python manage.py shell -c \"
from apps.tools.models import ToolExecution
from django.utils import timezone
from datetime import timedelta

recent = timezone.now() - timedelta(hours=1)
execs = ToolExecution.objects.filter(
    created_at__gte=recent,
    tool_name='pdf-docx-converter'
).order_by('-created_at')

for e in execs:
    print(f'{e.id}: {e.status} - {e.input_filename}')
\""
```

### Manually Trigger Conversion
```bash
curl -X POST https://func-magictoolbox-dev-rze6cb73hmijy.azurewebsites.net/api/pdf/convert \
  -H "Content-Type: application/json" \
  -d '{"execution_id": "<UUID>", "blob_name": "uploads/pdf/<UUID>.pdf"}'
```

### Check Function Health
```bash
curl https://func-magictoolbox-dev-rze6cb73hmijy.azurewebsites.net/api/health
```

### View Container App Logs
```bash
az containerapp logs show --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 --tail 50
```

## Resolution Confirmed ✅

- **Issue**: Pending conversions not processing
- **Cause**: Incomplete Azure Function implementation
- **Fix**: Added full PDF → DOCX conversion logic with database updates
- **Status**: ✅ Working end-to-end
- **Verified**: Manually tested pending conversion - now completed successfully
