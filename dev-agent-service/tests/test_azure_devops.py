import pytest
from unittest.mock import patch, MagicMock
from src.azure_devops import AzureDevOpsClient
from azure.devops.exceptions import AzureDevOpsServiceError


@pytest.fixture
def azure_client():
    with patch('src.azure_devops.Connection'):
        client = AzureDevOpsClient(
            organization_url="https://dev.azure.com/org",
            personal_access_token="token",
            project_name="project"
        )
    return client


def test_create_comment_success(azure_client):
    """Test successful comment creation."""
    mock_operation = MagicMock()
    mock_operation.op = "add"
    mock_operation.path = "/fields/System.History"
    mock_operation.value = "test comment"

    with patch.object(azure_client.wit_client, 'update_work_item') as mock_update:
        mock_update.return_value = MagicMock()

        result = azure_client.create_comment(123, "test comment")
        mock_update.assert_called_once()


def test_create_comment_retry_on_500(azure_client):
    """Test retry on server error."""
    azure_client.wit_client.update_work_item.side_effect = [
        AzureDevOpsServiceError(MagicMock(status=500), "Internal Server Error"),
        MagicMock()  # Success on retry
    ]

    with patch('time.sleep'):
        result = azure_client.create_comment(123, "test comment")
        # Should be called twice - once failed, once successful
        assert azure_client.wit_client.update_work_item.call_count == 2


def test_create_comment_fail_on_auth_error(azure_client):
    """Test failure on authentication error without retry."""
    azure_client.wit_client.update_work_item.side_effect = AzureDevOpsServiceError(
        MagicMock(status=401), "Unauthorized"
    )

    with pytest.raises(AzureDevOpsServiceError):
        azure_client.create_comment(123, "test comment")


def test_update_state_success(azure_client):
    """Test successful state update."""
    with patch.object(azure_client.wit_client, 'update_work_item') as mock_update:
        mock_update.return_value = MagicMock()

        result = azure_client.update_state(123, "Done")
        mock_update.assert_called_once()


def test_update_state_rate_limit_retry(azure_client):
    """Test retry on rate limit."""
    azure_client.wit_client.update_work_item.side_effect = [
        AzureDevOpsServiceError(MagicMock(status=429), "Rate limited"),
        MagicMock()  # Success on retry
    ]

    with patch('time.sleep') as mock_sleep:
        result = azure_client.update_state(123, "Done")
        assert azure_client.wit_client.update_work_item.call_count == 2
        mock_sleep.call_count >= 1  # Sleep called at least once


def test_get_links_success(azure_client):
    """Test successful link retrieval."""
    mock_work_item = MagicMock()
    mock_work_item.relations = [
        MagicMock(rel="System.LinkTypes.Hierarchy-Forward", attributes={"name": "Child"}),
        MagicMock(rel="System.LinkTypes.Hierarchy-Reverse", attributes={"name": "Parent"})
    ]

    azure_client.wit_client.get_work_item.return_value = mock_work_item

    links = azure_client.get_links(123)
    assert len(links) == 2


def test_get_work_item_success(azure_client):
    """Test successful work item retrieval."""
    mock_work_item = MagicMock()
    mock_work_item.id = 123
    mock_work_item.fields = {"System.State": "New", "System.Title": "Test Task"}

    azure_client.wit_client.get_work_item.return_value = mock_work_item

    result = azure_client.get_work_item(123)
    assert result["id"] == 123
    assert result["fields"]["System.State"] == "New"


def test_get_work_item_no_links(azure_client):
    """Test get links when no relations exist."""
    mock_work_item = MagicMock()
    mock_work_item.relations = None

    azure_client.wit_client.get_work_item.return_value = mock_work_item

    links = azure_client.get_links(123)
    assert links == []


def test_generic_retry_max_attempts(azure_client):
    """Test that retry stops after max attempts."""
    azure_client.wit_client.get_work_item.side_effect = AzureDevOpsServiceError(
        MagicMock(status=500), "Server Error"
    )

    with patch('time.sleep'):
        with pytest.raises(Exception):
            azure_client.get_work_item(123)

        assert azure_client.wit_client.get_work_item.call_count == 3  # Max attempts
