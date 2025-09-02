import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime

from src.utils import (
    get_logger,
    generate_correlation_id,
    send_audit_event,
    create_routing_audit_event,
    determine_agent_type,
    get_env_var
)
from src.models import (
    WebhookEvent,
    WorkItemState,
    WorkItemUpdate,
    AgentType,
    TaskRoutingResult,
    AuditEvent
)
from src.azure_devops import AzureDevOpsClient


async def handle_workitem_webhook(event: Dict[str, Any], correlation_id: str):
    """
    Handle Azure DevOps webhook events for work item updates.

    Process workitem.updated and workitem.created events, determine target agent,
    and route task with appropriate state management.
    """
    webhook_logger = get_logger(correlation_id)
    webhook_logger.info("Processing work item webhook", event_type=event.get("eventType"))

    try:
        # Extract work item information from webhook
        resource = event.get("resource", {})
        work_item_id = resource.get("workItemId")
        work_item_type = resource.get("workItemType", "Unknown")
        revision_count = resource.get("rev")

        if not work_item_id:
            webhook_logger.error("No work item ID in webhook event")
            return

        webhook_logger.info("Processing work item update",
                           work_item_id=work_item_id,
                           work_item_type=work_item_type,
                           revision_count=revision_count)

        # Initialize Azure DevOps client
        organization_url = get_env_var("AZURE_DEVOPS_ORG_URL")
        pat = get_env_var("AZURE_DEVOPS_PAT")

        if not organization_url or not pat:
            raise Exception("Missing Azure DevOps configuration")

        ado_client = AzureDevOpsClient(
            organization_url=organization_url,
            personal_access_token=pat
        )

        try:
            # Get current work item details
            work_item = await ado_client.get_work_item(work_item_id)
            fields = work_item.get('fields', {})

            webhook_logger.info("Retrieved work item details",
                               work_item_id=work_item_id,
                               state=fields.get('System.State'),
                               title=fields.get('System.Title', 'No Title'))

            # Determine if this work item should be processed
            if not should_process_workitem(work_item_type, fields):
                webhook_logger.info("Work item skipped (filter criteria not met)",
                                  work_item_id=work_item_id,
                                  work_item_type=work_item_type)
                await ado_client.close()
                return

            # Check if work item is in a routable state
            current_state = fields.get('System.State', '')

            # Determine target agent based on work item characteristics
            target_agent = determine_agent_type(work_item_type, fields, work_item_id)

            webhook_logger.info("Target agent determined",
                               work_item_id=work_item_id,
                               target_agent=target_agent,
                               current_state=current_state)

            # Route task to appropriate agent
            await route_workitem_to_agent(
                work_item_id=work_item_id,
                target_agent=target_agent,
                work_item_data=work_item,
                correlation_id=correlation_id,
                webhook_logger=webhook_logger,
                ado_client=ado_client
            )

        finally:
            await ado_client.close()

    except Exception as e:
        webhook_logger.error("Failed to process work item webhook",
                            work_item_id=work_item_id,
                            error=str(e))


