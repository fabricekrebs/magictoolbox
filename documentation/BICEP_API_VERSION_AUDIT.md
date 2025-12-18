# Bicep API Version Audit

**Generated:** December 17, 2025  
**Status:** 🔴 All API versions outdated

## Summary

All Bicep template API versions are outdated. The templates were created in late 2023/early 2024 and haven't been updated since.

### Overall Status
- **Total Resource Types:** 15
- **Outdated:** 15 (100%)
- **Up to date:** 0 (0%)

---

## Detailed Findings

| Resource Type | Current Version | Latest Version | Gap | File(s) |
|---------------|----------------|----------------|-----|---------|
| **Microsoft.ContainerRegistry/registries** | 2023-01-01-preview | **2025-11-01** | 23 months | acr.bicep, rbac.bicep |
| **Microsoft.Storage/storageAccounts** | 2023-01-01 | **2025-06-01** | 29 months | storage.bicep, storage-network-rules.bicep, rbac.bicep |
| **Microsoft.Web/serverfarms** | 2023-12-01 | **2025-03-01** | 15 months | function-app.bicep |
| **Microsoft.Web/sites** | 2023-12-01 | **2025-03-01** | 15 months | function-app.bicep |
| **Microsoft.KeyVault/vaults** | 2023-02-01 | **2025-05-01** | 27 months | keyvault.bicep, rbac.bicep |
| **Microsoft.DBforPostgreSQL/flexibleServers** | 2023-03-01-preview | **2025-08-01** | 29 months | postgresql.bicep |
| **Microsoft.Network/virtualNetworks** | 2023-05-01 | **2025-05-01** | 24 months | network.bicep |
| **Microsoft.Network/privateEndpoints** | 2023-05-01 | **2025-05-01** | 24 months | private-endpoints.bicep |
| **Microsoft.Network/privateDnsZones** | 2020-06-01 | **2024-06-01** | 48 months | private-endpoints.bicep |
| **Microsoft.App/containerApps** | 2023-05-01 | **2026-01-01** | 32 months | container-apps.bicep |
| **Microsoft.App/managedEnvironments** | 2023-05-01 | **2026-01-01** | 32 months | container-apps.bicep |
| **Microsoft.OperationalInsights/workspaces** | 2022-10-01 | **2025-07-01** | 33 months | monitoring.bicep |
| **Microsoft.Insights/components** | 2020-02-02 | **2020-02-02-preview** | N/A | monitoring.bicep |
| **Microsoft.Insights/diagnosticSettings** | 2021-05-01-preview | **2021-05-01-preview** | Current | function-app.bicep |
| **Microsoft.Authorization/roleAssignments** | 2022-04-01 | **2025-10-01-preview** | 42 months | rbac.bicep (5 occurrences) |

---

## Priority Updates

### 🔴 Critical (Large API gaps - 30+ months)

1. **Microsoft.Authorization/roleAssignments**: 2022-04-01 → 2025-10-01-preview
   - **Gap:** 42 months
   - **Impact:** Missing RBAC improvements, conditional access features
   - **Files:** rbac.bicep (5 role assignments)

2. **Microsoft.OperationalInsights/workspaces**: 2022-10-01 → 2025-07-01
   - **Gap:** 33 months
   - **Impact:** Missing log analytics improvements, cost optimizations
   - **Files:** monitoring.bicep

3. **Microsoft.App/containerApps & managedEnvironments**: 2023-05-01 → 2026-01-01
   - **Gap:** 32 months
   - **Impact:** Missing Container Apps v2 features, workload profiles, jobs
   - **Files:** container-apps.bicep

### 🟡 High (20-30 months gap)

4. **Microsoft.Storage/storageAccounts**: 2023-01-01 → 2025-06-01
   - **Gap:** 29 months
   - **Impact:** Missing security features, immutability policies, performance tiers
   - **Files:** storage.bicep, storage-network-rules.bicep, rbac.bicep

5. **Microsoft.DBforPostgreSQL/flexibleServers**: 2023-03-01-preview → 2025-08-01
   - **Gap:** 29 months (using preview API!)
   - **Impact:** Missing GA features, performance improvements, HA options
   - **Files:** postgresql.bicep

6. **Microsoft.KeyVault/vaults**: 2023-02-01 → 2025-05-01
   - **Gap:** 27 months
   - **Impact:** Missing RBAC enhancements, managed HSM features
   - **Files:** keyvault.bicep, rbac.bicep

7. **Microsoft.Network** (VNets, PrivateEndpoints): 2023-05-01 → 2025-05-01
   - **Gap:** 24 months
   - **Impact:** Missing network security features, DDOS protection
   - **Files:** network.bicep, private-endpoints.bicep

8. **Microsoft.ContainerRegistry/registries**: 2023-01-01-preview → 2025-11-01
   - **Gap:** 23 months (using preview API!)
   - **Impact:** Missing GA features, security scanning, artifact caching
   - **Files:** acr.bicep, rbac.bicep

### 🟢 Medium (15-20 months gap)

9. **Microsoft.Web** (serverfarms, sites): 2023-12-01 → 2025-03-01
   - **Gap:** 15 months
   - **Impact:** Missing Function App improvements, scaling options
   - **Files:** function-app.bicep

### 🔵 Low Priority

10. **Microsoft.Network/privateDnsZones**: 2020-06-01 → 2024-06-01
    - **Gap:** 48 months (!!)
    - **Impact:** Minimal - DNS zones are stable, but should update for consistency
    - **Files:** private-endpoints.bicep (4 occurrences)

