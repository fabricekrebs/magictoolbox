# 🚀 Start Here: GitHub Secrets Setup

## What You Need to Do NOW

You have everything ready! Here's what to do to enable CI/CD:

### ✅ Step 1: Run the Automated Setup (5 minutes)

```bash
# From your repository root
./scripts/setup-github-secrets.sh
```

The script will ask you a few questions:
1. **Development resource group**: Press Enter to use `magictoolbox-dev-rg`
2. **Setup staging?**: Type `n` (unless you want staging)
3. **Setup production?**: Type `y` 
4. **Production resource group**: Type `magictoolbox-prod-rg`
5. **Continue?**: Type `y`

That's it! The script will:
- ✅ Create GitHub environments
- ✅ Create Azure service principals
- ✅ Configure all secrets
- ✅ Validate everything

### ✅ Step 2: Configure Production Protection (2 minutes)

1. Go to: `https://github.com/fabricekrebs/magictoolbox/settings/environments`
2. Click on **production** environment
3. Check **Required reviewers**
4. Add yourself (and team members)
5. Click **Save protection rules**

### ✅ Step 3: Test the Pipeline (3 minutes)

```bash
# Make a small test change
echo "# CI/CD Test" >> .github/test.md
git add .github/test.md
git commit -m "test: GitHub Actions pipeline"

# Push to trigger deployment
git push origin main
```

Then:
1. Go to: `https://github.com/fabricekrebs/magictoolbox/actions`
2. Watch the workflow run
3. When it reaches production, click **Review deployments**
4. Approve the deployment

---

## 📦 What Was Created for You

### 3 New Files You'll Use:

1. **`scripts/setup-github-secrets.sh`** ⭐
   - Automated setup script
   - **USE THIS FIRST!**

2. **`GITHUB_SECRETS_QUICK_REFERENCE.md`**
   - Quick commands reference
   - Use if you need to manually update secrets

3. **`GITHUB_SECRETS_SETUP.md`**
   - Complete manual setup guide
   - Use if automation fails or you want to understand details

### Other Files (Reference):
- `GITHUB_SETUP_SUMMARY.md` - Overview of everything
- `.github/workflows/azure-deploy.yml` - CI/CD pipeline (already configured)

---

## 🎯 Your Current Setup

```yaml
Repository: fabricekrebs/magictoolbox
Branch: main

Azure Resources (Already Deployed):
  Subscription: fec3a155-e384-43cd-abc7-9c20391a3fd4
  Tenant: af2dd59c-81cf-4524-8d9e-6d8254d02438
  
Development (Existing):
  Resource Group: magictoolbox-demo-rg
  Container App: app-magictoolboxdevgrrafkow
  ACR: magictoolboxdevacrgrrafkow6cceq.azurecr.io
  
Production (To Be Created):
  Resource Group: magictoolbox-prod-rg
  Container App: (will be deployed)
  Location: (you choose during bicep deployment)
```

---

## 💡 What Happens After Setup

### When you push to `main` branch:

```
1. ✅ Run tests (pytest, coverage)
2. ✅ Security scan (Trivy)
3. ✅ Build Docker image
4. ✅ Push to Azure Container Registry
5. ✅ Deploy to staging (optional)
6. ⏸️  Wait for approval (production)
7. ✅ Deploy to production (after approval)
8. ✅ Run health checks
```

### When you push to `develop` branch:

```
1. ✅ Run tests
2. ✅ Security scan
3. ✅ Build Docker image
4. ✅ Push to ACR
5. ✅ Deploy to development (automatic)
```

---

## 🔍 How to Verify Everything Works

### Check Secrets Are Configured

```bash
# List all secrets
gh secret list

# Should show 4 repository secrets:
# - ACR_LOGIN_SERVER
# - ACR_USERNAME
# - ACR_PASSWORD
# - ACR_NAME

# Check environment secrets
gh secret list --env development
gh secret list --env production
```

### Check Environments Exist

Go to: `https://github.com/fabricekrebs/magictoolbox/settings/environments`

You should see:
- ✅ development
- ✅ staging (if you chose to create it)
- ✅ production

### Check Service Principals

```bash
# List service principals
az ad sp list --display-name "sp-magictoolbox-cicd-" --query "[].{name:displayName, appId:appId}"
```

---

## 🆘 Troubleshooting

### "GitHub CLI not installed"

```bash
# Ubuntu/Debian
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh

# macOS
brew install gh
```

### "Not authenticated with GitHub"

```bash
gh auth login
# Follow the prompts to authenticate
```

### "Not authenticated with Azure"

```bash
az login
# Opens browser for authentication

# Set correct subscription
az account set --subscription fec3a155-e384-43cd-abc7-9c20391a3fd4
```

### "Service principal creation failed"

Ensure you have permission to create service principals:
```bash
# Check your role
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv)

# You need one of these roles:
# - Owner
# - User Access Administrator
# - Application Administrator
```

---

## ✨ Quick Start (TL;DR)

**Just run this and follow prompts:**

```bash
./scripts/setup-github-secrets.sh
```

**Then add yourself as production reviewer:**

1. Go to repository Settings → Environments → production
2. Enable "Required reviewers"
3. Add your GitHub username
4. Save

**Done!** Now every push to `main` will trigger automated deployment with approval gate for production.

---

## 📞 Need Help?

- **Script issues**: Check `GITHUB_SECRETS_SETUP.md` for manual steps
- **Azure issues**: Run `az account show` to verify authentication
- **GitHub issues**: Run `gh auth status` to verify authentication
- **Pipeline issues**: Check Actions tab for error logs

---

**Ready?** → Run `./scripts/setup-github-secrets.sh` now! 🚀
