// Azure Function App for PDF to DOCX conversion
// This module deploys a Flex Consumption Function App with HTTP trigger

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
param applicationInsightsInstrumentationKey string

// VNet integration (supported in Flex Consumption plan)
param functionAppsSubnetId string

// Key Vault (for secret references)
param keyVaultName string

// Function App names
var functionAppName = 'func-${namingPrefix}-${uniqueString(resourceGroup().id)}'
var appServicePlanName = 'plan-flexconsumption-${namingPrefix}-${uniqueString(resourceGroup().id)}'

// App Service Plan (Flex Consumption for reliable HTTP triggers)
resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  tags: tags
  sku: {
    name: 'FC1'  // Flex Consumption plan
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
          value: 'https://${storageAccountName}.blob.${environment().suffixes.storage}/deployments'
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
        // Azure Functions runtime configuration for Python v2 worker indexing
        // Note: FUNCTIONS_WORKER_RUNTIME is set via functionAppConfig.runtime for Flex Consumption
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'PYTHON_ISOLATE_WORKER_DEPENDENCIES'
          value: '1'
        }
        {
          name: 'AzureWebJobsFeatureFlags'
          value: 'EnableWorkerIndexing'
        }
        
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
        // Application Insights integration
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: applicationInsightsConnectionString
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: applicationInsightsInstrumentationKey
        }
        {
          name: 'ApplicationInsightsAgent_EXTENSION_VERSION'
          value: '~3'  // Enable Application Insights agent for advanced monitoring
        }
        {
          name: 'XDT_MicrosoftApplicationInsights_Mode'
          value: 'recommended'  // Enable recommended Application Insights features
        }
        {
          name: 'InstrumentationEngine_EXTENSION_VERSION'
          value: 'disabled'  // Not needed for Python Functions
        }
        {
          name: 'APPLICATIONINSIGHTS_ENABLE_AGENT'
          value: 'true'  // Enable Application Insights SDK
        }
        {
          name: 'APPLICATIONINSIGHTS_SAMPLING_PERCENTAGE'
          value: '100'  // 100% sampling for dev, reduce in production
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
          value: '@Microsoft.KeyVault(SecretUri=https://${keyVaultName}${environment().suffixes.keyvaultDns}/secrets/postgres-password/)'
        }
        {
          name: 'DB_PORT'
          value: '5432'
        }
        {
          name: 'DB_SSLMODE'
          value: 'require'
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
    virtualNetworkSubnetId: functionAppsSubnetId
    publicNetworkAccess: 'Enabled' // Required initially, can be set to 'Disabled' after private endpoint is created
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
