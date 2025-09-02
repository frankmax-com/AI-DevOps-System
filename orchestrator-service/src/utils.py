import structlog
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime
import uuid
import os
from src.models import AuditEvent, HealthStatus


# Configure structured logging
def configure_logging():
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=shared_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    ))
    logger.addHandler(handler)


# Generate correlation ID
def generate_correlation_id() -> str:
    return str(uuid.uuid4())


# Structured logger with correlation ID
def get_logger(correlation_id: Optional[str] = None) -> Any:
    logger = structlog.get_logger()
    if correlation_id:
        logger = logger.bind(correlation_id=correlation_id)
    return logger


# Send audit event to audit service
async def send_audit_event_async(
    audit_service_url: str,
    event: AuditEvent,
    logger,
    timeout: int = 5
) -> bool:
    """Send audit event asynchronously to audit service."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{audit_service_url}/audit/event",
                json=event.dict(),
                timeout=timeout
            ) as response:
                if response.status == 200:
                    logger.debug("Audit event sent successfully", status_code=response.status)
                    return True
                else:
                    logger.warning("Failed to send audit event",
                                 status_code=response.status,
                                 response_text=await response.text())
                    return False
    except Exception as e:
        logger.warning("Error sending audit event", error=str(e))
        return False


def send_audit_event(
    audit_service_url: str,
    event: AuditEvent,
    logger,
    timeout: int = 5
) -> bool:
    """Synchronous wrapper for audit event sending."""
    import requests
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If running in async context, create new event loop
            import asyncio
            new_loop = asyncio.new_event_loop()
            return new_loop.run_until_complete(send_audit_event_async(audit_service_url, event, logger, timeout))
        else:
            return asyncio.run(send_audit_event_async(audit_service_url, event, logger, timeout))
    except Exception as e:
        logger.warning("Error sending audit event synchronously", error=str(e))
        return False


# Get environment variable with default
def get_env_var(key: str, default: Optional[str] = None) -> str:
    return os.getenv(key, default) or ""


# Determine agent based on work item characteristics
def determine_agent_type(
    work_item_type: str,
    fields: dict,
    work_item_id: int
) -> str:
    """Determine which agent should handle this work item."""
    from src.models import AgentType, WorkItemType

    # Check for security-related keywords in title/description
    title = fields.get("System.Title", "").lower()
    description = fields.get("System.Description", "").lower() or ""
    security_keywords = ["security", "vulnerability", "auth", "authorization", "permission"]

    if any(keyword in (title + description) for keyword in security_keywords):
        return AgentType.SECURITY_AGENT.value

    # Route based on work item type
    if work_item_type == WorkItemType.BUG.value or work_item_type == WorkItemType.TEST_CASE.value:
        return AgentType.QA_AGENT.value

    # Tasks are typically requirements in context
    if work_item_type == WorkItemType.TASK.value:
        return AgentType.DEV_AGENT.value

    # Release state check
    state = fields.get("System.State", "").lower()
    if "release" in state or "deploy" in title:
        return AgentType.RELEASE_AGENT.value

    # Default to dev agent
    return AgentType.DEV_AGENT.value


# Create audit event for project operations
def create_project_audit_event(
    event_type: str,
    project_name: str,
    project_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    details: Optional[dict] = None
) -> AuditEvent:
    """Create standardized audit event for project operations."""
    correlation_id = correlation_id or generate_correlation_id()
    return AuditEvent(
        correlation_id=correlation_id,
        event_type=event_type,
        project_name=project_name,
        project_id=project_id,
        timestamp=datetime.utcnow().isoformat(),
        details=details
    )


# Create audit event for task routing
def create_routing_audit_event(
    work_item_id: int,
    agent: str,
    old_state: str,
    new_state: str,
    correlation_id: Optional[str] = None,
    details: Optional[dict] = None
) -> AuditEvent:
    """Create standardized audit event for task routing."""
    correlation_id = correlation_id or generate_correlation_id()
    return AuditEvent(
        correlation_id=correlation_id,
        event_type="task_routed",
        work_item_id=work_item_id,
        agent=agent,
        old_state=old_state,
        new_state=new_state,
        timestamp=datetime.utcnow().isoformat(),
        details=details
    )


# Configure startup metrics
def initialize_metrics():
    """Initialize Prometheus metrics for the service."""
    from prometheus_client import Counter, Gauge, start_http_server
    import time

    # Metrics initialization
    global PROJECTS_CREATED, TASKS_ROUTED, ROUTING_FAILURES, BOOTSTRAP_FAILURES, UPTIME_START

    PROJECTS_CREATED = Counter('orchestrator_projects_created_total',
                             'Total projects created by orchestrator')
    TASKS_ROUTED = Counter('orchestrator_tasks_routed_total',
                         'Total tasks routed to agents', ['agent'])
    ROUTING_FAILURES = Counter('orchestrator_routing_failures_total',
                             'Total routing failures')
    BOOTSTRAP_FAILURES = Counter('orchestrator_bootstrap_failures_total',
                               'Total bootstrap failures')
    UPTIME_START = time.time()


def get_metrics_data():
    """Get current metrics data."""
    return {
        "projects_created_total": PROJECTS_CREATED._value,
        "tasks_routed_total": {
            label: counter._value
            for label, counter in TASKS_ROUTED._metrics.items()
        } if hasattr(TASKS_ROUTED, '_metrics') else {},
        "routing_failures_total": ROUTING_FAILURES._value,
        "bootstrap_failures_total": BOOTSTRAP_FAILURES._value,
        "uptime_seconds": time.time() - UPTIME_START
    }


# Initialize startup time
UPTIME_START = time.time()
