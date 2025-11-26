// RBAC role assignments for Managed Identity access to Azure resources
param keyVaultName string
param storageAccountName string
param containerAppIdentityPrincipalId string

// Built-in Azure Role Definition IDs
// https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

// Reference existing resources
resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' existing = {
  name: keyVaultName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

// Grant Container App managed identity access to Key Vault secrets
resource keyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, containerAppIdentityPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: containerAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
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

// Outputs
output keyVaultRoleAssignmentId string = keyVaultSecretsUserRoleAssignment.id
output storageRoleAssignmentId string = storageBlobDataContributorRoleAssignment.id
