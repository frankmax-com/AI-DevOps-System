"""
Dev Agent Service - Program Factory Worker

Core development automation agent that transforms technical requirements
into executable code. Specializes in scaffolding new programs in Azure Repos,
creating commits, managing pull requests, and updating documentation.

This service is the primary "factory worker" in the AI DevOps system,
taking requirements and turning them into runnable code with full audit trails.

Author: AI DevOps System
Version: 0.1.0
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agent import DevAgent, ScaffoldSpec, DevAgentResponse
from src.models import WorkItemRequest, WorkItemStatus, HealthResponse
from src.utils import get_logger, setup_logging
from src.azure_devops import AzureDevOpsClient
from src.azure_repos import AzureReposClient

# Service configuration
SERVICE_NAME = "dev-agent-service"
SERVICE_VERSION = "0.1.0"
SERVICE_DESCRIPTION = "AI DevOps Development Agent - Program Factory Worker"

# Initialize logger
logger = setup_logging()

# Pydantic models for API
class ScaffoldRequest(BaseModel):
    """Request model for scaffolding operations"""
    work_item_id: int = Field(..., description="Azure DevOps work item ID to associate with scaffolded code")
    organization_url: str = Field(..., description="Azure DevOps organization URL")
    project_name: str = Field(..., description="Target Azure DevOps project name")
    repository_name: str = Field(..., description="Target repository name (will be created if doesn't exist)")
    framework: str = Field("fastapi", description="Framework to scaffold: 'fastapi', 'flask', 'django'")
    include_frontend: bool = Field(False, description="Include React frontend scaffolding")
    template_url: Optional[str] = Field(None, description="Custom template repository URL")

class ScaffoldResponse(BaseModel):
    """Response model for scaffolding operations"""
    work_item_id: int
    repository_url: str
    branch: str
    commit_hash: str
    pull_request_url: Optional[str] = None
    status: str

class WorkItemUpdateRequest(BaseModel):
    """Request model for updating Azure DevOps work items"""
    work_item_id: int
    status: WorkItemStatus
    comment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Global state for Azure DevOps clients
azure_devops_clients = {}
azure_repos_clients = {}
dev_agents = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown"""
    logger.info(f"Starting {SERVICE_NAME} v{SERVICE_VERSION}")

    # Startup tasks
    # Initialize any required background services here

    yield

    # Shutdown tasks
    logger.info(f"Shutting down {SERVICE_NAME}")

    # Clean up clients
    for client in azure_repos_clients.values():
        try:
            await client.close()
        except Exception as e:
            logger.error(f"Error closing client: {e}")

# FastAPI app initialization
app = FastAPI(
    title=SERVICE_NAME,
    description=SERVICE_DESCRIPTION,
    version=SERVICE_VERSION,
    lifespan=lifespan
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring and load balancers"""
    return HealthResponse(
        service_name=SERVICE_NAME,
        version=SERVICE_VERSION,
        status="healthy",
        uptime_seconds=None,  # Could track actual uptime
        dependencies={
            "azure_devops": True,  # Simplified - in production check actual connection
            "azure_repos": True,
        }
    )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": SERVICE_NAME,
        "description": SERVICE_DESCRIPTION,
        "version": SERVICE_VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "scaffolds": {
                "list": "/scaffolds",
                "create": "/scaffolds POST",
                "status": "/scaffolds/{work_item_id}"
            },
            "work_items": {
                "update": "/work-items POST"
            }
        }
    }

@app.post("/scaffolds", response_model=ScaffoldResponse)
async def scaffold_program(
    request: ScaffoldRequest,
    background_tasks: BackgroundTasks
) -> ScaffoldResponse:
    """Scaffold a new program in Azure Repos

    This endpoint takes a work item ID and scaffolds a complete program
    structure in Azure Repos with the specified framework and options.
    """
    try:
        logger.info(f"Initiating scaffold for work item #{request.work_item_id}")

        # Create Azure DevOps clients if not cached
        client_key = f"{request.organization_url}:{request.project_name}"
        if client_key not in azure_devops_clients:
            pat = os.getenv("AZURE_DEVOPS_PAT")
            if not pat:
                raise HTTPException(status_code=500, detail="Azure DevOps PAT not configured")

            azure_devops_clients[client_key] = AzureDevOpsClient(
                organization_url=request.organization_url,
                project_name=request.project_name,
                personal_access_token=pat
            )

        if client_key not in azure_repos_clients:
            azure_repos_clients[client_key] = AzureReposClient(
                organization_url=request.organization_url,
                project_name=request.project_name,
                repository_name=request.repository_name,
                personal_access_token=pat
            )

        # Create dev agent instance
        dev_agent = dev_agents.get(client_key)
        if not dev_agent:
            dev_agent = DevAgent(
                azure_devops_client=azure_devops_clients[client_key],
                azure_repos_client=azure_repos_clients[client_key]
            )
            dev_agents[client_key] = dev_agent

        # Generate scaffold specification
        scaffold_spec = ScaffoldSpec(
            framework=request.framework,
            include_frontend=request.include_frontend,
            template_url=request.template_url
        )

        # Queue background task for scaffold execution
        # In production, this would queue to Redis/Celery
        response = await dev_agent.scaffold_program(
            scaffold_spec=scaffold_spec,
            work_item_id=request.work_item_id
        )

        logger.info(f"Scaffold completed for work item #{request.work_item_id}")
        return ScaffoldResponse(**response.dict())

    except Exception as e:
        logger.error(f"Scaffold failed for work item #{request.work_item_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Scaffold failed: {str(e)}")

@app.get("/scaffolds/{work_item_id}")
async def get_scaffold_status(work_item_id: int):
    """Get status of a scaffolding operation"""
    # In production, this would query Redis/database for task status
    return {
        "work_item_id": work_item_id,
        "status": "completed",  # Placeholder
        "message": "Scaffold completed successfully"
    }

@app.post("/work-items")
async def update_work_item(request: WorkItemUpdateRequest):
    """Update Azure DevOps work item status and metadata"""
    try:
        logger.info(f"Updating work item #{request.work_item_id}")

        # This would use the Azure DevOps client to update the work item
        # For now, return success response
        return {
            "work_item_id": request.work_item_id,
            "status": "updated",
            "comment": request.comment,
            "metadata": request.metadata
        }

    except Exception as e:
        logger.error(f"Work item update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Work item update failed: {str(e)}")

@app.get("/capabilities")
async def get_capabilities():
    """List service capabilities and supported frameworks"""
    return {
        "frameworks": ["fastapi", "flask", "django", "express", "react"],
        "frontend_support": True,
        "azure_integration": True,
        "audit_logging": True,
        "work_item_linking": True,
        "pull_request_automation": True
    }

# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return {"detail": exc.detail}

if __name__ == "__main__":
    import uvicorn

    # Start development server
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True  # Enable auto-reload for development
    )
