# Azure Key Vault and Application Insights Integration

## Overview

This document describes how MagicToolbox integrates with Azure Key Vault for secret management and Application Insights for application telemetry, following Azure DevOps best practices.

## Architecture

### Key Vault Integration

#### Secret Management
- **Django Secret Key**: Application secret key for cryptographic signing
- **Database Password**: PostgreSQL admin password
- **Redis Access Key**: Azure Cache for Redis authentication
- **Storage Account Key**: Azure Blob Storage access key

#### Authentication
- **Managed Identity**: Container App uses system-assigned managed identity
- **RBAC**: Key Vault Secrets User role assigned to Container App identity
- **No Keys in Code**: All authentication happens via Azure AD

#### Secret Retrieval Flow
1. Container App starts with managed identity
2. Django application requests secrets from Key Vault
3. Azure authenticates using managed identity token
4. Secrets are loaded into application memory
5. Fallback to environment variables if Key Vault unavailable

### Application Insights Integration

#### Telemetry Collection
- **Request Tracing**: HTTP request/response tracking with OpenCensus
- **Exception Logging**: Automatic exception capture and stack traces
- **Custom Metrics**: Performance counters and business metrics
- **Distributed Tracing**: End-to-end request correlation

#### Sampling Strategy
- **Development/Staging**: 100% sampling (all requests traced)
- **Production**: 50% sampling (reduced overhead, still representative)

#### Log Levels
- **INFO**: Normal operations, Key Vault access, configuration
- **WARNING**: Fallback scenarios, missing optional features
- **ERROR**: Exceptions, failed operations, critical issues

## Infrastructure as Code (Bicep)

### Key Resources

#### Key Vault (`infra/modules/keyvault.bicep`)
```bicep
- Soft delete enabled (7 days dev, 90 days prod)
- RBAC authorization (no access policies)
- Secrets stored during deployment
- Network ACLs for production isolation
```

#### RBAC Assignments (`infra/modules/rbac.bicep`)
```bicep
- Key Vault Secrets User role for Container App
- Storage Blob Data Contributor for managed identity
- Service Principal authentication
```

#### Container Apps (`infra/modules/container-apps.bicep`)
```bicep
- System-assigned managed identity
- Environment variables for Key Vault name
- Application Insights connection string as secret
- Automatic secret rotation support
```

### Deployment Flow

1. **Deploy Key Vault**: Create vault with RBAC enabled
2. **Store Secrets**: Add all secrets to Key Vault
3. **Deploy Container App**: Create with managed identity
4. **Assign RBAC Roles**: Grant access to Key Vault and Storage
5. **Application Start**: Django loads secrets from Key Vault

## Application Configuration

### Production Settings (`magictoolbox/settings/production.py`)

#### Key Vault Client Initialization
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KEY_VAULT_URL, credential=credential)
```

#### Secret Retrieval with Fallback
```python
def get_secret_or_env(secret_name, env_var_name, required=True):
    try:
        # Try Key Vault first
        return secret_client.get_secret(secret_name).value
    except AzureError:
        # Fallback to environment variable
        return config(env_var_name, default='')
```

#### Application Insights Configuration
```python
OPENCENSUS = {
    'TRACE': {
        'SAMPLER': ProbabilitySampler(rate=sample_rate),
        'EXPORTER': AzureExporter(connection_string=CONNECTION_STRING),
    },
    'METRICS': {
        'EXPORTER': MetricsExporter(connection_string=CONNECTION_STRING),
    },
}
```

### Environment Variables

Required environment variables for Container App:

```bash
# Key Vault
KEY_VAULT_NAME=kvmagictoolboxgrrafk

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=<from-secret>

# Environment
ENVIRONMENT=dev|staging|prod

# Fallback secrets (if Key Vault unavailable)
SECRET_KEY=<django-secret>
DB_PASSWORD=<postgres-password>
REDIS_ACCESS_KEY=<redis-key>
```

## DevOps Best Practices

### Security

1. **No Secrets in Code**: All secrets in Key Vault or env vars
2. **Managed Identity**: No password-based authentication
3. **Principle of Least Privilege**: Minimal RBAC permissions
4. **Soft Delete**: 90-day retention for production secrets
5. **Network Isolation**: Private endpoints for production

### Monitoring

1. **Comprehensive Logging**: All operations logged to App Insights
2. **Exception Tracking**: Automatic error capture with stack traces
3. **Performance Metrics**: Request duration, dependency calls
4. **Custom Events**: Business metrics and usage tracking
5. **Alerts**: Proactive notification on errors/performance issues

### Deployment

1. **Infrastructure as Code**: All resources in Bicep templates
2. **Automated Deployment**: Shell script with validation
3. **Zero-Downtime**: Blue-green deployments with revisions
4. **Health Checks**: Liveness and readiness probes
5. **Rollback Support**: Automatic revision management

### Reliability

1. **Graceful Degradation**: Fallback to env vars if Key Vault unavailable
2. **Retry Logic**: Automatic retry for transient failures
3. **Connection Pooling**: Efficient database and Redis connections
4. **Caching**: Redis for session and query caching
5. **Scaling**: Automatic horizontal scaling based on load

## Deployment Guide

### Prerequisites

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Set subscription
az account set --subscription <subscription-id>
```

