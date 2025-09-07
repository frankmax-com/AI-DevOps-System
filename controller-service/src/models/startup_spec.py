"""
Startup Specification Models
Defines the structure for startup creation requests and tenant management
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

class StartupSpec(BaseModel):
    """Complete specification for startup creation"""
    
    startup_id: str = Field(..., description="Unique startup identifier")
    company_name: str = Field(..., min_length=2, max_length=100, description="Company name")
    founder_email: EmailStr = Field(..., description="Founder's email address")
    industry: str = Field(..., description="Industry sector")
    target_market: str = Field(..., description="Target market description")
    funding_stage: str = Field(..., description="Current funding stage")
    compliance_frameworks: List[str] = Field(default=[], description="Required compliance frameworks")
    business_description: str = Field(..., min_length=10, description="Business description and goals")
    initial_team_size: int = Field(default=5, ge=1, le=50, description="Initial team size")
    
    # Technical specifications
    tech_stack_preferences: Dict[str, Any] = Field(default_factory=dict, description="Technology preferences")
    infrastructure_requirements: Dict[str, Any] = Field(default_factory=dict, description="Infrastructure needs")
    security_requirements: Dict[str, Any] = Field(default_factory=dict, description="Security requirements")
    
    # Business specifications
    revenue_model: Optional[str] = Field(None, description="Revenue model")
    target_launch_date: Optional[datetime] = Field(None, description="Target launch date")
    initial_budget: Optional[float] = Field(None, ge=0, description="Initial budget allocation")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="Creator identifier")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "startup_id": "startup-12345678",
                "company_name": "TechCorp AI",
                "founder_email": "founder@techcorp.ai",
                "industry": "Artificial Intelligence",
                "target_market": "Enterprise B2B Software",
                "funding_stage": "Pre-Seed",
                "compliance_frameworks": ["SOX", "GDPR"],
                "business_description": "AI-powered business automation platform for enterprises",
                "initial_team_size": 8,
                "tech_stack_preferences": {
                    "backend": "Python/FastAPI",
                    "frontend": "React/TypeScript",
                    "database": "PostgreSQL",
                    "cloud": "Azure"
                },
                "infrastructure_requirements": {
                    "high_availability": True,
                    "auto_scaling": True,
                    "regions": ["us-east-1", "eu-west-1"]
                },
                "security_requirements": {
                    "encryption_at_rest": True,
                    "encryption_in_transit": True,
                    "mfa_required": True
                },
                "revenue_model": "SaaS Subscription",
                "initial_budget": 50000.0
            }
        }

class TenantResources(BaseModel):
    """Tenant-specific resource allocation and boundaries"""
    
    tenant_id: str = Field(..., description="Unique tenant identifier")
    resource_prefix: str = Field(..., description="Resource naming prefix")
    encryption_key_id: str = Field(..., description="Tenant-specific encryption key")
    
    # GitHub resources
    github_org_name: str = Field(..., description="GitHub organization name")
    github_team_slug: str = Field(..., description="GitHub team identifier")
    
    # Azure DevOps resources
    azure_project_name: str = Field(..., description="Azure DevOps project name")
    azure_org_url: str = Field(..., description="Azure DevOps organization URL")
    
    # Storage and database
    storage_account_name: str = Field(..., description="Azure storage account")
    database_name: str = Field(..., description="Tenant database name")
    key_vault_name: str = Field(..., description="Azure Key Vault name")
    
    # Networking and isolation
    virtual_network_id: str = Field(..., description="Virtual network identifier")
    subnet_id: str = Field(..., description="Subnet identifier")
    resource_group_name: str = Field(..., description="Azure resource group")
    
    # Quotas and limits
    quotas: Dict[str, Any] = Field(default_factory=dict, description="Resource quotas")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    provisioned: bool = Field(default=False, description="Resources provisioned")
    
    class Config:
        schema_extra = {
            "example": {
                "tenant_id": "startup-12345678",
                "resource_prefix": "startup-12345678",
                "encryption_key_id": "vault-key-12345678",
                "github_org_name": "startup-12345678-github",
                "github_team_slug": "development-team",
                "azure_project_name": "startup-12345678-azure",
                "azure_org_url": "https://dev.azure.com/startup-org",
                "storage_account_name": "startup12345678storage",
                "database_name": "startup_12345678_db",
                "key_vault_name": "startup-12345678-vault",
                "virtual_network_id": "vnet-startup-12345678",
                "subnet_id": "subnet-startup-12345678",
                "resource_group_name": "rg-startup-12345678",
                "quotas": {
                    "github_repositories": 10,
                    "azure_devops_projects": 1,
                    "ai_requests_per_hour": 1000,
                    "storage_gb": 5,
                    "concurrent_agents": 5
                }
            }
        }

class StartupStatus(BaseModel):
    """Current status of startup creation process"""
    
    startup_id: str = Field(..., description="Startup identifier")
    status: str = Field(..., description="Current status")
    
    # Phase tracking
    phases: Dict[str, str] = Field(default_factory=dict, description="Phase completion status")
    current_phase: Optional[str] = Field(None, description="Currently executing phase")
    
    # Resource status
    github_org: Optional[str] = Field(None, description="GitHub organization URL")
    azure_project: Optional[str] = Field(None, description="Azure DevOps project URL")
    
    # Agent tracking
    agents: List[Dict[str, Any]] = Field(default_factory=list, description="Active agents")
    
    # Progress metrics
    completion_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Completion percentage")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    
    class Config:
        schema_extra = {
            "example": {
                "startup_id": "startup-12345678",
                "status": "orchestrating",
                "phases": {
                    "github_bootstrap": "completed",
                    "founder_analysis": "in_progress",
                    "azure_setup": "pending",
                    "team_agents": "pending",
                    "final_validation": "pending"
                },
                "current_phase": "founder_analysis",
                "github_org": "https://github.com/startup-12345678-github",
                "azure_project": "https://dev.azure.com/startup-org/startup-12345678-azure",
                "agents": [
                    {
                        "agent_id": "agent-bootstrap-001",
                        "role": "github_bootstrap", 
                        "status": "completed",
                        "created_at": "2025-09-07T10:00:00Z"
                    },
                    {
                        "agent_id": "agent-founder-001",
                        "role": "founder",
                        "status": "active",
                        "created_at": "2025-09-07T10:15:00Z"
                    }
                ],
                "completion_percentage": 35.0,
                "estimated_completion": "2025-09-07T10:45:00Z",
                "created_at": "2025-09-07T10:00:00Z",
                "last_updated": "2025-09-07T10:20:00Z"
            }
        }
