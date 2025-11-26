// Azure Key Vault for secrets management
param location string
param namingPrefix string
param uniqueSuffix string
param tags object
param tenantId string

// Key Vault name must be 3-24 alphanumeric characters and hyphens
// Keep it short: kv + appname + env + 6 chars = max 20 chars
var keyVaultName = 'kv${take(replace(namingPrefix, '-', ''), 12)}${take(uniqueSuffix, 6)}'

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
    softDeleteRetentionInDays: 7 // Minimum for dev, 90 for production
    enableRbacAuthorization: true // Use RBAC instead of access policies
    publicNetworkAccess: 'Enabled'
    sku: {
      family: 'A'
      name: 'standard'
    }
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow' // Change to 'Deny' for production with VNet integration
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

// Outputs
output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output keyVaultUri string = keyVault.properties.vaultUri
