// Azure Storage Account for blob storage
param location string
param namingPrefix string
param tags object
param containerAppsSubnetId string = '' // Optional: Container Apps subnet for VNet rules
param functionAppsSubnetId string = '' // Optional: Function Apps subnet for VNet rules
param functionAppResourceId string = '' // Optional: Function App resource ID for deployment access

// Location abbreviation for naming (shortened for storage 24 char limit)
var locationAbbr = location == 'westeurope' ? 'we' : location == 'northeurope' ? 'ne' : location == 'eastus' ? 'eu' : location == 'eastus2' ? 'eu2' : location == 'italynorth' ? 'in' : 'we'

// Storage account name must be 3-24 lowercase alphanumeric characters (no hyphens)
// Format: sa{locationAbbr}{app}{env}01
var storageAccountName = 'sa${locationAbbr}${replace(namingPrefix, '-', '')}01'

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' = {
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
      resourceAccessRules: functionAppResourceId != '' ? [
        {
          tenantId: subscription().tenantId
          resourceId: functionAppResourceId
        }
      ] : []
    }
  }
}

// Blob service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' = {
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
      enabled: false // Disabled: No soft delete for blobs
    }
    containerDeleteRetentionPolicy: {
      enabled: false // Disabled: No soft delete for containers
    }
  }
}

// Container for static files
resource staticContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'static'
  properties: {
    publicAccess: 'None' // Changed to None - use CDN or Container Apps for serving
  }
}

// Container for Function App deployment packages (FlexConsumption requirement)
resource deploymentsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'deployments'
  properties: {
    publicAccess: 'None'
  }
}

// ============================================================================
// TOOL-SPECIFIC CONTAINERS (Recommended Architecture)
// Each tool has dedicated upload and processed containers for better isolation
// ============================================================================

// PDF Tool Containers
resource pdfUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'pdf-uploads'
  properties: {
    publicAccess: 'None'
  }
}

resource pdfProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'pdf-processed'
  properties: {
    publicAccess: 'None'
  }
}

// Image Tool Containers
resource imageUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'image-uploads'
  properties: {
    publicAccess: 'None'
  }
}

resource imageProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'image-processed'
  properties: {
    publicAccess: 'None'
  }
}

// GPX Tool Containers
resource gpxUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'gpx-uploads'
  properties: {
    publicAccess: 'None'
  }
}

resource gpxProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'gpx-processed'
  properties: {
    publicAccess: 'None'
  }
}

// Video Tool Containers
resource videoUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'video-uploads'
  properties: {
    publicAccess: 'None'
  }
}

resource videoProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'video-processed'
  properties: {
    publicAccess: 'None'
  }
}

// OCR Tool Containers
resource ocrUploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'ocr-uploads'
  properties: {
    publicAccess: 'None'
  }
}

resource ocrProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'ocr-processed'
  properties: {
    publicAccess: 'None'
  }
}

// Outputs
output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output storageAccountKey string = listKeys(storageAccount.id, storageAccount.apiVersion).keys[0].value
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
