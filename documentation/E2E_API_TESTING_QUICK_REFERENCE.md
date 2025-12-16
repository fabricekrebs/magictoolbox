# Quick Reference: Running API-Based E2E Tests

## Prerequisites

### 1. Azure CLI Authentication
```bash
# Login to Azure
az login

# Verify authentication
az account show

# Verify Storage Blob Data Contributor role
az role assignment list \
  --all \
  --assignee $(az account show --query user.name -o tsv) \
  --query "[?contains(scope, 'sawemagictoolboxdev01')]"
```

### 2. Environment Variables
```bash
# Required for tests to run
export AZURE_INTEGRATION_TEST_ENABLED=true
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=sawemagictoolboxdev01;AccountKey=..."

# Optional (for async tools)
export AZURE_FUNCTION_BASE_URL="https://func-magictoolbox-dev-rze6cb73hmijy.azurewebsites.net"

# Optional (use Azure CLI auth instead of connection string)
export USE_AZURE_CLI_AUTH=true
export AZURE_STORAGE_ACCOUNT_NAME=sawemagictoolboxdev01
```

### 3. Storage Account Network Access
```bash
# Enable public access (temporary for testing)
az storage account update \
  --name sawemagictoolboxdev01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --default-action Allow

# Verify current setting
az storage account show \
  --name sawemagictoolboxdev01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query networkRuleSet.defaultAction
```

## Running Tests

### Run All API E2E Tests
```bash
cd /home/azureuser/magictoolbox
source .venv/bin/activate
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow -v -s
```

### Run Specific API Test
```bash
# Test 1: List all tools
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow::test_api_01_list_all_tools -v -s

# Test 2: Get tool metadata
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow::test_api_02_get_tool_metadata -v -s

# Test 3: Image format converter
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow::test_api_03_image_format_converter -v -s

# Test 4: Unit converter
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow::test_api_04_unit_converter -v -s

# Test 5: Async tool workflow
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow::test_api_05_async_tool_workflow -v -s

# Test 6: Error handling
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow::test_api_06_error_handling -v -s

# Test 7: GPX tools
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow::test_api_07_gpx_tools -v -s
```

### Run with Coverage
```bash
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow \
  --cov=apps \
  --cov-report=html \
  --cov-report=term-missing \
  -v -s
```

### Run Original Tests (for comparison)
```bash
# Run original workflow tests
pytest tests/test_complete_user_workflows.py::TestCompleteUserWorkflow -v -s
```

## Test Output Format

Each test provides detailed output:

```
================================
🧪 API TEST 1: List All Tools
================================
📋 Response status: 200
📋 Response type: <class 'list'>
📋 Number of tools: 11
  ✅ Tool: base64-encoder (Base64 Encoder/Decoder)
  ✅ Tool: image-format-converter (Image Format Converter)
  ...
================================
✅ API TEST 1 PASSED: List All Tools
================================
```

## Expected Test Results

### Success Criteria

All tests should PASS with:
- ✅ HTTP status codes: 200, 201, 202, 204 (success)
- ✅ HTTP status codes: 400, 404 (expected errors)
- ✅ Response structure validation passed
- ✅ Data type validation passed
- ✅ Business logic validation passed

### Test Summary

```
📊 API E2E TESTS - FINAL SUMMARY
================================

✅ All API-based E2E tests completed successfully!

API Coverage:
  ✅ GET /api/v1/tools/ - List all tools
  ✅ GET /api/v1/tools/{name}/ - Get tool metadata
  ✅ POST /api/v1/tools/{name}/convert/ - Upload & process files
  ✅ GET /api/v1/executions/{id}/status/ - Check processing status
  ✅ GET /api/v1/executions/?tool_name={name} - List execution history
  ✅ DELETE /api/v1/executions/{id}/ - Delete execution

Tools Tested:
  ✅ image-format-converter (sync)
  ✅ unit-converter (no file upload)
  ✅ pdf-docx-converter (async)
  ✅ gpx-analyzer (sync)
  ✅ gpx-kml-converter (sync)
  ✅ gpx-speed-modifier (sync)

Validation Coverage:
  ✅ HTTP status codes (200, 201, 202, 400, 404)
  ✅ Response structure validation
  ✅ Data type validation
  ✅ Business logic validation
  ✅ Error handling validation
```

## Troubleshooting

### Test Skipped: Azure Integration Not Enabled

**Problem**: Tests are skipped with message "Azure integration tests not enabled"

**Solution**:
```bash
export AZURE_INTEGRATION_TEST_ENABLED=true
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=sawemagictoolboxdev01;AccountKey=..."
```

### Authentication Errors

**Problem**: "DefaultAzureCredential failed to retrieve token"

**Solution**:
```bash
az login
az account show  # Verify logged in
```

### Network Access Errors

**Problem**: "This request is not authorized to perform this operation"

**Solution**:
```bash
# Enable public access on storage account
az storage account update \
  --name sawemagictoolboxdev01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --default-action Allow
```

### Test Failures

**Problem**: Tests fail with unexpected status codes

**Solution**:
1. Check Django server is running: `python manage.py runserver`
2. Verify database is accessible
3. Check Azure resources are deployed
4. Review test output for specific error messages

## Quick Test Command

Copy-paste this command to run all API tests:

```bash
cd /home/azureuser/magictoolbox && \
source .venv/bin/activate && \
export AZURE_INTEGRATION_TEST_ENABLED=true && \
export AZURE_STORAGE_CONNECTION_STRING="$(az storage account show-connection-string --name sawemagictoolboxdev01 --resource-group rg-westeurope-magictoolbox-dev-01 --query connectionString -o tsv)" && \
export AZURE_FUNCTION_BASE_URL="https://func-magictoolbox-dev-rze6cb73hmijy.azurewebsites.net" && \
pytest tests/test_complete_user_workflows.py::TestCompleteAPIWorkflow -v -s
```

## Next Steps

1. **Run tests locally** to verify they work
2. **Add to CI/CD pipeline** for automated testing
3. **Monitor test results** in GitHub Actions
4. **Update tests** when adding new tools or API endpoints
5. **Review coverage reports** to ensure comprehensive testing

## Related Documentation

- [E2E Testing Guide](E2E_TESTING_GUIDE.md) - Full E2E testing documentation
- [E2E API Testing Complete](E2E_API_TESTING_COMPLETE.md) - Detailed API test documentation
- [Testing Strategy](TESTING_STRATEGY.md) - Overall testing approach
