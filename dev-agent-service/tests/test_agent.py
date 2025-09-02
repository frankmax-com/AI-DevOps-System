import pytest
from unittest.mock import patch, MagicMock
from src.agent import process_dev_task, validate_cmme_links, simulate_development_time
from src.models import TaskStatus, WorkStartRequest
import time


@pytest.fixture
def mock_clients():
    """Mock Azure DevOps and GitHub clients."""
    mock_ado = MagicMock()
    mock_github = MagicMock()
    return mock_ado, mock_github


def test_simulate_development_time():
    """Test development time simulation."""
    start_time = time.time()
    simulate_development_time()
    end_time = time.time()
    # Should take between 5-15 seconds
    assert 5 <= (end_time - start_time) <= 15


def test_validate_cmme_links_success(mock_clients):
    """Test successful CMMI validation."""
    mock_ado, mock_github = mock_clients

    # Mock links with a Requirement
    mock_link = MagicMock()
    mock_link.rel = "System.LinkTypes.Hierarchy-Reverse"
    mock_link.attributes = {"name": "Requirement"}
    mock_ado.get_links.return_value = [mock_link]

    result = validate_cmme_links(mock_ado, 123)
    assert result is True
    mock_ado.get_links.assert_called_once_with(123)


def test_validate_cmme_links_missing_requirement(mock_clients):
    """Test CMMI validation failure when no Requirement link."""
    mock_ado, mock_github = mock_clients

    # Mock links without Requirement
    mock_link = MagicMock()
    mock_link.rel = "System.LinkTypes.Hierarchy-Forward"
    mock_link.attributes = {"name": "Bug"}
    mock_ado.get_links.return_value = [mock_link]

    result = validate_cmme_links(mock_ado, 123)
    assert result is False


@patch('src.agent.create_clients')
@patch('src.agent.update_task_status')
def test_process_dev_task_success(mock_update_status, mock_create_clients, mock_clients):
    """Test successful dev task processing."""
    mock_ado, mock_github = mock_clients
    mock_create_clients.return_value = mock_clients

    # Mock successful validation
    mock_link = MagicMock()
    mock_link.rel = "System.LinkTypes.Hierarchy-Reverse"
    mock_link.attributes = {"name": "Requirement"}
    mock_ado.get_links.return_value = [mock_link]

    # Mock repo operations
    mock_repo = MagicMock()
    mock_github.get_repo.return_value = mock_repo
    mock_branch = MagicMock()
    mock_repo.get_branch.return_value = mock_branch
    mock_pr = MagicMock()
    mock_repo.create_pull.return_value = mock_pr

    task_data = {
        "task_id": "DEV-001",
        "repository": "https://github.com/org/repo",
        "branch": "main",
        "azure_workitem_id": 123,
        "requirements": "Implement feature"
    }

    with patch('src.agent.simulate_development_time'):
        process_dev_task(task_data, "test-correlation-id")

    # Verify status updates were called for each state
    update_task_status.called_args_list = [
        ((mock_ado, WorkStartRequest(**task_data), "test-correlation-id", None, TaskStatus.VALIDATING), {}),
        ((mock_ado, WorkStartRequest(**task_data), "test-correlation-id", TaskStatus.VALIDATING, TaskStatus.SETUP), {}),
        ((mock_ado, WorkStartRequest(**task_data), "test-correlation-id", TaskStatus.SETUP, TaskStatus.CODING), {}),
        ((mock_ado, WorkStartRequest(**task_data), "test-correlation-id", TaskStatus.CODING, TaskStatus.COMMITTING), {}),
        ((mock_ado, WorkStartRequest(**task_data), "test-correlation-id", TaskStatus.COMMITTING, TaskStatus.PR_CREATED), {}),
        ((mock_ado, WorkStartRequest(**task_data), "test-correlation-id", TaskStatus.PR_CREATED, TaskStatus.COMPLETED), {}),
    ]

    assert mock_update_status.call_count == 6

    # Verify interactions
    mock_github.create_branch.assert_called_once_with(mock_repo, "main", "dev-dev-001")
    mock_repo.create_file.assert_called()  # Mocked file creation
    mock_repo.create_pull.assert_called()


@patch('src.agent.create_clients')
@patch('src.agent.update_task_status')
def test_process_dev_task_cmme_validation_fail(mock_update_status, mock_create_clients, mock_clients):
    """Test task processing with CMMI validation failure."""
    mock_ado, mock_github = mock_clients
    mock_create_clients.return_value = mock_clients

    # Mock validation failure
    mock_ado.get_links.return_value = []  # No links

    task_data = {
        "task_id": "DEV-001",
        "repository": "https://github.com/org/repo",
        "branch": "main",
        "azure_workitem_id": 123,
        "requirements": "Implement feature"
    }

    process_dev_task(task_data, "test-correlation-id")

    # Verify comment was added and state updated to blocked
    mock_ado.create_comment.assert_called_once_with(
        123,
        "Missing traceability links: please link to Feature/Requirement"
    )
    mock_ado.update_state.assert_called_once_with(123, "Blocked")
    mock_update_status.assert_any_call(
        mock_ado,
        WorkStartRequest(**task_data),
        "test-correlation-id",
        TaskStatus.VALIDATING,
        TaskStatus.BLOCKED
    )


@patch('src.agent.create_clients')
def test_process_dev_task_exception_handling(mock_create_clients, mock_clients):
    """Test exception handling in dev task processing."""
    mock_ado, mock_github = mock_clients
    mock_create_clients.return_value = mock_clients
    mock_ado.get_links.side_effect = Exception("Azure DevOps error")

    task_data = {
        "task_id": "DEV-001",
        "repository": "https://github.com/org/repo",
        "branch": "main",
        "azure_workitem_id": 123,
        "requirements": "Implement feature"
    }

    with patch('src.agent.logger', new_callable=MagicMock) as mock_logger:
        with patch('src.agent.update_task_status') as mock_update_status:
            process_dev_task(task_data, "test-correlation-id")

            mock_logger.error.assert_called()
            # Should call update_status with FAILED
            mock_update_status.assert_any_call(
                mock_ado,
                WorkStartRequest(**task_data),
                "test-correlation-id",
                None,  # Old status
                TaskStatus.FAILED
            )


def test_validate_cmme_links_with_no_attributes(mock_clients):
    """Test validation when link has no attributes."""
    mock_ado, mock_github = mock_clients

    # Mock link without attributes
    mock_link = MagicMock()
    mock_link.rel = "System.LinkTypes.Hierarchy-Reverse"
    mock_link.attributes = None
    mock_ado.get_links.return_value = [mock_link]

    result = validate_cmme_links(mock_ado, 123)
    assert result is False


def test_validate_cmme_links_with_other_link_types(mock_clients):
    """Test validation with different link types."""
    mock_ado, mock_github = mock_clients

    # Mock various link types excluding Requirement
    links = []
    for link_type in ["Bug", "Feature", "Epic", "Task"]:
        mock_link = MagicMock()
        mock_link.rel = "System.LinkTypes.Hierarchy-Forward"
        mock_link.attributes = {"name": link_type}
        links.append(mock_link)

    mock_ado.get_links.return_value = links
    result = validate_cmme_links(mock_ado, 123)
    assert result is False
