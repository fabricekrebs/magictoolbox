// Azure Container Apps Environment and App
// Supports both direct secrets and Key Vault references
// Use useKeyVaultReferences=false for initial deployment, true after RBAC is configured
param location string
param namingPrefix string
param tags object
param environment string
param logAnalyticsWorkspaceId string

param acrLoginServer string

@description('Use Key Vault references for secrets (requires RBAC to be configured first)')
param useKeyVaultReferences bool = false

param keyVaultUri string

@secure()
param djangoSecretKey string = ''
@secure()
param postgresPassword string = ''
@secure()
param storageAccountKey string = ''
@secure()
param appInsightsConnectionString string = ''

param storageAccountName string
param postgresHost string
param postgresDatabase string
param postgresAdminUsername string

@description('Subnet ID for Container Apps VNet integration')
param containerAppsSubnetId string

@description('Azure Function App base URL')
param functionAppUrl string = ''

@description('Container image tag (version) - can be semver tag like v1.2.3 or branch-based like develop-abc123')
param imageTag string = environment == 'prod' ? 'latest' : 'develop'

// Location abbreviation for naming (Container Apps have 32 char limit)
var locationAbbr = location == 'westeurope' ? 'we' : location == 'northeurope' ? 'ne' : location == 'italynorth' ? 'in' : location == 'eastus' ? 'eu' : location == 'eastus2' ? 'eu2' : 'we'

// Container App names must be 2-32 chars, lowercase alphanumeric or '-', no '--', start with letter, end with alphanumeric
// Using abbreviated names to fit within 32 char limit
var containerAppsEnvironmentName = 'env-${locationAbbr}-${namingPrefix}-01'
var containerAppName = 'app-${locationAbbr}-${namingPrefix}-01'
// Use semantic version tags for production (e.g., v1.2.3) or branch-based tags for development (e.g., develop-abc123)
var imageName = '${acrLoginServer}/magictoolbox:${imageTag}'

// Minimum and maximum replicas based on environment
var minReplicas = environment == 'prod' ? 2 : 1
var maxReplicas = environment == 'prod' ? 10 : 3

// CPU and memory based on environment
var cpuCores = environment == 'prod' ? '1.0' : '0.5'
var memorySize = environment == 'prod' ? '2Gi' : '1Gi'

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' = {
  name: containerAppsEnvironmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2025-07-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2025-07-01').primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: containerAppsSubnetId
      internal: false // Set to true for fully private (internal) environment
    }
    zoneRedundant: environment == 'prod' ? true : false
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2026-01-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned' // Managed Identity for ACR and Storage access
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single' // Use 'Multiple' for blue-green deployments
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false // HTTPS only
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: acrLoginServer
          identity: 'system' // Use managed identity instead of admin credentials
        }
      ]
      secrets: useKeyVaultReferences ? [
        {
          name: 'django-secret-key'
          keyVaultUrl: '${keyVaultUri}secrets/django-secret-key'
          identity: 'system'
        }
        {
          name: 'postgres-password'
          keyVaultUrl: '${keyVaultUri}secrets/postgres-password'
          identity: 'system'
        }
        {
          name: 'storage-account-key'
          keyVaultUrl: '${keyVaultUri}secrets/storage-account-key'
          identity: 'system'
        }
        {
          name: 'appinsights-connection-string'
          keyVaultUrl: '${keyVaultUri}secrets/appinsights-connection-string'
          identity: 'system'
        }
      ] : [
        {
          name: 'django-secret-key'
          value: djangoSecretKey
        }
        {
          name: 'postgres-password'
          value: postgresPassword
        }
        {
          name: 'storage-account-key'
          value: storageAccountKey
        }
        {
          name: 'appinsights-connection-string'
          value: appInsightsConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'magictoolbox'
          image: imageName
          resources: {
            cpu: json(cpuCores)
            memory: memorySize
          }
          env: [
            {
              name: 'DJANGO_SETTINGS_MODULE'
              value: 'magictoolbox.settings.production'
            }
            {
              name: 'ENVIRONMENT'
              value: environment
            }
            {
              name: 'SECRET_KEY'
              secretRef: 'django-secret-key'
            }
            {
              name: 'ALLOWED_HOSTS'
              value: '.azurecontainerapps.io' // Update with custom domain
            }
            {
              name: 'DEBUG'
              value: 'False'
            }
            {
              name: 'DB_NAME'
              value: postgresDatabase
            }
            {
              name: 'DB_USER'
              value: postgresAdminUsername
            }
            {
              name: 'DB_PASSWORD'
              secretRef: 'postgres-password'
            }
            {
              name: 'DB_HOST'
              value: postgresHost
            }
            {
              name: 'DB_PORT'
              value: '5432'
            }
            {
              name: 'DB_SSLMODE'
              value: 'require'
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT_NAME'
              value: storageAccountName
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT_KEY'
              secretRef: 'storage-account-key'
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_UPLOADS'
              value: 'uploads'
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_PROCESSED'
              value: 'processed'
            }
            {
              name: 'AZURE_STORAGE_CONTAINER_STATIC'
              value: 'static'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'appinsights-connection-string'
            }
            {
              name: 'WEBSITES_PORT'
              value: '8000'
            }
            {
              name: 'GUNICORN_WORKERS'
              value: environment == 'prod' ? '4' : '2'
            }
            {
              name: 'GUNICORN_THREADS'
              value: '4'
            }
            {
              name: 'GUNICORN_TIMEOUT'
              value: '120'
            }
            {
              name: 'MAX_UPLOAD_SIZE'
              value: '52428800' // 50MB in bytes
            }
            {
              name: 'USE_AZURE_FUNCTIONS_PDF_CONVERSION'
              value: 'true'
            }
            {
              name: 'AZURE_FUNCTION_BASE_URL'
              value: functionAppUrl
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT_NAME'
              value: storageAccountName
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health/'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 30
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health/'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

// Outputs
output containerAppId string = containerApp.id
output containerAppName string = containerApp.name
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output containerAppIdentityPrincipalId string = containerApp.identity.principalId
output containerAppsEnvironmentId string = containerAppsEnvironment.id
