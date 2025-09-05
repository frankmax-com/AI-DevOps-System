"""
Database Governance Factory - Main Application
FastAPI application with comprehensive database wrapper integration
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api import app as api_app

# Environment configuration
HOST = os.getenv("GOVERNANCE_API_HOST", "0.0.0.0")
PORT = int(os.getenv("GOVERNANCE_API_PORT", 8080))
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
RELOAD = os.getenv("RELOAD", "false").lower() == "true"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Database Governance Factory starting...")
    yield
    # Shutdown
    print("🔒 Database Governance Factory shutting down...")

# Configure the main app
def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="Database Governance Factory",
        description="Comprehensive multi-database governance system with unified wrappers",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ALLOWED_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount the API routes
    app.mount("/api", api_app)
    
    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    print(f"""
    🏗️  Database Governance Factory
    ====================================
    
    🌐 Server: http://{HOST}:{PORT}
    📚 Docs: http://{HOST}:{PORT}/docs
    📖 ReDoc: http://{HOST}:{PORT}/redoc
    🔧 Debug: {DEBUG_MODE}
    🔄 Reload: {RELOAD}
    
    Supported Databases:
    - MongoDB (motor/pymongo)
    - PostgreSQL (asyncpg)
    - Redis (aioredis)
    - Azure Cosmos DB (azure-cosmos)
    - Azure Blob Storage (azure-storage-blob)
    
    ====================================
    """)
    
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="debug" if DEBUG_MODE else "info"
    )
