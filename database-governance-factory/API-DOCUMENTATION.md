# Database Governance Factory - API Documentation

## 🌐 **REST API Reference**

**Base URL:** `http://localhost:8080`  
**API Version:** v1  
**Documentation:** Available at `/docs` (Swagger UI) and `/redoc`

## 📋 **API Overview**

The Database Governance Factory provides a comprehensive REST API for managing multiple database types through a unified interface. The API supports MongoDB, PostgreSQL, Redis, Azure Cosmos DB, and Azure Blob Storage operations.

## 🔐 **Authentication**

Currently, the API operates in development mode without authentication. For production deployment, implement:

- API Key authentication
- JWT token-based auth
- OAuth 2.0 integration
- Role-based access control

## 📚 **Endpoint Categories**

### 1. **Health & Status**
### 2. **Database Management** 
### 3. **Governance & Policies**
### 4. **Compliance & Audit**
### 5. **Monitoring & Metrics**

---

## 🏥 **Health & Status Endpoints**

### `GET /health`
**Description:** Service health check  
**Response:** System health status

```json
{
  "status": "healthy",
  "timestamp": "2025-09-05T18:00:00Z",
  "version": "1.0.0",
  "database_connections": {
    "mongodb": "connected",
    "postgresql": "connected", 
    "redis": "connected"
  }
}
```

### `GET /metrics`
**Description:** Prometheus metrics endpoint  
**Response:** Metrics in Prometheus format

---

## 🗄️ **Database Management Endpoints**

### `GET /api/v1/databases`
**Description:** List all configured databases

**Response:**
```json
[
  {
    "name": "my_mongodb",
    "type": "mongodb",
    "status": "connected",
    "health": "healthy",
    "last_check": "2025-09-05T18:00:00Z"
  },
  {
    "name": "my_postgres", 
    "type": "postgresql",
    "status": "connected",
    "health": "healthy",
    "last_check": "2025-09-05T18:00:00Z"
  }
]
```

### `POST /api/v1/databases/connections`
**Description:** Create new database connection

**Request Body:**
```json
{
  "name": "my_database",
  "type": "mongodb|postgresql|redis|cosmosdb|blobstorage",
  "config": {
    // Database-specific configuration
  }
}
```

**MongoDB Config Example:**
```json
{
  "name": "my_mongodb",
  "type": "mongodb",
  "config": {
    "host": "localhost",
    "port": 27017,
    "username": "admin", 
    "password": "password",
    "database": "my_app",
    "auth_source": "admin",
    "ssl": false
  }
}
```

**PostgreSQL Config Example:**
```json
{
  "name": "my_postgres",
  "type": "postgresql", 
  "config": {
    "host": "localhost",
    "port": 5432,
    "username": "postgres",
    "password": "password", 
    "database": "my_app",
    "ssl_mode": "prefer"
  }
}
```

**Redis Config Example:**
```json
{
  "name": "my_redis",
  "type": "redis",
  "config": {
    "host": "localhost",
    "port": 6379,
    "password": "password",
    "database": 0,
    "ssl": false
  }
}
```

**Azure Cosmos DB Config Example:**
```json
{
  "name": "my_cosmosdb", 
  "type": "cosmosdb",
  "config": {
    "endpoint": "https://myaccount.documents.azure.com:443/",
    "key": "your-primary-key",
    "database": "my_database",
    "consistency_level": "Session"
  }
}
```

**Azure Blob Storage Config Example:**
```json
{
  "name": "my_blobstorage",
  "type": "blobstorage", 
  "config": {
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=...",
    "container_name": "my-container"
  }
}
```

**Response:**
```json
{
  "connection_id": "uuid",
  "status": "created",
  "message": "Database connection created successfully"
}
```

### `GET /api/v1/databases/{db_name}/status`
**Description:** Check specific database health

**Response:**
```json
{
  "name": "my_mongodb",
  "type": "mongodb", 
  "status": "connected",
  "health": "healthy",
  "response_time_ms": 25,
  "last_check": "2025-09-05T18:00:00Z",
  "details": {
    "server_version": "7.0.0",
    "connection_count": 5,
    "available_connections": 95
  }
}
```

### `DELETE /api/v1/databases/{db_name}`
**Description:** Remove database connection

**Response:**
```json
{
  "status": "deleted",
  "message": "Database connection removed successfully"
}
```

### `POST /api/v1/databases/{db_name}/test-connection`
**Description:** Test database connectivity

**Response:**
```json
{
  "status": "success|failed",
  "response_time_ms": 45,
  "error": "Error message if failed",
  "timestamp": "2025-09-05T18:00:00Z"
}
```

---

## ⚖️ **Governance & Policies Endpoints**

### `GET /api/v1/policies`
**Description:** List all governance policies

