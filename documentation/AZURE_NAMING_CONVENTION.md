# Azure Resource Naming Convention

This document defines the standardized naming convention for all Azure resources in the MagicToolbox project.

## Overview

All Azure resources follow a consistent, hierarchical naming pattern that includes:
- **Resource type prefix** - Identifies the type of Azure resource
- **Location** - Azure region where the resource is deployed
- **Application name** - The project/application name
- **Environment** - Deployment environment (dev, staging, prod)
- **Instance number** - Allows multiple instances of the same resource type

## Standard Format

```
{prefix}-{location}-{app}-{env}-{instance}
```

For resources with strict naming constraints (no hyphens allowed):
```
{prefix}{locationAbbr}{app}{env}{instance}
```

## Location Abbreviations

For resources with length constraints, we use abbreviated location codes:

| Full Location | Abbreviation |
|---------------|--------------|
| `westeurope` | `we` |
| `northeurope` | `ne` |
| `eastus` | `eu` |
| `eastus2` | `eu2` |
| `westus` | `wu` |
| `westus2` | `wu2` |

For resources without strict length limits, use the full location name.

## Resource Naming Patterns

### Infrastructure Resources

| Resource Type | Prefix | Pattern | Example (dev/westeurope) |
|--------------|--------|---------|--------------------------|
| Resource Group | `rg` | `rg-{location}-{app}-{env}-{instance}` | `rg-westeurope-magictoolbox-dev-01` |
| Virtual Network | `vnet` | `vnet-{location}-{app}-{env}-{instance}` | `vnet-westeurope-magictoolbox-dev-01` |
| Subnet | `snet` | `snet-{location}-{app}-{purpose}-{instance}` | `snet-westeurope-magictoolbox-containerapp-01` |

### Compute Resources

| Resource Type | Prefix | Pattern | Example (dev/westeurope) |
|--------------|--------|---------|--------------------------|
| Container Apps Environment | `env` | `env-{location}-{app}-{env}-{instance}` | `env-westeurope-magictoolbox-dev-01` |
| Container App | `app` | `app-{location}-{app}-{env}-{instance}` | `app-westeurope-magictoolbox-dev-01` |
| App Service Plan | `plan` | `plan-{location}-{app}-{env}-{instance}` | `plan-westeurope-magictoolbox-dev-01` |
| App Service | `as` | `as-{location}-{app}-{env}-{instance}` | `as-westeurope-magictoolbox-dev-01` |
| Function App | `func` | `func-{location}-{app}-{env}-{instance}` | `func-westeurope-magictoolbox-dev-01` |

### Container & Registry

| Resource Type | Prefix | Pattern | Example (dev/westeurope) |
|--------------|--------|---------|--------------------------|
| Container Registry | `acr` | `acr{locationAbbr}{app}{env}{instance}` | `acrwemagictoolboxdev01` |
| Container Instance | `ci` | `ci-{location}-{app}-{env}-{instance}` | `ci-westeurope-magictoolbox-dev-01` |

**Note**: Container Registry names must be globally unique, lowercase alphanumeric only (5-50 chars), no hyphens.

### Data & Storage

| Resource Type | Prefix | Pattern | Example (dev/westeurope) |
|--------------|--------|---------|--------------------------|
| Storage Account | `sa` | `sa{locationAbbr}{app}{env}{instance}` | `sawemagictoolboxdev01` |
| Blob Container | N/A | `{purpose}` | `uploads`, `processed`, `static` |
| File Share | N/A | `{purpose}` | `data`, `backups` |

**Note**: Storage Account names must be globally unique, lowercase alphanumeric only (3-24 chars), no hyphens.

### Database Resources

| Resource Type | Prefix | Pattern | Example (dev/westeurope) |
|--------------|--------|---------|--------------------------|
| PostgreSQL Server | `psql` | `psql-{location}-{app}-{env}-{instance}` | `psql-westeurope-magictoolbox-dev-01` |
| MySQL Server | `mysql` | `mysql-{location}-{app}-{env}-{instance}` | `mysql-westeurope-magictoolbox-dev-01` |
| SQL Server | `sql` | `sql-{location}-{app}-{env}-{instance}` | `sql-westeurope-magictoolbox-dev-01` |
| Cosmos DB Account | `cosmos` | `cosmos-{location}-{app}-{env}-{instance}` | `cosmos-westeurope-magictoolbox-dev-01` |

### Cache & Messaging

| Resource Type | Prefix | Pattern | Example (dev/westeurope) |
|--------------|--------|---------|--------------------------|
| Redis Cache | `red` | `red-{location}-{app}-{env}-{instance}` | `red-westeurope-magictoolbox-dev-01` |
| Service Bus Namespace | `sb` | `sb-{location}-{app}-{env}-{instance}` | `sb-westeurope-magictoolbox-dev-01` |
| Event Hub Namespace | `evh` | `evh-{location}-{app}-{env}-{instance}` | `evh-westeurope-magictoolbox-dev-01` |

### Security & Secrets

| Resource Type | Prefix | Pattern | Example (dev/westeurope) |
|--------------|--------|---------|--------------------------|
| Key Vault | `kv` | `kv{locationAbbr}{app}{env}{instance}` | `kvwemagictoolboxdev01` |
| Managed Identity | `id` | `id-{location}-{app}-{env}-{instance}` | `id-westeurope-magictoolbox-dev-01` |

**Note**: Key Vault names must be globally unique, alphanumeric and hyphens only (3-24 chars). We omit hyphens for brevity.

