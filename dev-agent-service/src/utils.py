import structlog
import logging
from typing import Any, Dict, Optional
from datetime import datetime
import uuid
import os


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


# Send audit event
def send_audit_event(audit_service_url: str, event_data: Dict[str, Any], logger: Any):
    import requests
    try:
        response = requests.post(f"{audit_service_url}/audit/event", json=event_data, timeout=5)
        if response.status_code != 200:
            logger.warning("Failed to send audit event", status_code=response.status_code)
    except Exception as e:
        logger.warning("Error sending audit event", error=str(e))


# Get environment variable with default
def get_env_var(key: str, default: Optional[str] = None) -> str:
    return os.getenv(key, default)
