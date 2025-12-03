// Azure Key Vault for secrets management
param location string
param namingPrefix string
param tags object
param tenantId string

// Location abbreviation for naming (shortened for KeyVault 24 char limit)
var locationAbbr = location == 'westeurope' ? 'we' : location == 'northeurope' ? 'ne' : location == 'eastus' ? 'eu' : location == 'eastus2' ? 'eu2' : 'we'

// Key Vault name must be 3-24 alphanumeric characters (no hyphens for brevity)
// Format: kv{locationAbbr}{app}{env}01
var keyVaultName = 'kv${locationAbbr}${replace(namingPrefix, '-', '')}01'

@description('Environment (dev, staging, prod)')
param environment string = 'dev'

@description('Subnet ID for Function Apps to access Key Vault')
param functionAppsSubnetId string = ''

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    tenantId: tenantId
    enableSoftDelete: true
    softDeleteRetentionInDays: environment == 'prod' ? 90 : 7
    enableRbacAuthorization: true // Use RBAC for access control (best practice)
    publicNetworkAccess: 'Disabled' // Use private endpoints only
    sku: {
      family: 'A'
      name: 'standard'
    }
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny' // Use private endpoints only
      ipRules: []
      virtualNetworkRules: !empty(functionAppsSubnetId) ? [
        {
          id: functionAppsSubnetId
          ignoreMissingVnetServiceEndpoint: false
        }
      ] : []
    }
  }
}

// Store secrets in Key Vault
@secure()
param djangoSecretKey string

@secure()
param postgresAdminPassword string

@secure()
param redisAccessKey string

@secure()
param storageAccountKey string

@secure()
param applicationInsightsConnectionString string

@secure()
param acrPassword string

resource djangoSecretKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'django-secret-key'
  properties: {
    value: djangoSecretKey
    contentType: 'text/plain'
  }
}

resource postgresPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'postgres-password'
  properties: {
    value: postgresAdminPassword
    contentType: 'text/plain'
  }
}

resource redisAccessKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'redis-access-key'
  properties: {
    value: redisAccessKey
    contentType: 'text/plain'
  }
}

resource storageAccountKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'storage-account-key'
  properties: {
    value: storageAccountKey
    contentType: 'text/plain'
  }
}

resource applicationInsightsConnectionStringSecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'appinsights-connection-string'
  properties: {
    value: applicationInsightsConnectionString
    contentType: 'text/plain'
  }
}

resource acrPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'acr-password'
  properties: {
    value: acrPassword
    contentType: 'text/plain'
  }
}

// Outputs
output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
