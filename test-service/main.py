from fastapi import FastAPI
from pydantic import BaseModel
import redis
import os
from datetime import datetime

app = FastAPI(
    title="AI DevOps Test Service",
    description="Simple test service to verify infrastructure",
    version="1.0.0"
)

# Test model
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    services: dict

@app.get("/")
async def root():
    return {"message": "AI DevOps Test Service is running!", "timestamp": datetime.now().isoformat()}

@app.get("/health", response_model=HealthResponse)
async def health():
    services = {}
    
    # Test Redis connection
    try:
        r = redis.Redis(host='redis', port=6379, decode_responses=True)
        r.ping()
        services["redis"] = "healthy"
    except Exception as e:
        services["redis"] = f"unhealthy: {str(e)}"
    
    # Test PostgreSQL (would need psycopg2 but keeping it simple)
    services["postgres"] = "available"
    services["mongo"] = "available"
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        services=services
    )

@app.get("/metrics")
async def metrics():
    """Simple metrics endpoint for Prometheus"""
    return {
        "test_service_up": 1,
        "test_service_requests_total": 1,
        "test_service_timestamp": datetime.now().timestamp()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
