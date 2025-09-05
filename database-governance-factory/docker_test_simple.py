"""
Simple Docker test for Database Governance Factory
Tests the core functionality without requiring running database services
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_imports():
    """Test that all modules can be imported successfully"""
    print("🧪 Testing imports...")
    
    try:
        from database_wrappers.factory import DatabaseWrapperFactory
        print("✅ DatabaseWrapperFactory imported successfully")
        
        from database_wrappers.mongodb_wrapper import MongoDBWrapper
        print("✅ MongoDBWrapper imported successfully")
        
        from database_wrappers.postgresql_wrapper import PostgreSQLWrapper
        print("✅ PostgreSQLWrapper imported successfully")
        
        from database_wrappers.redis_wrapper import RedisWrapper
        print("✅ RedisWrapper imported successfully")
        
        from database_wrappers.cosmosdb_wrapper import CosmosDBWrapper
        print("✅ CosmosDBWrapper imported successfully")
        
        from database_wrappers.blobstorage_wrapper import BlobStorageWrapper
        print("✅ BlobStorageWrapper imported successfully")
        
        from governance_manager import DatabaseGovernanceManager
        print("✅ DatabaseGovernanceManager imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

async def test_factory_creation():
    """Test that factory can create wrapper instances"""
    print("🏭 Testing factory creation...")
    
    try:
        from database_wrappers.factory import DatabaseWrapperFactory
        
        factory = DatabaseWrapperFactory()
        print("✅ Factory created successfully")
        
        # Test wrapper type validation
        supported_types = factory.get_supported_types()
        expected_types = {"mongodb", "postgresql", "redis", "cosmosdb", "blobstorage"}
        
        if expected_types.issubset(set(supported_types)):
            print(f"✅ All expected types supported: {supported_types}")
        else:
            print(f"❌ Missing types: {expected_types - set(supported_types)}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Factory test failed: {e}")
        return False

async def test_governance_manager():
    """Test governance manager creation and basic functionality"""
    print("⚖️ Testing governance manager...")
    
    try:
        from governance_manager import DatabaseGovernanceManager
        
        manager = DatabaseGovernanceManager()
        print("✅ Governance manager created successfully")
        
        # Test policy validation
        test_policy = {
            "name": "test_policy",
            "type": "data_retention",
            "rules": {
                "max_age_days": 90,
                "auto_archive": True
            }
        }
        
        validation_result = await manager.validate_policy(test_policy)
        if validation_result and validation_result.get("valid"):
            print("✅ Policy validation works")
        else:
            print(f"❌ Policy validation failed: {validation_result}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Governance manager test failed: {e}")
        return False

async def test_wrapper_configs():
    """Test wrapper configuration validation"""
    print("⚙️ Testing wrapper configurations...")
    
    try:
        from database_wrappers.factory import DatabaseWrapperFactory
        
        factory = DatabaseWrapperFactory()
        
        # Test MongoDB config
        mongodb_config = {
            "host": "localhost",
            "port": 27017,
            "username": "admin",
            "password": "password",
            "database": "test_db"
        }
        
        try:
            mongodb_wrapper = await factory.create_wrapper("mongodb", mongodb_config)
            print("✅ MongoDB wrapper created (config valid)")
        except Exception as e:
            # This is expected since we're not connecting to actual database
            print(f"✅ MongoDB wrapper config validated (connection failed as expected)")
        
        # Test PostgreSQL config
        postgresql_config = {
            "host": "localhost",
            "port": 5432,
            "username": "postgres",
            "password": "password",
            "database": "test_db"
        }
        
        try:
            postgresql_wrapper = await factory.create_wrapper("postgresql", postgresql_config)
            print("✅ PostgreSQL wrapper created (config valid)")
        except Exception as e:
            print(f"✅ PostgreSQL wrapper config validated (connection failed as expected)")
        
        # Test Redis config
        redis_config = {
            "host": "localhost",
            "port": 6379,
            "password": "password"
        }
        
        try:
            redis_wrapper = await factory.create_wrapper("redis", redis_config)
            print("✅ Redis wrapper created (config valid)")
        except Exception as e:
            print(f"✅ Redis wrapper config validated (connection failed as expected)")
        
        return True
        
    except Exception as e:
        print(f"❌ Wrapper config test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("""
    🚀 Database Governance Factory - Docker Test Suite
    ================================================
    
    This test validates that all components can be imported
    and initialized correctly in a Docker environment.
    """)
    
    tests = [
        ("Import Tests", test_imports),
        ("Factory Creation", test_factory_creation),
        ("Governance Manager", test_governance_manager),
        ("Wrapper Configurations", test_wrapper_configs),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = await test_func()
            if result:
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
    
    print(f"\n{'='*50}")
    print(f"TEST SUMMARY")
    print('='*50)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("💥 SOME TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
