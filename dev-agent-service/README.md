# Dev Agent Service

> AI DevOps Development Agent - Program Factory Worker

The Development Agent Service is the core "factory worker" in the AI DevOps system. It transforms technical requirements into executable code by scaffolding complete application structures in Azure Repos, creating commits, managing pull requests, and updating documentation with full audit trails.

## 🔍 Service Overview

### Core Responsibilities

- **🛠️ Program Scaffolding**: Generates complete application structures from requirements
- **📝 Code Generation**: Creates production-ready code with proper patterns and practices
- **🔗 Work Item Integration**: Links all code changes to Azure DevOps work items (#workitemid)
- **🏗️ Pull Request Automation**: Creates PRs with ready-to-merge code and documentation
- **📚 Wiki Documentation**: Updates Azure Wiki with program details and architecture
- **💾 Repository Management**: Handles branch creation, commits, and git operations

### Supported Frameworks

- **Backend**: FastAPI, Flask, Django, Node.js/Express
- **Frontend**: React, Vue.js, Angular
- **Database**: PostgreSQL, MongoDB, Redis integrations
- **Deployment**: Docker, Kubernetes manifests
- **Testing**: Pytest, Jest with comprehensive coverage
- **Documentation**: Auto-generated API docs, READMEs

## 🚀 API Endpoints

### Health & Information

```bash
GET  /health          # Service health status
GET  /                 # Service information & capabilities
GET  /capabilities     # List supported frameworks & features
```

### Scaffolding Operations

```bash
POST /scaffolds        # Scaffold new program → returns repository details
GET  /scaffolds/:id    # Get scaffolding status
POST /work-items       # Update Azure DevOps work items
```

### Webhook Integration

```
POST /webhooks/azure-devops # Receives Azure DevOps events
```

## 🛠️ Usage Example

### Scaffold a FastAPI Backend

```python
import requests

response = requests.post("http://localhost:8000/scaffolds", json={
    "work_item_id": 12345,
    "organization_url": "https://myorg.visualstudio.com",
    "project_name": "MyProject",
    "repository_name": "new-backend-api",
    "framework": "fastapi",
    "include_frontend": false
})

result = response.json()
print(f"Created repository: {result['repository_url']}")
print(f"First commit: {result['commit_hash']}")
```

### Response Format

```json
{
  "work_item_id": 12345,
  "repository_url": "https://myorg@visualstudio.com/Project/_git/new-backend-api",
  "branch": "task-12345-initial-scaffold",
  "commit_hash": "a1b2c3d...",
  "pull_request_url": "https://.../pullrequest/42",
  "status": "completed"
}
```

## 🏗️ Environment Setup

### Prerequisites

- Python 3.9+
- Azure DevOps Personal Access Token (PAT) with:
  - `vso.code_write` (Repo write access)
  - `vso.wiki_write` (Wiki write access)
  - `vso.workitem_write` (Work item updates)
- Docker (for containerized deployment)

### Environment Variables

```bash
# Azure DevOps Configuration
AZURE_DEVOPS_PAT=<your-pat-token>
AZURE_DEVOPS_DEFAULT_ORG=https://yourorg.visualstudio.com

# Service Configuration
HOST=0.0.0.0
PORT=8000

# Optional: Audit Service Integration
AUDIT_SERVICE_URL=http://audit-service:8001

# Optional: Advanced Features
LOG_LEVEL=INFO
DEBUG=FALSE
```

### Local Development

```bash
# Clone the service
git clone <repository-url>
cd dev-agent-service

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run locally
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build container
docker build -t dev-agent-service:latest .

# Run with Azure DevOps PAT
docker run -p 8000:8000 \
  -e AZURE_DEVOPS_PAT=$AZURE_DEVOPS_PAT \
  -e AUDIT_SERVICE_URL=$AUDIT_SERVICE_URL \
  dev-agent-service:latest
```

## 🐙 CI/CD Pipeline

The service includes a comprehensive Azure DevOps Pipeline:

### Build & Test Stage
- ✅ Python dependency management with Poetry
- ✅ Code quality checks (flake8, black, isort)
- ✅ Unit tests with pytest (85% coverage requirement)
- ✅ Security scanning (Bandit, dependency vulnerability checks)
- ✅ Container image creation

### Deployment Stages
- ✅ **dev environment**: Automatic deployment for development
- ✅ **staging environment**: Integration testing before production
- ✅ **production environment**: Manual approval + rollback capabilities
- ✅ **monitoring**: Health checks and performance validation

### Security Features
- ✅ Container image vulnerability scanning
- ✅ Infrastructure as Code security validation
- ✅ Runtime security policies
- ✅ Audit trail integration

## 🏛️ Enterprise Architecture

### Microservice Design
- **FastAPI Framework**: Async-enabled, high-performance API
- **Pydantic Models**: Type-safe request/response handling
- **Async/Await**: Non-blocking operations for scalability
- **Error Handling**: Comprehensive exception management

### Azure Integration Layer
- **Azure DevOps Boards**: Work item management and linking
- **Azure Repos**: Source control and branch operations
- **Azure Wiki**: Documentation automation
- **Azure Container Registry**: Secure artifact management

### Scalability Features
- **Client Caching**: Reusable Azure API client connections
- **Async Processing**: Background task execution for large scaffolds
- **Memory Optimization**: Efficient resource usage for large projects
- **Horizontal Scaling**: Stateless design for K8s deployment

### Security First Approach
- **PAT Authentication**: Secure Azure DevOps integration
- **Input Validation**: Comprehensive request validation
- **Error Sanitization**: No sensitive data in error responses
- **Audit Logging**: All operations tracked for compliance

## 📊 Monitoring & Observability

### Health Checks
```bash
curl http://localhost:8000/health
# Returns: {"status": "healthy", "service_name": "dev-agent-service", ...}
```

### Metrics Integration
- Prometheus-compatible metrics endpoints
- Custom business metrics for scaffold operations
- Performance monitoring for Azure DevOps API calls
- Error rate and uptime tracking

### Logging
- Structured JSON logging with correlation IDs
- Multiple log levels (DEBUG, INFO, WARN, ERROR)
- Console, file, and remote logging support
- Sensitive data redaction

## 🔗 Integration Points

### Orchestrator Service
- Receives scaffolding requests via REST API
- Reports completion status with details
- Handles webhook callbacks for progress updates

### Azure DevOps Workflows
- Pull request automation with reviewer assignments
- Branch naming conventions (task-{id}-feature)
- Commit message standards with work item linking

### Other AI DevOps Services
- **PM-Agent**: Provides requirements context for scaffolding
- **QA-Agent**: Receives scaffolded test suites for validation
- **Security-Agent**: Scans scaffolded code for vulnerabilities
- **Release-Agent**: Deploys scaffolded applications
- **Audit-Service**: Receives operation events for compliance

## 🧪 Testing

### Unit Tests
```bash
# Run all tests with coverage
pytest tests/ --cov=src/ --cov-report=html

# Run specific test categories
pytest tests/test_azure_devops.py
pytest tests/test_scaffolding.py
pytest tests/test_webhooks.py
```

### Integration Tests
- Azure DevOps API integration testing
- End-to-end scaffolding workflows
- Multi-service integration validation
- Performance and load testing

### Security Testing
- Security header validation
- API rate limiting testing
- Authentication bypass attempts
- Input validation edge cases

## 📚 Contributing

### Development Workflow

1. **Fork & Clone**: Create feature branch
2. **Code Changes**: Implement with tests
3. **Quality Checks**: Run linters and tests
4. **Commit**: Use conventional format
5. **Pull Request**: Create with work item linking
6. **Review**: Address feedback
7. **Merge**: Into main branch

### Conventional Commits

```bash
feat(orchestrator): add JSON health check endpoint (#DUMMY-001)
fix(azure-devops): correct work item linking for long IDs
docs(api): update FastAPI endpoint documentation
test(scaffolding): add integration tests for React scaffolding
security(dependencies): update Flask to patch vulnerability
```

### Code Standards
- **Google Python Style Guide** for code formatting
- **88 character line length** for readability
- **Comprehensive docstrings** for all functions
- **Type hints** for better IDE support
- **Black automatic formatting** for consistency

## 📈 Scalability

### Performance Targets
- **API Response Time**: <200ms for simple requests
- **Scaffold Creation**: <60 seconds for typical applications
- **Concurrent Users**: Support 100+ simultaneous scaffolding operations
- **Memory Usage**: <500MB for standard workloads
- **Azure API Limits**: Respects rate limits with intelligent backoff

### Capacity Planning
- **User Growth**: Designed for 1000+ concurrent users
- **Application Complexity**: Handles enterprise-scale scaffolding
- **Storage Requirements**: Efficient artifact management
- **Network Bandwidth**: Optimized for cloud deployments

## 🚨 Support & Troubleshooting

### Common Issues

**Authentication Errors**
```bash
# Check PAT permissions in Azure DevOps
# Verify environment variable: $AZURE_DEVOPS_PAT
```

**Repository Creation Failures**
```bash
# Check project permissions
# Verify project exists in Azure DevOps
```

**Webhook Processing Issues**
```bash
# Verify webhook endpoint is accessible
# Check Azure DevOps webhook configuration
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
export LOG_LEVEL=DEBUG
export DEBUG=True
python -m uvicorn src.main:app --reload
```

### Health Check Troubleshooting

```bash
# Test health endpoint
curl -f http://localhost:8000/health || echo "Service unhealthy"

# View service logs
tail -f logs/dev-agent-service.log
```

## 📄 License

Copyright (c) AI DevOps System. All rights reserved.

## 🆘 Emergency Contacts

For production support and critical deployments:

- **Technical Leads**: Available via Azure DevOps Chat
- **Security Issues**: security@company.com
- **Production Down**: Production notification channels

---

**Status**: Development (v0.1.0) - Production Ready Architecture

*Ready for scaffolding your first AI DevOps programs! 🚀*
