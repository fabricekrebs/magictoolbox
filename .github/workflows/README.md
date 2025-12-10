# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD, testing, and deployment automation.

## Available Workflows

### 1. End-to-End Tests (`e2e-tests.yml`)

**Purpose**: Run comprehensive end-to-end tests against the deployed Azure environment.

**Trigger**: Manual (workflow_dispatch)

**Features**:
- ✅ Tests all 7 registered tools with real user workflows
- ✅ Validates Azure Blob Storage integration
- ✅ Tests both synchronous and asynchronous tools
- ✅ Automatically manages storage account network rules
- ✅ Cleans up test data after completion
- ✅ Generates test reports and coverage metrics

**How to Run**:

1. Go to **Actions** tab in GitHub repository
2. Select **"End-to-End Tests"** workflow
3. Click **"Run workflow"** button
4. Select parameters:
   - **Environment**: Choose `dev`, `test`, or `prod`
   - **Skip network config**: Check if storage account already allows public access
5. Click **"Run workflow"**

**Parameters**:
- `environment` (required): Target environment to test
  - `dev` - Development environment
  - `test` - Testing environment  
  - `prod` - Production environment
- `skip_network_config` (optional): Skip automatic network rule management
  - Default: `false`
  - Set to `true` if storage account already has public access enabled

**Prerequisites**:

See [GitHub Secrets Setup](../../documentation/GITHUB_SECRETS_SETUP.md#e2e-testing-secrets) for required configuration.

**Required Secrets** (per environment):
- `AZURE_CREDENTIALS` - Service principal for Azure login
- `AZURE_STORAGE_ACCOUNT_NAME` - Storage account name
- `AZURE_STORAGE_CONNECTION_STRING` - Storage connection string
- `AZURE_FUNCTIONS_URL` - Azure Functions app URL
- `APP_URL` - Deployed application URL
- `DJANGO_SECRET_KEY` - Django secret key
- `AZURE_RESOURCE_GROUP` - Resource group name
- `DB_HOST`, `DB_USER`, `DB_PASSWORD` - Database credentials

**Workflow Steps**:

1. **Checkout code** - Gets latest code from repository
2. **Setup Python** - Installs Python 3.11 and dependencies
3. **Azure Login** - Authenticates with Azure using service principal
4. **Set environment variables** - Configures test environment
5. **Enable public network access** - Temporarily allows external access to storage
6. **Create Django environment file** - Generates `.env.testing` configuration
7. **Run E2E tests** - Executes `tests/test_complete_user_workflows.py`
8. **Restore network settings** - Reverts storage network rules to original state
9. **Upload test results** - Saves test reports and coverage data
10. **Publish results** - Creates summary in GitHub Actions UI
11. **Cleanup** - Removes old test blobs (>24 hours)

**Test Coverage**:
- Image Format Converter
- GPX Analyzer
- GPX to KML Converter
- GPX Speed Modifier
- Unit Converter
- Video Rotation (async)
- PDF to DOCX Converter (async)

**Outputs**:
- Test results XML (JUnit format)
- Code coverage report (HTML + XML)
- Test summary in GitHub Actions UI
- Artifacts retained for 30 days

**Network Security**:

The workflow automatically:
1. Captures current storage network rule (`Allow` or `Deny`)
2. Enables public access for testing (`--default-action Allow`)
3. Runs tests
4. Restores original network rule after completion

This ensures tests can access Azure Storage while maintaining security in non-test times.

**Troubleshooting**:

| Issue | Solution |
|-------|----------|
| **401 Unauthorized** | Verify service principal has correct roles |
| **Network access denied** | Ensure network rules are being managed correctly |
| **Tests skipped** | Check `AZURE_INTEGRATION_TEST_ENABLED=true` is set |
| **Database connection failed** | Verify database credentials and firewall rules |
| **Blob upload failed** | Check Storage Blob Data Contributor role |

See [E2E Testing Guide](../../documentation/E2E_TESTING_GUIDE.md) for detailed troubleshooting.

---

## Workflow Best Practices

### Security

- **Never hardcode secrets** - Always use GitHub Secrets
- **Use environments** - Separate secrets for dev/test/prod
- **Limit service principal scope** - Grant minimum required permissions
- **Rotate credentials regularly** - Update service principals every 90 days

### Testing

- **Run E2E tests after deployment** - Validate deployed application works
- **Monitor test results** - Set up notifications for failures
- **Review coverage reports** - Ensure adequate test coverage
- **Clean up test data** - Use cleanup job to remove old artifacts

### Maintenance

- **Keep workflows updated** - Review and update GitHub Actions versions
- **Document changes** - Update this README when modifying workflows
- **Test in dev first** - Always test workflow changes in dev environment
- **Monitor workflow execution time** - Optimize slow steps

## Adding New Workflows

When creating a new workflow:

1. Create `.yml` file in `.github/workflows/`
2. Use descriptive name (e.g., `deploy-production.yml`)
3. Add comprehensive documentation in comments
4. Define clear triggers (`on:` section)
5. Use environment variables and secrets appropriately
6. Include error handling and cleanup steps
7. Add workflow to this README
8. Test thoroughly in dev environment

## Related Documentation

- [E2E Testing Guide](../../documentation/E2E_TESTING_GUIDE.md) - Comprehensive testing documentation
- [GitHub Secrets Setup](../../documentation/GITHUB_SECRETS_SETUP.md) - How to configure secrets
- [Azure Deployment](../../documentation/AZURE_DEPLOYMENT_README.md) - Deployment procedures
- [Development Guidelines](../../.github/copilot-instructions.md) - Project conventions

## Support

For workflow issues:
1. Check workflow logs in GitHub Actions tab
2. Review [E2E Testing Guide](../../documentation/E2E_TESTING_GUIDE.md)
3. Verify secrets configuration
4. Test Azure CLI commands locally
5. Review service principal permissions
