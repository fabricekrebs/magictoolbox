// Azure Function App for PDF to DOCX conversion
// This module deploys a consumption-based Function App with blob trigger

param location string
param namingPrefix string
param tags object

// Dependencies
param storageAccountName string
param logAnalyticsWorkspaceId string

// Database connection (for updating ToolExecution records)
param postgresqlServerName string
param postgresqlDatabaseName string
param postgresqlAdminUser string

// Application Insights
param applicationInsightsConnectionString string

// VNet integration (not supported in Consumption plan Y1)
// param functionAppsSubnetId string

// Key Vault (for secret references)
param keyVaultName string

// Function App names
var functionAppName = 'func-${namingPrefix}-${uniqueString(resourceGroup().id)}'
var appServicePlanName = 'plan-consumption-${namingPrefix}-${uniqueString(resourceGroup().id)}'

// App Service Plan (Consumption Y1 for blob trigger support)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: 'Y1'  // Consumption plan
    tier: 'Dynamic'
  }
  properties: {
    reserved: true  // Linux
  }
  kind: 'functionapp'
}

// Function App
resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
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
      appSettings: [
        // Identity-based storage connection (no shared key needed)
        {
          name: 'AzureWebJobsStorage__accountName'
          value: storageAccountName
        }
        {
          name: 'AzureWebJobsStorage__credential'
          value: 'managedidentity'
        }
        {
          name: 'AzureWebJobsStorage__clientId'
          value: 'system'
        }
        // Blob service identity-based connection
        {
          name: 'AzureWebJobsStorage__blobServiceUri'
          value: 'https://${storageAccountName}.blob.${environment().suffixes.storage}'
        }
        {
          name: 'AzureWebJobsStorage__queueServiceUri'
          value: 'https://${storageAccountName}.queue.${environment().suffixes.storage}'
        }
        {
          name: 'AzureWebJobsStorage__tableServiceUri'
          value: 'https://${storageAccountName}.table.${environment().suffixes.storage}'
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
          value: '@Microsoft.KeyVault(SecretUri=https://${keyVaultName}.vault.${environment().suffixes.keyvaultDns}/secrets/postgres-password/)'
        }
        {
          name: 'DB_PORT'
          value: '5432'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'PYTHON_VERSION'
          value: '3.11'
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
    // Note: Consumption plan (Y1) does not support VNet integration
    // virtualNetworkSubnetId: functionAppsSubnetId
  }
}

// Note: RBAC role assignments for Storage and Key Vault are handled in the rbac.bicep module
// to avoid duplicate assignments and ensure proper deployment order

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
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
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
