"""
Enhanced Controller Service with additional endpoints for autonomous orchestration
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import json
from pydantic import BaseModel

# Import governance factories
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from governance_factories.mock_github import GitHubGovernanceFactory
from governance_factories.mock_azure import AzureDevOpsGovernanceFactory
from governance_factories.ai_provider_factory import AIProviderFactory
from governance_factories.db_gov import DBGovernanceFactory

app = FastAPI(title="Enhanced Controller Service", version="1.0.0")
security = HTTPBearer()

# Initialize governance factories
github_factory = GitHubGovernanceFactory()
azure_factory = AzureDevOpsGovernanceFactory()
ai_factory = AIProviderFactory()
db_factory = DBGovernanceFactory()

# Pydantic models
class PlanOnboardRequest(BaseModel):
    tenant: str

class TokenMintRequest(BaseModel):
    agent_role: str
    tenant_id: str
    ttl_minutes: int = 30
    scopes: List[str]
    reason: str

class ActionRegisterRequest(BaseModel):
    request_id: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]

@app.post("/plan-onboard")
async def plan_onboard(request: PlanOnboardRequest):
    """
    Generate onboarding plan for tenant
    """
    try:
        request_id = str(uuid.uuid4())
        
        # Generate comprehensive onboarding plan
        plan = {
            "request_id": request_id,
            "tenant": request.tenant,
            "timestamp": datetime.utcnow().isoformat(),
            "plan_version": "1.0",
            "estimated_duration_minutes": 30,
            "phases": [
                {
                    "phase": "github_bootstrap",
                    "description": "Create GitHub organization and repositories",
                    "estimated_minutes": 10,
                    "actions": [
                        {
                            "action": "mint_token",
                            "role_template": "github_bootstrap",
                            "reason": f"Bootstrap GitHub for {request.tenant}"
                        },
                        {
                            "action": "create_organization",
                            "org_name": f"{request.tenant}-org"
                        },
                        {
                            "action": "create_repository",
                            "repo_name": f"{request.tenant}-app",
                            "private": True
                        },
                        {
                            "action": "create_team",
                            "team_name": f"{request.tenant}-developers"
                        },
                        {
                            "action": "create_workflow_file",
                            "workflow_name": "ci.yml",
                            "template": "templates/ci.yml"
                        },
                        {
                            "action": "create_branch_protection",
                            "branch": "main"
                        }
                    ]
                },
                {
                    "phase": "azure_devops_setup",
                    "description": "Create Azure DevOps project and pipelines",
                    "estimated_minutes": 12,
                    "actions": [
                        {
                            "action": "mint_token",
                            "role_template": "project_owner",
                            "reason": f"Setup Azure DevOps for {request.tenant}"
                        },
                        {
                            "action": "create_project",
                            "project_name": f"{request.tenant}-project",
                            "description": f"Azure DevOps project for {request.tenant}"
                        },
                        {
                            "action": "create_repository",
                            "repo_name": f"{request.tenant}-code"
                        },
                        {
                            "action": "create_pipeline_from_template",
                            "pipeline_name": f"{request.tenant}-ci-pipeline",
                            "template_path": "templates/azure-pipelines.yml"
                        }
                    ]
                },
                {
                    "phase": "agent_spawning",
                    "description": "Spawn roleplay agents",
                    "estimated_minutes": 5,
                    "actions": [
                        {
                            "action": "spawn_agent",
                            "agent_role": "founder",
                            "capabilities": ["strategic_planning", "business_analysis"]
                        },
                        {
                            "action": "spawn_agent", 
                            "agent_role": "dev",
                            "capabilities": ["code_development", "technical_implementation"]
                        },
                        {
                            "action": "spawn_agent",
                            "agent_role": "ops",
                            "capabilities": ["infrastructure", "deployment"]
                        },
                        {
                            "action": "spawn_agent",
                            "agent_role": "security",
                            "capabilities": ["security_scanning", "compliance_validation"]
                        },
                        {
                            "action": "spawn_agent",
                            "agent_role": "finance",
                            "capabilities": ["cost_tracking", "budget_management"]
                        }
                    ]
                },
                {
                    "phase": "ci_security_validation",
                    "description": "Run CI pipeline and security validation",
                    "estimated_minutes": 8,
                    "actions": [
                        {
                            "action": "trigger_ci_pipeline",
                            "pipeline": f"{request.tenant}-ci-pipeline"
                        },
                        {
                            "action": "run_security_scan",
                            "scan_type": "comprehensive"
                        },
                        {
                            "action": "validate_compliance",
                            "frameworks": ["SOX", "GDPR"]
                        }
                    ]
                }
            ]
        }
        
        # Log plan generation
        await db_factory.insert_entry({
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "plan_generated",
            "resource_type": "onboarding_plan", 
            "resource_id": request_id,
            "actor": "controller_service",
            "details": {
                "tenant": request.tenant,
                "phase_count": len(plan["phases"]),
                "estimated_duration": plan["estimated_duration_minutes"]
            }
        })
        
        return {
            "request_id": request_id,
            "plan": plan,
            "summary": [
                f"Phase 1: Bootstrap GitHub organization and repositories for {request.tenant}",
                f"Phase 2: Setup Azure DevOps project with CI/CD pipelines", 
                f"Phase 3: Spawn 5 roleplay agents (founder, dev, ops, security, finance)",
                f"Phase 4: Execute CI pipeline and comprehensive security validation",
                f"Total estimated time: {plan['estimated_duration_minutes']} minutes"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {str(e)}")

@app.post("/mint-token")
async def mint_token(request: TokenMintRequest):
    """
    Mint ephemeral token for agent operations
    """
    try:
        request_id = str(uuid.uuid4())
        
        # Determine platform based on role
        if request.agent_role in ["github_bootstrap", "repo_creator", "team_admin"]:
            # Use GitHub factory
            token_data = await github_factory.mint_token(
                role_template=request.agent_role,
                org=f"{request.tenant_id}-org",
                ttl_minutes=request.ttl_minutes,
                reason=request.reason,
                request_id=request_id
            )
            platform = "github"
        elif request.agent_role in ["project_owner", "repo_admin", "pipeline_admin"]:
            # Use Azure DevOps factory
            token_data = await azure_factory.mint_token(
                role_template=request.agent_role,
                organization=f"{request.tenant_id}-org",
                ttl_minutes=request.ttl_minutes,
                reason=request.reason,
                request_id=request_id
            )
            platform = "azure_devops"
        else:
            # Mock token for AI agents
            token_data = {
                "id": str(uuid.uuid4()),
                "token": f"ai_mock_{uuid.uuid4().hex[:8]}***",
                "expires_at": (datetime.utcnow()).isoformat(),
                "scopes": request.scopes,
                "role_template": request.agent_role
            }
            platform = "ai"
        
        # Register action in audit trail
        await db_factory.insert_entry({
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(), 
            "event_type": "token_minted",
            "resource_type": f"{platform}_token",
            "resource_id": token_data["id"],
            "actor": "controller_service",
            "details": {
                "agent_role": request.agent_role,
                "tenant_id": request.tenant_id,
                "ttl_minutes": request.ttl_minutes,
                "reason": request.reason,
                "platform": platform,
                "scopes": request.scopes
            }
        })
        
        return {
            "token_id": token_data["id"],
            "token": token_data["token"],  # Masked in logs
            "expires_at": token_data["expires_at"],
            "scopes": token_data.get("scopes", request.scopes),
            "platform": platform
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token minting failed: {str(e)}")

@app.post("/revoke-token")
async def revoke_token(token_id: str):
    """
    Revoke ephemeral token
    """
    try:
        request_id = str(uuid.uuid4())
        
        # Try to revoke from all factories
        revoked = False
        platform = "unknown"
        
        # Try GitHub factory
        try:
            result = await github_factory.revoke_token(token_id, request_id)
            if result.get("status") == "revoked":
                revoked = True
                platform = "github"
        except:
            pass
            
        # Try Azure factory
        if not revoked:
            try:
                result = await azure_factory.revoke_token(token_id, request_id)
                if result.get("status") == "revoked":
                    revoked = True
                    platform = "azure_devops"
            except:
                pass
        
        if not revoked:
            raise HTTPException(status_code=404, detail="Token not found")
        
        # Register action in audit trail
        await db_factory.insert_entry({
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "token_revoked",
            "resource_type": f"{platform}_token",
            "resource_id": token_id,
            "actor": "controller_service",
            "details": {
                "platform": platform,
                "revocation_reason": "manual_revocation"
            }
        })
        
        return {
            "status": "revoked",
            "token_id": token_id,
            "platform": platform,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        if "Token not found" in str(e):
            raise e
        raise HTTPException(status_code=500, detail=f"Token revocation failed: {str(e)}")

@app.post("/register-action")
async def register_action(request: ActionRegisterRequest):
    """
    Register action in audit trail
    """
    try:
        entry_id = await db_factory.insert_entry({
            "request_id": request.request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": request.action,
            "resource_type": request.resource_type,
            "resource_id": request.resource_id,
            "actor": "autonomous_agent",
            "details": request.details
        })
        
        return {
            "entry_id": entry_id,
            "status": "registered",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Action registration failed: {str(e)}")

@app.get("/audit/trail/{request_id}")
async def get_audit_trail(request_id: str):
    """
    Get audit trail for specific request
    """
    try:
        entries = await db_factory.get_entries_by_request(request_id)
        return {
            "request_id": request_id,
            "entry_count": len(entries),
            "entries": entries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit trail retrieval failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "enhanced-controller-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "governance_factories": {
            "github": "operational",
            "azure_devops": "operational", 
            "ai_provider": "operational",
            "database": "operational"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
