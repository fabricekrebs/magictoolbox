// Azure Key Vault for secrets management
param location string
param namingPrefix string
param uniqueSuffix string
param tags object
param tenantId string

// Key Vault name must be 3-24 alphanumeric characters and hyphens
// Keep it short: kv + appname + env + 6 chars = max 20 chars
var keyVaultName = 'kv${take(replace(namingPrefix, '-', ''), 12)}${take(uniqueSuffix, 6)}'

@description('Environment (dev, staging, prod)')
param environment string = 'dev'

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
    publicNetworkAccess: 'Enabled'
    sku: {
      family: 'A'
      name: 'standard'
    }
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow' // Use 'Deny' with private endpoints for production
      ipRules: []
      virtualNetworkRules: []
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

// Outputs
output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
