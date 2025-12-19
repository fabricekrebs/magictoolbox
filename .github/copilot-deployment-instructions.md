---
description: Deployment and infrastructure guidelines for MagicToolbox
applyTo: '{docker/**,bicep/**,*.dockerfile,docker-compose.yml,.github/workflows/**}'
---

# Deployment & Infrastructure Guidelines (Azure Container Apps)

## Docker Best Practices

### Backend Dockerfile (Django)
- Use official Python slim images
- Multi-stage builds for smaller images
- Run as non-root user
- Cache dependencies separately
- Use .dockerignore to exclude unnecessary files
- Collect static files for Django

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/production.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "magictoolbox.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

### Frontend Dockerfile
- Use Node.js for build stage
- Nginx for serving static files
- Optimize nginx configuration
- Enable gzip compression
- Implement proper caching headers

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build application
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose
- Separate dev and prod configurations
- Use environment files
- Define health checks
- Set resource limits
- Use named volumes

```yaml
# docker-compose.yml
version: '3.9'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/magictoolbox
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - upload-storage:/app/uploads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: magictoolbox
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M

volumes:
  postgres-data:
  redis-data:
  upload-storage:
```

## Azure Container Apps Deployment

### Infrastructure as Code (Bicep)
- Use Bicep for all Azure resources
- Modular structure with separate files per resource type
- Parameterize for different environments (dev, staging, prod)

```bicep
// main.bicep
param location string = resourceGroup().location
param environmentName string = 'production'
param containerRegistryName string
param storageAccountName string

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'magictoolbox-env-${environmentName}'
  location: location
  properties: {
    daprAIInstrumentationKey: appInsights.properties.InstrumentationKey
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Backend Container App
resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'magictoolbox-backend'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/database-url'
          identity: 'system'
        }
        {
          name: 'django-secret-key'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/django-secret-key'
          identity: 'system'
        }
      ]
      registries: [
        {
          server: '${containerRegistryName}.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${containerRegistryName}.azurecr.io/magictoolbox-backend:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'DJANGO_SETTINGS_MODULE'
              value: 'magictoolbox.settings.production'
            }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
          ]
          probes: [
            {
              type: 'liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 30
              periodSeconds: 10
            }
            {
              type: 'readiness'
              httpGet: {
                path: '/ready'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// Frontend Container App
resource frontendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'magictoolbox-frontend'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        allowInsecure: false
      }
      registries: [
        {
          server: '${containerRegistryName}.azurecr.io'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${containerRegistryName}.azurecr.io/magictoolbox-frontend:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}
```

### Azure Resources Setup

```bicep
// database.bicep
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: 'magictoolbox-db-${environmentName}'
  location: location
  sku: {
    name: 'Standard_B2s'
    tier: 'Burstable'
  }
  properties: {
    version: '15'
    administratorLogin: 'magictoolboxadmin'
    administratorLoginPassword: adminPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// redis.bicep
resource redis 'Microsoft.Cache/redis@2023-04-01' = {
  name: 'magictoolbox-redis-${environmentName}'
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 1
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      maxmemory-policy: 'allkeys-lru'
    }
  }
}

// storage.bicep
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/media'
  properties: {
    publicAccess: 'None'
  }
}
```

## CI/CD Pipeline (GitHub Actions for Azure)

### Build and Test Pipeline
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: test_magictoolbox
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Install dependencies
      working-directory: ./backend
      run: |
        pip install -r requirements/development.txt
        pip install pytest pytest-django pytest-cov
    
    - name: Run tests
      working-directory: ./backend
      env:
        DATABASE_URL: postgresql://postgres:testpass@localhost:5432/test_magictoolbox
        REDIS_URL: redis://localhost:6379/0
      run: pytest --cov=apps --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml

  frontend-test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'
        cache-dependency-path: ./frontend/package-lock.json
    
    - name: Install dependencies
      working-directory: ./frontend
      run: npm ci
    
    - name: Run linter
      working-directory: ./frontend
      run: npm run lint
    
    - name: Run tests
      working-directory: ./frontend
      run: npm run test:coverage
    
    - name: Build
      working-directory: ./frontend
      run: npm run build

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
    
    - name: Upload Trivy results to GitHub Security
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-results.sarif'
```

### Deployment Pipeline (Azure Container Apps)
```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure Container Apps

on:
  push:
    branches: [main]
    tags:
      - 'v*'