def should_process_workitem(work_item_type: str, fields: Dict[str, Any]) -> bool:
    """Determine if work item should be processed based on type and state."""
    from src.models import WorkItemType

    # Skip certain work item types
    skip_types = ["Test Case", "Test Suite", "Test Plan", "Feature", "Epic"]
    if work_item_type in skip_types:
        return False

    # Skip certain states that don't need agent processing
    skip_states = ["New", "Removed", "Resolved", "Closed", "Done"]
    current_state = fields.get('System.State', '')
    if current_state in skip_states:
        return False

    # Process tasks in development states
    process_states = [
        "Ready for Development",
        "In Progress",
        "Active",
        "Open",
        "Committed",
        "To Do"
    ]

    return current_state in process_states


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60)
)
async def route_workitem_to_agent(
    work_item_id: int,
    target_agent: str,
    work_item_data: Dict[str, Any],
    correlation_id: str,
    webhook_logger,
    ado_client: AzureDevOpsClient
):
    """
    Route work item to target agent service using exponential backoff retry.

    Manages the complete workflow:
    1. Prepare task data for agent
    2. Call agent's endpoint
    3. Handle success/failure
    4. Update work item state
    5. Send audit events
    """
    webhook_logger.info("Routing work item to agent",
                       work_item_id=work_item_id,
                       target_agent=target_agent)

    # Determine agent URL based on target
    agent_url = get_agent_service_url(target_agent)
    task_url = f"{agent_url}/work/start"

    # Prepare task data for agent
    task_data = prepare_task_data(work_item_data)

    # Send audit event for routing start
    old_state = work_item_data.get('fields', {}).get('System.State', '')
    audit_event = create_routing_audit_event(
        work_item_id=work_item_id,
        agent=target_agent,
        old_state=old_state,
        new_state="In Progress",  # Agent will handle the state
        correlation_id=correlation_id
    )
    audit_service_url = get_env_var("AUDIT_SERVICE_URL")
    if audit_service_url:
        await send_audit_event(audit_service_url, audit_event, webhook_logger)

    try:
        # Call agent's work/start endpoint
        routing_result = await call_agent_endpoint(
            task_url,
            work_item_id,
            task_data,
            webhook_logger
        )

        # Update work item with success status
        await update_workitem_after_routing(
            ado_client, work_item_id, "Commited", target_agent,
            f"Routed to {target_agent} (correlation: {correlation_id})",
            webhook_logger
        )

        # Send success audit event
        success_audit = create_routing_audit_event(
            work_item_id=work_item_id,
            agent=target_agent,
            old_state=old_state,
            new_state="Commited",
            correlation_id=correlation_id
        )
        if audit_service_url:
            await send_audit_event(audit_service_url, success_audit, webhook_logger)

        webhook_logger.info("Work item successfully routed to agent",
                          work_item_id=work_item_id,
                          target_agent=target_agent)

        return routing_result

    except Exception as e:
        # Handle routing failure
        error_message = f"Failed to route to {target_agent}: {str(e)}"
        webhook_logger.error("Routing failed",
                           work_item_id=work_item_id,
                           target_agent=target_agent,
                           error=error_message)

        # Update work item to blocked state
        await update_workitem_after_routing(
            ado_client, work_item_id, WorkItemState.BLOCKED.value, target_agent,
            f"Routing failed: {error_message}",
            webhook_logger
        )

        # Send failure audit event
        failure_audit = create_routing_audit_event(
            work_item_id=work_item_id,
            agent=target_agent,
            old_state=old_state,
            new_state=WorkItemState.BLOCKED.value,
            correlation_id=correlation_id,
            details={"error": error_message}
        )
        if audit_service_url:
            await send_audit_event(audit_service_url, failure_audit, webhook_logger)

        raise  # Re-raise to trigger retry logic


async def call_agent_endpoint(
    task_url: str,
    work_item_id: int,
    task_data: Dict[str, Any],
    logger
) -> TaskRoutingResult:
    """Call the agent's work/start endpoint."""
    logger.info("Calling agent endpoint", url=task_url, work_item_id=work_item_id)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                task_url,
                json=task_data,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:

                if response.status == 202:
                    # Accepted - agent will process async
                    response_data = await response.json()
                    correlation_id = response_data.get('correlation_id', generate_correlation_id())

                    logger.info("Agent accepted task",
                               work_item_id=work_item_id,
                               correlation_id=correlation_id,
                               status_code=response.status)

                    return TaskRoutingResult(
                        correlation_id=correlation_id,
                        work_item_id=work_item_id,
                        agent=task_data.get('target_agent', 'unknown'),
                        target_url=task_url,
                        old_state=task_data.get('current_state', ''),
                        new_state="In Progress",
                        success=True,
                        message="Agent accepted task",
                        timestamp=datetime.utcnow()
                    )

                else:
                    error_text = await response.text()
                    logger.error("Agent rejected task",
                               work_item_id=work_item_id,
                               status_code=response.status,
                               error=error_text)
                    raise Exception(f"Agent rejected: HTTP {response.status} - {error_text}")

        except aiohttp.ClientError as e:
            logger.error("Network error calling agent",
                        work_item_id=work_item_id,
                        error=str(e))
            raise Exception(f"Network error: {str(e)}")


