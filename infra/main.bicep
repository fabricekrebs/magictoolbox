// Main orchestration template for MagicToolbox Azure infrastructure
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

@description('Tags to apply to all resources')
param tags object = {
  Application: 'MagicToolbox'
  Environment: environment
  ManagedBy: 'Bicep'
}

// Variables
var namingPrefix = '${appName}-${environment}'

// Log Analytics Workspace and Application Insights (deploy first for monitoring)
module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    uniqueSuffix: '' // Not used with new naming convention
    tags: tags
  }
}

// Azure Container Registry
module acr './modules/acr.bicep' = {
  name: 'acr-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    uniqueSuffix: '' // Not used with new naming convention
    tags: tags
  }
}

// Azure Key Vault (for secrets management)
module keyVault './modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    uniqueSuffix: '' // Not used with new naming convention
    tags: tags
    tenantId: subscription().tenantId
    environment: environment
    djangoSecretKey: djangoSecretKey
    postgresAdminPassword: postgresAdminPassword
    redisAccessKey: redis.outputs.accessKey
    storageAccountKey: storage.outputs.storageAccountKey
  }
}

// Azure Storage Account (for blob storage)
module storage './modules/storage.bicep' = {
  name: 'storage-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    uniqueSuffix: '' // Not used with new naming convention
    tags: tags
  }
}

// Azure Cache for Redis
module redis './modules/redis.bicep' = {
  name: 'redis-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    uniqueSuffix: '' // Not used with new naming convention
    tags: tags
  }
}

// Azure Database for PostgreSQL Flexible Server
module postgresql './modules/postgresql.bicep' = {
  name: 'postgresql-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    uniqueSuffix: '' // Not used with new naming convention
    tags: tags
    administratorLogin: postgresAdminUsername
    administratorLoginPassword: postgresAdminPassword
    environment: environment
  }
}

// Azure Container Apps Environment and App
module containerApps './modules/container-apps.bicep' = {
  name: 'container-apps-deployment'
  params: {
    location: location
    namingPrefix: namingPrefix
    uniqueSuffix: '' // Not used with new naming convention
    tags: tags
    environment: environment
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    acrLoginServer: acr.outputs.loginServer
    keyVaultName: keyVault.outputs.keyVaultName
    storageAccountName: storage.outputs.storageAccountName
    storageAccountKey: storage.outputs.storageAccountKey
    redisHostName: redis.outputs.hostName
    redisAccessKey: redis.outputs.accessKey
    postgresHost: postgresql.outputs.fqdn
    postgresDatabase: postgresql.outputs.databaseName
    postgresAdminUsername: postgresAdminUsername
    postgresAdminPassword: postgresAdminPassword
    djangoSecretKey: djangoSecretKey
  }
}

// RBAC role assignments for Managed Identity
module rbac './modules/rbac.bicep' = {
  name: 'rbac-deployment'
  params: {
    keyVaultName: keyVault.outputs.keyVaultName
    storageAccountName: storage.outputs.storageAccountName
    containerAppIdentityPrincipalId: containerApps.outputs.containerAppIdentityPrincipalId
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
