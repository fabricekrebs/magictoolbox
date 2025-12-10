# E2E Testing - Quick Reference Card

## 🚀 Quick Start

### Local Testing
```bash
# 1. Login & enable access
az login
az storage account update --name sawemagictoolboxdev01 --resource-group rg-westeurope-magictoolbox-dev-01 --default-action Allow

# 2. Run tests
source .venv/bin/activate
export USE_AZURE_CLI_AUTH=true AZURE_INTEGRATION_TEST_ENABLED=true
pytest tests/test_complete_user_workflows.py -v

# 3. Restore restrictions (optional)
az storage account update --name sawemagictoolboxdev01 --resource-group rg-westeurope-magictoolbox-dev-01 --default-action Deny
```

### GitHub Actions
1. Go to **Actions** tab → **End-to-End Tests**
2. Click **Run workflow**
3. Select environment: `dev`, `test`, or `prod`
4. Click **Run workflow**

## 📋 Checklist

### Before First Run
- [ ] Azure CLI installed (`az --version`)
- [ ] Logged in to Azure (`az login`)
- [ ] Virtual environment activated (`source .venv/bin/activate`)
- [ ] Dependencies installed (`pip install -r requirements/base.txt`)
- [ ] Storage Blob Data Contributor role assigned
- [ ] Storage account public access enabled (temporary)

### For GitHub Actions
- [ ] Environments created: dev, test, prod
- [ ] Service principal created with roles
- [ ] All secrets configured per environment
- [ ] Workflow file committed (`.github/workflows/e2e-tests.yml`)

## 🔑 Required Secrets (Per Environment)

| Secret | Description | Get With |
|--------|-------------|----------|
| `AZURE_CREDENTIALS` | Service principal JSON | `az ad sp create-for-rbac --sdk-auth` |
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account name | `sawemagictoolboxdev01` |
| `AZURE_STORAGE_CONNECTION_STRING` | Connection string | `az storage account show-connection-string` |
| `AZURE_FUNCTIONS_URL` | Functions URL | `az functionapp show --query defaultHostName` |
| `APP_URL` | Application URL | `az containerapp show --query properties.configuration.ingress.fqdn` |
| `AZURE_RESOURCE_GROUP` | Resource group | `rg-westeurope-magictoolbox-dev-01` |
| `DJANGO_SECRET_KEY` | Django secret | `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DB_HOST`, `DB_USER`, `DB_PASSWORD` | Database credentials | From Azure Portal or Key Vault |

## 🛠️ Common Commands

### Azure Storage
```bash
# Enable public access
az storage account update --name <storage-account> --resource-group <rg> --default-action Allow

# Check network rules
az storage account show --name <storage-account> --resource-group <rg> --query networkRuleSet.defaultAction

# List containers
az storage container list --account-name <storage-account> --auth-mode login
```

### Service Principal
```bash
# Create
az ad sp create-for-rbac --name "magictoolbox-github-actions-dev" --role contributor --scopes "/subscriptions/<sub-id>/resourceGroups/<rg>" --sdk-auth

# List role assignments
az role assignment list --assignee $(az account show --query user.name -o tsv)

# Add storage roles
az role assignment create --assignee-object-id <sp-id> --role "Storage Blob Data Contributor" --scope "<storage-account-resource-id>"
```

### Testing
```bash
# Run all tests
pytest tests/test_complete_user_workflows.py -v

# Run specific test
pytest tests/test_complete_user_workflows.py::TestCompleteUserWorkflow::test_06_video_rotation_complete_workflow -v

# With coverage
pytest tests/test_complete_user_workflows.py -v --cov=apps --cov-report=html

# With detailed output
pytest tests/test_complete_user_workflows.py -v -s --tb=short
```

## 🐛 Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `AuthorizationFailure` | No network access or missing role | Enable public access; verify "Storage Blob Data Contributor" role |
| `Tests skipped` | Missing env var | Set `AZURE_INTEGRATION_TEST_ENABLED=true` |
| `401 Unauthorized` | Not logged in or expired token | Run `az login` |
| `Connection timeout` | Database firewall | Check PostgreSQL firewall rules |
| `Blob not found` | Wrong container or credentials | Verify container name and connection string |

### Debug Commands
```bash
# Check login status
az account show

# Test storage access
az storage blob list --container-name media --account-name sawemagictoolboxdev01 --auth-mode login

# Verify roles
az role assignment list --all --assignee $(az account show --query user.name -o tsv) --query "[?contains(scope, 'sawemagictoolboxdev01')]"

# Check database connection
psql -h <db-host> -U <db-user> -d <db-name>
```

## 📊 Test Results

### Success Indicators
- ✅ `10 passed` - All tests successful
- ✅ `44% coverage` - Code coverage achieved
- ✅ Duration: ~40-45 seconds
- ✅ No `ERROR` or `FAILED` messages

### Test Breakdown
1. Image format converter (sync)
2. GPX analyzer (sync)
3. GPX to KML converter (sync)
4. GPX speed modifier (sync)
5. Unit converter (sync)
6. Video rotation (async)
7. PDF to DOCX converter (async)
8. Multi-user isolation
9. Error handling
10. Summary statistics

## 📚 Documentation Links

- **Full Guide**: `documentation/E2E_TESTING_GUIDE.md`
- **Implementation Summary**: `documentation/E2E_TESTING_IMPLEMENTATION.md`
- **Workflow Details**: `.github/workflows/README.md`
- **Secrets Setup**: `documentation/GITHUB_SECRETS_SETUP.md`
- **Test File**: `tests/test_complete_user_workflows.py`

## 🎯 Performance Targets

- **Individual test**: 1-5 seconds
- **Full suite**: < 60 seconds
- **Coverage**: > 40%
- **Success rate**: 100%

## 🔐 Security Notes

- Public access is only needed during test execution
- Restore network restrictions after testing
- Service principals use least privilege roles
- Connection strings stored in secrets, not code
- Test data auto-cleaned after 24 hours

## 📝 Tips

1. **Run tests in dev first** - Always test in development before test/prod
2. **Check network access** - Enable before running, restore after
3. **Use Azure CLI auth locally** - Easier than managing connection strings
4. **Monitor test duration** - Should stay under 60 seconds
5. **Review coverage reports** - Aim for increasing coverage over time
6. **Clean up regularly** - Remove old test blobs if needed

---

**Last Updated**: December 10, 2025  
**Quick Help**: For detailed information, see `documentation/E2E_TESTING_GUIDE.md`
