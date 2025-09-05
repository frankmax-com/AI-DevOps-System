"""
Performance Tests for Database Governance Factory
Benchmarks and stress tests for database wrappers and governance system
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
import random
import string
from concurrent.futures import ThreadPoolExecutor

from src.database_wrappers.factory import DatabaseWrapperFactory
from src.governance_manager import DatabaseGovernanceManager

class TestDatabasePerformance:
    """Performance benchmarks for database wrappers"""
    
    @pytest.fixture
    async def factory(self):
        """Create database factory for testing"""
        return DatabaseWrapperFactory()
    
    @pytest.fixture
    async def governance_manager(self):
        """Create governance manager for testing"""
        return DatabaseGovernanceManager()
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_mongodb_connection_performance(self, factory, benchmark):
        """Benchmark MongoDB connection establishment"""
        config = {
            "host": "test-mongodb",
            "port": 27017,
            "username": "admin",
            "password": "test-password",
            "database": "performance_test"
        }
        
        async def create_connection():
            wrapper = await factory.create_wrapper("mongodb", config)
            await wrapper.connect()
            await wrapper.disconnect()
            return True
        
        result = await benchmark(create_connection)
        assert result is True
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_postgresql_connection_performance(self, factory, benchmark):
        """Benchmark PostgreSQL connection establishment"""
        config = {
            "host": "test-postgresql",
            "port": 5432,
            "username": "postgres",
            "password": "test-password",
            "database": "performance_test"
        }
        
        async def create_connection():
            wrapper = await factory.create_wrapper("postgresql", config)
            await wrapper.connect()
            await wrapper.disconnect()
            return True
        
        result = await benchmark(create_connection)
        assert result is True
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_redis_connection_performance(self, factory, benchmark):
        """Benchmark Redis connection establishment"""
        config = {
            "host": "test-redis",
            "port": 6379,
            "password": "test-password"
        }
        
        async def create_connection():
            wrapper = await factory.create_wrapper("redis", config)
            await wrapper.connect()
            await wrapper.disconnect()
            return True
        
        result = await benchmark(create_connection)
        assert result is True

class TestDataOperationPerformance:
    """Performance tests for data operations"""
    
    @pytest.fixture
    async def mongodb_wrapper(self):
        """Create MongoDB wrapper for testing"""
        factory = DatabaseWrapperFactory()
        config = {
            "host": "test-mongodb",
            "port": 27017,
            "username": "admin",
            "password": "test-password",
            "database": "performance_test"
        }
        wrapper = await factory.create_wrapper("mongodb", config)
        await wrapper.connect()
        yield wrapper
        await wrapper.disconnect()
    
    @pytest.fixture
    async def postgresql_wrapper(self):
        """Create PostgreSQL wrapper for testing"""
        factory = DatabaseWrapperFactory()
        config = {
            "host": "test-postgresql",
            "port": 5432,
            "username": "postgres",
            "password": "test-password",
            "database": "performance_test"
        }
        wrapper = await factory.create_wrapper("postgresql", config)
        await wrapper.connect()
        yield wrapper
        await wrapper.disconnect()
    
    @pytest.fixture
    async def redis_wrapper(self):
        """Create Redis wrapper for testing"""
        factory = DatabaseWrapperFactory()
        config = {
            "host": "test-redis",
            "port": 6379,
            "password": "test-password"
        }
        wrapper = await factory.create_wrapper("redis", config)
        await wrapper.connect()
        yield wrapper
        await wrapper.disconnect()
    
    def generate_test_data(self, count: int = 1000) -> List[Dict[str, Any]]:
        """Generate test data for performance testing"""
        data = []
        for i in range(count):
            data.append({
                "id": i,
                "name": f"test_user_{i}",
                "email": f"user{i}@example.com",
                "age": random.randint(18, 80),
                "city": random.choice(["New York", "London", "Tokyo", "Paris", "Sydney"]),
                "score": random.uniform(0, 100),
                "tags": [f"tag_{j}" for j in range(random.randint(1, 5))],
                "created_at": time.time(),
                "data": "".join(random.choices(string.ascii_letters, k=100))
            })
        return data
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_mongodb_bulk_insert_performance(self, mongodb_wrapper, benchmark):
        """Benchmark MongoDB bulk insert operations"""
        test_data = self.generate_test_data(1000)
        collection_name = "performance_test_collection"
        
        async def bulk_insert():
            return await mongodb_wrapper.bulk_insert(collection_name, test_data)
        
        result = await benchmark(bulk_insert)
        assert result["inserted_count"] == 1000
        
        # Cleanup
        await mongodb_wrapper.delete_many(collection_name, {})
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_postgresql_bulk_insert_performance(self, postgresql_wrapper, benchmark):
        """Benchmark PostgreSQL bulk insert operations"""
        # Create test table
        await postgresql_wrapper.execute_query("""
            CREATE TABLE IF NOT EXISTS performance_test (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100),
                age INTEGER,
                city VARCHAR(50),
                score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        test_data = [
            (f"test_user_{i}", f"user{i}@example.com", random.randint(18, 80), 
             random.choice(["New York", "London", "Tokyo", "Paris", "Sydney"]), 
             random.uniform(0, 100))
            for i in range(1000)
        ]
        
        async def bulk_insert():
            query = """
                INSERT INTO performance_test (name, email, age, city, score) 
                VALUES ($1, $2, $3, $4, $5)
            """
            return await postgresql_wrapper.bulk_execute(query, test_data)
        
        result = await benchmark(bulk_insert)
        assert result is not None
        
        # Cleanup
        await postgresql_wrapper.execute_query("DELETE FROM performance_test")
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_redis_bulk_operations_performance(self, redis_wrapper, benchmark):
        """Benchmark Redis bulk operations"""
        test_data = {f"key_{i}": f"value_{i}" for i in range(1000)}
        
        async def bulk_set():
            tasks = []
            for key, value in test_data.items():
                tasks.append(redis_wrapper.set(key, value))
            return await asyncio.gather(*tasks)
        
        result = await benchmark(bulk_set)
        assert len(result) == 1000
        
        # Cleanup
        keys = list(test_data.keys())
        await redis_wrapper.delete_many(keys)

