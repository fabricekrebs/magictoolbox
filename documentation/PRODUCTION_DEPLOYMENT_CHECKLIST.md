# Production Deployment Checklist

**Last Updated**: December 23, 2025  
**Quick Reference**: Use this checklist when deploying to a new Azure subscription  
**Full Guide**: See [PRODUCTION_SUBSCRIPTION_DEPLOYMENT.md](./PRODUCTION_SUBSCRIPTION_DEPLOYMENT.md)

---

## 🎯 Pre-Deployment (30 minutes)

### Azure Setup
- [ ] New Azure subscription ID ready: `________________`
- [ ] Login: `az login`
- [ ] Set subscription: `az account set --subscription <id>`
- [ ] Create resource group: `az group create --name rg-italynorth-magictoolbox-prod-01 --location italynorth`

### Generate Secrets
```bash
# Django Secret
DJANGO_SECRET_PROD=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# PostgreSQL Password
POSTGRES_PASSWORD_PROD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

# SAVE THESE VALUES!
```

### Service Principal
```bash
SP_NAME_PROD="sp-magictoolbox-cicd-prod"
PROD_SUBSCRIPTION_ID="<your-subscription-id>"

# Create with Contributor role
SP_JSON=$(az ad sp create-for-rbac \
  --name "$SP_NAME_PROD" \
  --role Contributor \
  --scopes "/subscriptions/$PROD_SUBSCRIPTION_ID" \
  --sdk-auth)

# Get App ID
SP_APP_ID=$(az ad sp list --display-name "$SP_NAME_PROD" --query "[0].appId" -o tsv)

# Add User Access Administrator role
az role assignment create \
  --assignee "$SP_APP_ID" \
  --role "User Access Administrator" \
  --scope "/subscriptions/$PROD_SUBSCRIPTION_ID"
```

- [ ] Service principal created
- [ ] Both roles assigned (Contributor + User Access Administrator)
- [ ] JSON output saved

---

## 🔐 GitHub Configuration (15 minutes)

### Create Production Environment
- [ ] Go to repo **Settings** → **Environments**
- [ ] Create environment: `Production`
- [ ] Enable **Required reviewers**
- [ ] Set deployment branches: `main` only

### Add Repository Secrets
```bash
gh secret set AZURE_CREDENTIALS_PROD --body "$SP_JSON"
gh secret set RESOURCE_GROUP_PROD --env Production --body "rg-italynorth-magictoolbox-prod-01"
gh secret set POSTGRES_ADMIN_PASSWORD_PROD --body "$POSTGRES_PASSWORD_PROD"
gh secret set DJANGO_SECRET_KEY_PROD --body "$DJANGO_SECRET_PROD"
```

- [ ] `AZURE_CREDENTIALS_PROD`
- [ ] `RESOURCE_GROUP_PROD`
- [ ] `POSTGRES_ADMIN_PASSWORD_PROD`
- [ ] `DJANGO_SECRET_KEY_PROD`
- [ ] ACR secrets verified (from dev): `ACR_LOGIN_SERVER`, `ACR_USERNAME`, `ACR_PASSWORD`

---

## 🏗️ Infrastructure Deployment (20 minutes)

### Option A: GitHub Actions (Recommended)
- [ ] Go to **Actions** → **Deploy Infrastructure**
- [ ] Click **Run workflow**
- [ ] Select: Branch=`main`, Environment=`prod`, Destroy=`false`
- [ ] Monitor deployment progress (~15-20 min)

### Option B: Manual CLI
```bash
cd /home/azureuser/magictoolbox/infra

az deployment group create \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --template-file main.bicep \
  --parameters parameters.prod.json \
  --parameters \
    postgresAdminPassword="$POSTGRES_PASSWORD_PROD" \
    djangoSecretKey="$DJANGO_SECRET_PROD" \
    useKeyVaultReferences=false
```

### Verify Deployment
```bash
# List resources
az resource list --resource-group rg-italynorth-magictoolbox-prod-01 --output table

# Check containers
STORAGE_ACCOUNT=$(az storage account list --resource-group rg-italynorth-magictoolbox-prod-01 --query "[0].name" -o tsv)
az storage container list --account-name $STORAGE_ACCOUNT --auth-mode login --output table
```

- [ ] Virtual Network deployed
- [ ] Storage Account with containers: `pdf-uploads`, `pdf-processed`, `image-uploads`, `image-processed`, `video-uploads`, `video-processed`, `gpx-uploads`, `gpx-processed`, `ocr-uploads`, `ocr-processed`
- [ ] PostgreSQL Flexible Server deployed
- [ ] Azure Cache for Redis deployed
- [ ] Key Vault deployed
- [ ] Container Apps Environment deployed
- [ ] Function App deployed

---

## 🚀 Application Deployment (10 minutes)

### Deploy Container App
```bash
# Merge to main or use workflow dispatch
git checkout main
git merge develop
git push origin main
```

- [ ] GitHub Actions workflow triggered
- [ ] Docker image built and pushed
- [ ] Container App updated
- [ ] Deployment successful

