# Deployment Verification Checklist

**Purpose:** Verify Azure infrastructure is correctly deployed and operational  
**Last Updated:** December 2, 2025

## Infrastructure Verification

### 1. Resource Group
```bash
az group show --name rg-westeurope-magictoolbox-dev-01
```
✅ **Expected:** Resource group exists in West Europe

### 2. Virtual Network
```bash
az network vnet show --name vnet-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "{addressSpace:addressSpace, subnets:subnets[].{name:name, addressPrefix:addressPrefix}}"
```
✅ **Expected:**
- Address space: `10.0.0.0/16`
- Subnets: `snet-container-apps`, `snet-private-endpoints`, `snet-function-apps`

### 3. Private Endpoints
```bash
az network private-endpoint list --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "[].{name:name, subnet:subnet.id, connections:privateLinkServiceConnections[].privateLinkServiceConnectionState.status}" -o table
```
✅ **Expected:** 5 private endpoints (Storage, Key Vault, PostgreSQL, Redis, ACR) - all **Approved**

### 4. Storage Account
```bash
# Check security settings
az storage account show --name sawemagictoolboxdev01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "{allowSharedKeyAccess:allowSharedKeyAccess, publicNetworkAccess:publicNetworkAccess, networkRuleSet:networkRuleSet}" -o json

# Check containers
az storage container list --account-name sawemagictoolboxdev01 \
  --auth-mode login --query "[].name" -o tsv
```
✅ **Expected:**
- `allowSharedKeyAccess`: `false`
- `publicNetworkAccess`: `Enabled`
- Network default action: `Deny`
- No IP rules
- Containers: `uploads`, `processed`, `deploymentpackage`, `static`

### 5. Key Vault
```bash
az keyvault show --name kvwemagictoolboxdev01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "{publicNetworkAccess:properties.publicNetworkAccess, networkAcls:properties.networkAcls}"
```
✅ **Expected:**
- `publicNetworkAccess`: `Disabled`
- Network default action: `Deny`

### 6. PostgreSQL
```bash
az postgres flexible-server show --name psql-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "{state:state, version:version, storage:storage, sku:sku}"

az postgres flexible-server db show --server-name psql-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --database-name magictoolbox
```
✅ **Expected:**
- State: `Ready`
- Database name: `magictoolbox`
- Version: 15

### 7. Container App
```bash
az containerapp show --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "{provisioningState:properties.provisioningState, runningStatus:properties.runningStatus, fqdn:properties.configuration.ingress.fqdn}"
```
✅ **Expected:**
- Provisioning state: `Succeeded`
- Running status: `Running`
- FQDN accessible via HTTPS

### 8. Function App
```bash
az functionapp show --name func-magictoolbox-dev-rze6cb73hmijy \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "{state:state, hostNames:defaultHostName, vnetRouteAllEnabled:siteConfig.appSettings[?name=='WEBSITE_VNET_ROUTE_ALL'].value}"
```
✅ **Expected:**
- State: `Running`
- `WEBSITE_VNET_ROUTE_ALL`: `1`

## Connectivity Verification

### 9. Function App → Key Vault
```bash
curl -s "https://func-magictoolbox-dev-rze6cb73hmijy.azurewebsites.net/api/db-diagnostic" | jq .
```
✅ **Expected:**
```json
{
  "connection_test": {
    "status": "success",
    "connected_to": {
      "database": "magictoolbox",
      "user": "magictoolbox"
    }
  }
}
```

### 10. Container App Health
```bash
CONTAINER_APP_URL=$(az containerapp show --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "properties.configuration.ingress.fqdn" -o tsv)

curl -s "https://$CONTAINER_APP_URL/" | grep -i magictoolbox
```
✅ **Expected:** HTML page with "MagicToolbox" title

## RBAC Verification

### 11. Container App Managed Identity Roles
```bash
CONTAINER_APP_IDENTITY=$(az containerapp show --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "identity.principalId" -o tsv)

az role assignment list --assignee $CONTAINER_APP_IDENTITY \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table
```
✅ **Expected roles:**
- Storage Blob Data Contributor
- AcrPull
- Key Vault Secrets User

### 12. Function App Managed Identity Roles
```bash
FUNCTION_APP_IDENTITY=$(az functionapp show --name func-magictoolbox-dev-rze6cb73hmijy \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "identity.principalId" -o tsv)

az role assignment list --assignee $FUNCTION_APP_IDENTITY \
  --query "[].{role:roleDefinitionName, scope:scope}" -o table
```
✅ **Expected roles:**
- Storage Blob Data Contributor
- Storage Queue Data Contributor
- Storage Table Data Contributor
- Storage File Data Privileged Contributor
- Key Vault Secrets User

## End-to-End Testing

