// Azure Container Apps Environment and App
param location string
param namingPrefix string
param uniqueSuffix string
param tags object
param environment string
param logAnalyticsWorkspaceId string

@secure()
param applicationInsightsConnectionString string

param acrLoginServer string
param acrUsername string

@secure()
param acrPassword string

param keyVaultName string
param storageAccountName string
param redisHostName string
param postgresHost string
param postgresDatabase string
param postgresAdminUsername string

@secure()
param storageAccountKey string

@secure()
param redisAccessKey string

@secure()
param postgresAdminPassword string

@secure()
param djangoSecretKey string

// Location abbreviation for naming (Container Apps have 32 char limit)
var locationAbbr = location == 'westeurope' ? 'we' : location == 'northeurope' ? 'ne' : location == 'eastus' ? 'eu' : location == 'eastus2' ? 'eu2' : 'we'

// Container App names must be 2-32 chars, lowercase alphanumeric or '-', no '--', start with letter, end with alphanumeric
// Using abbreviated names to fit within 32 char limit
var containerAppsEnvironmentName = 'env-${locationAbbr}-${namingPrefix}-01'
var containerAppName = 'app-${locationAbbr}-${namingPrefix}-01'
var imageName = '${acrLoginServer}/magictoolbox:latest'

// Minimum and maximum replicas based on environment
var minReplicas = environment == 'prod' ? 2 : 1
var maxReplicas = environment == 'prod' ? 10 : 3

// CPU and memory based on environment
var cpuCores = environment == 'prod' ? '1.0' : '0.5'
var memorySize = environment == 'prod' ? '2Gi' : '1Gi'

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppsEnvironmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
    zoneRedundant: environment == 'prod' ? true : false
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned' // Managed Identity for Key Vault access
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
          username: acrUsername
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acrPassword
        }
        {
          name: 'django-secret-key'
          value: djangoSecretKey
        }
        {
          name: 'postgres-password'
          value: postgresAdminPassword
        }
        {
          name: 'redis-access-key'
          value: redisAccessKey
        }
        {
          name: 'storage-account-key'
          value: storageAccountKey
        }
        {
          name: 'appinsights-connection-string'
          value: applicationInsightsConnectionString
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
              value: postgresAdminPassword
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
              name: 'REDIS_URL'
              value: 'rediss://:${redisAccessKey}@${redisHostName}:6380/0?ssl_cert_reqs=required'
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
              name: 'KEY_VAULT_NAME'
              value: keyVaultName
            }
            {
              name: 'REDIS_HOST'
              value: redisHostName
            }
            {
              name: 'REDIS_ACCESS_KEY'
              secretRef: 'redis-access-key'
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
