"""
Controller Service - AI Agent Orchestration Engine
Core FastAPI application for autonomous agent management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import structlog
from pydantic import BaseModel

from .core.controller import ControllerEngine
from .core.token_manager import TokenManager
from .core.policy_engine import PolicyEngine
from .core.tenant_manager import TenantManager
from .core.audit_manager import AuditManager
from .agents.agent_spawner import AgentSpawner
from .models.startup_spec import StartupSpec
from .models.agent_models import AgentSpawnRequest, AgentStatus, EphemeralToken
from .models.audit_models import AuditEvent

# Initialize FastAPI app
app = FastAPI(
    title="Controller Service",
    description="AI Agent Orchestration Engine for Startup Creation Platform",
    version="1.0.0",
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

# Initialize logger
logger = structlog.get_logger()

# Initialize core services
controller = ControllerEngine()
token_manager = TokenManager()
policy_engine = PolicyEngine()
tenant_manager = TenantManager()
audit_manager = AuditManager()
agent_spawner = AgentSpawner()

# Security
security = HTTPBearer()

# Pydantic models for API
class StartupCreationRequest(BaseModel):
    company_name: str
    founder_email: str
    industry: str
    target_market: str
    funding_stage: str
    compliance_frameworks: List[str] = []
    business_description: str
    initial_team_size: int = 5

class StartupResponse(BaseModel):
    startup_id: str
    status: str
    github_org: Optional[str] = None
    azure_project: Optional[str] = None
    agents: List[AgentStatus] = []
    created_at: datetime
    estimated_completion: Optional[datetime] = None

class TokenMintRequest(BaseModel):
    agent_role: str
    tenant_id: str
    ttl_minutes: int = 30
    scopes: List[str]
    reason: str

class ApprovalResponse(BaseModel):
    approval_id: str
    operation: str
    status: str
    requested_at: datetime
    approved_at: Optional[datetime] = None
    approver: Optional[str] = None
    reason: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "service": "controller-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "token_manager": "operational",
            "policy_engine": "operational", 
            "tenant_manager": "operational",
            "audit_manager": "operational",
            "agent_spawner": "operational"
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Service information and capabilities"""
    return {
        "service": "Controller Service",
        "description": "AI Agent Orchestration Engine for Startup Creation Platform",
        "version": "1.0.0",
        "capabilities": [
            "Autonomous agent orchestration",
            "Ephemeral token management", 
            "Multi-tenant isolation",
            "Policy enforcement",
            "Audit trail management",
            "Approval workflow integration"
        ],
        "endpoints": {
            "startups": "/startups - Startup management",
            "agents": "/agents - Agent lifecycle management", 
            "tokens": "/tokens - Token operations",
            "policies": "/policies - Governance policies",
            "audit": "/audit - Audit trails and monitoring",
            "health": "/health - Health check"
        }
    }

# Startup Management Endpoints
@app.post("/startups", response_model=StartupResponse)
async def create_startup(
    request: StartupCreationRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(security)
):
    """Create a new startup with autonomous agent orchestration"""
    try:
        # Generate unique startup ID
        startup_id = str(uuid.uuid4())
        
        # Create startup specification
        startup_spec = StartupSpec(
            startup_id=startup_id,
            company_name=request.company_name,
            founder_email=request.founder_email,
            industry=request.industry,
            target_market=request.target_market,
            funding_stage=request.funding_stage,
            compliance_frameworks=request.compliance_frameworks,
            business_description=request.business_description,
            initial_team_size=request.initial_team_size
        )
        
        # Validate against policies
        policy_result = await policy_engine.validate_startup_creation(startup_spec)
        if not policy_result.approved:
            raise HTTPException(
                status_code=403, 
                detail=f"Policy validation failed: {policy_result.reason}"
            )
        
        # Create tenant isolation
        tenant_resources = await tenant_manager.create_tenant(startup_id)
        
        # Start audit trail
        audit_event = AuditEvent(
            event_type="startup_creation_initiated",
            startup_id=startup_id,
            details={
                "company_name": request.company_name,
                "founder_email": request.founder_email,
                "tenant_resources": tenant_resources
            },
            timestamp=datetime.utcnow()
        )
        await audit_manager.log_event(audit_event)
        
        # Start autonomous agent orchestration in background
        background_tasks.add_task(
            controller.orchestrate_startup_creation,
            startup_spec
        )
        
        logger.info(
            "Startup creation initiated",
            startup_id=startup_id,
            company_name=request.company_name
        )
        
        return StartupResponse(
            startup_id=startup_id,
            status="initiated",
            created_at=datetime.utcnow(),
            estimated_completion=datetime.utcnow() + timedelta(minutes=30)
        )
        
    except Exception as e:
        logger.error("Failed to create startup", error=str(e))
        raise HTTPException(status_code=500, detail=f"Startup creation failed: {str(e)}")

@app.get("/startups/{startup_id}", response_model=StartupResponse)
async def get_startup_status(startup_id: str, token: str = Depends(security)):
    """Get startup creation status and progress"""
    try:
        startup_status = await controller.get_startup_status(startup_id)
        return startup_status
    except Exception as e:
        logger.error("Failed to get startup status", startup_id=startup_id, error=str(e))
        raise HTTPException(status_code=404, detail=f"Startup not found: {str(e)}")

