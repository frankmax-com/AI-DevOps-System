from pydantic import BaseModel
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class ProjectStatus(str, Enum):
    MISSING = "missing"
    CREATING = "creating"
    WELLFORMED = "wellFormed"
    DELETION_IN_PROGRESS = "deletionInProgress"
    NEW = "new"
    NOTSET = "notSet"


class WorkItemState(str, Enum):
    NEW = "New"
    ACTIVE = "Active"
    CLOSED = "Closed"
    REMOVED = "Removed"
    READY_FOR_DEVELOPMENT = "Ready for Development"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    BLOCKED = "Blocked"


class WorkItemType(str, Enum):
    BUG = "Bug"
    TASK = "Task"
    USER_STORY = "User Story"
    FEATURE = "Feature"
    EPIC = "Epic"
    REQUIREMENT = "Requirement"
    TEST_CASE = "Test Case"


class AgentType(Enum):
    DEV_AGENT = "dev-agent-service"
    QA_AGENT = "qa-agent-service"
    SECURITY_AGENT = "security-agent-service"
    RELEASE_AGENT = "release-agent-service"


class WebhookEvent(BaseModel):
    id: int
    eventType: str
    publisherId: str
    message: Dict[str, Any]
    detailedMessage: Optional[Dict[str, Any]] = None
    resource: Dict[str, Any]
    resourceVersion: Optional[str] = None
    resourceContainers: Dict[str, Any]
    createdDate: str


class WorkItemReference(BaseModel):
    id: int
    url: str


class WorkItemUpdate(BaseModel):
    id: int
    workItemId: int
    rev: int
    revisedBy: Optional[Dict[str, Any]] = None
    revisedDate: str
    fields: Dict[str, Any]
    links: Optional[Dict[str, Any]] = None
    url: str


class ProjectCreateRequest(BaseModel):
    name: str
    description: str
    visibility: str = "private"
    capabilities: Optional[Dict[str, Any]] = None
    _links: Optional[Dict[str, Any]] = None


class ProjectCreateResponse(BaseModel):
    id: str
    name: str
    url: str
    state: ProjectStatus
    visibility: str
    lastUpdateTime: str


class BootstrapResult(BaseModel):
    success: bool
    project_name: str
    project_id: Optional[str] = None
    status: ProjectStatus
    message: str
    created_at: datetime
    correlation_id: str


class TaskRoutingResult(BaseModel):
    correlation_id: str
    work_item_id: int
    agent: str
    target_url: str
    old_state: WorkItemState
    new_state: WorkItemState
    success: bool
    message: str
    timestamp: datetime


class AuditEvent(BaseModel):
    correlation_id: str
    event_type: str
    work_item_id: Optional[int] = None
    project_name: Optional[str] = None
    project_id: Optional[str] = None
    agent: Optional[str] = None
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    timestamp: str
    service: str = "orchestrator-service"
    details: Optional[Dict[str, Any]] = None


class HealthStatus(BaseModel):
    status: str  # "healthy" or "unhealthy"
    checks: Dict[str, bool]
    timestamp: datetime


class Metrics(BaseModel):
    projects_created_total: int
    tasks_routed_total: Dict[str, int]  # agent -> count
    routing_failures_total: int
    bootstrap_failures_total: int
    uptime_seconds: float
