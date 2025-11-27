# GitHub Secrets Configuration - Final Reference

## ✅ Summary of Changes

Your `deploy-infrastructure.yml` workflow has been **updated** to use environment-specific secrets that match your existing naming convention.

## 📋 Required GitHub Secrets

### Repository-Level Secrets (4 total) - ✅ Already Configured

```bash
✅ ACR_LOGIN_SERVER     # acrwemagictoolboxdev01.azurecr.io
✅ ACR_USERNAME         # acrwemagictoolboxdev01
✅ ACR_PASSWORD         # From: az acr credential show
✅ ACR_NAME             # acrwemagictoolboxdev01
```

These are used by `azure-deploy.yml` for Docker image building.

### Environment-Level Secrets for Development (6 total)

**Environment name in GitHub:** `development` or `dev`

```bash
☐ AZURE_CREDENTIALS_DEV          # Service principal JSON
☐ RESOURCE_GROUP_DEV             # rg-westeurope-magictoolbox-dev-01
☐ CONTAINER_APP_NAME_DEV         # app-westeurope-magictoolbox-dev-01
☐ POSTGRES_ADMIN_PASSWORD_DEV    # PostgreSQL admin password
☐ DJANGO_SECRET_KEY_DEV          # Django secret key
☐ REDIS_ACCESS_KEY_DEV           # (Optional - for manual configs)
```

### Environment-Level Secrets for Production (6 total)

**Environment name in GitHub:** `production` or `prod`

```bash
☐ AZURE_CREDENTIALS_PROD          # Service principal JSON
☐ RESOURCE_GROUP_PROD             # rg-westeurope-magictoolbox-prod-01
☐ CONTAINER_APP_NAME_PROD         # app-westeurope-magictoolbox-prod-01
☐ POSTGRES_ADMIN_PASSWORD_PROD    # PostgreSQL admin password
☐ DJANGO_SECRET_KEY_PROD          # Django secret key
☐ REDIS_ACCESS_KEY_PROD           # (Optional - for manual configs)
```

## 🔄 How the Workflows Use Secrets

### `azure-deploy.yml` (Application Deployment)

```yaml
# Uses repository-level secrets for ACR
secrets.ACR_LOGIN_SERVER
secrets.ACR_USERNAME
secrets.ACR_PASSWORD
secrets.ACR_NAME

# Uses environment-specific secrets for deployment
secrets.AZURE_CREDENTIALS_DEV         # or _PROD based on environment
secrets.RESOURCE_GROUP_DEV            # or _PROD
secrets.CONTAINER_APP_NAME_DEV        # or _PROD
```

### `deploy-infrastructure.yml` (Infrastructure Deployment) - ✅ NOW UPDATED

```yaml
# Uses dynamic secret lookup based on environment input
secrets[format('AZURE_CREDENTIALS_{0}', upper(github.event.inputs.environment))]
secrets[format('RESOURCE_GROUP_{0}', upper(github.event.inputs.environment))]
secrets[format('POSTGRES_ADMIN_PASSWORD_{0}', upper(github.event.inputs.environment))]
secrets[format('DJANGO_SECRET_KEY_{0}', upper(github.event.inputs.environment))]
```

**Example:** If you select `dev` environment, it will use:
- `AZURE_CREDENTIALS_DEV`
- `RESOURCE_GROUP_DEV`
- `POSTGRES_ADMIN_PASSWORD_DEV`
- `DJANGO_SECRET_KEY_DEV`

## 🚀 Setup Commands

### Step 1: Generate Secrets

```bash
# Generate Django secret key
DJANGO_SECRET_DEV=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
DJANGO_SECRET_PROD=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Generate PostgreSQL passwords
POSTGRES_PASSWORD_DEV=$(openssl rand -base64 32)
POSTGRES_PASSWORD_PROD=$(openssl rand -base64 32)

# Display them (save these!)
echo "DJANGO_SECRET_DEV: $DJANGO_SECRET_DEV"
echo "DJANGO_SECRET_PROD: $DJANGO_SECRET_PROD"
echo "POSTGRES_PASSWORD_DEV: $POSTGRES_PASSWORD_DEV"
echo "POSTGRES_PASSWORD_PROD: $POSTGRES_PASSWORD_PROD"
```

### Step 2: Create Azure Service Principals

```bash
# For Development
AZURE_CREDS_DEV=$(az ad sp create-for-rbac \
  --name "sp-magictoolbox-cicd-dev" \
  --role Contributor \
  --scopes "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/rg-westeurope-magictoolbox-dev-01" \
  --sdk-auth)

# For Production
AZURE_CREDS_PROD=$(az ad sp create-for-rbac \
  --name "sp-magictoolbox-cicd-prod" \
  --role Contributor \
  --scopes "/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/rg-westeurope-magictoolbox-prod-01" \
  --sdk-auth)
```

### Step 3: Set GitHub Secrets (Using GitHub CLI)

```bash
# Development environment secrets
gh secret set AZURE_CREDENTIALS_DEV --env development --body "$AZURE_CREDS_DEV"
gh secret set RESOURCE_GROUP_DEV --env development --body "rg-westeurope-magictoolbox-dev-01"
gh secret set CONTAINER_APP_NAME_DEV --env development --body "app-westeurope-magictoolbox-dev-01"
gh secret set POSTGRES_ADMIN_PASSWORD_DEV --env development --body "$POSTGRES_PASSWORD_DEV"
gh secret set DJANGO_SECRET_KEY_DEV --env development --body "$DJANGO_SECRET_DEV"

# Production environment secrets
gh secret set AZURE_CREDENTIALS_PROD --env production --body "$AZURE_CREDS_PROD"
gh secret set RESOURCE_GROUP_PROD --env production --body "rg-westeurope-magictoolbox-prod-01"
gh secret set CONTAINER_APP_NAME_PROD --env production --body "app-westeurope-magictoolbox-prod-01"
gh secret set POSTGRES_ADMIN_PASSWORD_PROD --env production --body "$POSTGRES_PASSWORD_PROD"
gh secret set DJANGO_SECRET_KEY_PROD --env production --body "$DJANGO_SECRET_PROD"
```

