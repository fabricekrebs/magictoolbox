// Azure Container Registry
param location string
param namingPrefix string
param tags object

// Location abbreviation for naming (shortened for ACR constraints)
var locationAbbr = location == 'westeurope' ? 'we' : location == 'northeurope' ? 'ne' : location == 'eastus' ? 'eu' : location == 'eastus2' ? 'eu2' : 'we'

// ACR name must be alphanumeric and globally unique (5-50 chars)
// Format: acr{locationAbbr}{app}{env}01
var acrName = 'acr${locationAbbr}${replace(namingPrefix, '-', '')}01'

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic' // Basic for dev/staging, Standard/Premium for production
  }
  properties: {
    adminUserEnabled: true // Enable for Container Apps managed identity pull
    publicNetworkAccess: 'Disabled' // Use private endpoints only
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
output acrUsername string = containerRegistry.listCredentials().username
output acrPassword string = containerRegistry.listCredentials().passwords[0].value
