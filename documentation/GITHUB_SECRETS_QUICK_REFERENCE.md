# GitHub Secrets Quick Reference

## 📋 Complete Secrets Checklist

### Repository Secrets (Shared - 4 total)

```bash
☐ ACR_LOGIN_SERVER     = acrwemagictoolboxdev01.azurecr.io
☐ ACR_USERNAME         = acrwemagictoolboxdev01
☐ ACR_PASSWORD         = <from: az acr credential show>
☐ ACR_NAME             = acrwemagictoolboxdev01
```

### Development Environment Secrets (3 total)

```bash
☐ AZURE_CREDENTIALS_DEV     = <service-principal-json>
☐ RESOURCE_GROUP_DEV        = rg-westeurope-magictoolbox-dev-01
☐ CONTAINER_APP_NAME_DEV    = app-westeurope-magictoolbox-dev-01
```

### Staging Environment Secrets (3 total) - Optional

```bash
☐ AZURE_CREDENTIALS_STAGING     = <service-principal-json>
☐ RESOURCE_GROUP_STAGING        = rg-westeurope-magictoolbox-staging-01
☐ CONTAINER_APP_NAME_STAGING    = app-westeurope-magictoolbox-sta-01
```

### Production Environment Secrets (3 total)

```bash
☐ AZURE_CREDENTIALS_PROD     = <service-principal-json>
☐ RESOURCE_GROUP_PROD        = rg-westeurope-magictoolbox-prod-01
☐ CONTAINER_APP_NAME_PROD    = app-westeurope-magictoolbox-prod-01
```

---

## 🚀 Quick Setup Commands

### Option 1: Automated Setup (Recommended)

```bash
# Run the automated setup script
./scripts/setup-github-secrets.sh
```

### Option 2: Manual Setup with GitHub CLI

#### 1. Set Repository Secrets

```bash
# ACR credentials
gh secret set ACR_LOGIN_SERVER --body "acrwemagictoolboxdev01.azurecr.io"
gh secret set ACR_USERNAME --body "acrwemagictoolboxdev01"
gh secret set ACR_NAME --body "acrwemagictoolboxdev01"

# Get ACR password
ACR_PASSWORD=$(az acr credential show --name acrwemagictoolboxdev01 --query "passwords[0].value" -o tsv)
gh secret set ACR_PASSWORD --body "$ACR_PASSWORD"
```

#### 2. Create Service Principal for Development

```bash
# Create service principal
AZURE_CREDS_DEV=$(az ad sp create-for-rbac \
  --name "sp-magictoolbox-cicd-dev" \
  --role Contributor \
  --scopes "/subscriptions/fec3a155-e384-43cd-abc7-9c20391a3fd4/resourceGroups/rg-westeurope-magictoolbox-dev-01" \
  --sdk-auth)

# Set development secrets
gh secret set AZURE_CREDENTIALS_DEV --env development --body "$AZURE_CREDS_DEV"
gh secret set RESOURCE_GROUP_DEV --env development --body "rg-westeurope-magictoolbox-dev-01"
gh secret set CONTAINER_APP_NAME_DEV --env development --body "app-westeurope-magictoolbox-dev-01"
```

#### 3. Create Service Principal for Production

```bash
# Create service principal
AZURE_CREDS_PROD=$(az ad sp create-for-rbac \
  --name "sp-magictoolbox-cicd-prod" \
  --role Contributor \
  --scopes "/subscriptions/fec3a155-e384-43cd-abc7-9c20391a3fd4/resourceGroups/rg-westeurope-magictoolbox-prod-01" \
  --sdk-auth)

# Get container app name (if exists)
CONTAINER_APP_PROD=$(az containerapp list --resource-group rg-westeurope-magictoolbox-prod-01 --query "[0].name" -o tsv 2>/dev/null || echo "app-westeurope-magictoolbox-prod-01")

# Set production secrets
gh secret set AZURE_CREDENTIALS_PROD --env production --body "$AZURE_CREDS_PROD"
gh secret set RESOURCE_GROUP_PROD --env production --body "rg-westeurope-magictoolbox-prod-01"
gh secret set CONTAINER_APP_NAME_PROD --env production --body "$CONTAINER_APP_PROD"
```