**Response:**
```json
[
  {
    "policy_id": "data_retention_policy",
    "name": "Data Retention Policy",
    "type": "data_retention", 
    "status": "active",
    "created_at": "2025-09-05T18:00:00Z",
    "rules": {
      "max_age_days": 90,
      "auto_archive": true
    }
  }
]
```

### `POST /api/v1/policies`
**Description:** Create new governance policy

**Request Body:**
```json
{
  "name": "Data Retention Policy",
  "type": "data_retention|access_control|backup|security",
  "rules": {
    // Policy-specific rules
  },
  "databases": ["db1", "db2"],
  "enabled": true
}
```

**Response:**
```json
{
  "policy_id": "uuid",
  "status": "created", 
  "message": "Policy created successfully"
}
```

### `POST /api/v1/policies/validate`
**Description:** Validate policy configuration

**Request Body:**
```json
{
  "policies": [
    {
      "name": "test_policy",
      "type": "data_retention",
      "rules": {
        "max_age_days": 90,
        "auto_archive": true
      }
    }
  ]
}
```

**Response:**
```json
{
  "validation_result": {
    "valid": true,
    "errors": [],
    "warnings": []
  },
  "policies_validated": 1,
  "timestamp": "2025-09-05T18:00:00Z"
}
```

### `PUT /api/v1/policies/{policy_id}`
**Description:** Update existing policy

### `DELETE /api/v1/policies/{policy_id}`  
**Description:** Delete policy

---

## 📊 **Compliance & Audit Endpoints**

### `GET /api/v1/compliance/report`
**Description:** Generate compliance report

**Query Parameters:**
- `database_name` (optional): Specific database
- `start_date` (optional): Report start date
- `end_date` (optional): Report end date

**Response:**
```json
{
  "compliance_status": "compliant|non_compliant|partial",
  "timestamp": "2025-09-05T18:00:00Z",
  "databases": [
    {
      "name": "my_mongodb",
      "status": "compliant", 
      "score": 95,
      "violations": [],
      "last_audit": "2025-09-05T17:00:00Z"
    }
  ],
  "summary": {
    "total_databases": 5,
    "compliant": 4,
    "non_compliant": 1,
    "overall_score": 88
  }
}
```

### `GET /api/v1/audit/trail`
**Description:** Retrieve audit logs

**Query Parameters:**
- `database_name` (optional): Filter by database
- `action` (optional): Filter by action type
- `start_date` (optional): Filter by date range
- `end_date` (optional): Filter by date range
- `limit` (optional): Maximum records (default: 100)

**Response:**
```json
{
  "audit_events": [
    {
      "event_id": "uuid",
      "timestamp": "2025-09-05T18:00:00Z",
      "database_name": "my_mongodb", 
      "action": "connection_created",
      "user": "system",
      "details": {
        "connection_type": "mongodb",
        "success": true
      }
    }
  ],
  "total_count": 150,
  "page": 1,
  "has_more": true
}
```

### `POST /api/v1/audit/run`
**Description:** Trigger manual audit

**Request Body:**
```json
{
  "database_name": "my_mongodb", // Optional
  "audit_type": "full|health|compliance"
}
```

**Response:**
```json
{
  "audit_id": "uuid",
  "status": "started",
  "estimated_completion": "2025-09-05T18:05:00Z"
}
```

### `GET /api/v1/audit/{audit_id}/status`
**Description:** Check audit status

**Response:**
```json
{
  "audit_id": "uuid",
  "status": "running|completed|failed",
  "progress": 75,
  "started_at": "2025-09-05T18:00:00Z",
  "completed_at": "2025-09-05T18:04:00Z",
  "results": {
    // Audit results when completed
  }
}
```

---

## 📈 **Monitoring & Metrics Endpoints**

### `GET /api/v1/monitoring/dashboard`
**Description:** Get monitoring dashboard data

**Response:**
```json
{
  "system_health": {
    "status": "healthy",
    "uptime_seconds": 86400,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 25
  },
  "database_metrics": [
    {
      "name": "my_mongodb",
      "connection_count": 5,
      "response_time_ms": 25,
      "queries_per_second": 150,
      "error_rate": 0.01
    }
  ],
  "compliance_summary": {
    "total_policies": 10,
    "violations": 2,
    "compliance_score": 88
  }
}
```

### `GET /api/v1/monitoring/metrics/{db_name}`
**Description:** Get specific database metrics

**Response:**
```json
{
  "database_name": "my_mongodb",
  "metrics": {
    "connection_pool": {
      "active": 5,
      "idle": 15,
      "max": 20
    },
    "performance": {
      "avg_response_time_ms": 25,
      "queries_per_second": 150,
      "error_rate": 0.01
    },
    "storage": {
      "size_mb": 1024,
      "collections": 15,
      "indexes": 45
    }
  },
  "timestamp": "2025-09-05T18:00:00Z"
}
```

---

## 💾 **Backup & Recovery Endpoints**

