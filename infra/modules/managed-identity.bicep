// User-Assigned Managed Identity for Container App
// This identity is assigned to the Container App for ACR pull, Storage access, and Key Vault access
param location string
param namingPrefix string
param tags object

// Create a descriptive name for the managed identity
var managedIdentityName = 'id-${namingPrefix}-containerapp'

// User-Assigned Managed Identity
resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
  tags: tags
}

// Outputs
output managedIdentityId string = managedIdentity.id
output managedIdentityName string = managedIdentity.name
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
output managedIdentityClientId string = managedIdentity.properties.clientId
