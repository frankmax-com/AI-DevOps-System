# 🚀 Getting Started with Database Governance Factory

Welcome to the Database Governance Factory! This guide will help you get up and running quickly.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Docker Desktop** (4.20+)
- **Docker Compose** (2.17+)
- **Git** (for cloning the repository)
- **PowerShell** or **Bash** (for running scripts)

## 🏃‍♂️ Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/frankmax-com/AI-DevOps-System.git
cd AI-DevOps-System/database-governance-factory
```

### 2. Start the Services

**For Windows:**
```cmd
start.bat
```

**For Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

### 3. Verify Installation

After 2-3 minutes, check if services are running:

```bash
docker-compose ps
```

Visit these URLs to verify everything is working:
- **API Health**: http://localhost:8080/health
- **API Documentation**: http://localhost:8080/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/governance-grafana-pass)

## 🔧 Configuration

### Environment Variables

The system uses environment variables for configuration. Update the `.env` file with your specific settings:

```bash
# Core API Settings
GOVERNANCE_API_TOKEN=your-secure-api-token-here

# Database Connections (replace with your actual connections)
USER_MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/user_management
PAYMENT_COSMOS_CONNECTION_STRING=AccountEndpoint=https://account.documents.azure.com:443/;AccountKey=key;

# Notification Settings
GOVERNANCE_ADMIN_EMAIL=admin@yourcompany.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

### Register Your First Database

Once the system is running, register a database via the API:

```bash
curl -X POST "http://localhost:8080/databases/register" \
  -H "Authorization: Bearer your-secure-api-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_user_database",
    "db_type": "mongodb",
    "connection_string": "mongodb://localhost:27017",
    "database_name": "users",
    "module_name": "user-service",
    "environment": "development",
    "governance_policies": ["mongodb_schema_validation", "data_quality_standards"],
    "compliance_frameworks": ["SOX", "GDPR"]
  }'
```

## 📊 Available Services

| Service | URL | Purpose |
|---------|-----|---------|
| **Governance API** | http://localhost:8080 | Main database governance API |
| **Swagger UI** | http://localhost:8080/docs | Interactive API documentation |
| **Grafana** | http://localhost:3000 | Monitoring dashboards |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **Jaeger** | http://localhost:16686 | Distributed tracing |
| **Kibana** | http://localhost:5601 | Log analysis |

## 🎯 Key Features

### 1. Multi-Database Support
- **MongoDB** (Atlas Free Tier)
- **PostgreSQL** (Supabase Free Tier)
- **Redis** (Redis Labs Free Tier)
- **Azure Cosmos DB** (Free Tier)
- **Azure Blob Storage** (Free Tier)

### 2. Compliance Frameworks
- **SOX** (Sarbanes-Oxley)
- **GDPR** (General Data Protection Regulation)
- **HIPAA** (Health Insurance Portability)
- **ISO27001** (Information Security Management)
- **PCI DSS** (Payment Card Industry)

### 3. Governance Policies
- Schema validation
- Referential integrity
- Memory optimization
- Data quality standards
- Performance monitoring

## 🔍 Monitoring & Observability

### Grafana Dashboards

Access Grafana at http://localhost:3000 with credentials:
- **Username**: admin
- **Password**: governance-grafana-pass

Available dashboards:
- Database Health Overview
- Compliance Score Tracking
- Performance Metrics
- Violation Trends

### Prometheus Metrics

Key metrics available at http://localhost:9090:
- `database_governance_compliance_score`
- `database_governance_violations_total`
- `database_governance_policy_execution_time`
- `database_governance_health_status`

## 🛠️ Common Operations

### View System Status
```bash
# Check all services
docker-compose ps

# View API logs
docker-compose logs -f governance-api

# Check database health
curl http://localhost:8080/health
```

### Run Governance Audit
```bash
curl -X POST "http://localhost:8080/audit/run" \
  -H "Authorization: Bearer your-api-token" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Get Dashboard Data
```bash
curl -X GET "http://localhost:8080/dashboard" \
  -H "Authorization: Bearer your-api-token"
```

### List Registered Databases
```bash
curl -X GET "http://localhost:8080/databases" \
  -H "Authorization: Bearer your-api-token"
```

## 🔧 Troubleshooting

### Services Won't Start
1. Check Docker is running: `docker info`
2. Check ports aren't in use: `netstat -an | grep :8080`
3. Check logs: `docker-compose logs governance-api`

### Database Connection Issues
1. Verify connection strings in `.env`
2. Check network connectivity
3. Ensure credentials are correct
4. Review firewall settings

### Performance Issues
1. Monitor resource usage: `docker stats`
2. Check database performance in Grafana
3. Review slow query logs
4. Optimize connection pooling

## 📚 Next Steps

### Production Deployment
1. **Update .env file** with production credentials
2. **Configure SSL certificates** in nginx/ssl/
3. **Set up monitoring alerts** in Grafana
4. **Configure backup strategies**
5. **Review security settings**

### Advanced Configuration
1. **Custom governance policies** in config/governance_config.yaml
2. **Additional database types** via custom connectors
3. **Webhook integrations** for external systems
4. **AI/ML features** for predictive analytics

### Learning Resources
- **API Documentation**: http://localhost:8080/docs
- **Architecture Guide**: specs/design/system-architecture.md
- **Configuration Reference**: config/governance_config.yaml
- **Example Queries**: Available in Grafana dashboards

## 🆘 Support

### Getting Help
- **Documentation**: Check the specs/ directory
- **Logs**: Use `docker-compose logs [service-name]`
- **Health Checks**: Visit http://localhost:8080/health
- **Community**: Join our Slack workspace

### Common Issues
- **Port conflicts**: Modify ports in docker-compose.yml
- **Memory issues**: Increase Docker memory allocation
- **Database timeouts**: Check connection pool settings
- **SSL errors**: Verify certificate configuration

## 🎉 Success!

You now have a fully functional Database Governance Factory! Start by:

1. ✅ Registering your first database
2. ✅ Running an initial governance audit
3. ✅ Exploring the Grafana dashboards
4. ✅ Setting up compliance monitoring
5. ✅ Configuring alerts and notifications

Happy governing! 🚀
