# 🔧 Environment Configuration Guide

## Overview
This guide helps you configure environment variables for all AI DevOps services. Each service requires specific configuration to connect to external APIs and services.

## ⚠️ Security Notice
- Never commit `.env` files to version control
- Use strong, unique passwords and API keys
- Rotate credentials regularly
- Consider using Azure Key Vault or similar for production

## 🏗️ Service Configuration

### 1. Controller Service
**File**: `controller-service/.env`

```bash
# Copy example file
cp controller-service/.env.example controller-service/.env
```

**Required Configuration**:
```env
# Azure Key Vault (Required for production)
AZURE_KEY_VAULT_NAME=your-key-vault-name
AZURE_CLIENT_ID=your-azure-client-id
AZURE_CLIENT_SECRET=your-azure-client-secret
AZURE_TENANT_ID=your-azure-tenant-id

# JWT Security
JWT_SECRET_KEY=your-super-secret-jwt-key-minimum-32-characters

# Database connections (using Docker defaults)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/aidevops
REDIS_URL=redis://redis:6379
```

### 2. GitHub Governance Factory
**File**: `github-governance-factory/.env`

```bash
# Copy example file (if exists)
cp github-governance-factory/.env.example github-governance-factory/.env
```

**Required Configuration**:
```env
# GitHub API
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_ORG=your-organization-name

# Service configuration
API_HOST=0.0.0.0
API_PORT=8001
```

### 3. Azure DevOps Governance Factory
**File**: `azure-devops-governance-factory/.env`

```env
# Azure DevOps API
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_TOKEN=your-personal-access-token

# Service configuration
API_HOST=0.0.0.0
API_PORT=8002
```

### 4. AI Provider Factory
**File**: `ai-provider-factory/.env`

```env
# OpenAI API
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4000

# Azure OpenAI (Alternative)
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2023-12-01-preview

# Anthropic Claude (Optional)
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Service configuration
API_HOST=0.0.0.0
API_PORT=8003
```

### 5. Database Governance Factory
**File**: `database-governance-factory/.env`

```env
# Database connections for governance
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=aidevops
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_DB=aidevops

REDIS_HOST=redis
REDIS_PORT=6379

# Service configuration
API_HOST=0.0.0.0
API_PORT=8004
```

## 🔑 Obtaining API Keys

### GitHub Token
1. Go to GitHub Settings > Developer settings > Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `admin:org`, `workflow`, `admin:repo_hook`
4. Copy the generated token

### Azure DevOps Token
1. Go to Azure DevOps > User settings > Personal access tokens
2. Create new token
3. Select scopes: `Build`, `Code`, `Project and team`, `Work items`
4. Copy the generated token

### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy the key (starts with `sk-`)

### Azure Key Vault Setup
1. Create Azure Key Vault in Azure Portal
2. Create Service Principal (App Registration)
3. Grant Service Principal access to Key Vault
4. Copy: Client ID, Client Secret, Tenant ID, Key Vault Name

## 🚀 Quick Setup Script

For Windows PowerShell:
```powershell
# Create all environment files from examples
$services = @(
    "controller-service",
    "github-governance-factory", 
    "azure-devops-governance-factory",
    "ai-provider-factory",
    "database-governance-factory"
)

foreach ($service in $services) {
    if (Test-Path "$service\.env.example") {
        if (!(Test-Path "$service\.env")) {
            Copy-Item "$service\.env.example" "$service\.env"
            Write-Host "✅ Created $service\.env" -ForegroundColor Green
        } else {
            Write-Host "⚠️  $service\.env already exists" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n🔧 Now edit each .env file with your API keys and credentials" -ForegroundColor Cyan
```

## 📋 Environment Checklist

Before starting the system, ensure you have:

### Required for Basic Operation:
- [ ] JWT secret key (32+ characters)
- [ ] Database passwords changed from defaults
- [ ] At least one AI provider configured (OpenAI/Azure OpenAI)

### Required for Full Functionality:
- [ ] GitHub token with proper scopes
- [ ] Azure DevOps token (if using Azure DevOps)
- [ ] Azure Key Vault configured (production)
- [ ] All service .env files created and configured

### Optional but Recommended:
- [ ] Monitoring credentials secured
- [ ] CORS origins configured for your domain
- [ ] Log levels set appropriately
- [ ] SSL certificates for production

## 🔒 Production Security

### Azure Key Vault Integration
The Controller Service can pull secrets from Azure Key Vault instead of environment variables:

```env
# Enable Key Vault mode
USE_AZURE_KEY_VAULT=true
AZURE_KEY_VAULT_NAME=your-production-vault

# Key Vault secret names
GITHUB_TOKEN_SECRET_NAME=github-api-token
OPENAI_API_KEY_SECRET_NAME=openai-api-key
DATABASE_PASSWORD_SECRET_NAME=postgres-password
```

### Docker Secrets (Production)
For production deployments, use Docker secrets or Kubernetes secrets instead of environment variables.

## 🆘 Troubleshooting

### Common Issues:

**Service won't start**:
- Check .env file exists and has required values
- Verify API keys are valid and have correct permissions
- Check service logs: `docker-compose logs <service-name>`

**Authentication errors**:
- Verify GitHub token has required scopes
- Check Azure tokens haven't expired
- Ensure Azure Key Vault permissions are correct

**Database connection errors**:
- Verify database services are running: `docker-compose ps`
- Check database credentials in .env files
- Ensure database containers have proper networking

### Getting Help:
- Check service logs: `docker-compose logs -f`
- Verify service health: http://localhost:8000/health
- Review Docker network: `docker network ls`

## 📚 Additional Resources

- [Docker Setup Guide](./DOCKER-SETUP.md)
- [Controller Service Documentation](./controller-service/README.md)
- [GitHub Governance Factory](./github-governance-factory/README.md)
- [AI Provider Factory](./ai-provider-factory/README.md)
- [Security Best Practices](./SECURITY.md)
