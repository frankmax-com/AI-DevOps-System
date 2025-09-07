# Controller Service Development Setup

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env with your Azure Key Vault and governance factory URLs

# 3. Run the service
python src/main.py

# 4. Access API documentation
# http://localhost:8000/docs
```

## 🔧 Development Environment

### Prerequisites
- Python 3.11+
- Azure Key Vault access (for production)
- Docker (for agent spawning)
- Running governance factories

### Environment Variables (.env)
```
# Azure Key Vault
AZURE_KEY_VAULT_URL=https://your-vault.vault.azure.net/
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# Governance Factory URLs
GITHUB_GOVERNANCE_URL=http://localhost:8001
AZURE_GOVERNANCE_URL=http://localhost:8002
AI_PROVIDER_GOVERNANCE_URL=http://localhost:8003
DATABASE_GOVERNANCE_URL=http://localhost:8004

# Controller Service
CONTROLLER_SERVICE_PORT=8000
JWT_SECRET_KEY=your-secret-key-generate-new-one
LOG_LEVEL=INFO
```

## 🏗️ Architecture

```
controller-service/
├── src/
│   ├── main.py              # FastAPI application
│   ├── core/
│   │   ├── controller.py    # Main orchestration engine
│   │   └── token_manager.py # JWT token management
│   ├── models/
│   │   ├── startup_spec.py  # Startup definitions
│   │   ├── agent_models.py  # Agent specifications
│   │   └── audit_models.py  # Audit and compliance
│   ├── integrations/
│   │   ├── vault_client.py         # Azure Key Vault
│   │   └── governance_factories.py # Factory clients
│   └── agents/
│       └── agent_spawner.py # Container orchestration
├── requirements.txt
└── README.md
```

## 🔌 API Endpoints

### Startup Management
- `POST /api/v1/startups` - Create new startup
- `GET /api/v1/startups/{startup_id}` - Get startup status
- `DELETE /api/v1/startups/{startup_id}` - Terminate startup

### Agent Management  
- `POST /api/v1/agents/spawn` - Spawn new agent
- `GET /api/v1/agents/{agent_id}` - Get agent status
- `POST /api/v1/agents/{agent_id}/terminate` - Terminate agent

### System Management
- `GET /health` - Health check
- `GET /api/v1/system/status` - System status
- `GET /api/v1/system/metrics` - Performance metrics

## 🧪 Testing

```bash
# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/

# Integration tests (requires running governance factories)
python -m pytest tests/integration/
```

## 🔒 Security

- JWT-based authentication with ephemeral tokens
- Azure Key Vault integration for secrets
- Tenant isolation with encrypted boundaries
- Role-based access control (RBAC)
- Comprehensive audit logging

## 📊 Monitoring

- Prometheus metrics at `/metrics`
- Health checks at `/health`  
- Structured logging with correlation IDs
- Performance monitoring for all operations

## 🚀 Production Deployment

```bash
# Build Docker image
docker build -t controller-service:latest .

# Run with Docker Compose
docker-compose up -d

# Deploy to Kubernetes
kubectl apply -f k8s/
```
