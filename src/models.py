from pydantic import BaseModel
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class TaskStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    SETUP = "setup"
    CODING = "coding"
    COMMITTING = "committing"
    PR_CREATED = "pr_created"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class WorkStartRequest(BaseModel):
    task_id: str
    repository: str
    branch: str
    azure_workitem_id: int
    requirements: Optional[str] = None


class WorkStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    progress: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class AuditEvent(BaseModel):
    correlation_id: str
    task_id: str
    work_item_id: int
    old_state: Optional[TaskStatus]
    new_state: TaskStatus
    timestamp: str
    service: str = "dev-agent-service"
