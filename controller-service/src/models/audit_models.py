"""
Audit and Compliance Models
Tracks governance actions, compliance validation, and audit trails
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum
import uuid

class AuditEventType(str, Enum):
    """Types of auditable events in the platform"""
    
    # Startup lifecycle events
    STARTUP_CREATED = "startup_created"
    STARTUP_TERMINATED = "startup_terminated"
    
    # Agent lifecycle events  
    AGENT_SPAWNED = "agent_spawned"
    AGENT_TERMINATED = "agent_terminated"
    AGENT_SUSPENDED = "agent_suspended"
    
    # Access and authentication
    TOKEN_ISSUED = "token_issued"
    TOKEN_REVOKED = "token_revoked"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    
    # Governance actions
    GITHUB_REPO_CREATED = "github_repo_created"
    GITHUB_PERMISSION_CHANGED = "github_permission_changed"
    AZURE_PROJECT_CREATED = "azure_project_created"
    AZURE_PIPELINE_EXECUTED = "azure_pipeline_executed"
    
    # Compliance events
    COMPLIANCE_CHECK_PASSED = "compliance_check_passed"
    COMPLIANCE_CHECK_FAILED = "compliance_check_failed"
    POLICY_VIOLATION = "policy_violation"
    
    # System events
    SYSTEM_ERROR = "system_error"
    CONFIGURATION_CHANGED = "configuration_changed"
    BACKUP_CREATED = "backup_created"
    RESTORE_COMPLETED = "restore_completed"

class ComplianceFramework(str, Enum):
    """Supported compliance frameworks"""
    SOX = "sox"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    NIST = "nist"
    CCPA = "ccpa"

class AuditEvent(BaseModel):
    """Individual audit event record"""
    
    event_id: str = Field(default_factory=lambda: f"audit-{uuid.uuid4().hex[:12]}", description="Unique event identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    
    # Event classification
    event_type: AuditEventType = Field(..., description="Type of audit event")
    severity: Literal["info", "warning", "error", "critical"] = Field(default="info", description="Event severity level")
    category: str = Field(..., description="Event category")
    
    # Context information
    startup_id: Optional[str] = Field(None, description="Associated startup identifier")
    agent_id: Optional[str] = Field(None, description="Associated agent identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    # Event details
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource affected")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    
    # Request context
    source_ip: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    request_id: Optional[str] = Field(None, description="Request identifier")
    
    # Event data
    before_state: Optional[Dict[str, Any]] = Field(None, description="State before action")
    after_state: Optional[Dict[str, Any]] = Field(None, description="State after action")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional event metadata")
    
    # Result information
    success: bool = Field(..., description="Whether action was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    
    # Compliance tracking
    compliance_frameworks: List[ComplianceFramework] = Field(default_factory=list, description="Relevant compliance frameworks")
    retention_period_days: int = Field(default=2555, description="Retention period in days (7 years default)")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "event_id": "audit-abc123def456",
                "timestamp": "2025-09-07T10:30:15.123Z",
                "event_type": "github_repo_created",
                "severity": "info",
                "category": "governance",
                "startup_id": "startup-12345678",
                "agent_id": "agent-bootstrap-001",
                "user_id": "founder@techcorp.ai",
                "action": "create_repository",
                "resource": "github_repository",
                "resource_id": "repo-startup-app",
                "source_ip": "192.168.1.100",
                "before_state": {"repositories": []},
                "after_state": {"repositories": ["startup-app"]},
                "metadata": {
                    "repository_name": "startup-app",
                    "visibility": "private",
                    "template": "python-fastapi"
                },
                "success": True,
                "compliance_frameworks": ["sox", "gdpr"]
            }
        }

class ComplianceCheck(BaseModel):
    """Compliance validation check"""
    
    check_id: str = Field(default_factory=lambda: f"check-{uuid.uuid4().hex[:12]}", description="Unique check identifier")
    startup_id: str = Field(..., description="Associated startup identifier")
    framework: ComplianceFramework = Field(..., description="Compliance framework")
    
    # Check definition
    check_name: str = Field(..., description="Name of compliance check")
    check_description: str = Field(..., description="Description of what is being checked")
    control_id: str = Field(..., description="Control identifier in framework")
    
    # Check parameters
    check_type: Literal["automated", "manual", "hybrid"] = Field(..., description="Type of compliance check")
    frequency: Literal["continuous", "daily", "weekly", "monthly", "quarterly", "annual"] = Field(..., description="Check frequency")
    
    # Check execution
    last_executed: Optional[datetime] = Field(None, description="Last execution timestamp")
    next_scheduled: Optional[datetime] = Field(None, description="Next scheduled execution")
    execution_duration: Optional[float] = Field(None, description="Last execution duration in seconds")
    
    # Results
    status: Literal["compliant", "non_compliant", "warning", "unknown", "error"] = Field(..., description="Compliance status")
    score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Compliance score percentage")
    findings: List[Dict[str, Any]] = Field(default_factory=list, description="Detailed findings")
    
    # Evidence and documentation
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Supporting evidence")
    remediation_steps: List[str] = Field(default_factory=list, description="Steps to remediate issues")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="Creator identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "check_id": "check-sox-001",
                "startup_id": "startup-12345678",
                "framework": "sox",
                "check_name": "Access Control Validation",
                "check_description": "Validate that user access follows principle of least privilege",
                "control_id": "SOX-302.4.b",
                "check_type": "automated",
                "frequency": "daily",
                "last_executed": "2025-09-07T10:00:00Z",
                "next_scheduled": "2025-09-08T10:00:00Z",
                "execution_duration": 45.2,
                "status": "compliant",
                "score": 95.5,
                "findings": [
                    {
                        "type": "info",
                        "message": "All users have appropriate role assignments",
                        "resource": "azure_devops_permissions"
                    }
                ],
                "evidence": [
                    {
                        "type": "permission_matrix",
                        "url": "https://storage.com/evidence/permissions.json",
                        "checksum": "sha256:abc123..."
                    }
                ],
                "created_by": "system"
            }
        }

class AuditTrail(BaseModel):
    """Aggregated audit trail for a specific entity"""
    
    trail_id: str = Field(default_factory=lambda: f"trail-{uuid.uuid4().hex[:12]}", description="Unique trail identifier")
    entity_type: Literal["startup", "agent", "user", "system"] = Field(..., description="Type of entity being audited")
    entity_id: str = Field(..., description="Identifier of the entity")
    
    # Trail metadata
    trail_name: str = Field(..., description="Human-readable trail name")
    description: str = Field(..., description="Trail description")
    
    # Time range
    start_time: datetime = Field(..., description="Trail start time")
    end_time: Optional[datetime] = Field(None, description="Trail end time")
    
    # Event summary
    total_events: int = Field(default=0, description="Total number of events")
    event_types: Dict[str, int] = Field(default_factory=dict, description="Count by event type")
    severity_counts: Dict[str, int] = Field(default_factory=dict, description="Count by severity")
    
    # Compliance status
    compliance_status: Dict[ComplianceFramework, str] = Field(default_factory=dict, description="Status by framework")
    violations: List[str] = Field(default_factory=list, description="Policy violations found")
    
    # Access and retention
    access_level: Literal["public", "internal", "confidential", "restricted"] = Field(default="internal", description="Access level")
    retention_policy: str = Field(..., description="Retention policy identifier")
    archived: bool = Field(default=False, description="Whether trail is archived")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(..., description="Creator identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "trail_id": "trail-startup-123",
                "entity_type": "startup",
                "entity_id": "startup-12345678",
                "trail_name": "TechCorp AI Audit Trail",
                "description": "Complete audit trail for TechCorp AI startup creation",
                "start_time": "2025-09-07T10:00:00Z",
                "end_time": None,
                "total_events": 247,
                "event_types": {
                    "startup_created": 1,
                    "agent_spawned": 5,
                    "github_repo_created": 3,
                    "azure_project_created": 1,
                    "token_issued": 15
                },
                "severity_counts": {
                    "info": 235,
                    "warning": 10,
                    "error": 2,
                    "critical": 0
                },
                "compliance_status": {
                    "sox": "compliant",
                    "gdpr": "compliant"
                },
                "violations": [],
                "access_level": "confidential",
                "retention_policy": "7_years_financial",
                "created_by": "system"
            }
        }

class PolicyViolation(BaseModel):
    """Policy violation record"""
    
    violation_id: str = Field(default_factory=lambda: f"violation-{uuid.uuid4().hex[:12]}", description="Unique violation identifier")
    startup_id: str = Field(..., description="Associated startup identifier")
    
    # Violation details
    policy_id: str = Field(..., description="Violated policy identifier")
    policy_name: str = Field(..., description="Policy name")
    violation_type: str = Field(..., description="Type of violation")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Violation severity")
    
    # Context
    violating_action: str = Field(..., description="Action that caused violation")
    violating_resource: str = Field(..., description="Resource involved in violation")
    violating_agent_id: Optional[str] = Field(None, description="Agent that caused violation")
    violating_user_id: Optional[str] = Field(None, description="User that caused violation")
    
    # Violation data
    expected_value: Any = Field(..., description="Expected value per policy")
    actual_value: Any = Field(..., description="Actual value that violated policy")
    violation_details: Dict[str, Any] = Field(default_factory=dict, description="Detailed violation information")
    
    # Resolution
    status: Literal["open", "investigating", "resolved", "waived", "false_positive"] = Field(default="open", description="Violation status")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    resolved_by: Optional[str] = Field(None, description="Who resolved the violation")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    
    # Impact assessment
    business_impact: Literal["none", "low", "medium", "high", "critical"] = Field(..., description="Business impact level")
    affected_systems: List[str] = Field(default_factory=list, description="Affected systems")
    customer_impact: bool = Field(default=False, description="Whether customers are impacted")
    
    # Compliance implications
    compliance_frameworks: List[ComplianceFramework] = Field(default_factory=list, description="Affected compliance frameworks")
    regulatory_risk: bool = Field(default=False, description="Whether there's regulatory risk")
    
    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    first_occurrence: datetime = Field(default_factory=datetime.utcnow)
    last_occurrence: datetime = Field(default_factory=datetime.utcnow)
    occurrence_count: int = Field(default=1, description="Number of times violation occurred")
    
    class Config:
        schema_extra = {
            "example": {
                "violation_id": "violation-sec-001",
                "startup_id": "startup-12345678",
                "policy_id": "security-001",
                "policy_name": "Require MFA for Admin Access",
                "violation_type": "access_control",
                "severity": "high",
                "violating_action": "admin_login_without_mfa",
                "violating_resource": "azure_devops_admin_portal",
                "violating_user_id": "founder@techcorp.ai",
                "expected_value": "mfa_required",
                "actual_value": "password_only",
                "violation_details": {
                    "login_method": "username_password",
                    "mfa_available": True,
                    "mfa_used": False
                },
                "status": "open",
                "business_impact": "medium",
                "affected_systems": ["azure_devops"],
                "compliance_frameworks": ["sox", "soc2"],
                "regulatory_risk": True,
                "detected_at": "2025-09-07T10:45:00Z"
            }
        }