env:
  AZURE_CONTAINER_REGISTRY: magictoolboxacr
  RESOURCE_GROUP: magictoolbox-rg
  LOCATION: eastus

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Azure Login
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
    
    - name: Login to Azure Container Registry
      uses: azure/docker-login@v1
      with:
        login-server: ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io
        username: ${{ secrets.ACR_USERNAME }}
        password: ${{ secrets.ACR_PASSWORD }}
    
    - name: Build and push backend image
      working-directory: ./backend
      run: |
        docker build -t ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-backend:${{ github.sha }} .
        docker push ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-backend:${{ github.sha }}
        docker tag ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-backend:${{ github.sha }} \
          ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-backend:latest
        docker push ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-backend:latest
    
    - name: Build and push frontend image
      working-directory: ./frontend
      run: |
        docker build -t ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-frontend:${{ github.sha }} .
        docker push ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-frontend:${{ github.sha }}
        docker tag ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-frontend:${{ github.sha }} \
          ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-frontend:latest
        docker push ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-frontend:latest

  deploy-infrastructure:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Azure Login
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
    
    - name: Deploy Bicep template
      uses: azure/arm-deploy@v1
      with:
        resourceGroupName: ${{ env.RESOURCE_GROUP }}
        template: ./bicep/main.bicep
        parameters: |
          environmentName=production
          containerRegistryName=${{ env.AZURE_CONTAINER_REGISTRY }}
          storageAccountName=magictoolboxstorage
        failOnStdErr: false

  deploy-container-apps:
    needs: [build-and-push, deploy-infrastructure]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Azure Login
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
    
    - name: Update Backend Container App
      uses: azure/container-apps-deploy-action@v1
      with:
        containerAppName: magictoolbox-backend
        resourceGroup: ${{ env.RESOURCE_GROUP }}
        imageToDeploy: ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-backend:${{ github.sha }}
    
    - name: Update Frontend Container App
      uses: azure/container-apps-deploy-action@v1
      with:
        containerAppName: magictoolbox-frontend
        resourceGroup: ${{ env.RESOURCE_GROUP }}
        imageToDeploy: ${{ env.AZURE_CONTAINER_REGISTRY }}.azurecr.io/magictoolbox-frontend:${{ github.sha }}
    
    - name: Run Database Migrations
      run: |
        az containerapp exec \
          --name magictoolbox-backend \
          --resource-group ${{ env.RESOURCE_GROUP }} \
          --command "python manage.py migrate --noinput"
```

## Azure Key Vault Configuration

```bicep
// keyvault.bicep
resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: 'kv-magictoolbox-${environmentName}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enabledForDeployment: false
    enabledForTemplateDeployment: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
  }
}

// Grant Container Apps access to Key Vault
resource keyVaultAccessPolicy 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: keyVault
  name: guid(keyVault.id, backendApp.id, 'SecretsUser')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: backendApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Secrets
resource djangoSecretKey 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'django-secret-key'
  properties: {
    value: djangoSecret
  }
}

resource databaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: 'postgresql://${postgresServer.properties.administratorLogin}:${adminPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/magictoolbox'
  }
}
```

## Monitoring & Logging (Azure)

### Application Insights Configuration
- Integrate Application Insights with Django
- Track custom events and metrics
- Monitor exceptions and performance
- Set up alerts for critical issues

```python
# settings/production.py
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure import metrics_exporter

APPLICATION_INSIGHTS_CONNECTION_STRING = config('APPLICATIONINSIGHTS_CONNECTION_STRING')

# Application Insights middleware
MIDDLEWARE += [
    'opencensus.ext.django.middleware.OpencensusMiddleware',
]

OPENCENSUS = {
    'TRACE': {
        'SAMPLER': 'opencensus.trace.samplers.ProbabilitySampler(rate=1.0)',
        'EXPORTER': f'opencensus.ext.azure.trace_exporter.AzureExporter(connection_string="{APPLICATION_INSIGHTS_CONNECTION_STRING}")',
    }
}
```

### Health Check Endpoints
- Implement `/health` for liveness checks
- Implement `/ready` for readiness checks with dependency status
- Return appropriate HTTP status codes
- Monitor with Azure Container Apps health probes

### Azure Monitor Integration
- Log aggregation via Log Analytics Workspace
- Custom dashboards for key metrics
- Alert rules for critical conditions
- Auto-scaling based on metrics

```bicep
// monitoring.bicep
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'magictoolbox-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'magictoolbox-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource metricAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'high-error-rate'
  location: 'global'
  properties: {
    severity: 2
    enabled: true
    scopes: [backendApp.id]
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'ErrorRate'
          metricName: 'Requests'
          dimensions: [
            {
              name: 'ResultCode'
              operator: 'Include'
              values: ['500', '502', '503']
            }
          ]
          operator: 'GreaterThan'
          threshold: 10
          timeAggregation: 'Count'
        }
      ]
    }
    actions: []
  }
}
```

## Security Checklist (Azure)
- [ ] All container images scanned for vulnerabilities (Trivy in CI/CD)
- [ ] Secrets stored in Azure Key Vault (never in code or environment variables)
- [ ] TLS certificates managed by Azure Container Apps (automatic HTTPS)
- [ ] Managed Identity enabled for all Container Apps
- [ ] Azure RBAC configured for least privilege access
- [ ] Resource limits set on all containers (CPU, memory)
- [ ] Non-root users in Dockerfiles
- [ ] Regular security updates applied (automated with Renovate)
- [ ] Database firewall rules configured (Azure PostgreSQL)
- [ ] Backup configured for database and storage
- [ ] Application Insights monitoring and alerting configured
- [ ] DDoS protection enabled
- [ ] Private endpoints for database and storage (production)
- [ ] Network isolation for Container Apps Environment
