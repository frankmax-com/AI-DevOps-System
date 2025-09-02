# Contributing Guidelines - AI DevOps System

## 🎯 **Overview**
Welcome to the AI DevOps Autonomous Development Platform! This is a self-governing enterprise system that uses its own GitHub Governance Factory to manage development. Before contributing, understand our recursive governance model.

## 🏗️ **Repository Architecture**

### **Git Strategy: Monorepo with Subtrees + Submodule**
- **Agent Services** → Git Subtrees (unified development)
- **Governance Factory** → Git Submodule (reusable across projects)
- **Issue Tracking** → Self-managed through GitHub Governance Factory

### **Why This Architecture?**
- **Unified Development**: All agent services developed together for coordination
- **Atomic Releases**: Deploy coordinated agent updates simultaneously  
- **Governance Reusability**: GitHub Governance Factory used across multiple projects
- **Enterprise Compliance**: Centralized audit trails and governance

## 🛠️ **Git Subtree Operations (Agent Services)**

### **Initial Setup for New Contributor**
```bash
# Clone the main repository
git clone https://github.com/frankmax-com/AI-DevOps-System.git
cd AI-DevOps-System

# Initialize submodule for governance
git submodule update --init --recursive
```

### **Pulling Latest Changes from Agent Service Upstream**
```bash
# For dev-agent-service
git subtree pull --prefix=dev-agent-service https://github.com/frankmax-com/dev-agent-service main --squash

# For ai-provider-agent-service  
git subtree pull --prefix=ai-provider-agent-service https://github.com/frankmax-com/ai-provider-agent-service main --squash

# For orchestrator-service
git subtree pull --prefix=orchestrator-service https://github.com/frankmax-com/orchestrator-service main --squash
```

### **Pushing Changes Back to Agent Service Upstream**
```bash
# For dev-agent-service
git subtree push --prefix=dev-agent-service https://github.com/frankmax-com/dev-agent-service main

# For ai-provider-agent-service
git subtree push --prefix=ai-provider-agent-service https://github.com/frankmax-com/ai-provider-agent-service main

# For orchestrator-service  
git subtree push --prefix=orchestrator-service https://github.com/frankmax-com/orchestrator-service main
```

### **Adding New Agent Service as Subtree**
```bash
# Add new agent service (example: security-agent-service)
git subtree add --prefix=security-agent-service https://github.com/frankmax-com/security-agent-service main --squash

# Update .github/COPILOT_INSTRUCTIONS.md to include new service
# Update README.md to reflect new service status
```

## 🏭 **Git Submodule Operations (Governance Factory)**

### **Initialize Submodule**
```bash
git submodule update --init --recursive
```

### **Update Governance Factory to Latest**
```bash
cd github-governance-factory
git checkout main && git pull origin main
cd ..
git add github-governance-factory
git commit -m "feat(governance): update GitHub Governance Factory submodule

Updated to latest governance templates and automation scripts.

Related to Epic #1 (System Foundation)"
```

### **Working with Governance Factory Changes**
```bash
# If you need to make changes to the governance factory
cd github-governance-factory
git checkout -b feature/update-templates
# Make your changes
git add .
git commit -m "feat: update organization templates"
git push origin feature/update-templates
# Create PR in governance factory repo

# Back in main repo, update submodule reference after merge
cd ..
git submodule update --remote github-governance-factory
git add github-governance-factory  
git commit -m "feat(governance): update to latest governance factory"
```

## 📋 **Development Workflow**

### **1. Branch Strategy**
```bash
# Feature development
git checkout -b feature/agent-service-enhancement

# Bug fixes
git checkout -b bugfix/orchestrator-webhook-error

# Agent service specific work
git checkout -b agent/dev-agent/react-templates
```

