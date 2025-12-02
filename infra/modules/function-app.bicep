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

// VNet integration
param functionAppsSubnetId string

// Key Vault (for secret references)
param keyVaultName string

// Function App names
var functionAppName = 'func-${namingPrefix}-${uniqueString(resourceGroup().id)}'
var appServicePlanName = 'plan-flex-${namingPrefix}-${uniqueString(resourceGroup().id)}'

// App Service Plan (FlexConsumption for Managed Identity support with disabled shared key access)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: 'FC1'  // FlexConsumption plan
    tier: 'FlexConsumption'
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
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: 'https://${storageAccountName}.blob.${environment().suffixes.storage}/deploymentpackage'
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 100
        instanceMemoryMB: 2048
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
    }
    siteConfig: {
      appSettings: [
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
          name: 'AzureWebJobsStorage__credential'
          value: 'managedidentity'
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
          value: postgresqlDatabaseName // 'magictoolbox' - matches actual database name
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
          name: 'WEBSITE_VNET_ROUTE_ALL'
          value: '1'
        }
        // Note: WEBSITE_RUN_FROM_PACKAGE, SCM_DO_BUILD_DURING_DEPLOYMENT, and ENABLE_ORYX_BUILD
        // are not supported with FlexConsumption SKU and have been removed
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
    virtualNetworkSubnetId: functionAppsSubnetId
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
