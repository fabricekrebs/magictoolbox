// Azure Function App for PDF to DOCX conversion
// This module deploys a consumption-based Function App with blob trigger

param location string
param namingPrefix string
param tags object

// Dependencies
param storageAccountId string
param storageAccountName string
param logAnalyticsWorkspaceId string
param keyVaultName string

// Database connection (for updating ToolExecution records)
param postgresqlServerName string
param postgresqlDatabaseName string
param postgresqlAdminUser string
@secure()
param postgresqlAdminPassword string

// Application Insights
param applicationInsightsConnectionString string

// Function App names
var functionAppName = 'func-${namingPrefix}-${uniqueString(resourceGroup().id)}'
var appServicePlanName = 'plan-${namingPrefix}-func-${uniqueString(resourceGroup().id)}'

// App Service Plan (Consumption for serverless)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: 'Y1'  // Consumption (serverless) plan
    tier: 'Dynamic'
  }
  properties: {
    reserved: true  // Linux
  }
  kind: 'functionapp,linux'
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'  // Managed Identity for keyless authentication
  }
  properties: {
    serverFarmId: appServicePlan.id
    reserved: true  // Linux
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'  // Python 3.11 runtime
      alwaysOn: false  // Not available in consumption plan
      functionAppScaleLimit: 10  // Max concurrent instances
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=listKeys(${storageAccountId}, \'2023-01-01\').keys[0].value;EndpointSuffix=core.windows.net'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};AccountKey=listKeys(${storageAccountId}, \'2023-01-01\').keys[0].value;EndpointSuffix=core.windows.net'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsConnectionString
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT_NAME'
          value: storageAccountName
        }
        {
          name: 'DB_HOST'
          value: '${postgresqlServerName}.postgres.database.azure.com'
        }
        {
          name: 'DB_NAME'
          value: postgresqlDatabaseName
        }
        {
          name: 'DB_USER'
          value: postgresqlAdminUser
        }
        {
          name: 'DB_PASSWORD'
          value: postgresqlAdminPassword
        }
        {
          name: 'DB_PORT'
          value: '5432'
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'ENABLE_ORYX_BUILD'
          value: 'true'
        }
      ]
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      cors: {
        allowedOrigins: [
          '*'  // Configure properly for production
        ]
      }
    }
    httpsOnly: true
  }
}

// Reference to existing storage account for RBAC
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

// Reference to existing Key Vault for RBAC
resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' existing = {
  name: keyVaultName
}

// Grant Function App "Storage Blob Data Contributor" role on storage account
// This allows the function to read/write blobs using Managed Identity
resource blobContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, storageAccountId, 'Storage Blob Data Contributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe'  // Storage Blob Data Contributor
    )
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Grant Function App access to Key Vault secrets (optional)
resource keyVaultSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, keyVaultName, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'  // Key Vault Secrets User
    )
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Diagnostic settings for Function App
resource functionAppDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'function-app-diagnostics'
  scope: functionApp
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    logs: [
      {
        category: 'FunctionAppLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 30
        }
      }
    ]
  }
}

// Outputs
output functionAppId string = functionApp.id
output functionAppName string = functionApp.name
output functionAppPrincipalId string = functionApp.identity.principalId
output functionAppHostName string = functionApp.properties.defaultHostName
output appServicePlanId string = appServicePlan.id