### 13. PDF to DOCX Conversion (via Function)
```bash
# Get function key
FUNC_KEY=$(az functionapp function keys list \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --name func-magictoolbox-dev-rze6cb73hmijy \
  --function-name PdfToDocxConverter \
  --query "default" -o tsv)

# Generate UUID for test
UUID=$(python3 -c "import uuid; print(str(uuid.uuid4()))")

# Call function with existing PDF
curl -X POST "https://func-magictoolbox-dev-rze6cb73hmijy.azurewebsites.net/api/pdf-to-docx?code=$FUNC_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"execution_id\": \"$UUID\",
    \"blob_name\": \"pdf/4d25e696-7894-46c5-a676-efac38b3043d.pdf\",
    \"original_filename\": \"test.pdf\"
  }"

# Check Application Insights for success logs
sleep 10
az monitor app-insights query \
  --app ai-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --analytics-query "traces | where timestamp > ago(2m) and message contains '$UUID'" \
  --query "tables[0].rows[][1]" -o tsv
```
✅ **Expected:**
- Response: `{"status": "completed"}`
- Logs show: `✅ Successfully updated execution ... to status: completed`
- DOCX file created in `processed/docx/` container

### 14. Check Application Insights Logs
```bash
az monitor app-insights query \
  --app ai-westeurope-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --analytics-query "traces | where timestamp > ago(30m) | summarize count() by severityLevel" \
  --query "tables[0].rows" -o table
```
✅ **Expected:** Logs are being ingested (count > 0)

## Security Audit

### 15. No Public Storage Access
```bash
# Should fail without managed identity
curl -s "https://sawemagictoolboxdev01.blob.core.windows.net/uploads/" 2>&1 | grep -i "PublicAccessNotPermitted\|AuthenticationFailed"
```
✅ **Expected:** Authentication error (public access denied)

### 16. No Public Key Vault Access
```bash
# Should fail from public internet
az keyvault secret show --vault-name kvwemagictoolboxdev01 --name postgres-password 2>&1 | grep -i "ForbiddenByFirewall\|blocked"
```
✅ **Expected:** Access denied (firewall blocked)

### 17. Check for Leaked Secrets
```bash
# Verify no secrets in environment variables (from Container App)
az containerapp show --name app-we-magictoolbox-dev-01 \
  --resource-group rg-westeurope-magictoolbox-dev-01 \
  --query "properties.template.containers[0].env[?contains(name, 'PASSWORD') || contains(name, 'KEY')].value" -o table
```
✅ **Expected:** No actual secret values visible (should show Key Vault references or be empty)

## Summary Checklist

- [ ] All 5 private endpoints approved and connected
- [ ] Storage account has `allowSharedKeyAccess=false`
- [ ] Key Vault has `publicNetworkAccess=Disabled`
- [ ] PostgreSQL database name is `magictoolbox`
- [ ] Container App is running and accessible
- [ ] Function App has VNet routing enabled
- [ ] Both managed identities have correct RBAC roles
- [ ] Function diagnostic endpoint shows successful DB connection
- [ ] End-to-end PDF conversion works
- [ ] Application Insights receiving logs
- [ ] No public access to secured services
- [ ] No secrets in plain text

## Quick Verification Script

```bash
#!/bin/bash
RG="rg-westeurope-magictoolbox-dev-01"
FUNC_NAME="func-magictoolbox-dev-rze6cb73hmijy"
APP_NAME="app-we-magictoolbox-dev-01"

echo "🔍 Verifying MagicToolbox Deployment..."

echo -e "\n📦 Storage Account:"
az storage account show --name sawemagictoolboxdev01 --resource-group $RG \
  --query "{sharedKeyDisabled:allowSharedKeyAccess, publicAccess:publicNetworkAccess}" -o table

echo -e "\n🔐 Key Vault:"
az keyvault show --name kvwemagictoolboxdev01 --resource-group $RG \
  --query "{publicAccess:properties.publicNetworkAccess}" -o table

echo -e "\n🌐 Private Endpoints:"
az network private-endpoint list --resource-group $RG \
  --query "[].{name:name, status:privateLinkServiceConnections[0].privateLinkServiceConnectionState.status}" -o table

echo -e "\n📱 Container App:"
az containerapp show --name $APP_NAME --resource-group $RG \
  --query "{state:properties.runningStatus, fqdn:properties.configuration.ingress.fqdn}" -o table

echo -e "\n⚡ Function App:"
az functionapp show --name $FUNC_NAME --resource-group $RG \
  --query "{state:state, vnetRouteAll:siteConfig.vnetRouteAllEnabled}" -o table

echo -e "\n🔬 Function Database Connection Test:"
curl -s "https://$FUNC_NAME.azurewebsites.net/api/db-diagnostic" | jq '.connection_test.status'

echo -e "\n✅ Verification complete!"
```

Save as `scripts/verify-deployment.sh` and run with `bash scripts/verify-deployment.sh`
