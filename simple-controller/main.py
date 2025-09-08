"""
AI DevOps Controller Service - Simplified Version
Central orchestration service for AI agent management
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import redis
import httpx
import structlog
import os

# Configure logging
logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="AI DevOps Controller Service",
    description="Central orchestration service for AI agent management",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Redis connection
redis_client = None

# Models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]

class AgentRequest(BaseModel):
    name: str = Field(..., description="Agent name")
    type: str = Field(..., description="Agent type (dev, qa, security, etc.)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")

class AgentResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    created_at: str
    config: Dict[str, Any]

# Startup event
@app.on_event("startup")
async def startup_event():
    global redis_client
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        logger.info("Connected to Redis", redis_url=redis_url)
    except Exception as e:
        logger.warning("Redis connection failed", error=str(e))
        redis_client = None

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health():
    services = {}
    
    # Check Redis
    if redis_client:
        try:
            redis_client.ping()
            services["redis"] = "healthy"
        except:
            services["redis"] = "unhealthy"
    else:
        services["redis"] = "unavailable"
    
    # Check other services
    service_urls = {
        "github_governance": "http://github-governance:8001/health",
        "database_governance": "http://database-governance:8080/health"
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, url in service_urls.items():
            try:
                response = await client.get(url)
                services[service_name] = "healthy" if response.status_code == 200 else "unhealthy"
            except:
                services[service_name] = "unreachable"
    
    overall_status = "healthy" if all(s in ["healthy", "available"] for s in services.values()) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now().isoformat(),
        version="2.0.0",
        services=services
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "AI DevOps Controller Service",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "agents": "/agents"
        }
    }

# Agent management endpoints
@app.get("/agents", response_model=List[AgentResponse])
async def list_agents():
    """List all registered agents"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    
    try:
        agent_keys = redis_client.keys("agent:*")
        agents = []
        
        for key in agent_keys:
            agent_data = redis_client.hgetall(key)
            if agent_data:
                agents.append(AgentResponse(
                    id=agent_data.get("id", ""),
                    name=agent_data.get("name", ""),
                    type=agent_data.get("type", ""),
                    status=agent_data.get("status", "unknown"),
                    created_at=agent_data.get("created_at", ""),
                    config=eval(agent_data.get("config", "{}"))  # Simple parsing for demo
                ))
        
        return agents
    except Exception as e:
        logger.error("Failed to list agents", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agents")

@app.post("/agents", response_model=AgentResponse)
async def create_agent(agent: AgentRequest):
    """Create a new agent"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    
    try:
        agent_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        agent_data = {
            "id": agent_id,
            "name": agent.name,
            "type": agent.type,
            "status": "created",
            "created_at": created_at,
            "config": str(agent.config)  # Simple serialization for demo
        }
        
        redis_client.hset(f"agent:{agent_id}", mapping=agent_data)
        
        logger.info("Created agent", agent_id=agent_id, name=agent.name, type=agent.type)
        
        return AgentResponse(
            id=agent_id,
            name=agent.name,
            type=agent.type,
            status="created",
            created_at=created_at,
            config=agent.config
        )
    except Exception as e:
        logger.error("Failed to create agent", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create agent")

@app.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get agent details"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    
    try:
        agent_data = redis_client.hgetall(f"agent:{agent_id}")
        if not agent_data:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return AgentResponse(
            id=agent_data.get("id", ""),
            name=agent_data.get("name", ""),
            type=agent_data.get("type", ""),
            status=agent_data.get("status", "unknown"),
            created_at=agent_data.get("created_at", ""),
            config=eval(agent_data.get("config", "{}"))
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve agent")

@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    
    try:
        result = redis_client.delete(f"agent:{agent_id}")
        if result == 0:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        logger.info("Deleted agent", agent_id=agent_id)
        return {"message": f"Agent {agent_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete agent")

# Service discovery endpoints
@app.get("/services")
async def list_services():
    """List all available services"""
    services = {
        "github_governance": {
            "name": "GitHub Governance Factory",
            "url": "http://localhost:8001",
            "docs": "http://localhost:8001/docs",
            "description": "GitHub repository and workflow management"
        },
        "database_governance": {
            "name": "Database Governance Factory", 
            "url": "http://localhost:8004",
            "docs": "http://localhost:8004/docs",
            "description": "Multi-database operations and governance"
        },
        "prometheus": {
            "name": "Prometheus Metrics",
            "url": "http://localhost:9091",
            "description": "Metrics collection and monitoring"
        },
        "grafana": {
            "name": "Grafana Dashboards",
            "url": "http://localhost:3001",
            "description": "Visualization and alerting dashboards"
        }
    }
    
    return {
        "services": services,
        "total_services": len(services),
        "timestamp": datetime.now().isoformat()
    }

# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    agent_count = 0
    if redis_client:
        try:
            agent_count = len(redis_client.keys("agent:*"))
        except:
            pass
    
    metrics_data = f"""# HELP aidevops_controller_agents_total Total number of agents
# TYPE aidevops_controller_agents_total counter
aidevops_controller_agents_total {agent_count}

# HELP aidevops_controller_up Controller service status
# TYPE aidevops_controller_up gauge
aidevops_controller_up 1

# HELP aidevops_controller_redis_connected Redis connection status
# TYPE aidevops_controller_redis_connected gauge
aidevops_controller_redis_connected {1 if redis_client else 0}
"""
    
    return metrics_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
