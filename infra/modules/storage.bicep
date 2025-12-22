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
// STANDARDIZED CONTAINER ARCHITECTURE (FR-011 Specification)
// Three containers with virtual subdirectories: uploads/{category}/, processed/{category}/, temp/
// This approach simplifies container management and aligns with Azure blob naming best practices
// ============================================================================

// Container for input files (uploads/{category}/)
resource uploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'uploads'
  properties: {
    publicAccess: 'None'
  }
}

// Container for processed/output files (processed/{category}/)
resource processedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'processed'
  properties: {
    publicAccess: 'None'
  }
}

// Container for temporary files with lifecycle management
resource tempContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'temp'
  properties: {
    publicAccess: 'None'
  }
}

// Lifecycle management policy for automatic cleanup of temp files
resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2025-06-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          enabled: true
          name: 'delete-old-temp-files'
          type: 'Lifecycle'
          definition: {
            actions: {
              baseBlob: {
                delete: {
                  daysAfterModificationGreaterThan: 1 // Delete files older than 24 hours
                }
              }
            }
            filters: {
              blobTypes: [
                'blockBlob'
              ]
              prefixMatch: [
                'temp/'
              ]
            }
          }
        }
      ]
    }
  }
}

// Outputs
output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output storageAccountKey string = listKeys(storageAccount.id, storageAccount.apiVersion).keys[0].value
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
