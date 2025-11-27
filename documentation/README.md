# MagicToolbox Documentation

This folder contains all deployment, operations, and Azure integration documentation for the MagicToolbox project.

## Quick Start Guides

### Getting Started
- **[START_HERE_GITHUB_SETUP.md](START_HERE_GITHUB_SETUP.md)** - Begin here for initial setup
- **[AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md)** - Quick Azure deployment guide
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference cheat sheet

## Azure Deployment

### Infrastructure & Naming
- **[AZURE_NAMING_CONVENTION.md](AZURE_NAMING_CONVENTION.md)** - ⭐ Azure resource naming standards (START HERE)
- **[AZURE_NAMING_MIGRATION.md](AZURE_NAMING_MIGRATION.md)** - Migration guide for new naming convention
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide with all steps

### Azure Integration
- **[AZURE_KEYVAULT_APPINSIGHTS.md](AZURE_KEYVAULT_APPINSIGHTS.md)** - Key Vault & Application Insights setup
- **[AZURE_CONTAINER_APPS_TROUBLESHOOTING.md](AZURE_CONTAINER_APPS_TROUBLESHOOTING.md)** - Troubleshooting guide
- **[AZURE_RESOURCES_USAGE_ANALYSIS.md](AZURE_RESOURCES_USAGE_ANALYSIS.md)** - Resource usage analysis

## GitHub Actions & CI/CD

### GitHub Setup
- **[GITHUB_SECRETS_QUICK_REFERENCE.md](GITHUB_SECRETS_QUICK_REFERENCE.md)** - ⭐ Secrets checklist (essential)
- **[GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)** - Detailed secrets configuration
- **[GITHUB_SETUP_SUMMARY.md](GITHUB_SETUP_SUMMARY.md)** - Complete GitHub Actions setup

## Implementation Summaries

- **[DEVOPS_IMPLEMENTATION_SUMMARY.md](DEVOPS_IMPLEMENTATION_SUMMARY.md)** - DevOps implementation overview

## Document Organization

### By Topic

**New to the Project?**
1. Read [AZURE_NAMING_CONVENTION.md](AZURE_NAMING_CONVENTION.md)
2. Follow [START_HERE_GITHUB_SETUP.md](START_HERE_GITHUB_SETUP.md)
3. Use [GITHUB_SECRETS_QUICK_REFERENCE.md](GITHUB_SECRETS_QUICK_REFERENCE.md)

**Deploying to Azure?**
1. Check [AZURE_NAMING_CONVENTION.md](AZURE_NAMING_CONVENTION.md)
2. Follow [DEPLOYMENT.md](DEPLOYMENT.md)
3. Configure [AZURE_KEYVAULT_APPINSIGHTS.md](AZURE_KEYVAULT_APPINSIGHTS.md)

**Troubleshooting?**
1. See [AZURE_CONTAINER_APPS_TROUBLESHOOTING.md](AZURE_CONTAINER_APPS_TROUBLESHOOTING.md)
2. Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for commands

**Setting Up CI/CD?**
1. Follow [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)
2. Use [GITHUB_SECRETS_QUICK_REFERENCE.md](GITHUB_SECRETS_QUICK_REFERENCE.md) as checklist

## Related Files in Repository

### Infrastructure as Code
- `/infra/` - Bicep templates for all Azure resources
- `/infra/modules/` - Modular Bicep components
- `/infra/parameters.*.json` - Environment-specific parameters

### Deployment Scripts
- `/scripts/deploy-to-azure.sh` - Automated deployment script
- `/scripts/setup-github-secrets.sh` - GitHub secrets automation
- `/scripts/startup.sh` - Container startup script

### Application Code
- `/apps/` - Django application modules
- `/magictoolbox/settings/` - Environment-specific settings
- `/templates/` - Django templates

## Contributing to Documentation

When updating documentation:

1. **Keep it current** - Update references when code changes
2. **Be specific** - Include exact commands and examples
3. **Cross-reference** - Link to related documentation
4. **Test commands** - Verify all commands work before committing
5. **Use consistent naming** - Follow the naming convention guide

## Questions or Issues?

If you find issues with the documentation:
1. Check if it's a known issue in troubleshooting guides
2. Verify you're using the latest version from `main` branch
3. Open an issue with details about what's unclear or incorrect

---

**Last Updated**: November 27, 2025  
**Maintained By**: MagicToolbox Team