### **2. Commit Message Standards**
```bash
# Standard format
git commit -m "type(scope): description

Longer description explaining the change and business impact.

Closes #issue-number
Related to Epic #epic-number, Feature #feature-number

Agent: [agent-service-name]
Sprint: [current-sprint]
Progress: [previous%] → [new%]"

# Examples
git commit -m "feat(dev-agent): implement React scaffolding templates

Added comprehensive React TypeScript templates with:
- Component scaffolding
- Hook patterns  
- Testing setup
- Storybook integration

Closes #42
Related to Epic #1, Feature #15

Agent: dev-agent-service
Sprint: September 1-15, 2025
Progress: Templates 60% → 85%"

git commit -m "fix(orchestrator): resolve webhook processing timeout

Fixed timeout issue in GitHub webhook processing by:
- Implementing async queue processing
- Adding retry logic with exponential backoff
- Improving error handling and logging

Closes #38
Related to Epic #1, Feature #8

Agent: orchestrator-service  
Sprint: September 1-15, 2025
Progress: Webhook reliability 70% → 95%"
```

### **3. Pull Request Process**
1. **Link to Issues**: Always reference Epic → Feature → Task hierarchy
2. **Agent Context**: Specify which agent service(s) are affected
3. **Testing**: Include test coverage and integration test results
4. **Documentation**: Update relevant README.md and spec files
5. **Governance**: Update GitHub Project board status

### **4. Code Review Checklist**
- [ ] **Architecture Compliance**: Follows agent service patterns
- [ ] **Error Handling**: Comprehensive try/catch with audit logging
- [ ] **Testing**: Unit tests + integration tests + coverage > 80%
- [ ] **Documentation**: Updated docstrings and README.md
- [ ] **Security**: No hardcoded secrets, proper validation
- [ ] **Performance**: Async patterns, proper connection pooling
- [ ] **Monitoring**: Includes health endpoints and metrics
- [ ] **Governance**: GitHub Issues and Project board updated

## 🔧 **Development Environment Setup**

### **Prerequisites**
```bash
# Python 3.11+
python --version

# Docker & Docker Compose
docker --version
docker-compose --version

# GitHub CLI (for governance integration)
gh --version

# Node.js (for frontend components)
node --version
npm --version
```

### **Local Development Setup**
```bash
# 1. Clone and setup
git clone https://github.com/frankmax-com/AI-DevOps-System.git
cd AI-DevOps-System
git submodule update --init --recursive

# 2. Create Python virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\activate   # Windows

# 3. Install dependencies for all services
pip install -r orchestrator-service/requirements.txt
pip install -r dev-agent-service/requirements.txt  
pip install -r ai-provider-agent-service/requirements.txt

# 4. Copy environment files
cp orchestrator-service/.env.example orchestrator-service/.env
cp dev-agent-service/.env.example dev-agent-service/.env
cp ai-provider-agent-service/.env.example ai-provider-agent-service/.env

# 5. Configure environment variables
# Edit .env files with your API keys and configuration

# 6. Start development stack
docker-compose up -d  # Starts databases and monitoring
```

### **Running Individual Services**
```bash
# Orchestrator Service
cd orchestrator-service
python -m src.main

# Dev Agent Service  
cd dev-agent-service
python -m src.agent

# AI Provider Agent Service
cd ai-provider-agent-service
python -m src.ai_provider_agent
```

### **Running Tests**
```bash
# Run all tests
python -m pytest

# Run tests for specific service
python -m pytest orchestrator-service/tests/
python -m pytest dev-agent-service/tests/
python -m pytest ai-provider-agent-service/tests/

# Run with coverage
python -m pytest --cov=src --cov-report=html
```

## 🎯 **Agent Service Development Patterns**

### **Standard Service Structure**
```
{agent-service}/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # Pydantic models
│   ├── utils.py             # Shared utilities
│   └── {service_specific}.py # Service-specific logic
├── tests/
│   ├── test_main.py         # API endpoint tests
│   ├── test_models.py       # Model validation tests
│   └── test_{specific}.py   # Service-specific tests
├── specs/
│   ├── README.md            # Service overview
│   ├── business/            # Business requirements
│   ├── functional/          # Functional specifications
│   └── implementation/      # Technical implementation details
├── k8s/                     # Kubernetes deployment configs
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── Dockerfile              # Container build instructions
└── README.md               # Service documentation
```

