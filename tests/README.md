# MagicToolbox Tests

This directory contains the complete integration test suite for MagicToolbox.

## Single Test File Approach

**`test_complete_user_workflows.py`** - The ONLY test file you need. It tests:
- ✅ Real user registration and authentication
- ✅ All 7 tools (image, GPX, video, PDF, unit converter)
- ✅ Real Azure Blob Storage uploads/downloads
- ✅ Real Azure Functions execution (PDF conversion)
- ✅ Database operations and user isolation
- ✅ Error handling with invalid files
- ✅ Complete cleanup (blobs, database records, test user)

## Requirements

### 1. Install Dependencies
```bash
source .venv/bin/activate
pip install -r requirements/development.txt
```

### 2. Set Environment Variables
```bash
# Required
export AZURE_INTEGRATION_TEST_ENABLED=true
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"

# Optional (for PDF async processing)
export AZURE_FUNCTIONS_URL="https://your-function-app.azurewebsites.net/api/convert"
```

## Running Tests

```bash
# Run complete test suite (all tools, all scenarios)
pytest tests/test_complete_user_workflows.py -v -s

# Run specific test (e.g., only image converter)
pytest tests/test_complete_user_workflows.py::TestCompleteUserWorkflow::test_01_image_format_converter_complete_workflow -v -s

# Run without Azure (will skip all tests)
pytest tests/test_complete_user_workflows.py -v
```

## What Gets Tested

### Each Tool Workflow
1. **User Login** - Authenticate with test user
2. **Access Tool** - GET request to tool page (HTTP 200)
3. **Upload File** - POST with real file data
4. **Process** - Tool processes the file
5. **Verify Blob** - Check Azure Blob Storage for uploaded file
6. **Verify Database** - Check ToolExecution record created
7. **Cleanup** - Delete blobs and database records

### Tools Covered
1. Image Format Converter (PNG → JPEG)
2. GPX Analyzer
3. GPX to KML Converter
4. GPX Speed Modifier
5. Unit Converter
6. Video Rotation
7. PDF to DOCX Converter (with Azure Functions)

### Additional Tests
- Multi-user isolation (users can't see each other's files)
- Error handling (oversized files, wrong file types)
- Database user tracking
- Blob storage cleanup

## Test User Management

- Test user created at test start: `testuser_{uuid}@example.com`
- User persists across all tests (class scope)
- User automatically deleted at end of test run
- Uses isolated test database (not production)

## CI/CD Integration

```yaml
# .github/workflows/test.yml
- name: Run Integration Tests
  env:
    AZURE_INTEGRATION_TEST_ENABLED: true
    AZURE_STORAGE_CONNECTION_STRING: ${{ secrets.AZURE_STORAGE_CONNECTION_STRING }}
    AZURE_FUNCTIONS_URL: ${{ secrets.AZURE_FUNCTIONS_URL }}
  run: |
    source .venv/bin/activate
    pytest tests/test_complete_user_workflows.py -v
```

## Expected Output

```
🧪 TEST 1: Image Format Converter
==============================================================
📄 Step 1: Access tool page
  ✅ Tool page accessible
📤 Step 2: Upload PNG and convert to JPEG
  ✅ File uploaded and conversion initiated
💾 Step 3: Verify database record
  ✅ Database record created: ID=123, Status=completed
☁️  Step 4: Verify Azure Blob Storage
  ✅ Blob found in uploads: images/123.png
🧹 Step 5: Cleanup
  🗑️  Deleted blob: images/123.png
  ✅ Cleanup completed
==============================================================
✅ TEST 1 PASSED: Image Format Converter
==============================================================
```

## Database

Tests use Django's test database:
- Automatically created before tests
- Isolated from production database
- Automatically destroyed after tests
- Each test gets fresh state

## Troubleshooting

### Tests Skipped
```
SKIPPED - Azure integration tests not enabled
```
**Solution**: Set `AZURE_INTEGRATION_TEST_ENABLED=true` and `AZURE_STORAGE_CONNECTION_STRING`

### Blob Not Found
```
⚠️  Blob not found (may use local storage in test mode)
```
**This is OK**: Some tools may use local storage during tests or async processing

### Azure Functions Timeout
```
⏳ Waiting... (60s/60s) Status: processing
```
**This is OK**: Function may take longer, status will be "processing" or "completed"
