"""
API Integration Tests for Database Governance Factory
Tests the FastAPI endpoints in containerized environment
"""

import pytest
import httpx
import asyncio
import json
import time
from typing import Dict, Any

class TestAPIIntegration:
    """Test API endpoints with real database connections"""
    
    BASE_URL = "http://test-api:8080"
    
    @pytest.fixture
    async def client(self):
        """Create HTTP client for API testing"""
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=30.0) as client:
            # Wait for API to be ready
            for _ in range(10):
                try:
                    response = await client.get("/health")
                    if response.status_code == 200:
                        break
                except Exception:
                    pass
                await asyncio.sleep(2)
            
            yield client
    
    async def test_health_endpoint(self, client: httpx.AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    async def test_list_databases(self, client: httpx.AsyncClient):
        """Test database listing endpoint"""
        response = await client.get("/api/v1/databases")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Should have configured database connections
        
    async def test_database_status(self, client: httpx.AsyncClient):
        """Test database status endpoint"""
        response = await client.get("/api/v1/databases/status")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "databases" in data
        
    async def test_create_database_connection(self, client: httpx.AsyncClient):
        """Test creating new database connection"""
        connection_config = {
            "name": "test_mongodb_connection",
            "type": "mongodb",
            "config": {
                "host": "test-mongodb",
                "port": 27017,
                "username": "admin",
                "password": "test-password",
                "database": "test_connection_db"
            }
        }
        
        response = await client.post(
            "/api/v1/databases/connections",
            json=connection_config
        )
        assert response.status_code in [200, 201]
        
        data = response.json()
        assert "connection_id" in data
        assert data["status"] == "created"
        
    async def test_validate_policies(self, client: httpx.AsyncClient):
        """Test policy validation endpoint"""
        policy_data = {
            "policies": [
                {
                    "name": "test_data_retention",
                    "type": "data_retention",
                    "rules": {
                        "max_age_days": 90,
                        "auto_archive": True
                    }
                }
            ]
        }
        
        response = await client.post(
            "/api/v1/policies/validate",
            json=policy_data
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "validation_result" in data
        assert data["validation_result"]["valid"] is True
        
    async def test_audit_trail(self, client: httpx.AsyncClient):
        """Test audit trail endpoint"""
        response = await client.get("/api/v1/audit/trail")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Audit trail might be empty for new system
        
    async def test_compliance_report(self, client: httpx.AsyncClient):
        """Test compliance reporting endpoint"""
        response = await client.get("/api/v1/compliance/report")
        assert response.status_code == 200
        
        data = response.json()
        assert "compliance_status" in data
        assert "timestamp" in data
        assert "databases" in data
        
    async def test_metrics_endpoint(self, client: httpx.AsyncClient):
        """Test metrics endpoint"""
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert "metrics" in data
        assert isinstance(data["metrics"], dict)
        
    async def test_backup_operations(self, client: httpx.AsyncClient):
        """Test backup operation endpoints"""
        # Test backup status
        response = await client.get("/api/v1/backup/status")
        assert response.status_code == 200
        
        # Test backup configuration
        backup_config = {
            "databases": ["test_db"],
            "schedule": "0 2 * * *",
            "retention_days": 30,
            "encryption": True
        }
        
        response = await client.post(
            "/api/v1/backup/configure",
            json=backup_config
        )
        assert response.status_code in [200, 201]
        
    async def test_error_handling(self, client: httpx.AsyncClient):
        """Test API error handling"""
        # Test invalid endpoint
        response = await client.get("/api/v1/invalid-endpoint")
        assert response.status_code == 404
        
        # Test invalid data
        response = await client.post(
            "/api/v1/databases/connections",
            json={"invalid": "data"}
        )
        assert response.status_code in [400, 422]
        
    async def test_authentication(self, client: httpx.AsyncClient):
        """Test authentication if enabled"""
        # For now, API might not have auth enabled in test mode
        # This test can be expanded when auth is implemented
        pass
        
    async def test_rate_limiting(self, client: httpx.AsyncClient):
        """Test rate limiting if enabled"""
        # Make multiple rapid requests to test rate limiting
        responses = []
        for i in range(5):
            response = await client.get("/health")
            responses.append(response.status_code)
            
        # In test mode, rate limiting might be disabled
        # This test validates the API can handle rapid requests
        assert all(status == 200 for status in responses)

@pytest.mark.asyncio
class TestDatabaseOperations:
    """Test database operations through API"""
    
    BASE_URL = "http://test-api:8080"
    
    @pytest.fixture
    async def client(self):
        """Create HTTP client for database testing"""
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=30.0) as client:
            yield client
    
    async def test_mongodb_operations(self, client: httpx.AsyncClient):
        """Test MongoDB operations through API"""
        # Test connection
        response = await client.post("/api/v1/databases/mongodb/test-connection", json={
            "host": "test-mongodb",
            "port": 27017,
            "username": "admin",
            "password": "test-password",
            "database": "test_db"
        })
        assert response.status_code == 200
        
        # Test basic operations if API supports them
        # This can be expanded based on actual API implementation
        
    async def test_postgresql_operations(self, client: httpx.AsyncClient):
        """Test PostgreSQL operations through API"""
        response = await client.post("/api/v1/databases/postgresql/test-connection", json={
            "host": "test-postgresql",
            "port": 5432,
            "username": "postgres",
            "password": "test-password",
            "database": "test_db"
        })
        assert response.status_code == 200
        
    async def test_redis_operations(self, client: httpx.AsyncClient):
        """Test Redis operations through API"""
        response = await client.post("/api/v1/databases/redis/test-connection", json={
            "host": "test-redis",
            "port": 6379,
            "password": "test-password"
        })
        assert response.status_code == 200

@pytest.mark.performance
class TestAPIPerformance:
    """Performance tests for API endpoints"""
    
    BASE_URL = "http://test-api:8080"
    
    @pytest.fixture
    async def client(self):
        """Create HTTP client for performance testing"""
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=60.0) as client:
            yield client
    
    async def test_health_endpoint_performance(self, client: httpx.AsyncClient):
        """Test health endpoint response time"""
        start_time = time.time()
        response = await client.get("/health")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second
        
    async def test_concurrent_requests(self, client: httpx.AsyncClient):
        """Test API under concurrent load"""
        async def make_request():
            response = await client.get("/health")
            return response.status_code
        
        # Create 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        
    async def test_large_data_handling(self, client: httpx.AsyncClient):
        """Test API with large data payloads"""
        # Create a large policy configuration
        large_policy = {
            "policies": [
                {
                    "name": f"policy_{i}",
                    "type": "data_retention",
                    "rules": {
                        "max_age_days": 90 + i,
                        "auto_archive": True,
                        "tags": [f"tag_{j}" for j in range(10)]
                    }
                } for i in range(100)
            ]
        }
        
        response = await client.post(
            "/api/v1/policies/validate",
            json=large_policy
        )
        
        # Should handle large payloads (might return 413 if too large)
        assert response.status_code in [200, 413]

if __name__ == "__main__":
    # Run tests directly if called as script
    pytest.main([__file__, "-v"])
