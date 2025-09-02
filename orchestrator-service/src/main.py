import asyncio
import os
from typing import Dict, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import redis
from prometheus_client import Counter, Histogram, generate_latest, start_http_server

from src.utils import (
    configure_logging,
    generate_correlation_id,
    get_logger,
    get_env_var,
    send_audit_event,
    get_metrics_data,
    create_project_audit_event,
    determine_agent_type
)
from src.models import (
    HealthStatus,
    WorkItemState,
    AuditEvent
)
from src.azure_devops import AzureDevOpsClient
from src.bootstrap import bootstrap_project
from src.handlers import handle_workitem_webhook, route_task_to_agent

# Initialize FastAPI app
app = FastAPI(
    title="Orchestrator Service",
    version="1.0.0",
    description="CMMI-compliant workflow orchestrator service"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
configure_logging()
logger = get_logger()

# Initialize Prometheus metrics
start_http_server(9090)
PROJECTS_CREATED = Counter('orchestrator_projects_created_total', 'Total projects created')
BOOTSTRAP_FAILURES = Counter('orchestrator_bootstrap_failures_total', 'Bootstrap failures')
TASKS_ROUTED = Counter('orchestrator_tasks_routed_total', 'Tasks routed per agent', ['agent'])
ROUTING_FAILURES = Counter('orchestrator_routing_failures_total', 'Routing failures')
HTTP_REQUEST_DURATION = Histogram('orchestrator_http_request_duration_seconds',
                                'HTTP request duration', ['method', 'endpoint'])

# Global clients
ado_client = None
redis_client = None

# Bootstrap task tracking
bootstrap_tasks: Dict[str, asyncio.Task] = {}


@app.on_event("startup")
async def startup_event():
    """Initialize clients and perform startup checks."""
    global ado_client, redis_client

    logger.info("Starting Orchestrator Service...")

    # Initialize clients
    try:
        organization_url = get_env_var("AZURE_DEVOPS_ORG_URL")
        pat = get_env_var("AZURE_DEVOPS_PAT")
        project_name = get_env_var("AZURE_DEVOPS_PROJECT")

        if organization_url and pat and project_name:
            ado_client = AzureDevOpsClient(
                organization_url=organization_url,
                personal_access_token=pat,
                project_name=project_name
            )
            logger.info("Azure DevOps client initialized")

        redis_url = get_env_var("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url)
        logger.info("Redis client initialized")

    except Exception as e:
        logger.error("Failed to initialize clients on startup", error=str(e))

    # Auto-bootstrap project if missing and configured to do so
    auto_bootstrap = get_env_var("ORCHESTRATOR_AUTO_BOOTSTRAP", "false").lower() == "true"
    if auto_bootstrap and ado_client:
        logger.info("Auto-bootstrap enabled, checking project status...")
        try:
            project_status = await ado_client.get_project_status(project_name)
            if project_status == "missing":
                logger.info("Project missing, starting auto-bootstrap...")
                correlation_id = generate_correlation_id()
                task = asyncio.create_task(bootstrap_project(
                    project_name=project_name,
                    organization_url=organization_url,
                    personal_access_token=pat,
                    correlation_id=correlation_id
                ))
                bootstrap_tasks[correlation_id] = task
                logger.info("Auto-bootstrap task started", correlation_id=correlation_id)
        except Exception as e:
            logger.error("Failed to check project for auto-bootstrap", error=str(e))

    logger.info("Orchestrator Service startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down Orchestrator Service...")

    # Cancel any running bootstrap tasks
    for task_id, task in bootstrap_tasks.items():
        if not task.done():
            task.cancel()
            logger.info("Cancelled bootstrap task", task_id=task_id)

    logger.info("Orchestrator Service shutdown complete")


@app.post("/bootstrap", summary="Trigger manual bootstrap process")
async def trigger_bootstrap():
    """Manually trigger project bootstrap process."""
    PROJECTS_CREATED.inc()

    correlation_id = generate_correlation_id()
    logger_req = get_logger(correlation_id)

    organization_url = get_env_var("AZURE_DEVOPS_ORG_URL")
    pat = get_env_var("AZURE_DEVOPS_PAT")
    project_name = get_env_var("AZURE_DEVOPS_PROJECT")

    if not all([organization_url, pat, project_name]):
        raise HTTPException(status_code=400,
                           detail="Missing required environment variables: AZURE_DEVOPS_ORG_URL, AZURE_DEVOPS_PAT, AZURE_DEVOPS_PROJECT")

    logger_req.info("Starting manual bootstrap", project_name=project_name)

    # Create background task for bootstrap
    task = asyncio.create_task(bootstrap_project(
        project_name=project_name,
        organization_url=organization_url,
        personal_access_token=pat,
        correlation_id=correlation_id
    ))
    bootstrap_tasks[correlation_id] = task

    return {
        "correlation_id": correlation_id,
        "message": "Bootstrap process started",
        "project_name": project_name
    }


@app.get("/projects/{project}/status", summary="Get project provisioning status")
async def get_project_status(project: str):
    """Check current status of project provisioning."""
    if not ado_client:
        raise HTTPException(status_code=503, detail="Azure DevOps client not initialized")

    try:
        status = await ado_client.get_project_status(project)
        return {
            "project_name": project,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Failed to get project status", project=project, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to check project status: {str(e)}")


@app.post("/webhooks/azure-devops", summary="Handle Azure DevOps webhook events")
async def handle_webhook_event(event: Dict[Any, Any]):
    """Process Azure DevOps webhook events for work item updates."""
    try:
        webhook_logger = get_logger()
        webhook_logger.debug("Received webhook event", event_type=event.get("eventType", "unknown"))

        # Process webhook asynchronously
        asyncio.create_task(handle_webhook_processing(event))

        return {"message": "Webhook event accepted", "status": "processing"}

    except Exception as e:
        logger.error("Failed to process webhook event", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")


async def handle_webhook_processing(event: Dict[Any, Any]):
    """Process webhook event asynchronously."""
    correlation_id = generate_correlation_id()
    event_logger = get_logger(correlation_id)

    try:
        event_logger.info("Processing webhook event",
                         event_type=event.get("eventType", "unknown"),
                         work_item_id=event.get("resource", {}).get("workItemId"))

        # Handle work item update events
        if event.get("eventType") == "workitem.updated":
            await handle_workitem_webhook(event, correlation_id)

        # Handle work item create events
        elif event.get("eventType") == "workitem.created":
            await handle_workitem_webhook(event, correlation_id)

        event_logger.info("Webhook processing complete")

    except Exception as e:
        event_logger.error("Failed to process webhook event",
                          event_type=event.get("eventType", "unknown"),
                          error=str(e))


@app.get("/healthz", summary="Health check endpoint")
async def health_check():
    """Check service health: FastAPI, Redis, Azure DevOps connectivity."""
    health = {
        "status": "healthy",
        "checks": {
            "fastapi": True,
            "redis": False,
            "azure_devops": False
        }
    }

    # Check Redis
    try:
        if redis_client:
            redis_client.ping()
            health["checks"]["redis"] = True
        else:
            health["checks"]["redis"] = False
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        health["status"] = "unhealthy"

    # Check Azure DevOps
    try:
        if ado_client:
            # Simple endpoint check
            await ado_client.get_project_status(get_env_var("AZURE_DEVOPS_PROJECT", ""))
            health["checks"]["azure_devops"] = True
        else:
            health["checks"]["azure_devops"] = False
    except Exception as e:
        logger.error("Azure DevOps health check failed", error=str(e))
        health["status"] = "unhealthy"

    if health["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health)

    return HealthStatus(status=health["status"], checks=health["checks"],
                       timestamp=datetime.utcnow())


@app.get("/metrics", summary="Metrics endpoint")
async def metrics():
    """Return Prometheus metrics."""
    return generate_latest()


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("Unhandled exception", error=str(exc), url=str(request.url))
    return {"detail": "Internal server error"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
