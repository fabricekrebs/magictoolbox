# MagicToolbox Documentation

**Last Updated**: December 11, 2025

This folder contains all deployment, operations, and Azure integration documentation for the MagicToolbox project.

---

## ⭐ GOLD STANDARD - START HERE

### For New Async File Processing Tools
- **[ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](ASYNC_FILE_PROCESSING_GOLD_STANDARD.md)** - **MANDATORY** architecture pattern for all async file processing tools
  - Complete flow diagrams
  - Code templates and examples
  - Naming conventions
  - Testing requirements
  - Deployment standards
  - **Reference implementations**: PDF to DOCX, Video Rotation

---

## 🚀 Quick Start

### Essential Guides (First-Time Deployment)
- **[AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md)** - Main deployment overview with architecture
- **[GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)** - GitHub Actions secrets configuration

## 📁 Documentation Structure

### Azure Infrastructure & Deployment
- **[AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md)** - Overview, architecture, and quick start
- **[VNET_AND_SECURITY.md](VNET_AND_SECURITY.md)** - Network topology, security, and private endpoints

### Security & Networking
- **[VNET_AND_SECURITY.md](VNET_AND_SECURITY.md)** - VNet integration, private endpoints, security configurations
- **[PRIVATE_ENDPOINTS_MIGRATION.md](PRIVATE_ENDPOINTS_MIGRATION.md)** - Private endpoint migration guide
- **[AZURE_KEYVAULT_APPINSIGHTS.md](AZURE_KEYVAULT_APPINSIGHTS.md)** - Key Vault & Application Insights setup

### CI/CD & GitHub Setup
- **[GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)** - Complete GitHub Actions secrets guide
  - Service principal creation
  - ACR credentials
  - Environment secrets configuration

### Azure Naming & Standards
- **[AZURE_NAMING_CONVENTION.md](AZURE_NAMING_CONVENTION.md)** - Azure resource naming standards

### Tool-Specific Documentation (Reference Implementations)
- **[PDF_DOCX_INTEGRATION_GUIDE.md](PDF_DOCX_INTEGRATION_GUIDE.md)** - PDF to DOCX converter (async reference)
- **[AZURE_FUNCTIONS_PDF_CONVERSION.md](AZURE_FUNCTIONS_PDF_CONVERSION.md)** - Azure Function implementation
- **[PDF_CONVERSION_WORKFLOW.md](PDF_CONVERSION_WORKFLOW.md)** - Complete workflow
- **[PDF_DOCX_TEST_RESULTS.md](PDF_DOCX_TEST_RESULTS.md)** - Test results
- **[VIDEO_ROTATION_TOOL.md](VIDEO_ROTATION_TOOL.md)** - Video rotation tool

### Testing
- **[TESTING_STRATEGY.md](TESTING_STRATEGY.md)** - Overall testing approach
- **[E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md)** - End-to-end testing
- **[E2E_TESTING_IMPLEMENTATION.md](E2E_TESTING_IMPLEMENTATION.md)** - E2E implementation details
- **[E2E_TESTING_QUICK_REFERENCE.md](E2E_TESTING_QUICK_REFERENCE.md)** - Quick reference
- **[AZURE_E2E_TESTING_GUIDE.md](AZURE_E2E_TESTING_GUIDE.md)** - Azure-specific E2E testing

### Monitoring & Operations
- **[DEPLOYMENT_MONITORING.md](DEPLOYMENT_MONITORING.md)** - Monitoring and observability

---

## 🎯 Quick Navigation

### I Want To...

**Create a New Async File Processing Tool**
1. **READ** [ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](ASYNC_FILE_PROCESSING_GOLD_STANDARD.md) - Complete pattern
2. Review reference implementations: PDF Converter or Video Rotation
3. Follow the compliance checklist
4. Copy naming conventions and structure

**Deploy to Azure for the First Time**
1. Review [AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md) for architecture overview
2. Set up GitHub secrets with [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)
3. Run deployment from `/infra/` folder

**Understand the Network Architecture**
1. Read [VNET_AND_SECURITY.md](VNET_AND_SECURITY.md)
2. Review [AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md) architecture section
3. Check [PRIVATE_ENDPOINTS_MIGRATION.md](PRIVATE_ENDPOINTS_MIGRATION.md) for private endpoint details

**Verify My Deployment**
1. Use [DEPLOYMENT_VERIFICATION.md](DEPLOYMENT_VERIFICATION.md) - comprehensive checklist with all commands
2. Check [INFRASTRUCTURE_CLEANUP_SUMMARY.md](INFRASTRUCTURE_CLEANUP_SUMMARY.md) for current state

**Set Up CI/CD**
1. Follow [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)
2. Use automated script: `./scripts/setup-github-secrets.sh`

**Troubleshoot Issues**
1. Check [VNET_AND_SECURITY.md](VNET_AND_SECURITY.md) troubleshooting section
2. Review [DEPLOYMENT_VERIFICATION.md](DEPLOYMENT_VERIFICATION.md) for connectivity tests
3. Verify infrastructure state in [INFRASTRUCTURE_CLEANUP_SUMMARY.md](INFRASTRUCTURE_CLEANUP_SUMMARY.md)

## 📂 Related Files in Repository

### Infrastructure as Code
- `/infra/main.bicep` - Main orchestration template
- `/infra/modules/` - Modular Bicep components (network, storage, database, etc.)
- `/infra/parameters.*.bicepparam` - Environment-specific parameters

### Deployment Scripts
- `/scripts/deploy-to-azure.sh` - Automated deployment script
- `/scripts/setup-github-secrets.sh` - GitHub secrets automation
- `.github/workflows/` - CI/CD workflows

### Application Code
- `/apps/` - Django application modules
- `/function_app/` - Azure Functions app for PDF conversion
- `/magictoolbox/settings/` - Environment-specific settings
- `/templates/` - Django templates

## 📝 Current Infrastructure Status

As of **December 2, 2025**, the infrastructure is **production-ready** with:

✅ **Network Security**: VNet integration, private endpoints for all services  
✅ **Database**: PostgreSQL with private endpoint, correct database name (`magictoolbox`)  
✅ **Storage**: Managed identity access only, no IP firewall rules  
✅ **Key Vault**: Private endpoint only, no public access  
✅ **Function App**: VNet integrated, all traffic routed through VNet  
✅ **End-to-End Testing**: PDF to DOCX conversion validated  

See [INFRASTRUCTURE_CLEANUP_SUMMARY.md](INFRASTRUCTURE_CLEANUP_SUMMARY.md) for details.

## 🤝 Contributing to Documentation

When updating documentation:

1. **Keep it current** - Update references when code changes
2. **Be specific** - Include exact commands and examples
3. **Cross-reference** - Link to related documentation
4. **Test commands** - Verify all commands work before committing
5. **Use consistent naming** - Follow the naming convention guide
6. **Update this README** - When adding new documentation files

## ❓ Questions or Issues?

If you find issues with the documentation:
1. Check [VNET_AND_SECURITY.md](VNET_AND_SECURITY.md) troubleshooting section
2. Review [DEPLOYMENT_VERIFICATION.md](DEPLOYMENT_VERIFICATION.md)
3. Verify you're using the latest version from `main` branch
4. Open an issue with details about what's unclear or incorrect

---

**Last Updated**: December 2, 2025  
**Status**: Production-ready infrastructure, comprehensive documentation  
**Maintained By**: MagicToolbox Team
