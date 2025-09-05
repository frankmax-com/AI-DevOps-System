# Database Governance Factory - FastAPI Service

"""
Database Governance Factory - REST API Service
Provides REST API endpoints for database governance management
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import asyncio
import logging
from datetime import datetime
import os
import json

from src.governance_manager import (
    DatabaseGovernanceManager,
    DatabaseConnection,
    DatabaseType,
    GovernancePolicy,
    GovernanceViolation,
    create_database_governance_manager
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Database Governance Factory API",
    description="Comprehensive multi-database governance system for enterprise applications",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Global governance manager
governance_manager: DatabaseGovernanceManager = None

# Pydantic models for API
class DatabaseConnectionRequest(BaseModel):
    name: str = Field(..., description="Unique database name")
    db_type: str = Field(..., description="Database type: mongodb, postgresql, redis, cosmos_db, blob_storage")
    connection_string: str = Field(..., description="Database connection string")
    database_name: str = Field(..., description="Database name")
    module_name: str = Field(..., description="Service or module name")
    environment: str = Field(..., description="Environment: development, staging, production")
    governance_policies: List[str] = Field(..., description="List of governance policy IDs")
    compliance_frameworks: List[str] = Field(..., description="List of compliance frameworks")

class GovernanceAuditRequest(BaseModel):
    database_name: Optional[str] = Field(None, description="Specific database to audit (optional)")
    policy_ids: Optional[List[str]] = Field(None, description="Specific policies to check (optional)")

class GovernancePolicyRequest(BaseModel):
    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Policy display name")
    description: str = Field(..., description="Policy description")
    applicable_db_types: List[str] = Field(..., description="Applicable database types")
    compliance_frameworks: List[str] = Field(..., description="Related compliance frameworks")
    enforcement_level: str = Field(..., description="Enforcement level: warning, error, blocking")
    validation_rules: Dict[str, Any] = Field(..., description="Validation rules configuration")
    remediation_actions: List[str] = Field(..., description="Suggested remediation actions")

class ViolationResolutionRequest(BaseModel):
    violation_id: str = Field(..., description="Violation ID to resolve")
    resolution_action: str = Field(..., description="Action taken to resolve")
    notes: Optional[str] = Field(None, description="Additional resolution notes")

# API Response models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class DatabaseStatus(BaseModel):
    name: str
    type: str
    module: str
    environment: str
    status: str
    last_health_check: str
    violations_count: int

class GovernanceAuditResult(BaseModel):
    audit_id: str
    timestamp: str
    databases_audited: List[Dict[str, Any]]
    violations_found: List[Dict[str, Any]]
    compliance_score: float
    recommendations: List[str]

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize governance manager on startup"""
    global governance_manager
    governance_manager = create_database_governance_manager()
    logger.info("Database Governance Factory API started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global governance_manager
    if governance_manager:
        await governance_manager.close_all_connections()
    logger.info("Database Governance Factory API stopped")

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token"""
    # In production, implement proper JWT verification
    expected_token = os.getenv("GOVERNANCE_API_TOKEN", "dev-token")
    if credentials.credentials != expected_token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    return credentials

# API Endpoints

@app.get("/", response_model=APIResponse)
async def root():
    """Root endpoint with API information"""
    return APIResponse(
        success=True,
        message="Database Governance Factory API",
        data={
            "version": "1.0.0",
            "description": "Multi-database governance system for enterprise applications",
            "endpoints": {
                "health": "/health",
                "databases": "/databases",
                "audit": "/audit",
                "policies": "/policies",
                "dashboard": "/dashboard"
            }
        }
    )

@app.get("/health", response_model=APIResponse)
async def health_check():
    """Health check endpoint"""
    try:
        status = {
            "status": "healthy",
            "governance_manager": "active" if governance_manager else "inactive",
            "registered_databases": len(governance_manager.connections) if governance_manager else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        return APIResponse(
            success=True,
            message="Service is healthy",
            data=status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")

@app.post("/databases/register", response_model=APIResponse)
async def register_database(
    request: DatabaseConnectionRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Register a database for governance monitoring"""
    try:
        # Convert string db_type to enum
        try:
            db_type = DatabaseType(request.db_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid database type: {request.db_type}")
        
        # Create database connection config
        connection_config = DatabaseConnection(
            name=request.name,
            db_type=db_type,
            connection_string=request.connection_string,
            database_name=request.database_name,
            module_name=request.module_name,
            environment=request.environment,
            governance_policies=request.governance_policies,
            compliance_frameworks=request.compliance_frameworks
        )
        
        # Register database
        success = await governance_manager.register_database(connection_config)
        
        if success:
            # Schedule initial audit in background
            background_tasks.add_task(governance_manager.run_governance_audit, request.name)
            
            return APIResponse(
                success=True,
                message=f"Database {request.name} registered successfully",
                data={"database_name": request.name, "status": "registered"}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to register database")
            
    except Exception as e:
        logger.error(f"Error registering database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/databases", response_model=APIResponse)
async def list_databases(
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """List all registered databases"""
    try:
        databases = []
        for db_name, db_info in governance_manager.connections.items():
            config = db_info['config']
            databases.append(DatabaseStatus(
                name=db_name,
                type=config.db_type.value,
                module=config.module_name,
                environment=config.environment,
                status=db_info['governance_status'],
                last_health_check=db_info['last_health_check'].isoformat(),
                violations_count=len([v for v in governance_manager.violations 
                                    if v.database_name == db_name and v.status == 'open'])
            ).dict())
        
        return APIResponse(
            success=True,
            message=f"Found {len(databases)} registered databases",
            data={"databases": databases, "total_count": len(databases)}
        )
    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/audit/run", response_model=APIResponse)
async def run_audit(
    request: GovernanceAuditRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Run governance audit on specified database or all databases"""
    try:
        # Run audit
        audit_results = await governance_manager.run_governance_audit(request.database_name)
        
        return APIResponse(
            success=True,
            message="Governance audit completed successfully",
            data=GovernanceAuditResult(**audit_results).dict()
        )
    except Exception as e:
        logger.error(f"Error running audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/results", response_model=APIResponse)
async def get_audit_results(
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    database_name: Optional[str] = Query(None, description="Filter by database name"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Get audit results with pagination and filtering"""
    try:
        violations = governance_manager.violations
        
        # Apply filters
        if database_name:
            violations = [v for v in violations if v.database_name == database_name]
        if severity:
            violations = [v for v in violations if v.severity == severity]
        
        # Sort by detection time (newest first)
        violations = sorted(violations, key=lambda x: x.detected_at, reverse=True)
        
        # Apply pagination
        total_count = len(violations)
        paginated_violations = violations[offset:offset + limit]
        
        # Convert to dict for JSON serialization
        violations_data = []
        for violation in paginated_violations:
            violations_data.append({
                "violation_id": violation.violation_id,
                "database_name": violation.database_name,
                "policy_id": violation.policy_id,
                "severity": violation.severity,
                "description": violation.description,
                "detected_at": violation.detected_at.isoformat(),
                "violation_data": violation.violation_data,
                "remediation_suggested": violation.remediation_suggested,
                "status": violation.status
            })
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(violations_data)} audit results",
            data={
                "violations": violations_data,
                "pagination": {
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            }
        )
    except Exception as e:
        logger.error(f"Error getting audit results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policies", response_model=APIResponse)
async def list_policies(
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """List all governance policies"""
    try:
        policies_data = []
        for policy_id, policy in governance_manager.policies.items():
            policies_data.append({
                "policy_id": policy.policy_id,
                "name": policy.name,
                "description": policy.description,
                "applicable_db_types": [db_type.value for db_type in policy.applicable_db_types],
                "compliance_frameworks": policy.compliance_frameworks,
                "enforcement_level": policy.enforcement_level,
                "validation_rules": policy.validation_rules,
                "remediation_actions": policy.remediation_actions
            })
        
        return APIResponse(
            success=True,
            message=f"Found {len(policies_data)} governance policies",
            data={"policies": policies_data, "total_count": len(policies_data)}
        )
    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard", response_model=APIResponse)
async def get_dashboard(
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Get comprehensive governance dashboard data"""
    try:
        dashboard_data = await governance_manager.get_governance_dashboard()
        
        return APIResponse(
            success=True,
            message="Dashboard data retrieved successfully",
            data=dashboard_data
        )
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/violations/{violation_id}/resolve", response_model=APIResponse)
async def resolve_violation(
    violation_id: str,
    request: ViolationResolutionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Mark a violation as resolved"""
    try:
        # Find violation
        violation = None
        for v in governance_manager.violations:
            if v.violation_id == violation_id:
                violation = v
                break
        
        if not violation:
            raise HTTPException(status_code=404, detail="Violation not found")
        
        # Update violation status
        violation.status = "resolved"
        
        # Log resolution
        governance_manager._log_audit_event(
            action="violation_resolved",
            database_name=violation.database_name,
            details={
                "violation_id": violation_id,
                "resolution_action": request.resolution_action,
                "notes": request.notes
            }
        )
        
        return APIResponse(
            success=True,
            message="Violation marked as resolved",
            data={
                "violation_id": violation_id,
                "status": "resolved",
                "resolution_action": request.resolution_action
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving violation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/compliance/{framework}", response_model=APIResponse)
async def get_compliance_status(
    framework: str,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Get compliance status for specific framework"""
    try:
        dashboard_data = await governance_manager.get_governance_dashboard()
        compliance_summary = dashboard_data.get('compliance_summary', {})
        
        if framework not in compliance_summary:
            raise HTTPException(status_code=404, detail=f"Compliance framework '{framework}' not found")
        
        framework_data = compliance_summary[framework]
        
        return APIResponse(
            success=True,
            message=f"Compliance status for {framework}",
            data={
                "framework": framework,
                "compliance_score": framework_data["compliance_score"],
                "violations_count": framework_data["violations_count"],
                "policies_count": framework_data["policies_count"],
                "status": "compliant" if framework_data["compliance_score"] >= 90 else "non_compliant"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting compliance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/export", response_model=APIResponse)
async def export_metrics(
    format: str = Query("json", description="Export format: json, csv, prometheus"),
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """Export governance metrics in various formats"""
    try:
        dashboard_data = await governance_manager.get_governance_dashboard()
        
        if format == "prometheus":
            # Export in Prometheus format
            metrics_text = "# HELP database_governance_compliance_score Database compliance score\n"
            metrics_text += "# TYPE database_governance_compliance_score gauge\n"
            
            for db in dashboard_data["databases"]:
                metrics_text += f'database_governance_compliance_score{{database="{db["name"]}",module="{db["module"]}"}} {100 - db["violations_count"]}\n'
            
            return APIResponse(
                success=True,
                message="Metrics exported in Prometheus format",
                data={"metrics": metrics_text, "format": "prometheus"}
            )
        else:
            # Default JSON format
            return APIResponse(
                success=True,
                message="Metrics exported successfully",
                data={"metrics": dashboard_data, "format": "json"}
            )
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates (optional)
@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await websocket.accept()
    try:
        while True:
            # Send dashboard updates every 30 seconds
            dashboard_data = await governance_manager.get_governance_dashboard()
            await websocket.send_json({
                "type": "dashboard_update",
                "data": dashboard_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(30)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=os.getenv("GOVERNANCE_API_HOST", "0.0.0.0"),
        port=int(os.getenv("GOVERNANCE_API_PORT", 8080)),
        reload=os.getenv("DEBUG_MODE", "false").lower() == "true"
    )
