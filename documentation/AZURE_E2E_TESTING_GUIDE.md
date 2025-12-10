# Azure End-to-End Testing Guide

This guide explains how to run end-to-end tests against your Azure deployment to validate all tools are working correctly in the cloud environment.

## Test Files

- **`tests/test_all_tools_e2e.py`**: Local unit tests for all tools (runs against local code)
- **`tests/test_all_tools_e2e_azure.py`**: Integration tests against Azure deployment
- **`scripts/test_azure_deployment.sh`**: Automation script for Azure testing

## Quick Start

### 1. Configure Environment Variables

Create a `.env.dev` file (or `.env.test`, `.env.prod`) with your Azure deployment URL:

```bash
# Azure deployment configuration
AZURE_TEST_BASE_URL=https://your-app-name.azurewebsites.net
AZURE_TEST_API_KEY=your-jwt-token-if-needed
AZURE_FUNCTIONS_ENABLED=true
AZURE_STORAGE_ENABLED=true
AZURE_APP_INSIGHTS_KEY=your-insights-key
```

### 2. Run Tests Against Azure

```bash
# Test development environment
./scripts/test_azure_deployment.sh dev

# Test staging environment
./scripts/test_azure_deployment.sh test

# Test production environment
./scripts/test_azure_deployment.sh prod
```

### 3. Run Specific Azure Tests

```bash
# Enable Azure testing
export AZURE_TEST_ENABLED=true
export AZURE_TEST_BASE_URL=https://your-app.azurewebsites.net

# Run all Azure tests
pytest tests/test_all_tools_e2e_azure.py -v

# Run specific test class
pytest tests/test_all_tools_e2e_azure.py::TestAzureDeployment -v

# Run deployment health checks only
pytest tests/test_all_tools_e2e_azure.py -v -k "health or homepage"
```

## Test Categories

### 1. **Deployment Health Tests**
- Health endpoint availability
- Homepage accessibility
- Static files serving
- Response time validation

### 2. **Tool Accessibility Tests**
- All tool pages are accessible
- Tool listing works
- Each tool's detail page loads

### 3. **Azure Functions Integration**
- PDF conversion triggers Azure Function
- Async processing workflow
- Status polling

### 4. **Azure Storage Tests**
- File upload to Blob Storage
- File retrieval
- Storage connectivity

### 5. **Database Connectivity**
- PostgreSQL connection
- Query execution through app
- Data persistence

### 6. **Performance Tests**
- Page load times
- API response times
- Under-threshold validation

## Running Tests in CI/CD

### GitHub Actions Integration

Add to your `.github/workflows/azure-e2e-tests.yml`:

```yaml
name: Azure E2E Tests

on:
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  test-azure-deployment:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [dev, test]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          python -m venv .venv
          source .venv/bin/activate
          pip install -r requirements/development.txt
      
      - name: Run Azure E2E Tests
        env:
          AZURE_TEST_ENABLED: true
          AZURE_TEST_BASE_URL: ${{ secrets[format('AZURE_URL_{0}', matrix.environment)] }}
          AZURE_TEST_API_KEY: ${{ secrets[format('AZURE_API_KEY_{0}', matrix.environment)] }}
        run: |
          source .venv/bin/activate
          pytest tests/test_all_tools_e2e_azure.py -v --tb=short
      
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: azure-test-results-${{ matrix.environment }}
          path: htmlcov/
```

## Continuous Monitoring

### Option 1: Scheduled Tests

Run tests on a schedule to catch deployment issues:

```bash
# Add to crontab
0 */6 * * * cd /path/to/magictoolbox && ./scripts/test_azure_deployment.sh prod >> /var/log/azure-tests.log 2>&1
```

### Option 2: Azure Monitor Integration

Use Application Insights availability tests:
- Navigate to Azure Portal → Application Insights
- Create Availability tests for key endpoints
- Configure alerts for failures

### Option 3: Post-Deployment Testing

Add to your deployment script:

```bash
# In scripts/deploy-to-azure.sh
echo "Deployment completed. Running validation tests..."
./scripts/test_azure_deployment.sh $ENVIRONMENT

if [ $? -eq 0 ]; then
    echo "✓ Deployment validation passed"
else
    echo "✗ Deployment validation failed - consider rollback"
    exit 1
fi
```

## Authentication Strategies

### Using JWT Token

```bash
# Get JWT token
TOKEN=$(curl -X POST https://your-app.azurewebsites.net/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}' | jq -r '.access')

export AZURE_TEST_API_KEY=$TOKEN
pytest tests/test_all_tools_e2e_azure.py -v
```

### Using Azure AD

For production, use managed identity or service principal:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://your-vault.vault.azure.net/", credential=credential)
api_key = client.get_secret("test-api-key").value
```

## Test Reports

### Generate HTML Report

```bash
pytest tests/test_all_tools_e2e_azure.py \
  --html=azure-test-report.html \
  --self-contained-html \
  -v
```

### View Coverage

```bash
pytest tests/test_all_tools_e2e_azure.py \
  --cov=apps \
  --cov-report=html \
  --cov-report=term
```

## Troubleshooting

### Tests Skip with "Azure testing not enabled"

```bash
# Ensure environment variable is set
export AZURE_TEST_ENABLED=true
export AZURE_TEST_BASE_URL=https://your-app.azurewebsites.net
```

### Connection Timeouts

```bash
# Increase timeout in test file or use environment variable
export AZURE_TEST_TIMEOUT=60

# Or test connectivity first
curl -v https://your-app.azurewebsites.net/health/
```

### Authentication Failures

```bash
# Test authentication manually
curl -v https://your-app.azurewebsites.net/tools/ \
  -H "Authorization: Bearer $AZURE_TEST_API_KEY"
```

### SSL Certificate Issues

```bash
# For development/testing only - not for production
export PYTHONHTTPSVERIFY=0
# Or
pytest tests/test_all_tools_e2e_azure.py --disable-warnings
```

## Best Practices

1. **Run local tests first**: Always run `test_all_tools_e2e.py` before Azure tests
2. **Test after deployment**: Include in CI/CD pipeline post-deployment
3. **Monitor regularly**: Schedule tests every 6 hours to catch issues
4. **Use staging first**: Test on dev/staging before production
5. **Keep secrets secure**: Use Key Vault or GitHub Secrets
6. **Alert on failures**: Configure notifications for test failures
7. **Test rollback**: Validate rollback procedures work

## Example Workflow

```bash
# 1. Run local tests
pytest tests/test_all_tools_e2e.py -v

# 2. Deploy to Azure (dev)
./scripts/deploy-to-azure.sh dev

# 3. Test Azure deployment
./scripts/test_azure_deployment.sh dev

# 4. If successful, deploy to production
./scripts/deploy-to-azure.sh prod

# 5. Validate production
./scripts/test_azure_deployment.sh prod

# 6. Monitor with scheduled tests
crontab -e  # Add scheduled test job
```

## Additional Resources

- [Azure Testing Documentation](https://learn.microsoft.com/azure/app-service/deploy-best-practices)
- [pytest Documentation](https://docs.pytest.org/)
- [requests Library](https://requests.readthedocs.io/)
- Application Insights for monitoring
