// Azure Storage Account for blob storage
param location string
param namingPrefix string
param tags object
param containerAppsSubnetId string = '' // Optional: Container Apps subnet for VNet rules
param functionAppsSubnetId string = '' // Optional: Function Apps subnet for VNet rules

// Location abbreviation for naming (shortened for storage 24 char limit)
var locationAbbr = location == 'westeurope' ? 'we' : location == 'northeurope' ? 'ne' : location == 'eastus' ? 'eu' : location == 'eastus2' ? 'eu2' : 'we'

// Storage account name must be 3-24 lowercase alphanumeric characters (no hyphens)
// Format: sa{locationAbbr}{app}{env}01
var storageAccountName = 'sa${locationAbbr}${replace(namingPrefix, '-', '')}01'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: take(toLower(storageAccountName), 24)
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS' // Change to Standard_ZRS or Premium_LRS for production
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false // Disable public blob access
    allowSharedKeyAccess: true // Required for connection strings
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
      defaultAction: 'Deny' // Use private endpoints and VNet rules
      ipRules: []
      virtualNetworkRules: union(
        containerAppsSubnetId != '' ? [
          {
            id: containerAppsSubnetId
            action: 'Allow'
          }
        ] : [],
        functionAppsSubnetId != '' ? [
          {
            id: functionAppsSubnetId
            action: 'Allow'
          }
        ] : []
      )
    }
  }
}

// Blob service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    cors: {
      corsRules: [
        {
          allowedOrigins: [
            '*' // Restrict to your domain in production
          ]
          allowedMethods: [
            'GET'
            'HEAD'
            'POST'
            'PUT'
            'DELETE'
          ]
          allowedHeaders: [
            '*'
          ]
          exposedHeaders: [
            '*'
          ]
          maxAgeInSeconds: 3600
        }
      ]
    }
    deleteRetentionPolicy: {
      enabled: true
      days: 7 // Increase for production
    }
  }
}

// Container for uploaded files
resource uploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'uploads'
  properties: {
    publicAccess: 'None'
  }
}

// Container for processed files
resource processedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'processed'
  properties: {
    publicAccess: 'None'
  }
}

// Container for static files
resource staticContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'static'
  properties: {
    publicAccess: 'None' // Changed to None - use CDN or Container Apps for serving
  }
}

// Container for Function App deployment packages (FlexConsumption requirement)
resource deploymentPackageContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'deploymentpackage'
  properties: {
    publicAccess: 'None'
  }
}

// Outputs
output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output storageAccountKey string = listKeys(storageAccount.id, storageAccount.apiVersion).keys[0].value
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