### Deploy Infrastructure

```bash
# Deploy to development
./scripts/deploy-to-azure.sh \
    --environment dev \
    --resource-group rg-westeurope-magictoolbox-dev-01 \
    --location westeurope

# Deploy to production
./scripts/deploy-to-azure.sh \
    --environment prod \
    --resource-group rg-westeurope-magictoolbox-prod-01 \
    --location eastus2
```

### Verify Deployment

```bash
# Check Container App health
az containerapp show \
    --name <app-name> \
    --resource-group <resource-group> \
    --query "properties.runningStatus"

# Check Key Vault access
az containerapp exec \
    --name <app-name> \
    --resource-group <resource-group> \
    --command "python -c 'from azure.identity import DefaultAzureCredential; print(DefaultAzureCredential())'"

# View Application Insights logs
az monitor app-insights query \
    --app <app-insights-name> \
    --analytics-query "requests | take 10"
```

## Monitoring and Troubleshooting

### Key Vault Issues

#### Symptom: "Could not retrieve secret from Key Vault"

**Diagnosis:**
```bash
# Check managed identity
az containerapp show --name <app-name> --resource-group <rg> \
    --query "identity.principalId"

# Check RBAC assignments
az role assignment list \
    --assignee <principal-id> \
    --scope <key-vault-id>
```

**Solution:**
1. Verify managed identity is system-assigned
2. Ensure Key Vault Secrets User role is assigned
3. Check Key Vault firewall rules
4. Verify KEY_VAULT_NAME environment variable

#### Symptom: "Application using environment variables instead of Key Vault"

**Diagnosis:**
```bash
# Check Key Vault connectivity
az containerapp exec \
    --name <app-name> \
    --resource-group <rg> \
    --command "nslookup <keyvault-name>.vault.azure.net"
```

**Solution:**
1. Application falls back to env vars if Key Vault unavailable (expected behavior)
2. Check Container App logs for Key Vault warnings
3. Verify secrets exist in Key Vault
4. Check network connectivity

### Application Insights Issues

#### Symptom: "No telemetry data in Application Insights"

**Diagnosis:**
```bash
# Check if packages are installed
az containerapp exec \
    --name <app-name> \
    --resource-group <rg> \
    --command "pip list | grep opencensus"

# Check connection string
az containerapp show \
    --name <app-name> \
    --resource-group <rg> \
    --query "properties.template.containers[0].env[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING']"
```

**Solution:**
1. Verify opencensus packages in requirements/production.txt
2. Rebuild and redeploy container image
3. Check APPLICATIONINSIGHTS_CONNECTION_STRING is set
4. Wait 2-5 minutes for telemetry ingestion

#### Symptom: "High latency or performance issues"

**Diagnosis:**
```bash
# Query Application Insights
az monitor app-insights query \
    --app <app-name> \
    --analytics-query "requests | summarize avg(duration) by name | order by avg_duration desc"
```

**Solution:**
1. Review slow requests in Application Insights
2. Check database query performance
3. Review Redis cache hit rate
4. Consider increasing Container App resources

## Cost Optimization

### Key Vault
- **Standard Tier**: $0.03 per 10,000 operations
- **Soft Delete**: No additional cost
- **Estimated**: ~$5/month for typical usage

### Application Insights
- **Data Ingestion**: $2.30 per GB after 5 GB free
- **Data Retention**: 90 days included, $0.12/GB/month after
- **Sampling**: 50% in prod reduces cost by ~50%
- **Estimated**: $10-30/month depending on traffic

### Best Practices
1. **Sampling**: Use 50% or lower in production
2. **Log Levels**: INFO or WARNING in production (not DEBUG)
3. **Retention**: 90 days default (adjust based on compliance)
4. **Alerts**: Configure budget alerts for cost monitoring

## Security Considerations

### Key Vault Security
- ✅ RBAC enabled (not access policies)
- ✅ Soft delete enabled (prevent accidental deletion)
- ✅ Managed identity (no password-based auth)
- ✅ Audit logging enabled
- ⚠️ Consider private endpoints for production
- ⚠️ Implement Key Vault firewall for production

### Application Security
- ✅ Secrets never in code or logs
- ✅ HTTPS only (enforced by Container Apps)
- ✅ Environment variable encryption at rest
- ✅ Managed identity for all Azure services
- ⚠️ Implement secret rotation policy
- ⚠️ Regular security scanning of container images

## Additional Resources

- [Azure Key Vault Best Practices](https://docs.microsoft.com/en-us/azure/key-vault/general/best-practices)
- [Application Insights Overview](https://docs.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
- [Managed Identity Best Practices](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/managed-identity-best-practice-recommendations)
- [Container Apps Security](https://docs.microsoft.com/en-us/azure/container-apps/security)
- [OpenCensus Python](https://github.com/census-instrumentation/opencensus-python)

## Support

For issues or questions:
1. Check Container App logs: `az containerapp logs show --name <app-name> --resource-group <rg> --follow`
2. Review Application Insights: Azure Portal > Application Insights > Failures
3. Check Key Vault audit logs: Azure Portal > Key Vault > Activity Log
4. Open GitHub issue with error details and logs