### Verify Application
```bash
CONTAINER_APP_URL=$(az containerapp show \
  --name app-magictoolbox-prod \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

curl -s "https://$CONTAINER_APP_URL/api/v1/health/" | python -m json.tool
```

- [ ] Health endpoint returns 200 OK
- [ ] Application accessible

---

## ⚡ Azure Functions Deployment (5 minutes)

```bash
cd /home/azureuser/magictoolbox/function_app

FUNCTION_APP_NAME=$(az functionapp list \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --query "[0].name" \
  --output tsv)

func azure functionapp publish $FUNCTION_APP_NAME --python
```

### Verify Functions
```bash
FUNCTION_URL=$(az functionapp show \
  --name $FUNCTION_APP_NAME \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --query defaultHostName \
  --output tsv)

curl -s "https://$FUNCTION_URL/api/health?detailed=true" | python -m json.tool
```

- [ ] Functions deployed
- [ ] Health endpoint returns healthy

---

## 🔒 Security & Admin (10 minutes)

### Create Admin User
```bash
az containerapp exec \
  --name app-magictoolbox-prod \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --command "/bin/bash"

# Inside container:
python manage.py createsuperuser
exit
```

- [ ] Superuser created
- [ ] Admin panel accessible at `/admin/`

### Verify Security
- [ ] No public access to PostgreSQL
- [ ] No public access to Redis
- [ ] No public access to Storage (only via Container App/Functions)
- [ ] All secrets in Key Vault
- [ ] HTTPS enforced
- [ ] Managed Identity configured

---

## 📊 Monitoring Setup (10 minutes)

### Application Insights
```bash
APP_INSIGHTS_KEY=$(az monitor app-insights component show \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --query "[0].instrumentationKey" \
  --output tsv)
```

- [ ] Application Insights receiving telemetry
- [ ] Live metrics visible in Azure Portal
- [ ] Logs flowing to Log Analytics

### Configure Alerts
```bash
# High CPU alert
az monitor metrics alert create \
  --name "High CPU Usage" \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --scopes "/subscriptions/$PROD_SUBSCRIPTION_ID/resourceGroups/rg-italynorth-magictoolbox-prod-01/providers/Microsoft.App/containerApps/app-magictoolbox-prod" \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m
```

- [ ] CPU alert configured
- [ ] Memory alert configured
- [ ] Error rate alert configured
- [ ] Database connection alert configured

---

## ✅ Final Verification (10 minutes)

### Functional Testing
- [ ] Homepage loads correctly
- [ ] Tool selection works
- [ ] File upload successful
- [ ] PDF to DOCX conversion works
- [ ] Video rotation works
- [ ] Image conversion works
- [ ] OCR tool works
- [ ] GPX tools work
- [ ] History section loads
- [ ] Download functionality works

### Performance Testing
- [ ] Page load time < 2 seconds
- [ ] File upload responsive
- [ ] Async processing updates status correctly
- [ ] No errors in browser console

### Monitoring
- [ ] Application Insights dashboard shows data
- [ ] Logs visible in Log Analytics
- [ ] Alerts configured and active

---

## 📝 Post-Deployment Tasks

### Documentation
- [ ] Update README with production URL
- [ ] Document production-specific configurations
- [ ] Add production contact information

### Backup & DR
- [ ] Verify PostgreSQL automated backups enabled (default)
- [ ] Configure blob lifecycle policies for cleanup
- [ ] Document disaster recovery procedures

### Optimization
- [ ] Review Container App scaling settings
- [ ] Optimize Redis cache policies
- [ ] Consider CDN for static assets

### Security Review
- [ ] Audit all RBAC assignments
- [ ] Enable Azure Defender
- [ ] Review network security groups
- [ ] Schedule regular security audits

---

## 🆘 Quick Troubleshooting

### Deployment Failed
```bash
# Check deployment logs
az deployment group list --resource-group rg-italynorth-magictoolbox-prod-01 --output table

# View specific deployment
az deployment group show \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --name <deployment-name>
```

### Container App Won't Start
```bash
# View logs
az containerapp logs show \
  --name app-magictoolbox-prod \
  --resource-group rg-italynorth-magictoolbox-prod-01 \
  --follow
```

### Function App Not Responding
```bash
# Restart Function App
az functionapp restart \
  --name $FUNCTION_APP_NAME \
  --resource-group rg-italynorth-magictoolbox-prod-01
```

---

## 🎉 Deployment Complete!

**Total Time**: ~90-120 minutes

**Production URL**: `https://<container-app-fqdn>`

**Next Steps**:
1. Monitor application for first 24 hours
2. Review Application Insights for anomalies
3. Test all critical user flows
4. Update status page/documentation
5. Notify stakeholders of successful deployment

---

**For detailed instructions**, see [PRODUCTION_SUBSCRIPTION_DEPLOYMENT.md](./PRODUCTION_SUBSCRIPTION_DEPLOYMENT.md)

**Last Updated**: December 17, 2025