### Monitoring & Logging

| Resource Type | Prefix | Pattern | Example (dev/westeurope) |
|--------------|--------|---------|--------------------------|
| Log Analytics Workspace | `law` | `law-{location}-{app}-{env}-{instance}` | `law-westeurope-magictoolbox-dev-01` |
| Application Insights | `ai` | `ai-{location}-{app}-{env}-{instance}` | `ai-westeurope-magictoolbox-dev-01` |
| Action Group | `ag` | `ag-{location}-{app}-{env}-{instance}` | `ag-westeurope-magictoolbox-dev-01` |

## Complete Examples by Environment

### Development Environment (westeurope)

```yaml
Resource Group:           rg-westeurope-magictoolbox-dev-01
Container Apps Env:       env-westeurope-magictoolbox-dev-01
Container App:            app-westeurope-magictoolbox-dev-01
Container Registry:       acrwemagictoolboxdev01
Key Vault:                kvwemagictoolboxdev01
Application Insights:     ai-westeurope-magictoolbox-dev-01
Log Analytics Workspace:  law-westeurope-magictoolbox-dev-01
Redis Cache:              red-westeurope-magictoolbox-dev-01
PostgreSQL Server:        psql-westeurope-magictoolbox-dev-01
Storage Account:          sawemagictoolboxdev01
```

### Staging Environment (westeurope)

```yaml
Resource Group:           rg-westeurope-magictoolbox-staging-01
Container Apps Env:       env-westeurope-magictoolbox-staging-01
Container App:            app-westeurope-magictoolbox-sta-01
Container Registry:       acrwemagictoolboxsta01
Key Vault:                kvwemagictoolboxsta01
Application Insights:     ai-westeurope-magictoolbox-staging-01
Log Analytics Workspace:  law-westeurope-magictoolbox-staging-01
Redis Cache:              red-westeurope-magictoolbox-staging-01
PostgreSQL Server:        psql-westeurope-magictoolbox-staging-01
Storage Account:          sawemagictoolboxsta01
```

**Note**: "staging" is shortened to "sta" for resources with 32-character limits.

### Production Environment (westeurope)

```yaml
Resource Group:           rg-westeurope-magictoolbox-prod-01
Container Apps Env:       env-westeurope-magictoolbox-prod-01
Container App:            app-westeurope-magictoolbox-prod-01
Container Registry:       acrwemagictoolboxprod01
Key Vault:                kvwemagictoolboxprod01
Application Insights:     ai-westeurope-magictoolbox-prod-01
Log Analytics Workspace:  law-westeurope-magictoolbox-prod-01
Redis Cache:              red-westeurope-magictoolbox-prod-01
PostgreSQL Server:        psql-westeurope-magictoolbox-prod-01
Storage Account:          sawemagictoolboxprod01
```

## Azure Resource Naming Rules & Constraints

| Resource Type | Min Length | Max Length | Valid Characters | Global Unique | Case Sensitive |
|--------------|-----------|------------|------------------|---------------|----------------|
| Resource Group | 1 | 90 | Alphanumeric, underscore, parentheses, hyphen, period | No | No |
| Container Registry | 5 | 50 | Alphanumeric only | Yes | No |
| Container App | 2 | 32 | Lowercase, alphanumeric, hyphen | No | Yes |
| Storage Account | 3 | 24 | Lowercase alphanumeric only | Yes | No |
| Key Vault | 3 | 24 | Alphanumeric, hyphen | Yes | No |
| PostgreSQL Server | 3 | 63 | Lowercase, alphanumeric, hyphen | Yes | No |
| Redis Cache | 1 | 63 | Alphanumeric, hyphen | Yes | No |
| App Insights | 1 | 260 | Alphanumeric, hyphen, underscore, parentheses, period | No | No |
| Log Analytics | 4 | 63 | Alphanumeric, hyphen | No | No |

## Service Principal Naming

For GitHub Actions CI/CD pipelines:

```
sp-{app}-cicd-{env}
```

Examples:
- `sp-magictoolbox-cicd-dev`
- `sp-magictoolbox-cicd-staging`
- `sp-magictoolbox-cicd-prod`

## Tags

All resources should include these standard tags:

```yaml
Application: MagicToolbox
Environment: dev | staging | prod
ManagedBy: Bicep | Terraform
Project: MagicToolbox
CostCenter: Engineering
```

## Benefits of This Convention

1. ✅ **Consistency** - All resources follow the same pattern
2. ✅ **Clarity** - Resource type, location, and environment are immediately visible
3. ✅ **Searchability** - Easy to find and filter resources in Azure Portal
4. ✅ **Automation** - Predictable names enable script automation
5. ✅ **Governance** - Supports cost tracking and policy enforcement
6. ✅ **Scalability** - Instance numbers allow for multiple deployments
7. ✅ **Compliance** - Adheres to Azure naming rules and constraints

## Implementation

The naming convention is implemented in:
- **Bicep Templates**: `/infra/modules/*.bicep`
- **Parameter Files**: `/infra/parameters.*.json`
- **Documentation**: All `.md` files in the repository
- **Scripts**: `/scripts/*.sh`

## References

- [Azure Naming Conventions Best Practices](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming)
- [Azure Resource Naming Rules](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-name-rules)
- [Cloud Adoption Framework - Naming Standards](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/naming-and-tagging)

---

**Last Updated**: November 27, 2025  
**Version**: 1.0
