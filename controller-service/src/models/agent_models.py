"""
Agent Models for AI DevOps Platform
Defines agent specifications, lifecycle management, and communication protocols
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime, timedelta
from enum import Enum
import uuid

class AgentRole(str, Enum):
    """Standardized agent roles in the platform"""
    GITHUB_BOOTSTRAP = "github_bootstrap"
    FOUNDER = "founder"
    DEVELOPER = "developer"
    DEVOPS = "devops"
    SECURITY = "security"
    QA = "qa"
    RELEASE = "release"
    PM = "pm"
    AUDIT = "audit"

class AgentStatus(str, Enum):
    """Agent lifecycle status tracking"""
    CREATED = "created"
    SPAWNING = "spawning"
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    SUSPENDED = "suspended"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    ERROR = "error"

class AgentSpec(BaseModel):
    """Specification for agent creation"""
    
    agent_id: str = Field(default_factory=lambda: f"agent-{uuid.uuid4().hex[:12]}", description="Unique agent identifier")
    startup_id: str = Field(..., description="Associated startup identifier")
    role: AgentRole = Field(..., description="Agent role and responsibilities")
    
    # Configuration
    name: str = Field(..., min_length=1, max_length=100, description="Agent display name")
    description: str = Field(..., description="Agent purpose and capabilities")
    
    # Resource allocation
    cpu_limit: float = Field(default=2.0, ge=0.1, le=8.0, description="CPU cores allocated")
    memory_limit: str = Field(default="4Gi", description="Memory allocation")
    disk_limit: str = Field(default="10Gi", description="Disk space allocation")
    
    # Behavioral configuration
    max_idle_duration: timedelta = Field(default=timedelta(hours=1), description="Maximum idle time before suspension")
    max_runtime_duration: timedelta = Field(default=timedelta(hours=8), description="Maximum runtime before forced termination")
    
    # Scopes and permissions
    scopes: List[str] = Field(default_factory=list, description="Authorized operation scopes")
    governance_access: Dict[str, List[str]] = Field(default_factory=dict, description="Governance factory access")
    
    # Agent-specific configuration
    config: Dict[str, Any] = Field(default_factory=dict, description="Role-specific configuration")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    
    # Metadata
    created_by: Optional[str] = Field(None, description="Creator identifier")
    tags: List[str] = Field(default_factory=list, description="Agent tags")
    
    @validator('scopes')
    def validate_scopes_for_role(cls, v, values):
        """Validate that scopes are appropriate for the agent role"""
        role = values.get('role')
        if role:
            required_scopes = cls._get_required_scopes_for_role(role)
            if not all(scope in v for scope in required_scopes):
                raise ValueError(f"Missing required scopes for role {role}: {required_scopes}")
        return v
    
    @staticmethod
    def _get_required_scopes_for_role(role: AgentRole) -> List[str]:
        """Get required scopes for each agent role"""
        scope_mapping = {
            AgentRole.GITHUB_BOOTSTRAP: ["github:repo", "github:admin"],
            AgentRole.FOUNDER: ["github:read", "azure:read", "ai:moderate"],
            AgentRole.DEVELOPER: ["github:write", "ai:high", "docker:basic"],
            AgentRole.DEVOPS: ["azure:admin", "docker:admin", "kubernetes:admin"],
            AgentRole.SECURITY: ["security:audit", "vault:read", "compliance:validate"],
            AgentRole.QA: ["testing:execute", "ai:moderate", "reporting:write"],
            AgentRole.RELEASE: ["github:admin", "azure:deploy", "release:manage"],
            AgentRole.PM: ["project:manage", "reporting:admin", "communication:send"],
            AgentRole.AUDIT: ["audit:full", "compliance:validate", "reporting:admin"]
        }
        return scope_mapping.get(role, [])
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            timedelta: lambda v: str(v)
        }
        schema_extra = {
            "example": {
                "agent_id": "agent-dev-001",
                "startup_id": "startup-12345678",
                "role": "developer",
                "name": "Senior Developer Agent",
                "description": "Handles core development tasks, code reviews, and architecture decisions",
                "cpu_limit": 4.0,
                "memory_limit": "8Gi",
                "disk_limit": "20Gi",
                "scopes": ["github:write", "ai:high", "docker:basic"],
                "governance_access": {
                    "github": ["repository:write", "pull_request:manage"],
                    "ai_provider": ["code_generation", "code_review"],
                    "database": ["schema:read", "migration:create"]
                },
                "config": {
                    "preferred_languages": ["Python", "TypeScript"],
                    "testing_framework": "pytest",
                    "code_style": "black"
                },
                "environment_variables": {
                    "PYTHON_VERSION": "3.11",
                    "NODE_VERSION": "18"
                },
                "tags": ["senior", "fullstack", "python"]
            }
        }

class AgentInstance(BaseModel):
    """Running agent instance with state tracking"""
    
    agent_id: str = Field(..., description="Agent identifier")
    startup_id: str = Field(..., description="Associated startup identifier")
    role: AgentRole = Field(..., description="Agent role")
    
    # Current state
    status: AgentStatus = Field(default=AgentStatus.CREATED, description="Current agent status")
    container_id: Optional[str] = Field(None, description="Container runtime identifier")
    endpoint_url: Optional[str] = Field(None, description="Agent API endpoint")
    
    # Token and authentication
    access_token: Optional[str] = Field(None, description="Current access token")
    token_expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    
    # Resource usage
    cpu_usage: float = Field(default=0.0, description="Current CPU usage percentage")
    memory_usage: float = Field(default=0.0, description="Current memory usage percentage")
    disk_usage: float = Field(default=0.0, description="Current disk usage percentage")
    
    # Activity tracking
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    total_requests: int = Field(default=0, description="Total requests processed")
    failed_requests: int = Field(default=0, description="Failed requests count")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None, description="Start time")
    terminated_at: Optional[datetime] = Field(None, description="Termination time")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Last error message")
    health_status: str = Field(default="unknown", description="Health check status")
    
    # Configuration reference
    spec: AgentSpec = Field(..., description="Agent specification")
    
    def is_healthy(self) -> bool:
        """Check if agent is in healthy state"""
        return (
            self.status in [AgentStatus.ACTIVE, AgentStatus.IDLE] and
            self.health_status == "healthy" and
            self.error_message is None
        )
    
    def is_expired(self) -> bool:
        """Check if agent token is expired"""
        return (
            self.token_expires_at is not None and
            datetime.utcnow() > self.token_expires_at
        )
    
    def should_terminate(self) -> bool:
        """Check if agent should be terminated due to runtime limits"""
        if self.started_at is None:
            return False
        
        runtime = datetime.utcnow() - self.started_at
        return runtime > self.spec.max_runtime_duration
    
    class Config:
        schema_extra = {
            "example": {
                "agent_id": "agent-dev-001",
                "startup_id": "startup-12345678",
                "role": "developer",
                "status": "active",
                "container_id": "container-abc123",
                "endpoint_url": "https://agent-dev-001.agents.platform.com",
                "access_token": "jwt-token-here",
                "token_expires_at": "2025-09-07T11:00:00Z",
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_usage": 23.1,
                "last_activity": "2025-09-07T10:25:00Z",
                "total_requests": 127,
                "failed_requests": 2,
                "created_at": "2025-09-07T10:00:00Z",
                "started_at": "2025-09-07T10:02:00Z",
                "error_message": null,
                "health_status": "healthy"
            }
        }

class AgentCommunication(BaseModel):
    """Agent-to-agent communication protocol"""
    
    message_id: str = Field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:12]}", description="Unique message identifier")
    from_agent_id: str = Field(..., description="Sender agent identifier")
    to_agent_id: str = Field(..., description="Recipient agent identifier")
    
    # Message content
    message_type: Literal["request", "response", "notification", "broadcast"] = Field(..., description="Message type")
    subject: str = Field(..., description="Message subject")
    body: Dict[str, Any] = Field(..., description="Message body content")
    
    # Routing and priority
    priority: Literal["low", "normal", "high", "critical"] = Field(default="normal", description="Message priority")
    requires_response: bool = Field(default=False, description="Whether response is required")
    response_timeout: Optional[timedelta] = Field(None, description="Response timeout duration")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    response_message_id: Optional[str] = Field(None, description="Response message identifier")
    
    # Status tracking
    delivered: bool = Field(default=False, description="Message delivered")
    processed: bool = Field(default=False, description="Message processed")
    error: Optional[str] = Field(None, description="Delivery error")
    
    class Config:
        schema_extra = {
            "example": {
                "message_id": "msg-abc123def456",
                "from_agent_id": "agent-dev-001", 
                "to_agent_id": "agent-qa-001",
                "message_type": "request",
                "subject": "Code Review Request",
                "body": {
                    "pull_request_url": "https://github.com/startup/repo/pull/123",
                    "review_type": "security_scan",
                    "deadline": "2025-09-07T12:00:00Z"
                },
                "priority": "high",
                "requires_response": True,
                "response_timeout": "PT30M",
                "created_at": "2025-09-07T10:30:00Z"
            }
        }

class AgentTask(BaseModel):
    """Task assigned to an agent"""
    
    task_id: str = Field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}", description="Unique task identifier")
    agent_id: str = Field(..., description="Assigned agent identifier")
    startup_id: str = Field(..., description="Associated startup identifier")
    
    # Task definition
    task_type: str = Field(..., description="Type of task")
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task description")
    instructions: List[str] = Field(default_factory=list, description="Step-by-step instructions")
    
    # Task parameters
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task-specific parameters")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for task")
    expected_output: Optional[Dict[str, Any]] = Field(None, description="Expected output format")
    
    # Scheduling and execution
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=highest, 10=lowest)")
    estimated_duration: Optional[timedelta] = Field(None, description="Estimated execution time")
    deadline: Optional[datetime] = Field(None, description="Task deadline")
    
    # Dependencies
    depends_on: List[str] = Field(default_factory=list, description="Task dependencies")
    blocks: List[str] = Field(default_factory=list, description="Tasks blocked by this task")
    
    # Status tracking
    status: Literal["created", "queued", "running", "completed", "failed", "cancelled"] = Field(default="created")
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Completion percentage")
    
    # Results
    output_data: Optional[Dict[str, Any]] = Field(None, description="Task output data")
    artifacts: List[str] = Field(default_factory=list, description="Generated artifacts")
    logs: List[str] = Field(default_factory=list, description="Execution logs")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "task-setup-repo",
                "agent_id": "agent-dev-001",
                "startup_id": "startup-12345678",
                "task_type": "repository_setup",
                "title": "Initialize Repository Structure",
                "description": "Set up initial repository structure with best practices",
                "instructions": [
                    "Create directory structure",
                    "Initialize git repository", 
                    "Add README and gitignore",
                    "Set up CI/CD pipeline"
                ],
                "parameters": {
                    "language": "Python",
                    "framework": "FastAPI",
                    "include_docker": True
                },
                "priority": 2,
                "estimated_duration": "PT45M",
                "deadline": "2025-09-07T12:00:00Z",
                "status": "running",
                "progress_percentage": 65.0
            }
        }