### **Standard API Patterns**
```python
# Health check (required for all services)
@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "service": "{service-name}", "version": "1.0.0"}

# Work initiation pattern
@app.post("/api/v1/work/start")
async def start_work(request: WorkRequest):
    """Start work item with audit trail and orchestrator coordination"""
    
# Status tracking pattern
@app.get("/api/v1/work/{work_id}/status")
async def get_work_status(work_id: str):
    """Get work item status with progress tracking"""
    
# Webhook pattern (for GitHub integration)
@app.post("/api/v1/webhook/github")
async def handle_github_webhook(request: GitHubWebhookRequest):
    """Handle GitHub webhook with signature verification"""
```

## 📊 **GitHub Integration Standards**

### **Issue Management**
- **Epic Level**: High-level business capabilities (months)
- **Feature Level**: Specific functionality (2-4 weeks)  
- **Task Level**: Implementation units (1-3 days)

### **Project Board Integration**
All work items must be tracked in the GitHub Project board:
1. **Backlog**: Planned work items
2. **Sprint Ready**: Items ready for current sprint
3. **In Progress**: Active development
4. **Review**: Code review and testing
5. **Done**: Completed and deployed

### **Label Standards**
```
Agent Services:
- agent:orchestrator
- agent:dev
- agent:ai-provider
- agent:qa
- agent:security
- agent:release
- agent:pm
- agent:audit

Work Types:
- type:feature
- type:bug
- type:enhancement
- type:docs

Priority:
- priority:critical
- priority:high  
- priority:medium
- priority:low

Sprint:
- sprint:current
- sprint:next
- sprint:backlog
```

## 🔒 **Security Guidelines**

### **Secrets Management**
- **Never commit secrets**: Use .env files (in .gitignore)
- **Environment Variables**: All sensitive config via env vars
- **Vault Integration**: Production uses Azure Key Vault
- **API Keys**: Rotate regularly, use service principals

### **Code Security**
- **Input Validation**: All API inputs validated with Pydantic
- **SQL Injection**: Use parameterized queries only
- **XSS Prevention**: Proper output encoding
- **Authentication**: JWT tokens with proper expiration
- **Rate Limiting**: Implement on all public endpoints

## 🚀 **Deployment Process**

### **Development Deployment**
```bash
# Build and test locally
docker-compose build
docker-compose up -d
python -m pytest

# Deploy to development environment
kubectl apply -f k8s/development/
```

### **Production Deployment**
Production deployments are handled through GitHub Actions and Azure Pipelines:
1. **PR Merge** → Triggers CI/CD pipeline
2. **Build & Test** → Docker images built and tested
3. **Security Scan** → Vulnerability scanning
4. **Deploy to Staging** → Automated staging deployment
5. **Integration Tests** → End-to-end testing
6. **Production Deployment** → Blue/green deployment
7. **Monitoring** → Automatic rollback if issues detected

## 🔍 **Debugging & Troubleshooting**

### **Common Issues**

**Subtree Merge Conflicts**:
```bash
# Resolve conflicts manually, then:
git add .
git commit -m "resolve: merge conflicts in subtree pull"
```

**Submodule Not Updating**:
```bash
git submodule update --init --recursive --remote
```

**Agent Service Communication Issues**:
```bash
# Check service discovery
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/api/v1/health

# Check orchestrator logs
docker-compose logs orchestrator-service
```

### **Logging Standards**
```python
import structlog

logger = structlog.get_logger()

# Standard log format
logger.info("operation_completed", 
           operation="scaffold_react_app",
           agent="dev-agent-service", 
           work_id="work_123",
           duration_ms=1250,
           status="success")
```

## 🤝 **Getting Help**

### **Documentation**
- **Architecture**: `specs/design/` directory
- **API Documentation**: Auto-generated at `/docs` endpoint
- **Governance**: `github-governance-factory/specs/`

### **Support Channels**
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Architecture discussions
- **GitHub Project**: Sprint planning and status

### **Code Review**
- All PRs require at least 2 reviewers
- Architecture changes require senior architect approval
- Security-related changes require security team approval

---

**Remember**: This is a self-governing system. When you contribute, you're helping build a platform that manages its own development. Your changes will be tracked, audited, and coordinated through the very system you're improving!