# Agent Management Endpoints
@app.post("/agents/spawn")
async def spawn_agent(
    request: AgentSpawnRequest,
    token: str = Depends(security)
):
    """Spawn a new autonomous agent"""
    try:
        # Validate agent spawn request
        policy_result = await policy_engine.validate_agent_spawn(request)
        if not policy_result.approved:
            raise HTTPException(
                status_code=403,
                detail=f"Agent spawn denied: {policy_result.reason}"
            )
        
        # Spawn agent
        agent_result = await agent_spawner.spawn_agent(request)
        
        # Log audit event
        audit_event = AuditEvent(
            event_type="agent_spawned",
            startup_id=request.tenant_id,
            agent_id=agent_result.agent_id,
            details={
                "agent_role": request.agent_role,
                "parent_agent_id": request.parent_agent_id,
                "capabilities": request.capabilities
            },
            timestamp=datetime.utcnow()
        )
        await audit_manager.log_event(audit_event)
        
        return agent_result
        
    except Exception as e:
        logger.error("Failed to spawn agent", error=str(e))
        raise HTTPException(status_code=500, detail=f"Agent spawn failed: {str(e)}")

@app.get("/agents/{agent_id}")
async def get_agent_status(agent_id: str, token: str = Depends(security)):
    """Get agent status and operational metrics"""
    try:
        agent_status = await agent_spawner.get_agent_status(agent_id)
        return agent_status
    except Exception as e:
        logger.error("Failed to get agent status", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=404, detail=f"Agent not found: {str(e)}")

@app.post("/agents/{agent_id}/revoke")
async def revoke_agent(agent_id: str, token: str = Depends(security)):
    """Revoke agent and all associated tokens"""
    try:
        result = await agent_spawner.revoke_agent(agent_id)
        
        # Log audit event
        audit_event = AuditEvent(
            event_type="agent_revoked",
            agent_id=agent_id,
            details={"revocation_reason": "manual_revocation"},
            timestamp=datetime.utcnow()
        )
        await audit_manager.log_event(audit_event)
        
        return result
    except Exception as e:
        logger.error("Failed to revoke agent", agent_id=agent_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Agent revocation failed: {str(e)}")

# Token Management Endpoints
@app.post("/tokens/mint", response_model=EphemeralToken)
async def mint_token(
    request: TokenMintRequest,
    token: str = Depends(security)
):
    """Mint ephemeral token for agent operations"""
    try:
        # Validate token mint request
        policy_result = await policy_engine.validate_token_mint(request)
        if not policy_result.approved:
            raise HTTPException(
                status_code=403,
                detail=f"Token mint denied: {policy_result.reason}"
            )
        
        # Mint ephemeral token
        ephemeral_token = await token_manager.mint_token(
            agent_role=request.agent_role,
            tenant_id=request.tenant_id,
            ttl_minutes=request.ttl_minutes,
            scopes=request.scopes,
            reason=request.reason
        )
        
        # Log audit event
        audit_event = AuditEvent(
            event_type="token_minted",
            startup_id=request.tenant_id,
            details={
                "token_id": ephemeral_token.token_id,
                "agent_role": request.agent_role,
                "scopes": request.scopes,
                "ttl_minutes": request.ttl_minutes,
                "reason": request.reason
            },
            timestamp=datetime.utcnow()
        )
        await audit_manager.log_event(audit_event)
        
        return ephemeral_token
        
    except Exception as e:
        logger.error("Failed to mint token", error=str(e))
        raise HTTPException(status_code=500, detail=f"Token minting failed: {str(e)}")

@app.post("/tokens/{token_id}/revoke")
async def revoke_token(token_id: str, token: str = Depends(security)):
    """Revoke ephemeral token"""
    try:
        result = await token_manager.revoke_token(token_id)
        
        # Log audit event
        audit_event = AuditEvent(
            event_type="token_revoked",
            details={
                "token_id": token_id,
                "revocation_reason": "manual_revocation"
            },
            timestamp=datetime.utcnow()
        )
        await audit_manager.log_event(audit_event)
        
        return result
    except Exception as e:
        logger.error("Failed to revoke token", token_id=token_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Token revocation failed: {str(e)}")

# Policy and Governance Endpoints
@app.get("/policies")
async def list_policies(token: str = Depends(security)):
    """List all governance policies"""
    try:
        policies = await policy_engine.list_policies()
        return {"policies": policies}
    except Exception as e:
        logger.error("Failed to list policies", error=str(e))
        raise HTTPException(status_code=500, detail=f"Policy listing failed: {str(e)}")

@app.post("/policies/validate")
async def validate_operation(
    operation: str,
    context: Dict[str, Any],
    token: str = Depends(security)
):
    """Validate operation against governance policies"""
    try:
        validation_result = await policy_engine.validate_operation(operation, context)
        return validation_result
    except Exception as e:
        logger.error("Failed to validate operation", error=str(e))
        raise HTTPException(status_code=500, detail=f"Policy validation failed: {str(e)}")

# Audit and Monitoring Endpoints
@app.get("/audit/trail/{startup_id}")
async def get_audit_trail(startup_id: str, token: str = Depends(security)):
    """Get complete audit trail for startup"""
    try:
        audit_trail = await audit_manager.get_startup_audit_trail(startup_id)
        return {"startup_id": startup_id, "audit_trail": audit_trail}
    except Exception as e:
        logger.error("Failed to get audit trail", startup_id=startup_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Audit trail retrieval failed: {str(e)}")

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics = await controller.get_metrics()
        return metrics
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Metrics retrieval failed: {str(e)}")

# Startup lifecycle event handlers
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Controller Service starting up")
    await controller.initialize()
    await token_manager.initialize()
    await policy_engine.initialize()
    await tenant_manager.initialize()
    await audit_manager.initialize()
    await agent_spawner.initialize()
    logger.info("Controller Service fully operational")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Controller Service shutting down")
    await controller.cleanup()
    await token_manager.cleanup()
    await policy_engine.cleanup()
    await tenant_manager.cleanup()
    await audit_manager.cleanup()
    await agent_spawner.cleanup()
    logger.info("Controller Service shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