---

## 🔍 Verification Commands

### Check All Secrets

```bash
# List all repository secrets
gh secret list

# List environment secrets
gh secret list --env development
gh secret list --env staging
gh secret list --env production
```

### Verify Azure Resources

```bash
# Current subscription
az account show --query "{subscription:id, tenant:tenantId}"

# ACR details
az acr list --resource-group rg-westeurope-magictoolbox-dev-01 --query "[].{name:name, loginServer:loginServer}"

# Container apps
az containerapp list --resource-group rg-westeurope-magictoolbox-dev-01 --query "[].{name:name, url:properties.configuration.ingress.fqdn}"

# Service principals
az ad sp list --display-name "sp-magictoolbox-cicd-" --query "[].{displayName:displayName, appId:appId}"
```

---

## 📊 Service Principal JSON Format

Each `AZURE_CREDENTIALS_*` secret should be a JSON object like this:

```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "fec3a155-e384-43cd-abc7-9c20391a3fd4",
  "tenantId": "af2dd59c-81cf-4524-8d9e-6d8254d02438"
}
```

---

## 🔒 Security Checklist

- [ ] Service principals have minimal permissions (Contributor on RG only)
- [ ] ACR admin user is enabled
- [ ] Production environment has required reviewers
- [ ] Branch protection rules enabled on main/develop
- [ ] Secret scanning enabled in repository settings
- [ ] Service principal credentials rotation scheduled (every 90 days)

---

## 🎯 Current Configuration

Your current Azure setup:

```yaml
Subscription: fec3a155-e384-43cd-abc7-9c20391a3fd4
Tenant: af2dd59c-81cf-4524-8d9e-6d8254d02438

Development:
  Resource Group: rg-westeurope-magictoolbox-dev-01
  Container App: app-westeurope-magictoolbox-dev-01
  Container Apps Env: env-westeurope-magictoolbox-dev-01
  ACR: acrwemagictoolboxdev01.azurecr.io
  Key Vault: kvwemagictoolboxdev01
  PostgreSQL: psql-westeurope-magictoolbox-dev-01
  Redis: red-westeurope-magictoolbox-dev-01
  Storage: sawemagictoolboxdev01
  App Insights: ai-westeurope-magictoolbox-dev-01
  Log Analytics: law-westeurope-magictoolbox-dev-01
  Location: westeurope

Production: (to be created)
  Resource Group: rg-westeurope-magictoolbox-prod-01
  Container App: app-westeurope-magictoolbox-prod-01
  Location: westeurope
```

---

## 🔗 Quick Links

- **Set Secrets**: `https://github.com/<owner>/<repo>/settings/secrets/actions`
- **Environments**: `https://github.com/<owner>/<repo>/settings/environments`
- **Actions**: `https://github.com/<owner>/<repo>/actions`
- **Azure Portal**: `https://portal.azure.com`

---

## 💡 Tips

1. **Use the automated script** - It handles everything automatically
2. **Copy Azure credentials carefully** - They're JSON and need to be exact
3. **Test in development first** - Push to develop branch before main
4. **Configure reviewers** - Add team members to production environment
5. **Monitor first deployment** - Watch the Actions tab during first run

---

## ⚠️ Troubleshooting

**Secrets not working?**
```bash
# Verify GitHub CLI authentication
gh auth status

# Verify Azure CLI authentication  
az account show

# Re-authenticate if needed
gh auth login
az login
```

**Service principal access denied?**
```bash
# Check service principal exists
az ad sp list --display-name "sp-magictoolbox-cicd-dev"

# Verify role assignment
az role assignment list --assignee <service-principal-app-id>
```

**ACR authentication failed?**
```bash
# Enable admin user
az acr update --name acrwemagictoolboxdev01 --admin-enabled true

# Get new credentials
az acr credential show --name acrwemagictoolboxdev01
```

---

For detailed instructions, see [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)
