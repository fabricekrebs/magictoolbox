// RBAC role assignments for Managed Identity access to Azure resources
// Note: Key Vault access removed - secrets are passed directly to Container App
param storageAccountName string
param acrName string
param containerAppIdentityPrincipalId string

// Built-in Azure Role Definition IDs
// https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull role

// Reference existing resources
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: acrName
}

// Grant Container App managed identity access to Blob Storage
resource storageBlobDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, containerAppIdentityPrincipalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: containerAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Container App managed identity ACR Pull access
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, containerAppIdentityPrincipalId, acrPullRoleId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: containerAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output storageRoleAssignmentId string = storageBlobDataContributorRoleAssignment.id
output acrRoleAssignmentId string = acrPullRoleAssignment.id
