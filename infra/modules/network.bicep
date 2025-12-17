// Virtual Network for private endpoints and Container Apps
param location string
param namingPrefix string
param tags object

// Location abbreviation for naming
var locationAbbr = location == 'westeurope' ? 'westeurope' : location == 'northeurope' ? 'northeurope' : location == 'italynorth' ? 'italynorth' : location == 'eastus' ? 'eastus' : location == 'eastus2' ? 'eastus2' : location

var vnetName = 'vnet-${locationAbbr}-${namingPrefix}-01'

// Virtual Network with multiple subnets
resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16' // Large address space for all subnets
      ]
    }
    subnets: [
      {
        name: 'snet-container-apps'
        properties: {
          addressPrefix: '10.0.0.0/23' // /23 for Container Apps (512 IPs)
          // Delegation is automatically added by Container Apps Environment, do not pre-delegate
          serviceEndpoints: [
            {
              service: 'Microsoft.Storage'
              locations: [
                location
              ]
            }
          ]
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: '10.0.2.0/24' // /24 for private endpoints (256 IPs)
          privateEndpointNetworkPolicies: 'Disabled' // Required for private endpoints
          serviceEndpoints: [
            {
              service: 'Microsoft.Storage'
              locations: [
                location
              ]
            }
          ]
        }
      }
      {
        name: 'snet-function-apps'
        properties: {
          addressPrefix: '10.0.3.0/24' // /24 for Function Apps VNet integration (256 IPs)
          delegations: [
            {
              name: 'delegation'
              properties: {
                serviceName: 'Microsoft.App/environments' // FlexConsumption uses Container Apps infra
              }
            }
          ]
          serviceEndpoints: [
            {
              service: 'Microsoft.Storage'
              locations: [
                location
              ]
            }
            {
              service: 'Microsoft.KeyVault'
              locations: [
                '*'
              ]
            }
          ]
        }
      }
    ]
  }
}

// Outputs
output vnetId string = virtualNetwork.id
output vnetName string = virtualNetwork.name
output containerAppsSubnetId string = virtualNetwork.properties.subnets[0].id
output privateEndpointsSubnetId string = virtualNetwork.properties.subnets[1].id
output functionAppsSubnetId string = virtualNetwork.properties.subnets[2].id