11. **Microsoft.Insights/components**: 2020-02-02 → 2020-02-02-preview
    - **Impact:** Preview version available, but current version is stable
    - **Recommendation:** Keep current unless preview features are needed

---

## Risks of Not Updating

### Security Risks
- **Missing security patches** in resource provider implementations
- **Missing RBAC improvements** (role assignments especially)
- **Missing encryption options** (Storage, Key Vault, PostgreSQL)
- **Using preview APIs in production** (ACR, PostgreSQL)

### Functional Risks
- **Missing features:**
  - Container Apps v2 features (workload profiles, jobs, dapr)
  - PostgreSQL high availability options
  - Storage immutability policies and hierarchical namespace
  - Network security enhancements

### Operational Risks
- **Deployment failures** if Azure deprecates old APIs
- **Incompatibility** with newer Azure Portal features
- **Support issues** - Microsoft may not support very old API versions

---

## Recommended Update Strategy

### Phase 1: Critical Security Updates (Week 1)
```bicep
# Update in this order to minimize risk:
1. rbac.bicep - Update roleAssignments to 2025-10-01-preview
2. keyvault.bicep - Update to 2025-05-01
3. postgresql.bicep - Update to 2025-08-01 (remove preview!)
4. acr.bicep - Update to 2025-11-01 (remove preview!)
```

### Phase 2: Core Infrastructure (Week 2)
```bicep
5. storage.bicep - Update to 2025-06-01
6. network.bicep - Update to 2025-05-01
7. private-endpoints.bicep - Update all network resources to 2025-05-01
```

### Phase 3: Application Tier (Week 3)
```bicep
8. container-apps.bicep - Update to 2026-01-01
9. function-app.bicep - Update to 2025-03-01
10. monitoring.bicep - Update Log Analytics to 2025-07-01
```

### Phase 4: Final Cleanup (Week 4)
```bicep
11. private-endpoints.bicep - Update privateDnsZones to 2024-06-01
12. Test entire deployment end-to-end
13. Document any breaking changes
```

---

## Testing Plan

### For Each API Version Update:

1. **Syntax Validation**
   ```bash
   az bicep build --file infra/modules/<module>.bicep
   ```

2. **What-If Deployment** (safe, no changes made)
   ```bash
   az deployment group what-if \
     --resource-group rg-test \
     --template-file infra/main.bicep \
     --parameters infra/parameters.dev.json
   ```

3. **Deploy to Dev Environment**
   ```bash
   az deployment group create \
     --resource-group rg-westeurope-magictoolbox-dev-01 \
     --template-file infra/main.bicep \
     --parameters infra/parameters.dev.json
   ```

4. **Verify Resources**
   - Check resource properties in Azure Portal
   - Test connectivity (database, storage, functions)
   - Run smoke tests

5. **Deploy to Production** (after dev validation)

---

## Breaking Changes to Watch For

### PostgreSQL (2023-03-01-preview → 2025-08-01)
- **GA API** - May have property name changes
- Check: `geoRedundantBackup`, `highAvailability`, `storage` properties
- **Action:** Review PostgreSQL Bicep schema documentation

### Container Apps (2023-05-01 → 2026-01-01)
- **Major version jump** - May introduce breaking changes
- Check: `configuration`, `template`, `workloadProfiles` structure
- **Action:** Review Container Apps API changelog

### Storage (2023-01-01 → 2025-06-01)
- Check: `networkAcls`, `encryption`, `immutabilityPolicy` properties
- **Action:** Review Storage API changelog

### Key Vault (2023-02-01 → 2025-05-01)
- Check: `accessPolicies` vs RBAC model changes
- **Action:** Ensure RBAC permissions are correctly configured

---

## Automation Recommendations

### Add to CI/CD Pipeline

```yaml
# .github/workflows/bicep-validation.yml
name: Bicep Validation

on: [pull_request]

jobs:
  validate-bicep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Bicep Build
        run: |
          az bicep build --file infra/main.bicep
      
      - name: What-If Deployment
        run: |
          az deployment group what-if \
            --resource-group rg-test \
            --template-file infra/main.bicep \
            --parameters infra/parameters.dev.json
```

### API Version Checker Script

```bash
#!/bin/bash
# scripts/check-bicep-api-versions.sh
# Checks Bicep files for outdated API versions

echo "Checking Bicep API versions..."
outdated=0

for file in infra/modules/*.bicep; do
  echo "Checking $file..."
  # Extract API versions and check against latest
  # Set outdated=1 if any are old
done

exit $outdated
```

---

## References

- [Azure Resource Provider API Versions](https://learn.microsoft.com/en-us/azure/templates/)
- [Bicep API Version Reference](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/bicep-functions-resource#api-version)
- [Azure Container Apps API Changes](https://learn.microsoft.com/en-us/azure/container-apps/whats-new)
- [PostgreSQL Flexible Server API](https://learn.microsoft.com/en-us/azure/templates/microsoft.dbforpostgresql/flexibleservers)

---

**Next Steps:**
1. Review this audit report
2. Plan update timeline (phased approach recommended)
3. Update development environment first
4. Test thoroughly before production
5. Document any breaking changes encountered
6. Add API version checks to CI/CD

---

**Last Updated:** December 17, 2025  
**Reviewed By:** GitHub Copilot  
**Next Audit:** March 17, 2026 (quarterly)
