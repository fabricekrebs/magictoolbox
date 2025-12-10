# End-to-End Testing Guide

## Overview

The comprehensive end-to-end test suite (`tests/test_complete_user_workflows.py`) validates all registered tools with real user workflows, including:

- User registration and authentication
- File upload and processing for all 7 tools
- Azure Blob Storage integration
- Database record creation and verification
- Multi-user isolation
- Error handling

## Test Coverage

### Tools Tested

1. **Image Format Converter** (sync) - PNG/JPEG conversion
2. **GPX Analyzer** (sync) - GPS track analysis
3. **GPX to KML Converter** (sync) - GPS format conversion
4. **GPX Speed Modifier** (sync) - GPS speed adjustment
5. **Unit Converter** (sync) - Unit calculations
6. **Video Rotation** (async) - Video rotation via Azure Functions
7. **PDF to DOCX Converter** (async) - PDF conversion via Azure Functions

### Test Scenarios

- ✅ Complete user workflows (registration → tool usage → cleanup)
- ✅ API endpoint authentication
- ✅ Synchronous tool processing (immediate file response)
- ✅ Asynchronous tool processing (Azure Functions + Blob Storage)
- ✅ Multi-user data isolation
- ✅ Invalid file handling
- ✅ Database integrity

## Prerequisites

### 1. Azure Resources

- Azure Storage Account with Blob Storage
- Azure Functions App (for async tools: video, PDF)
- PostgreSQL Database (configured in `.env.development`)

### 2. Azure Authentication

You must be authenticated with Azure CLI and have proper permissions:

```bash
# Login to Azure
az login

# Verify you have Storage Blob Data Contributor role
az role assignment list \
  --all \
  --assignee $(az account show --query user.name -o tsv) \
  --query "[?contains(scope, 'sawemagictoolboxdev01')]"
```

### 3. Network Access

The storage account must allow public network access during test execution:

```bash
# Enable public access (required for testing)
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

### 4. Environment Variables

Create or update `.env.development`:

```bash
# Required
AZURE_INTEGRATION_TEST_ENABLED=true
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=sawemagictoolboxdev01;..."
AZURE_STORAGE_ACCOUNT_NAME=sawemagictoolboxdev01

# Optional (for async tools)
AZURE_FUNCTIONS_URL=https://func-westeurope-magictoolbox-dev-01.azurewebsites.net

# Use Azure CLI authentication instead of connection string
USE_AZURE_CLI_AUTH=true
```

## Running Tests Locally

### Quick Start

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Set environment variables
export AZURE_INTEGRATION_TEST_ENABLED=true
export USE_AZURE_CLI_AUTH=true

# 3. Run all tests
pytest tests/test_complete_user_workflows.py -v

# 4. Run with detailed output
pytest tests/test_complete_user_workflows.py -v -s

# 5. Run specific test
pytest tests/test_complete_user_workflows.py::TestCompleteUserWorkflow::test_06_video_rotation_complete_workflow -v
```

### Authentication Options

#### Option 1: Azure CLI Authentication (Recommended for Local)

```bash
# Ensure you're logged in
az login

# Set flag to use Azure CLI credential
export USE_AZURE_CLI_AUTH=true

# Run tests
pytest tests/test_complete_user_workflows.py -v
```

**Advantages:**
- No need to manage connection strings
- Uses your Azure AD identity
- Better security (no secrets in environment)

**Requirements:**
- Must be logged in: `az login`
- Must have "Storage Blob Data Contributor" role
- Storage account must allow public access or your IP

#### Option 2: Connection String (For CI/CD)

```bash
# Use connection string from Azure portal or Key Vault
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."

# Don't set USE_AZURE_CLI_AUTH (or set to false)
unset USE_AZURE_CLI_AUTH

# Run tests
pytest tests/test_complete_user_workflows.py -v
```

**Advantages:**
- Works in CI/CD pipelines
- No need for interactive login
- Works from any location

## Test Architecture

### Synchronous Tools (Image, GPX)

```
User → API POST → Tool.process() → File Bytes Returned (200)
                                 → No Database Record
                                 → No Blob Storage
```

### Asynchronous Tools (Video, PDF)

