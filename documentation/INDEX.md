# MagicToolbox Documentation Index

**Last Updated:** December 20, 2025

This index provides quick access to all documentation organized by topic.

---

## 📜 Project Constitution

- **[Constitution](../.specify/memory/constitution.md)** - **⚠️ REQUIRED READING** - Core principles, quality standards, and governance (v1.0.0)
  - Code Quality & Type Safety
  - Test-First Development (TDD)
  - User Experience Consistency
  - Performance Requirements
  - Security by Design

---

## 🚀 Getting Started

- **[README.md](README.md)** - Project overview and quick start guide
- **[ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](ASYNC_FILE_PROCESSING_GOLD_STANDARD.md)** - **⭐ MUST READ** - Critical reference for developing async tools

---

## 🏗️ Development Guides

### Frontend Development
- **[FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md)** - Django templates, Bootstrap, forms, and UI patterns

### Azure Integration  
- **[AZURE_NAMING_CONVENTION.md](AZURE_NAMING_CONVENTION.md)** - Resource naming standards and conventions

---

## 🔧 Tools Documentation

### Implemented Tools
- **[GPX_MERGER_TOOL.md](GPX_MERGER_TOOL.md)** - Multi-file GPX merging with 3 modes (chronological, sequential, preserve)
- **[OCR_TOOL.md](OCR_TOOL.md)** - Text extraction from images (14+ languages, Tesseract OCR)
- **[TEXT_TOOLS.md](TEXT_TOOLS.md)** - JSON formatter, Base64 encoder/decoder, hash generators
- **[VIDEO_ROTATION_TOOL.md](VIDEO_ROTATION_TOOL.md)** - Async video rotation (90°, 180°, 270°)

### PDF Tools
- **[PDF_CONVERSION_WORKFLOW.md](PDF_CONVERSION_WORKFLOW.md)** - PDF to DOCX conversion architecture
- **[PDF_DOCX_INTEGRATION_GUIDE.md](PDF_DOCX_INTEGRATION_GUIDE.md)** - Complete integration guide for PDF tools
- **[AZURE_FUNCTIONS_PDF_CONVERSION.md](AZURE_FUNCTIONS_PDF_CONVERSION.md)** - Azure Functions implementation details

---

## ☁️ Azure Deployment

### Infrastructure Setup
- **[AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md)** - Complete deployment guide (Bicep, Container Apps, Functions)
- **[PRODUCTION_SUBSCRIPTION_DEPLOYMENT.md](PRODUCTION_SUBSCRIPTION_DEPLOYMENT.md)** - **NEW** Step-by-step guide for deploying production to a new Azure subscription
- **[PRODUCTION_DEPLOYMENT_CHECKLIST.md](PRODUCTION_DEPLOYMENT_CHECKLIST.md)** - **NEW** Quick reference checklist for production deployment
- **[GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)** - CI/CD configuration and GitHub Actions secrets
- **[DEPLOYMENT_MONITORING.md](DEPLOYMENT_MONITORING.md)** - Application Insights, logging, and monitoring

### Security & Networking
- **[AZURE_KEYVAULT_APPINSIGHTS.md](AZURE_KEYVAULT_APPINSIGHTS.md)** - Key Vault and Application Insights setup
- **[VNET_AND_SECURITY.md](VNET_AND_SECURITY.md)** - Virtual Network configuration and security
- **[PRIVATE_ENDPOINTS_MIGRATION.md](PRIVATE_ENDPOINTS_MIGRATION.md)** - Private endpoints implementation

---

## 🧪 Testing

- **[E2E_API_TESTING_COMPLETE.md](E2E_API_TESTING_COMPLETE.md)** - Comprehensive API-based E2E testing guide
- **[E2E_API_TESTING_QUICK_REFERENCE.md](E2E_API_TESTING_QUICK_REFERENCE.md)** - Quick reference for running tests

---

## 🔍 Troubleshooting

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions for Azure Functions, deployments, and infrastructure

---

## 📚 Documentation Categories

### By Audience

**For New Developers:**
1. Start with [README.md](README.md)
2. Read [ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](ASYNC_FILE_PROCESSING_GOLD_STANDARD.md)
3. Review [FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md)
4. Check [E2E_API_TESTING_QUICK_REFERENCE.md](E2E_API_TESTING_QUICK_REFERENCE.md)

