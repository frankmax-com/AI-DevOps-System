# 🐳 AI DevOps System - Docker Environment

## 🚀 Quick Start

```bash
# 1. Start all services
docker-compose up -d

# 2. Check service status
docker-compose ps

# 3. View logs
docker-compose logs -f controller-service

# 4. Stop all services
docker-compose down
```

## 📋 Services Overview

| Service | Port | Description | Health Check |
|---------|------|-------------|--------------|
| **Controller Service** | 8000 | Main orchestration API | http://localhost:8000/health |
| **GitHub Governance** | 8001 | GitHub operations | http://localhost:8001/health |
| **Azure Governance** | 8002 | Azure DevOps operations | http://localhost:8002/health |
| **AI Provider** | 8003 | AI model management | http://localhost:8003/health |
| **Database Governance** | 8004 | Database operations | http://localhost:8004/health |
| **Redis** | 6379 | Cache & sessions | - |
| **PostgreSQL** | 5432 | Primary database | - |
| **MongoDB** | 27017 | Document store | - |
| **Prometheus** | 9091 | Metrics collection | http://localhost:9091 |
| **Grafana** | 3001 | Metrics dashboard | http://localhost:3001 |

## 🔧 Environment Configuration

Each service requires environment variables. Create `.env` files:

### Controller Service (.env)
```bash
# Copy example and edit
cp controller-service/.env.example controller-service/.env
```

### Governance Factories
```bash
# GitHub Governance Factory
cp github-governance-factory/.env.example github-governance-factory/.env

# Azure DevOps Governance Factory  
cp azure-devops-governance-factory/.env.example azure-devops-governance-factory/.env

# AI Provider Factory
cp ai-provider-factory/.env.example ai-provider-factory/.env

# Database Governance Factory
cp database-governance-factory/.env.example database-governance-factory/.env
```

## 🚀 Development Workflow

### Start Services
```bash
# Start core infrastructure
docker-compose up -d redis postgres mongo

# Start governance factories
docker-compose up -d github-governance azure-governance ai-provider database-governance

# Start controller service
docker-compose up -d controller-service

# Start monitoring
docker-compose up -d prometheus grafana
```

### View Service Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f controller-service
docker-compose logs -f github-governance
```

### Rebuild Services
```bash
# Rebuild specific service
docker-compose build controller-service
docker-compose up -d controller-service

# Rebuild all
docker-compose build
docker-compose up -d
```

## 🔍 Testing & Debugging

### Health Checks
```bash
# Check all service health
curl http://localhost:8000/health  # Controller Service
curl http://localhost:8001/health  # GitHub Governance
curl http://localhost:8002/health  # Azure Governance
curl http://localhost:8003/health  # AI Provider
curl http://localhost:8004/health  # Database Governance
```

### API Documentation
- **Controller Service**: http://localhost:8000/docs
- **GitHub Governance**: http://localhost:8001/docs
- **Azure Governance**: http://localhost:8002/docs
- **AI Provider**: http://localhost:8003/docs
- **Database Governance**: http://localhost:8004/docs

### Monitoring Dashboards
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3001 (admin/admin)

## 🛠️ Service Management

### Scale Services
```bash
# Scale specific service
docker-compose up -d --scale controller-service=2

# Scale governance factories
docker-compose up -d --scale github-governance=2
```

### Update Configuration
```bash
# Restart service after config change
docker-compose restart controller-service
```

### Database Access
```bash
# PostgreSQL
docker exec -it ai-devops-postgres-1 psql -U postgres -d governance

# MongoDB
docker exec -it ai-devops-mongo-1 mongosh governance

# Redis
docker exec -it ai-devops-redis-1 redis-cli
```

## 🔒 Security & Production

### Environment Variables
- Use strong passwords for databases
- Configure proper API keys for governance factories
- Set up Azure Key Vault credentials for production

### Volume Persistence
Data is persisted in Docker volumes:
- `redis_data` - Redis cache
- `postgres_data` - PostgreSQL database
- `mongo_data` - MongoDB documents
- `prometheus_data` - Metrics history
- `grafana_data` - Dashboards and settings

### Backup Strategy
```bash
# Backup volumes
docker run --rm -v ai-devops_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data

# Restore volumes
docker run --rm -v ai-devops_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres-backup.tar.gz -C /
```

## 🐛 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check logs
docker-compose logs service-name

# Check resource usage
docker stats

# Restart problematic service
docker-compose restart service-name
```

**Network connectivity:**
```bash
# Test internal network
docker exec controller-service ping github-governance
docker exec controller-service curl http://github-governance:8001/health
```

**Database connections:**
```bash
# Check database logs
docker-compose logs postgres
docker-compose logs mongo

# Verify database connectivity
docker exec controller-service ping postgres
```

## 🎯 Next Steps

1. **Configure Environment**: Set up all `.env` files with proper credentials
2. **Start Services**: Run `docker-compose up -d`
3. **Verify Health**: Check all service health endpoints
4. **Create Startup**: Use Controller Service API to create first AI startup
5. **Monitor**: Watch Grafana dashboards for system metrics

The AI Agent Startup Creation Platform is ready for development! 🚀
