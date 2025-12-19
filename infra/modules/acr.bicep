// Azure Container Registry
param location string
param namingPrefix string
param tags object

// Location abbreviation for naming (shortened for ACR constraints)
var locationAbbr = location == 'westeurope' ? 'we' : location == 'northeurope' ? 'ne' : location == 'italynorth' ? 'in' : location == 'eastus' ? 'eu' : location == 'eastus2' ? 'eu2' : 'we'

// ACR name must be alphanumeric and globally unique (5-50 chars)
// Format: acr{locationAbbr}{app}{env}01
var acrName = 'acr${locationAbbr}${replace(namingPrefix, '-', '')}01'

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-11-01' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic' // Basic for dev/staging, Standard/Premium for production
  }
  properties: {
    adminUserEnabled: true // Enable for Container Apps managed identity pull
    publicNetworkAccess: 'Enabled' // Basic SKU doesn't support private endpoints
    zoneRedundancy: 'Disabled' // Enable for production with Premium SKU
    policies: {
      quarantinePolicy: {
        status: 'Disabled'
      }
      trustPolicy: {
        type: 'Notary'
        status: 'Disabled'
      }
      retentionPolicy: {
        days: 7
        status: 'Disabled'
      }
    }
    encryption: {
      status: 'Disabled'
    }
    dataEndpointEnabled: false
    networkRuleBypassOptions: 'AzureServices'
  }
}

// Outputs
output acrId string = containerRegistry.id
output acrName string = containerRegistry.name
output loginServer string = containerRegistry.properties.loginServer
