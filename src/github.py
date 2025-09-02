import time
from typing import Optional
from github import Github
from github.GithubException import GithubException
from github.Repository import Repository
from github.Branch import Branch
import structlog


class GitHubClient:
    def __init__(self, access_token: str):
        self.github = Github(access_token)
        self.logger = structlog.get_logger()

    def _retry_with_backoff(self, func, max_attempts=3, backoff_factor=2):
        """Generic retry with exponential backoff for GitHub API."""
        attempt = 0
        wait_time = 1
        while attempt < max_attempts:
            try:
                return func()
            except GithubException as e:
                if e.status >= 500:  # Server error
                    attempt += 1
                    self.logger.warning("GitHub API error, retrying", attempt=attempt, error=str(e), wait_time=wait_time)
                    time.sleep(wait_time)
                    wait_time *= backoff_factor
                elif e.status == 403 and "rate limit" in str(e).lower():
                    attempt += 1
                    self.logger.warning("GitHub rate limit hit, retrying", attempt=attempt, error=str(e), wait_time=wait_time*2)
                    time.sleep(wait_time * 2)  # Longer wait for rate limits
                    wait_time *= backoff_factor
                elif e.status in [401, 403]:
                    self.logger.error("Unauthorized GitHub access", error=str(e))
                    raise
                else:
                    self.logger.error("Non-retryable GitHub error", error=str(e))
                    raise
            except Exception as e:
                attempt += 1
                if attempt >= max_attempts:
                    self.logger.error("Max retries exceeded for GitHub", error=str(e))
                    raise
                time.sleep(wait_time)
                wait_time *= backoff_factor
        raise Exception("Max retries exceeded for GitHub")

    def get_repo(self, repo_path: str) -> Repository:
        """Get GitHub repository object."""
        def _get_repo():
            return self.github.get_repo(repo_path)
        return self._retry_with_backoff(_get_repo)

    def create_branch(self, repo: Repository, base_branch: str, new_branch: str) -> Branch:
        """Create a new branch from base branch."""
        def _create_branch():
            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_ref.object.sha)
            return repo.get_branch(new_branch)
        return self._retry_with_backoff(_create_branch)

    def commit_file(self, repo: Repository, branch: str, file_path: str, content: str, message: str):
        """Commit a new file or update existing file on a specific branch."""
        def _commit_file():
            try:
                # Get the file if it exists
                file = repo.get_contents(file_path, ref=branch)
                # Update the file
                repo.update_file(
                    path=file_path,
                    message=message,
                    content=content,
                    sha=file.sha,
                    branch=branch
                )
            except GithubException:
                # File doesn't exist, create new
                repo.create_file(
                    path=file_path,
                    message=message,
                    content=content,
                    branch=branch
                )
        return self._retry_with_backoff(_commit_file)

    def create_pull_request(self, repo: Repository, source_branch: str, target_branch: str, title: str, body: str):
        """Create a pull request."""
        def _create_pr():
            return repo.create_pull(
                title=title,
                body=body,
                head=source_branch,
                base=target_branch
            )
        return self._retry_with_backoff(_create_pr)

    def get_pull_request(self, repo: Repository, pr_number: int):
        """Get pull request by number."""
        def _get_pr():
            return repo.get_pull(pr_number)
        return self._retry_with_backoff(_get_pr)