**For DevOps/Infrastructure:**
1. [AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md)
2. [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)
3. [VNET_AND_SECURITY.md](VNET_AND_SECURITY.md)
4. [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

**For Feature Development:**
1. [ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](ASYNC_FILE_PROCESSING_GOLD_STANDARD.md) ⭐
2. Tool-specific docs (GPX, OCR, PDF, Video, Text)
3. [FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md)
4. [E2E_API_TESTING_COMPLETE.md](E2E_API_TESTING_COMPLETE.md)

**For Testing/QA:**
1. [E2E_API_TESTING_COMPLETE.md](E2E_API_TESTING_COMPLETE.md)
2. [E2E_API_TESTING_QUICK_REFERENCE.md](E2E_API_TESTING_QUICK_REFERENCE.md)
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### By Technology

**Django/Python:**
- ASYNC_FILE_PROCESSING_GOLD_STANDARD.md
- FRONTEND_IMPLEMENTATION_GUIDE.md
- Tool-specific docs

**Azure Services:**
- AZURE_DEPLOYMENT_README.md
- AZURE_FUNCTIONS_PDF_CONVERSION.md
- AZURE_KEYVAULT_APPINSIGHTS.md
- VNET_AND_SECURITY.md
- PRIVATE_ENDPOINTS_MIGRATION.md
- TROUBLESHOOTING.md

**CI/CD & DevOps:**
- GITHUB_SECRETS_SETUP.md
- DEPLOYMENT_MONITORING.md
- AZURE_DEPLOYMENT_README.md

**Testing:**
- E2E_API_TESTING_COMPLETE.md
- E2E_API_TESTING_QUICK_REFERENCE.md

---

## 📖 Reading Order for Common Tasks

### Task: Deploy to Azure (First Time)
1. [AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md) - Main deployment guide
2. [GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md) - Configure CI/CD
3. [AZURE_KEYVAULT_APPINSIGHTS.md](AZURE_KEYVAULT_APPINSIGHTS.md) - Set up secrets and monitoring
4. [DEPLOYMENT_MONITORING.md](DEPLOYMENT_MONITORING.md) - Configure observability
5. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - If issues arise

### Task: Add a New Async Tool
1. [ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](ASYNC_FILE_PROCESSING_GOLD_STANDARD.md) ⭐ - **READ THIS FIRST**
2. Reference implementations: [GPX_MERGER_TOOL.md](GPX_MERGER_TOOL.md), [VIDEO_ROTATION_TOOL.md](VIDEO_ROTATION_TOOL.md), [OCR_TOOL.md](OCR_TOOL.md)
3. [FRONTEND_IMPLEMENTATION_GUIDE.md](FRONTEND_IMPLEMENTATION_GUIDE.md) - UI patterns
4. [E2E_API_TESTING_COMPLETE.md](E2E_API_TESTING_COMPLETE.md) - Add tests

### Task: Debug Deployment Issues
1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
2. [DEPLOYMENT_MONITORING.md](DEPLOYMENT_MONITORING.md) - Check logs
3. [VNET_AND_SECURITY.md](VNET_AND_SECURITY.md) - Network issues
4. [AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md) - Verify configuration

### Task: Run Tests
1. [E2E_API_TESTING_QUICK_REFERENCE.md](E2E_API_TESTING_QUICK_REFERENCE.md) - Quick start
2. [E2E_API_TESTING_COMPLETE.md](E2E_API_TESTING_COMPLETE.md) - Detailed guide

---

## 📝 Document Maintenance

### Active Documents (Regularly Updated)
- ASYNC_FILE_PROCESSING_GOLD_STANDARD.md ⭐
- E2E_API_TESTING_COMPLETE.md
- TROUBLESHOOTING.md
- README.md

### Reference Documents (Stable)
- AZURE_DEPLOYMENT_README.md
- AZURE_NAMING_CONVENTION.md
- FRONTEND_IMPLEMENTATION_GUIDE.md
- VNET_AND_SECURITY.md

### Implementation Guides (Per-Tool)
- GPX_MERGER_TOOL.md
- OCR_TOOL.md
- TEXT_TOOLS.md
- VIDEO_ROTATION_TOOL.md
- PDF_CONVERSION_WORKFLOW.md
- PDF_DOCX_INTEGRATION_GUIDE.md
- AZURE_FUNCTIONS_PDF_CONVERSION.md

---

## 🆘 Quick Links

**Need help with Azure Functions?**  
→ [TROUBLESHOOTING.md#azure-functions-issues](TROUBLESHOOTING.md)

**Need to add a new tool?**  
→ [ASYNC_FILE_PROCESSING_GOLD_STANDARD.md](ASYNC_FILE_PROCESSING_GOLD_STANDARD.md)

**Need to deploy?**  
→ [AZURE_DEPLOYMENT_README.md](AZURE_DEPLOYMENT_README.md)

**Need to test?**  
→ [E2E_API_TESTING_QUICK_REFERENCE.md](E2E_API_TESTING_QUICK_REFERENCE.md)

**Network/security issues?**  
→ [VNET_AND_SECURITY.md](VNET_AND_SECURITY.md) or [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

**Total Documents:** 20  
**Categories:** Development (5), Azure (8), Testing (2), Tools (7), Troubleshooting (1), Index (1)