### `GET /api/v1/backup/status`
**Description:** Get backup status for all databases

**Response:**
```json
{
  "backups": [
    {
      "database_name": "my_mongodb",
      "last_backup": "2025-09-05T02:00:00Z",
      "status": "completed",
      "size_mb": 256,
      "retention_days": 30
    }
  ],
  "next_scheduled": "2025-09-06T02:00:00Z"
}
```

### `POST /api/v1/backup/configure`
**Description:** Configure backup settings

**Request Body:**
```json
{
  "databases": ["my_mongodb", "my_postgres"],
  "schedule": "0 2 * * *", // Cron expression
  "retention_days": 30,
  "encryption": true,
  "storage_location": "azure_blob|aws_s3|local"
}
```

### `POST /api/v1/backup/trigger`
**Description:** Trigger manual backup

**Request Body:**
```json
{
  "database_name": "my_mongodb",
  "backup_type": "full|incremental"
}
```

---

## 🔧 **Database Operations Endpoints**

### MongoDB Specific

#### `POST /api/v1/databases/mongodb/{db_name}/query`
**Description:** Execute MongoDB query

**Request Body:**
```json
{
  "collection": "users",
  "operation": "find|aggregate|insert|update|delete",
  "query": {},
  "options": {}
}
```

### PostgreSQL Specific  

#### `POST /api/v1/databases/postgresql/{db_name}/query`
**Description:** Execute SQL query

**Request Body:**
```json
{
  "query": "SELECT * FROM users WHERE active = $1",
  "parameters": [true],
  "transaction": false
}
```

### Redis Specific

#### `POST /api/v1/databases/redis/{db_name}/command`
**Description:** Execute Redis command

**Request Body:**
```json
{
  "command": "GET",
  "args": ["user:123"]
}
```

---

## ⚠️ **Error Responses**

### Standard Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid database configuration",
    "details": {
      "field": "host",
      "reason": "Host is required"
    },
    "timestamp": "2025-09-05T18:00:00Z"
  }
}
```

### Common Error Codes
- `VALIDATION_ERROR` (400) - Invalid request data
- `DATABASE_CONNECTION_ERROR` (500) - Database connectivity issues  
- `POLICY_VIOLATION` (403) - Governance policy violation
- `RESOURCE_NOT_FOUND` (404) - Resource doesn't exist
- `INTERNAL_ERROR` (500) - Internal server error

---

## 🚀 **Usage Examples**

### Python Client Example
```python
import httpx
import asyncio

async def example_usage():
    client = httpx.AsyncClient(base_url="http://localhost:8080")
    
    # Create database connection
    response = await client.post("/api/v1/databases/connections", json={
        "name": "my_app_db",
        "type": "mongodb",
        "config": {
            "host": "localhost",
            "port": 27017,
            "database": "my_app"
        }
    })
    
    # Check health
    health = await client.get("/health")
    print(health.json())
    
    # Run compliance check
    compliance = await client.get("/api/v1/compliance/report")
    print(compliance.json())
    
    await client.aclose()

asyncio.run(example_usage())
```

### JavaScript/Node.js Example
```javascript
const axios = require('axios');

const client = axios.create({
  baseURL: 'http://localhost:8080'
});

async function exampleUsage() {
  // Create database connection
  const response = await client.post('/api/v1/databases/connections', {
    name: 'my_app_db',
    type: 'postgresql',
    config: {
      host: 'localhost',
      port: 5432,
      username: 'postgres',
      password: 'password',
      database: 'my_app'
    }
  });
  
  // Check health
  const health = await client.get('/health');
  console.log(health.data);
  
  // Get metrics
  const metrics = await client.get('/api/v1/monitoring/dashboard');
  console.log(metrics.data);
}

exampleUsage().catch(console.error);
```

### cURL Examples
```bash
# Health check
curl http://localhost:8080/health

# Create MongoDB connection
curl -X POST http://localhost:8080/api/v1/databases/connections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_mongodb",
    "type": "mongodb", 
    "config": {
      "host": "localhost",
      "port": 27017,
      "database": "my_app"
    }
  }'

# Get compliance report
curl http://localhost:8080/api/v1/compliance/report

# Validate policy
curl -X POST http://localhost:8080/api/v1/policies/validate \
  -H "Content-Type: application/json" \
  -d '{
    "policies": [{
      "name": "test_policy",
      "type": "data_retention",
      "rules": {"max_age_days": 90}
    }]
  }'
```

---

## 📖 **Interactive Documentation**

For interactive API exploration:

- **Swagger UI:** http://localhost:8080/docs
- **ReDoc:** http://localhost:8080/redoc

These interfaces provide:
- Interactive request/response testing
- Complete schema documentation
- Example requests and responses
- Authentication testing (when enabled)

---

**Database Governance Factory API** - Complete documentation for your one-stop database solution! 🚀
