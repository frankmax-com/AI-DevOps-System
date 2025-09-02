import os
import time
from typing import List, Optional
from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking.models import WorkItem
from azure.devops.v7_1.work_item_tracking.models import WorkItemUpdate
from azure.devops.v7_1.work_item_tracking.models import JsonPatchOperation
from msrest.authentication import BasicTokenAuthentication
from azure.devops.exceptions import AzureDevOpsServiceError
import structlog


class AzureDevOpsClient:
    def __init__(self, organization_url: str, personal_access_token: str, project_name: str):
        self.organization_url = organization_url
        self.project_name = project_name
        self.logger = structlog.get_logger()
        self.connection = Connection(base_url=organization_url,
                                   creds=BasicTokenAuthentication({'personal_access_token': personal_access_token}))
        self.wit_client = self.connection.clients.get_work_item_tracking_client()

    def _retry_with_backoff(self, func, max_attempts=3, backoff_factor=2):
        """Generic retry with exponential backoff."""
        attempt = 0
        wait_time = 1
        while attempt < max_attempts:
            try:
                return func()
            except AzureDevOpsServiceError as e:
                if e.status >= 500:  # Server error
                    attempt += 1
                    self.logger.warning("Azure DevOps API error, retrying", attempt=attempt, error=str(e), wait_time=wait_time)
                    time.sleep(wait_time)
                    wait_time *= backoff_factor
                elif e.status == 429:  # Rate limit
                    attempt += 1
                    self.logger.warning("Rate limit hit, retrying", attempt=attempt, error=str(e), wait_time=wait_time*2)
                    time.sleep(wait_time * 2)
                    wait_time *= backoff_factor
                elif e.status in [401, 403]:
                    self.logger.error("Authentication error", error=str(e))
                    raise
                else:
                    self.logger.error("Non-retryable Azure DevOps error", error=str(e))
                    raise
            except Exception as e:
                attempt += 1
                if attempt >= max_attempts:
                    self.logger.error("Max retries exceeded", error=str(e))
                    raise
                time.sleep(wait_time)
                wait_time *= backoff_factor
        raise Exception("Max retries exceeded")

    def create_comment(self, work_item_id: int, text: str):
        """Add a comment to a work item."""
        def _add_comment():
            document = JsonPatchOperation()
            document.op = "add"
            document.path = "/fields/System.History"
            document.value = text
            return self.wit_client.update_work_item(document=document,
                                                  project=self.project_name,
                                                  id=work_item_id)
        return self._retry_with_backoff(_add_comment)

    def update_state(self, work_item_id: int, state: str):
        """Update work item state."""
        def _update_state():
            document = JsonPatchOperation()
            document.op = "add"
            document.path = "/fields/System.State"
            document.value = state
            return self.wit_client.update_work_item(document=document,
                                                  project=self.project_name,
                                                  id=work_item_id)
        return self._retry_with_backoff(_update_state)

    def get_links(self, work_item_id: int) -> List[dict]:
        """Get work item relations (links)."""
        def _get_links():
            work_item = self.wit_client.get_work_item(id=work_item_id, project=self.project_name)
            return work_item.relations or []
        return self._retry_with_backoff(_get_links)

    def get_work_item(self, work_item_id: int) -> dict:
        """Get work item details."""
        def _get_item():
            work_item = self.wit_client.get_work_item(id=work_item_id, project=self.project_name)
            return {
                'id': work_item.id,
                'fields': work_item.fields or {}
            }
        return self._retry_with_backoff(_get_item)
