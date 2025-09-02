from celery import Celery
from typing import Dict, Optional
from datetime import datetime
from src.models import TaskStatus, WorkStartRequest, AuditEvent
from src.azure_devops import AzureDevOpsClient
from src.github import GitHubClient
from src.utils import get_logger, send_audit_event, get_env_var
import structlog
import uuid
import time
import random


# Celery app configuration
app = Celery(
    'dev_agent',
    broker=get_env_var('REDIS_URL', 'redis://localhost:6379/0'),
    backend=get_env_var('REDIS_URL', 'redis://localhost:6379/0')
)
app.conf.worker_prefetch_multiplier = 1  # Handle tasks in order


def create_clients():
    """Create Azure DevOps and GitHub clients from environment variables."""
    ado_client = AzureDevOpsClient(
        organization_url=get_env_var('AZURE_DEVOPS_ORG_URL'),
        personal_access_token=get_env_var('AZURE_DEVOPS_PAT'),
        project_name=get_env_var('AZURE_DEVOPS_PROJECT')
    )
    github_client = GitHubClient(access_token=get_env_var('GITHUB_TOKEN'))
    return ado_client, github_client


def validate_cmme_links(ado_client: AzureDevOpsClient, work_item_id: int) -> bool:
    """Validate that task links to Requirement → Feature → Epic."""
    logger = structlog.get_logger()
    logger.info("Validating CMMI links for work item", work_item_id=work_item_id)

    links = ado_client.get_links(work_item_id)
    task_links = [link for link in links if link.rel in ['System.LinkTypes.Hierarchy-Forward', 'System.LinkTypes.Hierarchy-Reverse']]

    has_requirement = any('Requirement' in (link.attributes.get('name', '') if link.attributes else '') for link in task_links)
    if not has_requirement:
        logger.warning("No Requirement link found for task", work_item_id=work_item_id)
        return False

    # For simplicity, assume Feature and Epic exist if Requirement exists
    # In production, you'd need to traverse the hierarchy
    return True


def simulate_development_time() -> None:
    """Simulate coding time (5-15 seconds)."""
    time.sleep(random.uniform(5, 15))


@app.task(bind=True)
def process_dev_task(self, task_data: Dict, correlation_id: str):
    """Celery task for processing dev work."""
    logger = get_logger(correlation_id)
    logger.info("Starting dev task processing", task_id=task_data['task_id'])

    # Clients
    ado_client, github_client = create_clients()
    task = WorkStartRequest(**task_data)

    current_status = None
    new_status = TaskStatus.VALIDATING

    try:
        # Validate and update status
        update_task_status(logger, ado_client, task, correlation_id, current_status, new_status)
        current_status = new_status

        # CMMI Validation
        if not validate_cmme_links(ado_client, task.azure_workitem_id):
            logger.warning("CMMI validation failed", task_id=task.task_id)
            ado_client.create_comment(
                task.azure_workitem_id,
                "Missing traceability links: please link to Feature/Requirement"
            )
            ado_client.update_state(task.azure_workitem_id, "Blocked")
            update_task_status(logger, ado_client, task, correlation_id, current_status, TaskStatus.BLOCKED)
            return

        # Setup phase
        update_task_status(logger, ado_client, task, correlation_id, current_status, TaskStatus.SETUP)
        current_status = TaskStatus.SETUP

        # Coding simulation
        update_task_status(logger, ado_client, task, correlation_id, current_status, TaskStatus.CODING)
        current_status = TaskStatus.CODING
        simulate_development_time()

        # Commit to GitHub
        update_task_status(logger, ado_client, task, correlation_id, current_status, TaskStatus.COMMITTING)
        current_status = TaskStatus.COMMITTING

        repo = github_client.get_repo(task.repository.split('/')[-1])  # Extract org/repo
        branch_name = f"dev-{task.task_id.lower()}"
        github_client.create_branch(repo, task.branch, branch_name)

        # Simulate code changes
        files_to_create = [
            ("sample_code.py", "# Sample code\nimport os\nprint('Hello World')"),
            ("README.md", f"# Feature for {task.task_id}\n\n{task.requirements or 'No requirements specified.'}")
        ]

        for filename, content in files_to_create:
            github_client.commit_file(repo, branch_name, filename, content,
                                    f"Implement {task.task_id}: {filename}")

        # Create PR
        update_task_status(logger, ado_client, task, correlation_id, current_status, TaskStatus.PR_CREATED)
        current_status = TaskStatus.PR_CREATED

        pr_title = f"Implement {task.task_id}"
        pr_body = f"Requirements: {task.requirements or 'See task details'}\n\nCloses #{task.task_id}"
        pr = github_client.create_pull_request(repo, branch_name, task.branch, pr_title, pr_body)

        # Wait for PR to be merged (in real scenario, this would be polled)
        # For simulation, just mark complete after short wait
        time.sleep(2)

        # Complete
        update_task_status(logger, ado_client, task, correlation_id, current_status, TaskStatus.COMPLETED)
        current_status = TaskStatus.COMPLETED

        ado_client.update_state(task.azure_workitem_id, "Done")

        logger.info("Task completed successfully", task_id=task.task_id)

    except Exception as e:
        logger.error("Task failed", task_id=task.task_id, error=str(e))
        update_task_status(logger, ado_client, task, correlation_id, current_status, TaskStatus.FAILED)


def update_task_status(logger, ado_client, task, correlation_id, old_status, new_status):
    """Helper to update status and send audit event."""
    audit_event = AuditEvent(
        correlation_id=correlation_id,
        task_id=task.task_id,
        work_item_id=task.azure_workitem_id,
        old_state=old_status,
        new_state=new_status,
        timestamp=datetime.utcnow().isoformat()
    )

    # Send audit event
    audit_service_url = get_env_var('AUDIT_SERVICE_URL', 'http://localhost:8001')
    send_audit_event(audit_service_url, audit_event.dict(), logger)

    # Log state change
    logger.info("Task status changed", task_id=task.task_id, old_status=old_status, new_status=new_status)
