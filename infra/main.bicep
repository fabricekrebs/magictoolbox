// Main orchestration template for MagicToolbox Azure infrastructure
// Last updated: 2025-12-02
targetScope = 'resourceGroup'

// Parameters
@description('The environment name (dev, staging, prod)')
@allowed([
  'dev'
  'staging'
  'prod'
])
param environment string

@description('The Azure region for all resources')
param location string = resourceGroup().location

@description('The application name')
@minLength(3)
@maxLength(24)
param appName string

@description('The administrator username for PostgreSQL')
@secure()
param postgresAdminUsername string

@description('The administrator password for PostgreSQL')
@secure()
param postgresAdminPassword string

@description('The Django secret key')
@secure()
param djangoSecretKey string

@description('Use Key Vault references in Container App (false for first deployment, true after RBAC propagates)')
param useKeyVaultReferences bool = false

@description('Tags to apply to all resources')
param tags object = {
  Application: 'MagicToolbox'
  Environment: environment
  ManagedBy: 'Bicep'
}

// Variables
var namingPrefix = '${appName}-${environment}'

// Virtual Network (deploy first for private endpoints and Container Apps)
module network './modules/network.bicep' = {
  name: 'network-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
  }
}

// Log Analytics Workspace and Application Insights (deploy first for monitoring)
module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
  }
}

// Azure Container Registry
module acr './modules/acr.bicep' = {
  name: 'acr-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
  }
}

// Azure Key Vault (for secrets management)
module keyVault './modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
    tenantId: subscription().tenantId
    environment: environment
    djangoSecretKey: djangoSecretKey
    postgresAdminPassword: postgresAdminPassword
    redisAccessKey: redis.outputs.accessKey
    storageAccountKey: storage.outputs.storageAccountKey
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    acrPassword: acr.outputs.acrPassword
    functionAppsSubnetId: network.outputs.functionAppsSubnetId
  }
}

// Azure Storage Account (for blob storage)
module storage './modules/storage.bicep' = {
  name: 'storage-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
    containerAppsSubnetId: network.outputs.containerAppsSubnetId
    functionAppsSubnetId: network.outputs.functionAppsSubnetId
  }
}

// Azure Cache for Redis
module redis './modules/redis.bicep' = {
  name: 'redis-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
  }
}

// Azure Database for PostgreSQL Flexible Server
module postgresql './modules/postgresql.bicep' = {
  name: 'postgresql-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
    administratorLogin: postgresAdminUsername
    administratorLoginPassword: postgresAdminPassword
    environment: environment
  }
}

// Azure Function App for PDF to DOCX conversion (optional - deploy when USE_AZURE_FUNCTIONS_PDF_CONVERSION=true)
module functionApp './modules/function-app.bicep' = {
  name: 'function-app-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
    storageAccountName: storage.outputs.storageAccountName
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    postgresqlServerName: postgresql.outputs.postgresServerName
    postgresqlDatabaseName: postgresql.outputs.databaseName
    postgresqlAdminUser: postgresAdminUsername
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    applicationInsightsInstrumentationKey: monitoring.outputs.applicationInsightsInstrumentationKey
    keyVaultName: keyVault.outputs.keyVaultName
  }
}

// Update storage account network rules to allow Function App access for deployments
// This must be done after Function App creation since it needs the Function App resource ID
module storageNetworkRulesUpdate './modules/storage-network-rules.bicep' = {
  name: 'storage-network-rules-update'
  params: {
    storageAccountName: storage.outputs.storageAccountName
    location: location
    tags: tags
    containerAppsSubnetId: network.outputs.containerAppsSubnetId
    functionAppsSubnetId: network.outputs.functionAppsSubnetId
    functionAppResourceId: functionApp.outputs.functionAppId
  }
}

// Azure Container Apps Environment and App (with VNet integration)
module containerApps './modules/container-apps.bicep' = {
  name: 'container-apps-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
    environment: environment
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    acrLoginServer: acr.outputs.loginServer
    acrUsername: acr.outputs.acrUsername
    acrPassword: acr.outputs.acrPassword
    useKeyVaultReferences: useKeyVaultReferences
    keyVaultUri: keyVault.outputs.keyVaultUri
    djangoSecretKey: djangoSecretKey
    postgresPassword: postgresAdminPassword
    redisAccessKey: redis.outputs.accessKey
    storageAccountKey: storage.outputs.storageAccountKey
    appInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    storageAccountName: storage.outputs.storageAccountName
    redisHostName: redis.outputs.hostName
    postgresHost: postgresql.outputs.fqdn
    postgresDatabase: postgresql.outputs.databaseName
    postgresAdminUsername: postgresAdminUsername
    containerAppsSubnetId: network.outputs.containerAppsSubnetId
    functionAppUrl: 'https://${functionApp.outputs.functionAppHostName}/api/convert/pdf-to-docx'
  }
}

// Private Endpoints for ACR, PostgreSQL, Redis, Storage, and Key Vault
module privateEndpoints './modules/private-endpoints.bicep' = {
  name: 'private-endpoints-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    tags: tags
    vnetId: network.outputs.vnetId
    privateEndpointsSubnetId: network.outputs.privateEndpointsSubnetId
    postgresServerId: postgresql.outputs.postgresServerId
    redisId: redis.outputs.redisId
    storageAccountId: storage.outputs.storageAccountId
    keyVaultId: keyVault.outputs.keyVaultId
  }
  dependsOn: [
    containerApps // Deploy private endpoints after container apps to ensure connectivity
  ]
}

// RBAC role assignments for Managed Identity (ACR, Storage, and Key Vault)
module rbac './modules/rbac.bicep' = {
  name: 'rbac-deployment'
  params: {
    storageAccountName: storage.outputs.storageAccountName
    acrName: acr.outputs.acrName
    keyVaultName: keyVault.outputs.keyVaultName
    containerAppIdentityPrincipalId: containerApps.outputs.containerAppIdentityPrincipalId
    functionAppIdentityPrincipalId: functionApp.outputs.functionAppPrincipalId
  }
}

// Outputs
output containerAppUrl string = containerApps.outputs.containerAppUrl
output containerAppName string = containerApps.outputs.containerAppName
output acrLoginServer string = acr.outputs.loginServer
output keyVaultName string = keyVault.outputs.keyVaultName
output storageAccountName string = storage.outputs.storageAccountName
output redisHostName string = redis.outputs.hostName
output postgresHost string = postgresql.outputs.fqdn
output postgresDatabase string = postgresql.outputs.databaseName
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
output applicationInsightsConnectionString string = monitoring.outputs.applicationInsightsConnectionString
output functionAppName string = functionApp.outputs.functionAppName