```
User → API POST → Upload to Blob Storage → Create ToolExecution Record
                → Trigger Azure Function
                → Return executionId (202)
                → Azure Function processes in background
                → Updates ToolExecution status
```

## Test Flow

Each tool test follows this pattern:

```python
1. Register test user
2. Authenticate (force_authenticate with APIClient)
3. Access tool page (GET /tools/{tool}/)
4. Upload file (POST /api/v1/tools/{tool}/convert/)
5. Verify response (sync: file bytes, async: JSON with executionId)
6. Verify database record (async only)
7. Verify blob storage (async only)
8. Cleanup (delete records, user)
```

## Troubleshooting

### Common Issues

#### 1. AuthorizationFailure Error

```
Error: This request is not authorized to perform this operation.
ErrorCode:AuthorizationFailure
```

**Solutions:**
- Ensure `az login` is completed
- Verify role assignment: `Storage Blob Data Contributor`
- Check network access: storage account must allow public access
- Clear Azure CLI cache: `az account clear && az login`

#### 2. Tests Skipped

```
SKIPPED [1] tests/test_complete_user_workflows.py:59: 
Azure integration tests not enabled
```

**Solution:**
```bash
export AZURE_INTEGRATION_TEST_ENABLED=true
```

#### 3. Connection Timeout

```
psycopg2.OperationalError: connection to server ... timeout expired
```

**Solution:**
- Check database connection string in `.env.development`
- Verify network connectivity to PostgreSQL
- Ensure database server allows your IP

#### 4. 401 Unauthorized on API Calls

```
AssertionError: API returned 401
```

**Solution:**
- Tests use `force_authenticate()` which should prevent this
- Verify `APIClient` is being used (not Django's `Client`)
- Check that `authenticated_client` fixture is working

#### 5. Blob Upload Fails with Managed Identity

```
Error: No credential available
```

**Solution:**
- Set `USE_AZURE_CLI_AUTH=true` for local testing
- Or ensure `DefaultAzureCredential` can find credentials
- Check environment variables are set correctly

## CI/CD Integration

### GitHub Actions

See `.github/workflows/e2e-tests.yml` for automated testing workflow.

**Key Points:**
- Uses connection string authentication (stored in GitHub Secrets)
- Temporarily enables public network access
- Runs against deployed Azure environment
- Restores network restrictions after tests

### Manual Trigger

Tests can be triggered manually via GitHub Actions UI with parameters:
- Environment selection (dev/test/prod)
- Azure subscription
- Resource group

## Performance Expectations

- **Synchronous tools**: ~1-2 seconds per test
- **Asynchronous tools**: ~3-5 seconds per test (includes blob upload)
- **Full test suite**: ~30-45 seconds
- **Database operations**: Isolated test database, auto-cleanup

## Best Practices

### Local Development

1. **Always use Azure CLI auth locally**: `USE_AZURE_CLI_AUTH=true`
2. **Enable public access temporarily**: Disable after testing
3. **Use development environment**: `.env.development`
4. **Run subset of tests**: Use `-k` flag for specific tests

### CI/CD

1. **Use connection string**: Store in GitHub Secrets
2. **Automate network rules**: Enable/disable in workflow
3. **Run against deployed environment**: Test real Azure resources
4. **Cleanup after tests**: Ensure test data is removed

### Security

1. **Never commit connection strings**: Use `.env.development` (gitignored)
2. **Rotate keys regularly**: Update GitHub Secrets
3. **Use Managed Identity in production**: Only CLI auth for testing
4. **Restrict network access**: Only allow during testing

## Maintenance

### Adding New Tool Tests

1. Create test method: `test_XX_tool_name_complete_workflow`
2. Follow existing pattern (see test_01 for reference)
3. Determine if tool is sync or async
4. Add appropriate assertions
5. Update this documentation

### Updating Azure Resources

If Azure resource names change, update:
- `.env.development`
- `documentation/E2E_TESTING_GUIDE.md`
- `.github/workflows/e2e-tests.yml`
- Tool configuration in `apps/tools/plugins/`

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test output with `-v -s` flags
3. Check Azure portal for resource status
4. Review application logs in Azure Application Insights
