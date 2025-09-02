import pytest
from unittest.mock import patch, MagicMock
from src.github import GitHubClient
from github.GithubException import GithubException


@pytest.fixture
def github_client():
    with patch('github.Github'):
        client = GitHubClient(access_token="token")
    return client


def test_get_repo_success(github_client):
    """Test successful repository retrieval."""
    mock_repo = MagicMock()
    github_client.github.get_repo.return_value = mock_repo

    result = github_client.get_repo("org/repo")
    github_client.github.get_repo.assert_called_once_with("org/repo")
    assert result == mock_repo


def test_create_branch_success(github_client):
    """Test successful branch creation."""
    mock_repo = MagicMock()
    mock_base_ref = MagicMock()
    mock_base_ref.object.sha = "sha123"
    mock_repo.get_git_ref.return_value = mock_base_ref
    mock_repo.create_git_ref.return_value = None
    mock_new_branch = MagicMock()
    mock_repo.get_branch.return_value = mock_new_branch

    result = github_client.create_branch(mock_repo, "main", "feature-branch")
    mock_repo.get_git_ref.assert_called_once_with("heads/main")
    mock_repo.create_git_ref.assert_called_once_with(ref="refs/heads/feature-branch", sha="sha123")
    assert result == mock_new_branch


def test_create_branch_retry_on_500(github_client):
    """Test retry on server error."""
    mock_repo = MagicMock()
    mock_repo.get_git_ref.side_effect = [
        GithubException(MagicMock(status=500), "Internal Server Error"),
        MagicMock(object=MagicMock(sha="sha123"))  # Success on retry
    ]
    mock_repo.get_branch.return_value = MagicMock()

    with patch('time.sleep'):
        result = github_client.create_branch(mock_repo, "main", "feature-branch")
        # Should be called twice - once failed, once successful
        assert mock_repo.get_git_ref.call_count == 2


def test_create_branch_rate_limit_retry(github_client):
    """Test retry on rate limit error."""
    mock_repo = MagicMock()
    mock_repo.get_git_ref.side_effect = [
        GithubException(MagicMock(status=403), '{"message":"API rate limit exceeded"}'),
        MagicMock(object=MagicMock(sha="sha123"))  # Success on retry
    ]
    mock_repo.get_branch.return_value = MagicMock()

    with patch('time.sleep') as mock_sleep:
        result = github_client.create_branch(mock_repo, "main", "feature-branch")
        assert mock_repo.get_git_ref.call_count == 2
        mock_sleep.call_count >= 1  # Sleep called


def test_commit_file_create_new(github_client):
    """Test creating a new file."""
    mock_repo = MagicMock()
    mock_repo.get_contents.side_effect = GithubException(MagicMock(status=404), "Not Found")
    mock_repo.create_file.return_value = MagicMock()

    result = github_client.commit_file(mock_repo, "main", "new_file.txt", "Hello World", "Add new file")

    mock_repo.get_contents.assert_called_once_with("new_file.txt", ref="main")
    mock_repo.create_file.assert_called_once_with(
        path="new_file.txt",
        message="Add new file",
        content="Hello World",
        branch="main"
    )


def test_commit_file_update_existing(github_client):
    """Test updating an existing file."""
    mock_repo = MagicMock()
    mock_file = MagicMock()
    mock_file.sha = "old_sha"
    mock_repo.get_contents.return_value = mock_file
    mock_repo.update_file.return_value = MagicMock()

    result = github_client.commit_file(mock_repo, "main", "existing_file.txt", "Updated content", "Update file")

    mock_repo.get_contents.assert_called_once_with("existing_file.txt", ref="main")
    mock_repo.update_file.assert_called_once_with(
        path="existing_file.txt",
        message="Update file",
        content="Updated content",
        sha="old_sha",
        branch="main"
    )


def test_create_pull_request_success(github_client):
    """Test successful pull request creation."""
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.number = 1
    mock_pr.title = "Test PR"
    mock_repo.create_pull.return_value = mock_pr

    result = github_client.create_pull_request(
        mock_repo, "feature-branch", "main", "Test PR", "Description"
    )

    mock_repo.create_pull.assert_called_once_with(
        title="Test PR",
        body="Description",
        head="feature-branch",
        base="main"
    )
    assert result == mock_pr


def test_create_pull_request_auth_failure(github_client):
    """Test failure on authorization error."""
    mock_repo = MagicMock()
    mock_repo.create_pull.side_effect = GithubException(MagicMock(status=401), "Unauthorized")

    with pytest.raises(GithubException):
        github_client.create_pull_request(mock_repo, "branch", "main", "Title", "Body")


def test_get_pull_request_success(github_client):
    """Test successful pull request retrieval."""
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.number = 5
    mock_repo.get_pull.return_value = mock_pr

    result = github_client.get_pull_request(mock_repo, 5)
    mock_repo.get_pull.assert_called_once_with(5)
    assert result == mock_pr


def test_max_retries_exceeded(github_client):
    """Test that operations stop after max retries."""
    mock_repo = MagicMock()
    mock_repo.get_repo.side_effect = GithubException(MagicMock(status=500), "Server Error")

    with patch('time.sleep'):
        with pytest.raises(Exception):
            github_client.get_repo("org/repo")

        assert mock_repo.get_repo.call_count == 3  # Max attempts