### Step 4: Verify Secrets

```bash
# Check repository secrets
gh secret list

# Check environment secrets
gh secret list --env development
gh secret list --env production
```

## 🎯 Workflow Usage

### Deploy Infrastructure (Manual Trigger)

```bash
# Via GitHub CLI
gh workflow run deploy-infrastructure.yml --field environment=dev

# Or via GitHub UI
# Actions → Deploy Infrastructure → Run workflow → Select environment
```

### Deploy Application (Automatic)

```bash
# Push to develop branch → triggers deploy to dev
git push origin develop

# Push to main branch → triggers deploy to staging/prod
git push origin main
```

## 🔍 Verification Checklist

Before running workflows, verify:

```bash
# 1. Repository secrets exist
gh secret list | grep -E "ACR_"

# 2. Development environment secrets exist
gh secret list --env development | grep -E "AZURE_CREDENTIALS|RESOURCE_GROUP|CONTAINER_APP|POSTGRES|DJANGO"

# 3. Production environment secrets exist (when ready)
gh secret list --env production | grep -E "AZURE_CREDENTIALS|RESOURCE_GROUP|CONTAINER_APP|POSTGRES|DJANGO"

# 4. Azure service principals exist
az ad sp list --display-name "sp-magictoolbox-cicd-" --query "[].{Name:displayName, AppId:appId}" -o table

# 5. Resource groups exist (or ready to create)
az group list --query "[?contains(name, 'magictoolbox')]" -o table
```

## 📊 Secret Mapping

| Workflow | Secret Name Pattern | Example for Dev | Example for Prod |
|----------|---------------------|-----------------|------------------|
| `azure-deploy.yml` | `AZURE_CREDENTIALS_{ENV}` | `AZURE_CREDENTIALS_DEV` | `AZURE_CREDENTIALS_PROD` |
| `azure-deploy.yml` | `RESOURCE_GROUP_{ENV}` | `RESOURCE_GROUP_DEV` | `RESOURCE_GROUP_PROD` |
| `azure-deploy.yml` | `CONTAINER_APP_NAME_{ENV}` | `CONTAINER_APP_NAME_DEV` | `CONTAINER_APP_NAME_PROD` |
| `deploy-infrastructure.yml` | `AZURE_CREDENTIALS_{ENV}` | `AZURE_CREDENTIALS_DEV` | `AZURE_CREDENTIALS_PROD` |
| `deploy-infrastructure.yml` | `RESOURCE_GROUP_{ENV}` | `RESOURCE_GROUP_DEV` | `RESOURCE_GROUP_PROD` |
| `deploy-infrastructure.yml` | `POSTGRES_ADMIN_PASSWORD_{ENV}` | `POSTGRES_ADMIN_PASSWORD_DEV` | `POSTGRES_ADMIN_PASSWORD_PROD` |
| `deploy-infrastructure.yml` | `DJANGO_SECRET_KEY_{ENV}` | `DJANGO_SECRET_KEY_DEV` | `DJANGO_SECRET_KEY_PROD` |
| Both | `ACR_*` | Shared across all environments | Shared across all environments |

## ⚠️ Important Notes

1. **Service Principal Scope**: Create separate service principals for dev and prod with minimal permissions (Contributor on specific resource group only)

2. **Secret Rotation**: Plan to rotate secrets every 90 days:
   - Service principal credentials
   - PostgreSQL passwords (coordinate with Key Vault)
   - Django secret keys (requires app restart)

3. **Production Protection**: Configure GitHub environment protection rules:
   ```bash
   # Via GitHub UI:
   # Settings → Environments → production → Configure environment
   # - Add required reviewers
   # - Set deployment branch to 'main' only
   # - Enable wait timer (optional)
   ```

4. **Infrastructure First**: Always run `deploy-infrastructure.yml` before `azure-deploy.yml` for new environments

5. **Secret Precedence**: 
   - Bicep deployments use GitHub secrets (`POSTGRES_ADMIN_PASSWORD_DEV`, `DJANGO_SECRET_KEY_DEV`)
   - Container Apps load from Key Vault (automatically populated by Bicep)
   - Application code falls back to environment variables if Key Vault unavailable

## 🔗 Related Documentation

- `GITHUB_SECRETS_QUICK_REFERENCE.md` - Original reference (may be outdated)
- `GITHUB_SECRETS_SETUP.md` - Detailed setup instructions
- `AZURE_DEPLOYMENT_README.md` - Azure infrastructure details
- `DEVOPS_IMPLEMENTATION_SUMMARY.md` - DevOps implementation overview

---

## 📝 Summary

**What changed:**
- ✅ `deploy-infrastructure.yml` now uses environment-specific secrets with consistent naming
- ✅ Aligns with `azure-deploy.yml` secret patterns
- ✅ Supports multiple environments (dev, prod) through dynamic secret lookup

**What you need to do:**
1. Generate secrets (Django, PostgreSQL passwords)
2. Create Azure service principals (one for dev, one for prod)
3. Set GitHub secrets using the commands above
4. Create GitHub environments (`development`, `production`)
5. Test with `gh workflow run deploy-infrastructure.yml --field environment=dev`

**Result:**
Both workflows will work seamlessly with consistent secret management across your CI/CD pipeline.