def prepare_task_data(work_item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare task data for agent consumption."""
    fields = work_item_data.get('fields', {}).copy()

    # Extract key information
    return {
        "task_id": f"{work_item_data['id']}-{generate_correlation_id()[:8]}",
        "repository": fields.get('System.TeamProject'),  # Usually the project name
        "branch": "main",  # Could be configurable
        "azure_workitem_id": work_item_data['id'],
        "requirements": fields.get('System.Description', ''),
        "work_item_type": work_item_data.get('work_item_type'),
        "current_state": fields.get('System.State'),
        "assigned_to": fields.get('System.AssignedTo'),
        "area_path": fields.get('System.AreaPath'),
        "iteration_path": fields.get('System.IterationPath')
    }


async def update_workitem_after_routing(
    ado_client: AzureDevOpsClient,
    work_item_id: int,
    new_state: str,
    target_agent: str,
    comment: str,
    logger
):
    """Update work item state and add comment after routing."""
    try:
        # Update work item state
        await ado_client.update_work_item_state(
            work_item_id=int(work_item_id),
            state=new_state,
            comment=comment
        )

        logger.info("Work item updated after routing",
                   work_item_id=work_item_id,
                   new_state=new_state)

    except Exception as e:
        logger.error("Failed to update work item after routing",
                    work_item_id=work_item_id,
                    error=str(e))
        # Don't raise - this is secondary to routing success


def get_agent_service_url(agent: str) -> str:
    """Get the base URL for the target agent service."""
    # Service URLs could be configured via environment variables
    # For now, use hardcoded localhost URLs with different ports

    base_urls = {
        AgentType.DEV_AGENT.value: "http://dev-agent-service:8080",
        AgentType.QA_AGENT.value: "http://qa-agent-service:8081",
        AgentType.SECURITY_AGENT.value: "http://security-agent-service:8082",
        AgentType.RELEASE_AGENT.value: "http://release-agent-service:8083"
    }

    # Allow environment overrides
    env_var = f"{agent.replace('-', '_').upper()}_SERVICE_URL"
    return get_env_var(env_var, base_urls.get(agent, "http://unknown-service:8080"))


async def escalate_to_human(
    ado_client: AzureDevOpsClient,
    work_item_id: int,
    reason: str,
    correlation_id: str,
    logger
):
    """Escalate failed routing to human intervention."""
    try:
        comment = f"""
⚠️ AUTOMATED ROUTING FAILED

Reason: {reason}
Correlation ID: {correlation_id}
Timestamp: {datetime.utcnow().isoformat()}

Please review and route this work item manually or contact the development team.
"""

        await ado_client.add_comment(work_item_id, comment)
        await ado_client.update_work_item_state(
            work_item_id, WorkItemState.BLOCKED.value
        )

        logger.info("Escalated to human intervention",
                   work_item_id=work_item_id,
                   reason=reason,
                   correlation_id=correlation_id)

        # Send escalation audit event
        audit_event = AuditEvent(
            correlation_id=correlation_id,
            event_type="routing_escalation",
            work_item_id=work_item_id,
            timestamp=datetime.utcnow().isoformat(),
            service="orchestrator-service",
            details={"reason": reason}
        )

        audit_service_url = get_env_var("AUDIT_SERVICE_URL")
        if audit_service_url:
            await send_audit_event(audit_service_url, audit_event, logger)

    except Exception as e:
        logger.error("Failed to escalate to human intervention",
                    work_item_id=work_item_id,
                    error=str(e))
