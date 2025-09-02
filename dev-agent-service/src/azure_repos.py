import os
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils import get_logger, send_audit_event, get_env_var
from src.models import AuditEvent


class AzureReposClient:
    """Azure Repos REST API client for repository operations with work item linking and tagging."""

    def __init__(
        self,
        organization_url: str,
        project_name: str,
        repository_name: str,
        personal_access_token: str
    ):
        self.organization_url = organization_url.rstrip('/')
        self.project_name = project_name
        self.repository_name = repository_name
        self.personal_access_token = personal_access_token
        self.base_url = f"{self.organization_url}/_apis/git/repositories/{self.repository_name}"
        self.logger = get_logger()

        # Async HTTP session with authentication
        self.session = aiohttp.ClientSession(
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Basic {personal_access_token}'
            }
        )

    async def close(self):
        """Clean up HTTP session."""
        if self.session:
            await self.session.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        api_version: str = "7.0"
    ) -> Dict[str, Any]:
        """Make authenticated request to Azure DevOps REST API."""
        url = f"{self.base_url}{endpoint}"
        if params:
            import urllib.parse
            query_string = urllib.parse.urlencode(params)
            url += f"?{query_string}&api-version={api_version}"
        else:
            url += f"?api-version={api_version}"

        request_kwargs = {
            'method': method.upper(),
            'url': url,
            'headers': {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {self.personal_access_token}'
            }
        }

        if data:
            request_kwargs['json'] = data

        try:
            async with self.session.request(**request_kwargs) as response:
                if response.status >= 400:
                    error_detail = await response.text()
                    self.logger.error(f"Azure Repos API error",
                                    status_code=response.status,
                                    endpoint=endpoint,
                                    error=error_detail)
                    raise Exception(f"Azure Repos API error: HTTP {response.status} - {error_detail}")

                if method.upper() == 'PATCH' or response.status == 204:
                    return {}

                return await response.json()

        except aiohttp.ClientError as e:
            self.logger.error(f"Network error in Azure Repos API",
                            endpoint=endpoint,
                            error=str(e))
            raise Exception(f"Azure Repos network error: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def create_branch(
        self,
        base_branch: str,
        new_branch: str,
        base_commit_id: Optional[str] = None
    ) -> str:
        """
        Create a new branch from base branch.

        Returns: New branch object ID (commit ID)
        """
        # Get base branch reference
        if not base_commit_id:
            refs = await self.get_refs(f"refs/heads/{base_branch}")
            if not refs:
                raise Exception(f"Base branch '{base_branch}' not found")
            base_commit_id = refs[0]['objectId']

        # Create new branch reference
        branch_data = {
            "name": f"refs/heads/{new_branch}",
            "oldObjectId": "0000000000000000000000000000000000000000",
            "newObjectId": base_commit_id
        }

        branch_ref = await self._make_request(
            "POST",
            f"/refs?api-version=7.0",
            data=[branch_data]
        )

        self.logger.info("Branch created",
                        base_branch=base_branch,
                        new_branch=new_branch,
                        commit_id=base_commit_id)

        # Send audit event
        from datetime import datetime
        from src.utils import generate_correlation_id

        audit_event = AuditEvent(
            correlation_id=generate_correlation_id(),
            event_type="branch_created",
            project_name=self.project_name,
            repo_name=self.repository_name,
            timestamp=datetime.utcnow().isoformat(),
            service="dev-agent-service",
            details={
                "base_branch": base_branch,
                "new_branch": new_branch,
                "commit_id": base_commit_id
            }
        )
        await send_audit_event(get_env_var("AUDIT_SERVICE_URL"), audit_event, self.logger)

        return base_commit_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def get_refs(self, filter_ref: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get repository references (branches/tags)."""
        params = {}
        if filter_ref:
            params["filter"] = filter_ref

        result = await self._make_request("GET", "/refs", params=params)
        return result.get("value", [])

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def commit_file(
        self,
        branch: str,
        filename: str,
        content: str,
        message: str,
        work_item_id: Optional[int] = None
    ) -> tuple[str, str]:
        """
        Commit a new file to the repository.

        Returns: (commit_id, commit_url)
        """
        # Enhanced commit message with work item linking
        if work_item_id:
            message = f"{message} (#{work_item_id})"
        else:
            # Try to extract work item ID from message if already present
            import re
            work_item_match = re.search(r'#(\d+)', message)
            if work_item_match:
                work_item_id = int(work_item_match.group(1))

        # Get current branch ref
        branch_ref = f"refs/heads/{branch}"
        refs = await self.get_refs(branch_ref)

        if not refs:
            raise Exception(f"Branch '{branch}' not found")

        # Get latest commit on branch
        latest_commit_id = refs[0]['objectId']
        latest_commit = await self._make_request("GET", f"/commits/{latest_commit_id}")

        # Create change object
        change = {
            "changeType": "add" if filename not in [item['path'] for item in latest_commit.get('changes', [])]
                       else "edit",
            "item": {
                "path": filename
            },
            "newContent": {
                "content": content,
                "contentType": "rawtext"
            }
        }

        # Create commit
        commit_data = {
            "comment": message,
            "changes": [change]
        }

        if work_item_id:
            # Add work item reference if specified
            commit_data["workItems"] = [{"id": str(work_item_id)}]

        commit_result = await self._make_request(
            "POST",
            f"/pushes?api-version=7.0",
            data={
                "refUpdates": [{
                    "name": branch_ref,
                    "oldObjectId": latest_commit_id
                }],
                "commits": [commit_data]
            }
        )

        commit_id = commit_result['commits'][0]['commitId']
        commit_url = f"{self.organization_url}/{self.project_name}/_git/{self.repository_name}/commit/{commit_id}"

        self.logger.info("File committed",
                        filename=filename,
                        branch=branch,
                        commit_id=commit_id,
                        work_item_id=work_item_id)

        # Send audit event
        audit_event = AuditEvent(
            correlation_id=generate_correlation_id(),
            event_type="commit_pushed",
            project_name=self.project_name,
            repo_name=self.repository_name,
            work_item_id=work_item_id,
            timestamp=datetime.utcnow().isoformat(),
            service="dev-agent-service",
            details={
                "filename": filename,
                "branch": branch,
                "commit_id": commit_id,
                "message": message,
                "work_item_linked": work_item_id is not None
            }
        )
        await send_audit_event(get_env_var("AUDIT_SERVICE_URL"), audit_event, self.logger)

        return commit_id, commit_url

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def create_pull_request(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str,
        work_item_id: int,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Create pull request with work item linking and enhanced metadata."""

        # Enhance PR description with audit metadata
        enhanced_description = f"""{description}

## Acceptance Criteria
[Extracted from linked work item]

## Audit Trail
- **Correlation ID**: {correlation_id}
- **Timestamp**: {datetime.utcnow().isoformat()}
- **Service**: dev-agent-service
- **Work Item**: #{work_item_id}

## Automated Changes
- Files committed automatically based on requirements
- All changes include work item references for traceability"""

        pr_data = {
            "sourceRefName": f"refs/heads/{source_branch}",
            "targetRefName": f"refs/heads/{target_branch}",
            "title": title,
            "description": enhanced_description,
            "reviewers": [],
            "completionOptions": {
                "squashMerge": True,
                "deleteSourceBranch": True
            }
        }

        # Add work item link to PR
        if work_item_id:
            pr_data["workItemRefs"] = [{"id": str(work_item_id)}]

        pr_result = await self._make_request(
            "POST",
            f"/pullRequests?api-version=7.0",
            data=pr_data
        )

        pr_id = pr_result['pullRequestId']
        pr_url = f"{self.organization_url}/{self.project_name}/_git/{self.repository_name}/pullrequest/{pr_id}"

        self.logger.info("Pull request created",
                        pr_id=pr_id,
                        source_branch=source_branch,
                        target_branch=target_branch,
                        work_item_id=work_item_id)

        # Send audit event
        audit_event = AuditEvent(
            correlation_id=correlation_id,
            event_type="pr_created",
            project_name=self.project_name,
            repo_name=self.repository_name,
            work_item_id=work_item_id,
            timestamp=datetime.utcnow().isoformat(),
            service="dev-agent-service",
            details={
                "pr_id": pr_id,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title
            }
        )
        await send_audit_event(get_env_var("AUDIT_SERVICE_URL"), audit_event, self.logger)

        return {
            "pullRequestId": pr_id,
            "pullRequestUrl": pr_url,
            "data": pr_result
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def create_tag(
        self,
        commit_id: str,
        tag_name: str,
        work_item_id: Optional[int] = None,
        description: Optional[str] = None
    ) -> str:
        """Create annotated tag for changeset tagging."""

        # Create lightweight tag (can be made annotated later if needed)
        tag_data = {
            "name": tag_name,
            "oldObjectId": "0000000000000000000000000000000000000000",
            "newObjectId": commit_id
        }

        if description:
            tag_data["message"] = description

        tag_result = await self._make_request(
            "POST",
            "/refs?api-version=7.0",
            data=[tag_data]
        )

        self.logger.info("Tag created",
                        tag_name=tag_name,
                        commit_id=commit_id,
                        work_item_id=work_item_id)

        # Send audit event
        audit_event = AuditEvent(
            correlation_id=generate_correlation_id(),
            event_type="tag_created",
            project_name=self.project_name,
            repo_name=self.repository_name,
            work_item_id=work_item_id,
            timestamp=datetime.utcnow().isoformat(),
            service="dev-agent-service",
            details={
                "tag_name": tag_name,
                "commit_id": commit_id,
                "description": description
            }
        )
        await send_audit_event(get_env_var("AUDIT_SERVICE_URL"), audit_event, self.logger)

        return tag_name

    async def get_pull_request(self, pr_id: int) -> Dict[str, Any]:
        """Get pull request details."""
        return await self._make_request("GET", f"/pullRequests/{pr_id}")

    async def get_commit(self, commit_id: str) -> Dict[str, Any]:
        """Get commit details."""
        return await self._make_request("GET", f"/commits/{commit_id}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
