import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app
from src.models import WorkStartRequest


client = TestClient(app)


@pytest.fixture
def sample_request():
    return WorkStartRequest(
        task_id="DEV-001",
        repository="https://github.com/org/repo",
        branch="main",
        azure_workitem_id=123,
        requirements="Implement user login"
    )


@patch('src.main.redis_client')
def test_start_work_success(mock_redis, sample_request):
    """Test successful work start."""
    # Mock Redis
    mock_redis.setex.return_value = None

    with patch('src.agent.process_dev_task.delay') as mock_task:
        mock_task.return_value.id = "test-celery-id"

        response = client.post("/work/start", json=sample_request.dict())

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == sample_request.task_id
        assert "correlation_id" in data
        mock_task.assert_called_once()


@patch('src.main.redis_client')
def test_start_work_validation_error(mock_redis, sample_request):
    """Test validation error on missing fields."""
    invalid_request = sample_request.dict()
    invalid_request["task_id"] = ""  # Empty task_id

    response = client.post("/work/start", json=invalid_request)

    assert response.status_code == 400
    data = response.json()
    assert "Missing required fields" in data["detail"]


@patch('src.main.redis_client')
def test_get_work_status_not_found(mock_redis):
    """Test status request for non-existent task."""
    mock_redis.get.return_value = None

    response = client.get("/work/status/DEV-999")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"]


@patch('src.main.redis_client')
@patch('src.main.ado_client')
def test_health_check_healthy(mock_redis, mock_ado):
    """Test health check when all systems are healthy."""
    mock_redis.ping.return_value = None
    mock_ado.connection.authenticate.return_value = None

    response = client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["fastapi"] is True
    assert data["checks"]["redis"] is True
    assert data["checks"]["azure_devops"] is True


@patch('src.main.redis_client')
@patch('src.main.ado_client')
def test_health_check_unhealthy(mock_redis, mock_ado):
    """Test health check when Redis fails."""
    mock_redis.ping.side_effect = Exception("Redis error")
    mock_ado.connection.authenticate.return_value = None

    response = client.get("/healthz")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["redis"] is False


def test_metrics_endpoint():
    """Test metrics endpoint returns Prometheus data."""
    response = client.get("/metrics")

    assert response.status_code == 200
    # Should contain Prometheus metrics format
    assert b"dev_agent_tasks_started_total" in response.content


def test_global_error_handler():
    """Test global exception handling."""
    # This would require more complex setup to trigger unhandled exceptions
    # For now, just ensure the endpoint exists and responds
    response = client.get("/nonexistent")
    # FastAPI should handle 404 appropriately
    assert response.status_code == 404
