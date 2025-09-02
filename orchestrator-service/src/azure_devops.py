import httpx
import asyncio
from typing import Optional, Dict, Any, List
from uptime import boottime  # type: ignore
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils import get_logger, generate_correlation_id, get_env_var
from src.models import (
    ProjectStatus,
    WorkItemState,
    WebhookEvent,
    WorkItemUpdate,
    AuditEvent
)


class AzureDevOpsClient:
    """Azure DevOps client for orchestrator operations with administrative privileges."""

    def __init__(
        self,
        organization_url: str,
        personal_access_token: str,
        project_name: Optional[str] = None
    ):
        self.organization_url = organization_url.rstrip('/')
        self.project_name = project_name
        self.personal_access_token = personal_access_token
        self.logger = get_logger()

        # Async HTTP client for concurrent operations
        self.client = httpx.AsyncClient(
            base_url=self.organization_url,
            headers=self._get_headers(),
            timeout=30.0
        )

    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for Azure DevOps API calls."""
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {self.personal_access_token}'
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make authenticated HTTP request to Azure DevOps API."""
        url = f"{self.organization_url}/{endpoint.lstrip('/')}"

        request_kwargs = {
            'method': method.upper(),
            'url': url,
            'headers': self._get_headers()
        }

        if data:
            request_kwargs['json'] = data
        if params:
            request_kwargs['params'] = params

        response = await self.client.request(**request_kwargs)

        if response.status_code >= 400:
            error_detail = response.text
            self.logger.error("Azure DevOps API error",
                            status_code=response.status_code,
                            endpoint=endpoint,
                            error=error_detail)
            raise Exception(f"Azure DevOps API error: HTTP {response.status_code} - {error_detail}")

        return response.json()

    async def get_project_status(self, project_name: str) -> str:
        """
        Get the provisioning status of a project.

        Returns: ProjectStatus enum value
        """
        try:
            endpoint = f"_apis/projects/{project_name}?api-version=7.0"
            result = await self._make_request("GET", endpoint)

            status = result.get('state', 'missing')
            return status

        except Exception as e:
            # Assume missing if not found or error
            return ProjectStatus.MISSING.value

    async def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects in the organization."""
        try:
            endpoint = "_apis/projects?api-version=7.0"
            result = await self._make_request("GET", endpoint)

            return result.get('value', [])

        except Exception as e:
            self.logger.error("Failed to list projects", error=str(e))
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def create_project(
        self,
        name: str,
        description: str,
        process_template_id: Optional[str] = None
    ) -> str:
        """Create a new project with specified process template."""
        if not process_template_id:
            # Default to CMMI process template for compliance
            process_template_id = "27450541-8e31-4150-9947-dc59f998fc01"

        endpoint = "_apis/projects?api-version=7.0"

        payload = {
            "name": name,
            "description": description,
            "visibility": "private",
            "capabilities": {
                "versioncontrol": {
                    "sourceControlType": "Git"
                },
                "processTemplate": {
                    "templateTypeId": process_template_id
                }
            }
        }

        result = await self._make_request("POST", endpoint, data=payload)
        return result['id']

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def update_work_item_state(
        self,
        work_item_id: int,
        state: WorkItemState,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update work item state and optionally add comment."""
        operations = []

        if comment:
            operations.append({
                "op": "add",
                "path": "/fields/System.History",
                "value": comment
            })

        if state.value != "Existing":  # Only update if it's an actual state change
            operations.append({
                "op": "add",
                "path": "/fields/System.State",
                "value": state.value
            })

        endpoint = f"_apis/wit/workitems/{work_item_id}?api-version=7.0"

        return await self._make_request("PATCH", endpoint, data=operations)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def get_work_item(self, work_item_id: int) -> Dict[str, Any]:
        """Get work item details including fields and relations."""
        endpoint = f"_apis/wit/workitems/{work_item_id}?api-version=7.0&$expand=all"

        result = await self._make_request("GET", endpoint)

        # Extract useful information
        return {
            'id': result['id'],
            'fields': result['fields'],
            'relations': result.get('relations', []),
            'url': result['url'],
            'work_item_type': result['fields'].get('System.WorkItemType', 'Unknown')
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def add_comment(self, work_item_id: int, comment: str) -> Dict[str, Any]:
        """Add a comment to a work item."""
        endpoint = f"_apis/wit/workitems/{work_item_id}?api-version=7.0"

        operations = [{
            "op": "add",
            "path": "/fields/System.History",
            "value": comment
        }]

        return await self._make_request("PATCH", endpoint, data=operations)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def get_work_item_links(self, work_item_id: int) -> List[Dict[str, Any]]:
        """Get work item relations/links for CMMI validation."""
        try:
            work_item = await self.get_work_item(work_item_id)
            return work_item.get('relations', [])
        except Exception as e:
            self.logger.error("Failed to get work item links",
                            work_item_id=work_item_id,
                            error=str(e))
            return []

    async def close(self):
        """Close the HTTP client session."""
        if self.client:
            await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
