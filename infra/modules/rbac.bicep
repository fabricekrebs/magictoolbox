// RBAC role assignments for Managed Identity access to Azure resources
param storageAccountName string
param acrName string
param keyVaultName string
param containerAppIdentityPrincipalId string
param functionAppIdentityPrincipalId string = '' // Optional, only used when Function App is deployed

// Built-in Azure Role Definition IDs
// https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var storageQueueDataContributorRoleId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
var storageTableDataContributorRoleId = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
var storageFileDataPrivilegedContributorRoleId = '69566ab7-960f-475b-8e7c-b3118f30c6bd'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull role
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6' // Key Vault Secrets User

// Reference existing resources
resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageAccountName
}

resource acr 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: acrName
}

resource keyVault 'Microsoft.KeyVault/vaults@2025-05-01' existing = {
  name: keyVaultName
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

// Grant Container App managed identity Key Vault Secrets User access
resource keyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, containerAppIdentityPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: containerAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App managed identity Storage Blob Data Contributor access (if Function App is deployed)
resource functionAppStorageBlobDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (functionAppIdentityPrincipalId != '') {
  name: guid(storageAccount.id, functionAppIdentityPrincipalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: functionAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App managed identity Key Vault Secrets User access (if Function App is deployed)
resource functionAppKeyVaultSecretsUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (functionAppIdentityPrincipalId != '') {
  name: guid(keyVault.id, functionAppIdentityPrincipalId, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: functionAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App managed identity Storage Queue Data Contributor (required for Function runtime)
resource functionAppStorageQueueDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (functionAppIdentityPrincipalId != '') {
  name: guid(storageAccount.id, functionAppIdentityPrincipalId, storageQueueDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRoleId)
    principalId: functionAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App managed identity Storage Table Data Contributor (required for Function runtime)
resource functionAppStorageTableDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (functionAppIdentityPrincipalId != '') {
  name: guid(storageAccount.id, functionAppIdentityPrincipalId, storageTableDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageTableDataContributorRoleId)
    principalId: functionAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App managed identity Storage File Data Privileged Contributor (required for WEBSITE_CONTENTSHARE)
resource functionAppStorageFileDataPrivilegedContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (functionAppIdentityPrincipalId != '') {
  name: guid(storageAccount.id, functionAppIdentityPrincipalId, storageFileDataPrivilegedContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageFileDataPrivilegedContributorRoleId)
    principalId: functionAppIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output storageRoleAssignmentId string = storageBlobDataContributorRoleAssignment.id
output acrRoleAssignmentId string = acrPullRoleAssignment.id
output keyVaultRoleAssignmentId string = keyVaultSecretsUserRoleAssignment.id
