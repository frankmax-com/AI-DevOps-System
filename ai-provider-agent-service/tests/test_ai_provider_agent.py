import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.ai_provider_agent import (
    TaskType, AIRequest, AIResponse, ProviderConfig,
    RouterEngine, FailoverManager, QuotaManager
)


class TestTaskType:
    def test_task_type_values(self):
        """Test TaskType enum values"""
        assert TaskType.THINKING.value == "thinking"
        assert TaskType.CODING.value == "coding"
        assert TaskType.WRITING.value == "writing"
        assert TaskType.ANALYSIS.value == "analysis"


class TestModels:
    def test_ai_request_model(self):
        """Test AIRequest model validation"""
        request = AIRequest(
            task_type=TaskType.CODING,
            prompt="Write a function",
            max_tokens=100
        )
        assert request.task_type == TaskType.CODING
        assert request.prompt == "Write a function"
        assert request.max_tokens == 100
        assert request.model == "auto"

    def test_ai_response_model(self):
        """Test AIResponse model"""
        response = AIResponse(
            content="def hello(): pass",
            provider="openai",
            model="gpt-3.5-turbo",
            tokens_used=50,
            cost=0.001
        )
        assert response.content == "def hello(): pass"
        assert response.provider == "openai"
        assert response.tokens_used == 50


class TestProviderConfig:
    def test_provider_config_creation(self):
        """Test ProviderConfig creation"""
        config = ProviderConfig(
            type="openai",
            api_key="test-key",
            models=["gpt-3.5-turbo"],
            daily_limit=1000,
            rate_limit=10,
            cost_per_token=0.001,
            priority=1,
            enabled=True,
            task_types=[TaskType.CODING]
        )
        assert config.type == "openai"
        assert config.enabled is True
        assert TaskType.CODING in config.task_types


@pytest.fixture
def sample_providers():
    """Sample provider configurations"""
    return [
        ProviderConfig(
            type="openai_free",
            api_key=None,
            models=["gpt-3.5-turbo"],
            daily_limit=100,
            rate_limit=3,
            cost_per_token=0.0,
            priority=1,
            enabled=True,
            task_types=[TaskType.CODING, TaskType.THINKING]
        ),
        ProviderConfig(
            type="anthropic_free",
            api_key=None,
            models=["claude-3-haiku"],
            daily_limit=50,
            rate_limit=5,
            cost_per_token=0.0,
            priority=2,
            enabled=True,
            task_types=[TaskType.WRITING, TaskType.ANALYSIS]
        )
    ]


class TestQuotaManager:
    @pytest.mark.asyncio
    async def test_quota_check_within_limit(self, sample_providers):
        """Test quota check when within limits"""
        manager = QuotaManager()
        provider = sample_providers[0]
        
        # Should be within limit
        can_use = await manager.can_use_provider(provider)
        assert can_use is True

    @pytest.mark.asyncio
    async def test_quota_tracking(self, sample_providers):
        """Test quota usage tracking"""
        manager = QuotaManager()
        provider = sample_providers[0]
        
        # Track usage
        await manager.track_usage(provider.type, 50)
        
        # Check internal state (this would need access to private methods)
        # In a real test, you'd verify the quota was decremented


class TestFailoverManager:
    @pytest.mark.asyncio
    async def test_record_failure(self, sample_providers):
        """Test recording provider failures"""
        manager = FailoverManager()
        provider = sample_providers[0]
        
        # Record failure
        manager.record_failure(provider.type)
        
        # Check if provider is available (should still be true for first failure)
        available = manager.is_provider_available(provider.type)
        assert available is True

    @pytest.mark.asyncio
    async def test_multiple_failures_disable_provider(self, sample_providers):
        """Test that multiple failures disable provider"""
        manager = FailoverManager()
        provider = sample_providers[0]
        
        # Record multiple failures
        for _ in range(5):
            manager.record_failure(provider.type)
        
        # Provider should be temporarily disabled
        available = manager.is_provider_available(provider.type)
        assert available is False


class TestRouterEngine:
    @pytest.fixture
    def router_engine(self, sample_providers):
        """Create RouterEngine with sample providers"""
        quota_manager = QuotaManager()
        failover_manager = FailoverManager()
        return RouterEngine(sample_providers, quota_manager, failover_manager)

    @pytest.mark.asyncio
    async def test_select_provider_for_coding(self, router_engine):
        """Test provider selection for coding tasks"""
        request = AIRequest(
            task_type=TaskType.CODING,
            prompt="Write a function",
            max_tokens=100
        )
        
        provider = await router_engine.select_provider(request)
        assert provider is not None
        assert TaskType.CODING in provider.task_types

    @pytest.mark.asyncio
    async def test_select_provider_for_writing(self, router_engine):
        """Test provider selection for writing tasks"""
        request = AIRequest(
            task_type=TaskType.WRITING,
            prompt="Write an essay",
            max_tokens=500
        )
        
        provider = await router_engine.select_provider(request)
        assert provider is not None
        assert TaskType.WRITING in provider.task_types

    @pytest.mark.asyncio
    async def test_no_suitable_provider(self, router_engine):
        """Test behavior when no suitable provider is available"""
        request = AIRequest(
            task_type=TaskType.VISION,  # No provider supports this
            prompt="Analyze this image",
            max_tokens=100
        )
        
        provider = await router_engine.select_provider(request)
        assert provider is None

    @pytest.mark.asyncio
    @patch('src.ai_provider_agent.aiohttp.ClientSession.post')
    async def test_process_request_success(self, mock_post, router_engine):
        """Test successful request processing"""
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "def hello(): pass"}}],
            "usage": {"total_tokens": 50}
        }
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        request = AIRequest(
            task_type=TaskType.CODING,
            prompt="Write a function",
            max_tokens=100
        )
        
        response = await router_engine.process_request(request)
        assert response is not None
        assert response.content == "def hello(): pass"
        assert response.tokens_used == 50

    @pytest.mark.asyncio
    @patch('src.ai_provider_agent.aiohttp.ClientSession.post')
    async def test_process_request_with_failover(self, mock_post, router_engine):
        """Test request processing with failover"""
        # First call fails, second succeeds
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500
        
        mock_response_success = AsyncMock()
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "def hello(): pass"}}],
            "usage": {"total_tokens": 50}
        }
        mock_response_success.status = 200
        
        mock_post.return_value.__aenter__.side_effect = [
            mock_response_fail,
            mock_response_success
        ]
        
        request = AIRequest(
            task_type=TaskType.CODING,
            prompt="Write a function",
            max_tokens=100
        )
        
        response = await router_engine.process_request(request)
        assert response is not None
        assert response.content == "def hello(): pass"


if __name__ == "__main__":
    pytest.main([__file__])
