import asyncio
import aiohttp
from typing import Optional
from datetime import datetime, timedelta
import json
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils import (
    get_logger,
    send_audit_event,
    create_project_audit_event,
    create_routing_audit_event
)
from src.models import BootstrapResult, ProjectStatus, ProjectCreateRequest, AuditEvent

PROJECT_CREATION_TIMEOUT_MINUTES = 60
PROJECT_CREATION_POLL_INTERVAL_SECONDS = 30


class BootstrapError(Exception):
    """Custom exception for bootstrap failures."""
    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry_error_callback=lambda retry_state: None
)
async def create_project_via_api(
    organization_url: str,
    personal_access_token: str,
    project_name: str,
    process_template_id: Optional[str] = None
) -> str:
    """
    Create Azure DevOps project via REST API.

    Returns: Project ID if successful
    Raises: BootstrapError on failure
    """
    url = f"{organization_url.rstrip('/')}/_apis/projects?api-version=7.0"

    # Determine process template ID
    if not process_template_id:
        # Default to CMMI (requirement for CMMI compliance)
        process_template_id = "27450541-8e31-4150-9947-dc59f998fc01"  # CMMI template

    request_payload = ProjectCreateRequest(
        name=project_name,
        description=f"CMMI Project: {project_name} - Created by Orchestrator Service",
        visibility="private",
        capabilities={
            "versioncontrol": {
                "sourceControlType": "Git"
            },
            "processTemplate": {
                "templateTypeId": process_template_id
            }
        }
    )

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {personal_access_token}'
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url,
                json=request_payload.dict(),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout for creation
            ) as response:

                if response.status == 201:
                    # Project creation initiated
                    response_data = await response.json()
                    return response_data['id']

                elif response.status == 400:
                    error_detail = await response.text()
                    if "already exists" in error_detail.lower():
                        # Project already exists, get its ID
                        await get_existing_project_id(organization_url, personal_access_token, project_name)
                    raise BootstrapError(f"Bad request: {error_detail}")

                elif response.status == 403:
                    raise BootstrapError("Authentication failed - check PAT permissions")

                else:
                    error_text = await response.text()
                    raise BootstrapError(f"HTTP {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            raise BootstrapError(f"Network error during project creation: {str(e)}")


@retry(
    stop=stop_after_attempt(120),  # Poll for up to 60 minutes (30s * 120)
    wait=wait_exponential(multiplier=1, min=PROJECT_CREATION_POLL_INTERVAL_SECONDS, max=60),
    retry_error_callback=lambda retry_state: "timeout"
)
async def wait_for_project_ready(
    organization_url: str,
    personal_access_token: str,
    project_id: str
) -> ProjectStatus:
    """
    Poll project status until it's well-formed or failed.

    Returns: ProjectStatus enum
    """
    url = f"{organization_url.rstrip('/')}/_apis/projects/{project_id}?api-version=7.0"

    headers = {
        'Authorization': f'Basic {personal_access_token}'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=30) as response:

            if response.status == 200:
                project_data = await response.json()
                state = project_data.get('state', 'unknown')

                try:
                    status = ProjectStatus(state)
                except ValueError:
                    # Unknown state, keep polling
                    raise Exception(f"Unknown project state: {state}")

                if status == ProjectStatus.WELLFORMED:
                    return status
                elif status in [ProjectStatus.DELETION_IN_PROGRESS, ProjectStatus.NOTSET]:
                    raise Exception(f"Project creation failed with state: {state}")

                # Still creating, continue polling
                raise Exception("Project creation in progress")

            elif response.status == 404:
                raise Exception("Project not found")
            else:
                raise Exception(f"Failed to check project status: HTTP {response.status}")


async def get_existing_project_id(
    organization_url: str,
    personal_access_token: str,
    project_name: str
) -> str:
    """Get project ID for existing project."""
    url = f"{organization_url.rstrip('/')}/_apis/projects?api-version=7.0"

    headers = {
        'Authorization': f'Basic {personal_access_token}'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status == 200:
                projects = await response.json()
                for project in projects['value']:
                    if project['name'].lower() == project_name.lower():
                        return project['id']

    raise BootstrapError(f"Could not find existing project: {project_name}")


async def bootstrap_project(
    project_name: str,
    organization_url: str,
    personal_access_token: str,
    correlation_id: str
) -> BootstrapResult:
    """
    Complete bootstrap process: create project + wait for readiness + audit events.

    Returns: BootstrapResult with success/failure status
    """
    logger = get_logger(correlation_id)
    audit_service_url = None  # Should be from env

    logger.info("Starting project bootstrap",
               project_name=project_name,
               organization_url=organization_url)

    try:
        # Step 1: Check if project already exists
        try:
            existing_project_id = await get_existing_project_id(
                organization_url, personal_access_token, project_name
            )
            logger.info("Project already exists", project_name=project_name, project_id=existing_project_id)

            # Send audit event for found existing project
            audit_event = create_project_audit_event(
                event_type="project_already_exists",
                project_name=project_name,
                project_id=existing_project_id,
                correlation_id=correlation_id
            )
            if audit_service_url:
                await send_audit_event_async(audit_service_url, audit_event, logger)

            return BootstrapResult(
                success=True,
                project_name=project_name,
                project_id=existing_project_id,
                status=ProjectStatus.WELLFORMED,
                message="Project already exists and is ready for use",
                created_at=datetime.utcnow(),
                correlation_id=correlation_id
            )

        except BootstrapError:
            # Project doesn't exist, proceed with creation
            pass

        # Step 2: Initiate project creation
        logger.info("Creating new project", project_name=project_name)

        # Send audit event for creation start
        audit_event = create_project_audit_event(
            event_type="project_creation_started",
            project_name=project_name,
            correlation_id=correlation_id
        )
        if audit_service_url:
            await send_audit_event_async(audit_service_url, audit_event, logger)

        project_id = await create_project_via_api(
            organization_url, personal_access_token, project_name
        )

        # Send audit event for creation initiated
        audit_event = create_project_audit_event(
            event_type="project_creation_initiated",
            project_name=project_name,
            project_id=project_id,
            correlation_id=correlation_id
        )
        if audit_service_url:
            await send_audit_event_async(audit_service_url, audit_event, logger)

        logger.info("Project creation initiated",
                   project_name=project_name,
                   project_id=project_id)

        # Step 3: Wait for project to be ready
        logger.info("Waiting for project to be ready", project_id=project_id)

        status = await wait_for_project_ready(
            organization_url, personal_access_token, project_id
        )

        # Step 4: Success - send final audit event
        audit_event = create_project_audit_event(
            event_type="project_creation_completed",
            project_name=project_name,
            project_id=project_id,
            correlation_id=correlation_id
        )
        if audit_service_url:
            await send_audit_event_async(audit_service_url, audit_event, logger)

        logger.info("Project bootstrap completed successfully",
                   project_name=project_name,
                   project_id=project_id,
                   status=status.value)

        return BootstrapResult(
            success=True,
            project_name=project_name,
            project_id=project_id,
            status=status,
            message="Project created and configured successfully",
            created_at=datetime.utcnow(),
            correlation_id=correlation_id
        )

    except Exception as e:
        # Failure - send audit event and log error
        error_message = str(e)
        logger.error("Project bootstrap failed",
                    project_name=project_name,
                    error=error_message)

        audit_event = create_project_audit_event(
            event_type="project_creation_failed",
            project_name=project_name,
            correlation_id=correlation_id,
            details={"error": error_message}
        )
        if audit_service_url:
            await send_audit_event_async(audit_service_url, audit_event, logger)

        # Escalate to human intervention if timeout
        if "timeout" in error_message.lower():
            logger.warning("Project creation timeout - escalating to human intervention",
                          project_name=project_name)

            await add_timeout_comment(
                organization_url, personal_access_token,
                project_name, correlation_id, logger
            )

        return BootstrapResult(
            success=False,
            project_name=project_name,
            status=ProjectStatus.NOTSET,
            message=f"Bootstrap failed: {error_message}",
            created_at=datetime.utcnow(),
            correlation_id=correlation_id
        )


async def add_timeout_comment(
    organization_url: str,
    personal_access_token: str,
    project_name: str,
    correlation_id: str,
    logger
):
    """Add a comment to organization/project item about timeout."""
    try:
        # This would interact with Azure DevOps organization API
        # For now, just log the escalation
        logger.warning("Would add escalation comment to Azure DevOps organization",
                      project_name=project_name,
                      correlation_id=correlation_id)
    except Exception as e:
        logger.error("Failed to add escalation comment", error=str(e))
