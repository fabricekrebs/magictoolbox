// Update Storage Account network rules to allow subnet access for Container Apps and Function Apps
// Function Apps use Managed Identity with RBAC roles for storage access (configured in rbac.bicep)

param storageAccountName string
param location string
param tags object
param containerAppsSubnetId string
param functionAppsSubnetId string

// Update network rules to add Function App resource access
// We only update networkAcls to avoid modifying other properties
resource storageAccountUpdate 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
        file: {
          enabled: true
          keyType: 'Account'
        }
      }
      keySource: 'Microsoft.Storage'
    }
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      ipRules: []
      virtualNetworkRules: [
        {
          id: containerAppsSubnetId
          action: 'Allow'
        }
        {
          id: functionAppsSubnetId
          action: 'Allow'
        }
      ]
    }
  }
}

output storageAccountId string = storageAccountUpdate.id