class TestConcurrencyPerformance:
    """Test performance under concurrent load"""
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_concurrent_mongodb_operations(self):
        """Test MongoDB under concurrent load"""
        factory = DatabaseWrapperFactory()
        config = {
            "host": "test-mongodb",
            "port": 27017,
            "username": "admin",
            "password": "test-password",
            "database": "concurrency_test"
        }
        
        async def worker_task(worker_id: int):
            wrapper = await factory.create_wrapper("mongodb", config)
            await wrapper.connect()
            
            try:
                # Perform multiple operations
                collection = f"worker_{worker_id}_collection"
                
                # Insert
                doc = {"worker_id": worker_id, "timestamp": time.time()}
                await wrapper.insert_one(collection, doc)
                
                # Find
                result = await wrapper.find_one(collection, {"worker_id": worker_id})
                assert result is not None
                
                # Update
                await wrapper.update_one(
                    collection, 
                    {"worker_id": worker_id}, 
                    {"$set": {"updated": True}}
                )
                
                # Delete
                await wrapper.delete_one(collection, {"worker_id": worker_id})
                
                return True
                
            finally:
                await wrapper.disconnect()
        
        # Run 10 concurrent workers
        start_time = time.time()
        tasks = [worker_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        assert all(results)
        assert (end_time - start_time) < 30  # Should complete within 30 seconds
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_concurrent_postgresql_operations(self):
        """Test PostgreSQL under concurrent load"""
        factory = DatabaseWrapperFactory()
        config = {
            "host": "test-postgresql",
            "port": 5432,
            "username": "postgres",
            "password": "test-password",
            "database": "concurrency_test"
        }
        
        async def worker_task(worker_id: int):
            wrapper = await factory.create_wrapper("postgresql", config)
            await wrapper.connect()
            
            try:
                # Create worker table
                table_name = f"worker_{worker_id}_table"
                await wrapper.execute_query(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id SERIAL PRIMARY KEY,
                        data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert data
                await wrapper.execute_query(
                    f"INSERT INTO {table_name} (data) VALUES ($1)",
                    [f"worker_{worker_id}_data"]
                )
                
                # Query data
                result = await wrapper.execute_query(
                    f"SELECT * FROM {table_name} WHERE data = $1",
                    [f"worker_{worker_id}_data"]
                )
                assert len(result) > 0
                
                # Cleanup
                await wrapper.execute_query(f"DROP TABLE IF EXISTS {table_name}")
                
                return True
                
            finally:
                await wrapper.disconnect()
        
        # Run 10 concurrent workers
        start_time = time.time()
        tasks = [worker_task(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        assert all(results)
        assert (end_time - start_time) < 30  # Should complete within 30 seconds

class TestGovernancePerformance:
    """Performance tests for governance operations"""
    
    @pytest.fixture
    async def governance_manager(self):
        """Create governance manager for testing"""
        return DatabaseGovernanceManager()
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_policy_validation_performance(self, governance_manager, benchmark):
        """Benchmark policy validation performance"""
        # Create large policy set
        policies = []
        for i in range(100):
            policies.append({
                "name": f"policy_{i}",
                "type": "data_retention",
                "rules": {
                    "max_age_days": 90 + i,
                    "auto_archive": True,
                    "conditions": [f"condition_{j}" for j in range(10)]
                }
            })
        
        async def validate_policies():
            results = []
            for policy in policies:
                result = await governance_manager.validate_policy(policy)
                results.append(result)
            return results
        
        results = await benchmark(validate_policies)
        assert len(results) == 100
    
    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_compliance_check_performance(self, governance_manager, benchmark):
        """Benchmark compliance checking performance"""
        # Mock database connections for testing
        test_databases = []
        for i in range(20):
            test_databases.append({
                "name": f"test_db_{i}",
                "type": "mongodb",
                "config": {
                    "host": "test-mongodb",
                    "port": 27017,
                    "database": f"test_db_{i}"
                }
            })
        
        async def check_compliance():
            results = []
            for db in test_databases:
                # Simulate compliance check
                result = {
                    "database": db["name"],
                    "compliant": True,
                    "checks_performed": 10,
                    "timestamp": time.time()
                }
                results.append(result)
            return results
        
        results = await benchmark(check_compliance)
        assert len(results) == 20

class TestMemoryUsage:
    """Monitor memory usage during operations"""
    
    @pytest.mark.asyncio
    async def test_memory_usage_large_dataset(self):
        """Test memory usage with large datasets"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        large_data = []
        for i in range(10000):
            large_data.append({
                "id": i,
                "data": "x" * 1000,  # 1KB per record
                "nested": {
                    "array": list(range(100)),
                    "text": "sample text " * 50
                }
            })
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Should not use more than 200MB for this dataset
        assert memory_increase < 200
        
        # Cleanup
        del large_data
    
    @pytest.mark.asyncio
    async def test_connection_pool_memory(self):
        """Test memory usage of connection pools"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        factory = DatabaseWrapperFactory()
        wrappers = []
        
        # Create multiple connections
        for i in range(20):
            config = {
                "host": "test-mongodb",
                "port": 27017,
                "username": "admin",
                "password": "test-password",
                "database": f"test_db_{i}"
            }
            wrapper = await factory.create_wrapper("mongodb", config)
            await wrapper.connect()
            wrappers.append(wrapper)
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Cleanup
        for wrapper in wrappers:
            await wrapper.disconnect()
        
        # Memory increase should be reasonable
        assert memory_increase < 100  # Less than 100MB for 20 connections

if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "--benchmark-only"])
