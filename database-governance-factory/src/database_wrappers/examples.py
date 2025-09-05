"""
Database Wrappers Examples
Comprehensive examples for all database wrapper types

This file demonstrates how to use each database wrapper with real-world examples
and common use cases.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

# Import all wrappers and factory
from database_wrappers import (
    DatabaseWrapperFactory,
    DatabaseConfig,
    DatabaseType,
    create_and_connect
)

# Example configurations for each database type
EXAMPLE_CONFIGS = {
    'mongodb': {
        'host': 'localhost',
        'port': 27017,
        'database_name': 'example_db',
        'username': 'user',
        'password': 'password',
        'connection_string': 'mongodb://user:password@localhost:27017/example_db'
    },
    'postgresql': {
        'host': 'localhost',
        'port': 5432,
        'database_name': 'example_db',
        'username': 'user',
        'password': 'password'
    },
    'redis': {
        'host': 'localhost',
        'port': 6379,
        'database_name': '0',
        'password': None
    },
    'cosmosdb': {
        'host': 'https://myaccount.documents.azure.com:443/',
        'port': 443,
        'database_name': 'example_db',
        'password': 'your-cosmos-key-here'
    },
    'blobstorage': {
        'host': 'blobstorage',
        'port': 443,
        'database_name': 'example-container',
        'connection_string': 'DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=key;EndpointSuffix=core.windows.net'
    }
}

async def mongodb_examples():
    """MongoDB wrapper examples"""
    print("\n=== MongoDB Examples ===")
    
    # Create MongoDB wrapper
    config = DatabaseConfig(**EXAMPLE_CONFIGS['mongodb'])
    config.additional_config['type'] = 'mongodb'
    
    try:
        wrapper = DatabaseWrapperFactory.create_wrapper(config)
        await wrapper.connect()
        
        # Basic CRUD operations
        print("1. Creating documents...")
        users = [
            {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'},
            {'name': 'Bob', 'age': 25, 'email': 'bob@example.com'},
            {'name': 'Charlie', 'age': 35, 'email': 'charlie@example.com'}
        ]
        
        result = await wrapper.create('users', users)
        print(f"Created {result.count} users")
        
        # Query documents
        print("2. Querying documents...")
        result = await wrapper.read('users', {'age': {'$gte': 30}})
        print(f"Found {result.count} users aged 30 or older")
        
        # Aggregation example
        print("3. Aggregation pipeline...")
        pipeline = [
            {'$group': {'_id': None, 'avg_age': {'$avg': '$age'}, 'total_users': {'$sum': 1}}},
            {'$project': {'_id': 0, 'avg_age': 1, 'total_users': 1}}
        ]
        result = await wrapper.aggregate('users', pipeline)
        print(f"Average age: {result.data[0]['avg_age']:.1f}")
        
        # Index creation
        print("4. Creating indexes...")
        await wrapper.create_index('users', {'email': 1}, {'unique': True})
        await wrapper.create_index('users', {'name': 'text'})
        
        # Text search
        print("5. Text search...")
        result = await wrapper.read('users', {'$text': {'$search': 'Alice'}})
        print(f"Text search found {result.count} results")
        
        await wrapper.disconnect()
        print("MongoDB examples completed successfully!")
        
    except Exception as e:
        print(f"MongoDB example error: {e}")

async def postgresql_examples():
    """PostgreSQL wrapper examples"""
    print("\n=== PostgreSQL Examples ===")
    
    config = DatabaseConfig(**EXAMPLE_CONFIGS['postgresql'])
    config.additional_config['type'] = 'postgresql'
    
    try:
        wrapper = DatabaseWrapperFactory.create_wrapper(config)
        await wrapper.connect()
        
        # Create table
        print("1. Creating table...")
        schema = {
            'columns': [
                {'name': 'id', 'type': 'SERIAL', 'constraints': ['PRIMARY KEY']},
                {'name': 'name', 'type': 'VARCHAR(100)', 'constraints': ['NOT NULL']},
                {'name': 'age', 'type': 'INTEGER'},
                {'name': 'email', 'type': 'VARCHAR(255)', 'constraints': ['UNIQUE']},
                {'name': 'created_at', 'type': 'TIMESTAMP', 'default': 'CURRENT_TIMESTAMP'}
            ]
        }
        await wrapper.create_table_or_collection('users', schema)
        
        # Insert data
        print("2. Inserting data...")
        users = [
            {'name': 'Alice', 'age': 30, 'email': 'alice@example.com'},
            {'name': 'Bob', 'age': 25, 'email': 'bob@example.com'},
            {'name': 'Charlie', 'age': 35, 'email': 'charlie@example.com'}
        ]
        result = await wrapper.create('users', users)
        print(f"Inserted {result.count} users")
        
        # Complex query
        print("3. Complex SQL query...")
        sql = """
        SELECT name, age, 
               CASE WHEN age < 30 THEN 'Young' 
                    WHEN age < 40 THEN 'Middle' 
                    ELSE 'Senior' END as age_group
        FROM users 
        WHERE age > $1 
        ORDER BY age DESC
        """
        result = await wrapper.query(sql, [20])
        print(f"Query returned {result.count} results")
        
        # Stored procedure
        print("4. Creating stored procedure...")
        proc_sql = """
        CREATE OR REPLACE FUNCTION get_user_stats()
        RETURNS TABLE(total_users INTEGER, avg_age NUMERIC) AS $$
        BEGIN
            RETURN QUERY SELECT COUNT(*)::INTEGER, AVG(age) FROM users;
        END;
        $$ LANGUAGE plpgsql;
        """
        await wrapper.query(proc_sql)
        
        # Call stored procedure
        result = await wrapper.query("SELECT * FROM get_user_stats()")
        stats = result.data[0]
        print(f"Total users: {stats['total_users']}, Average age: {stats['avg_age']:.1f}")
        
        # Full-text search
        print("5. Full-text search...")
        await wrapper.query("ALTER TABLE users ADD COLUMN search_vector tsvector")
        await wrapper.query("""
            UPDATE users SET search_vector = to_tsvector('english', name || ' ' || email)
        """)
        await wrapper.create_index('users', {'search_vector': 'gin'})
        
        result = await wrapper.query(
            "SELECT name, email FROM users WHERE search_vector @@ to_tsquery('Alice')"
        )
        print(f"Full-text search found {result.count} results")
        
        await wrapper.disconnect()
        print("PostgreSQL examples completed successfully!")
        
    except Exception as e:
        print(f"PostgreSQL example error: {e}")

async def redis_examples():
    """Redis wrapper examples"""
    print("\n=== Redis Examples ===")
    
    config = DatabaseConfig(**EXAMPLE_CONFIGS['redis'])
    config.additional_config['type'] = 'redis'
    
    try:
        wrapper = DatabaseWrapperFactory.create_wrapper(config)
        await wrapper.connect()
        
        # Basic key-value operations
        print("1. Key-value operations...")
        await wrapper.create('cache', {'user:1': {'name': 'Alice', 'age': 30}})
        result = await wrapper.read('cache', {'key': 'user:1'})
        print(f"Retrieved user: {result.data}")
        
        # Hash operations
        print("2. Hash operations...")
        hash_data = {
            'user:2:profile': {
                'name': 'Bob',
                'age': 25,
                'email': 'bob@example.com',
                'location': 'New York'
            }
        }
        await wrapper.create('hashes', hash_data)
        
        # Set operations
        print("3. Set operations...")
        await wrapper.execute_db_specific_operation('sadd', {
            'key': 'active_users',
            'members': ['user:1', 'user:2', 'user:3']
        })
        
        # Sorted set operations
        print("4. Sorted set operations...")
        await wrapper.execute_db_specific_operation('zadd', {
            'key': 'user_scores',
            'score_members': {'user:1': 100, 'user:2': 85, 'user:3': 92}
        })
        
        # List operations
        print("5. List operations...")
        await wrapper.execute_db_specific_operation('lpush', {
            'key': 'notifications',
            'values': ['Welcome!', 'New message', 'Friend request']
        })
        
        # Pub/Sub example
        print("6. Pub/Sub operations...")
        await wrapper.execute_db_specific_operation('publish', {
            'channel': 'news',
            'message': 'Breaking: Redis is awesome!'
        })
        
        # Lua script
        print("7. Lua script execution...")
        script = """
        local key = KEYS[1]
        local current = redis.call('GET', key)
        if current == false then
            current = 0
        end
        local new_value = current + ARGV[1]
        redis.call('SET', key, new_value)
        return new_value
        """
        result = await wrapper.execute_db_specific_operation('eval_script', {
            'script': script,
            'keys': ['counter'],
            'args': ['5']
        })
        print(f"Counter value: {result}")
        
        await wrapper.disconnect()
        print("Redis examples completed successfully!")
        
    except Exception as e:
        print(f"Redis example error: {e}")

async def cosmosdb_examples():
    """Cosmos DB wrapper examples"""
    print("\n=== Cosmos DB Examples ===")
    
    config = DatabaseConfig(**EXAMPLE_CONFIGS['cosmosdb'])
    config.additional_config['type'] = 'cosmosdb'
    
    try:
        wrapper = DatabaseWrapperFactory.create_wrapper(config)
        await wrapper.connect()
        
        # Create container
        print("1. Creating container...")
        container_schema = {
            'partition_key': '/category',
            'throughput': 400
        }
        await wrapper.create_table_or_collection('products', container_schema)
        
        # Insert documents
        print("2. Inserting documents...")
        products = [
            {
                'id': '1',
                'name': 'Laptop',
                'category': 'Electronics',
                'price': 999.99,
                'in_stock': True
            },
            {
                'id': '2', 
                'name': 'Book',
                'category': 'Education',
                'price': 29.99,
                'in_stock': True
            },
            {
                'id': '3',
                'name': 'Phone',
                'category': 'Electronics', 
                'price': 699.99,
                'in_stock': False
            }
        ]
        result = await wrapper.create('products', products)
        print(f"Created {result.count} products")
        
        # SQL query
        print("3. SQL query...")
        sql_query = "SELECT * FROM c WHERE c.category = 'Electronics' AND c.price < 800"
        result = await wrapper.query(sql_query)
        print(f"Found {result.count} electronics under $800")
        
        # Cross-partition query
        print("4. Cross-partition query...")
        sql_query = "SELECT c.category, COUNT(1) as count FROM c GROUP BY c.category"
        result = await wrapper.query(sql_query)
        print(f"Product categories: {result.data}")
        
        # Point read (most efficient)
        print("5. Point read...")
        result = await wrapper.read('products', {
            'id': '1',
            'partition_key': 'Electronics'
        })
        print(f"Point read result: {result.data['name']}")
        
        # Update document
        print("6. Updating document...")
        result = await wrapper.update('products', 
            {'id': '1', 'partition_key': 'Electronics'},
            {'price': 899.99, 'sale': True}
        )
        print(f"Updated product: {result.success}")
        
        # Stored procedure
        print("7. Stored procedure...")
        stored_proc = """
        function updatePrice(itemId, newPrice) {
            var context = getContext();
            var collection = context.getCollection();
            
            var query = "SELECT * FROM c WHERE c.id = '" + itemId + "'";
            collection.queryDocuments(collection.getSelfLink(), query, function(err, items) {
                if (err) throw err;
                if (items.length > 0) {
                    var item = items[0];
                    item.price = newPrice;
                    item.updated = new Date();
                    collection.replaceDocument(item._self, item, function(err, updated) {
                        if (err) throw err;
                        getContext().getResponse().setBody(updated);
                    });
                }
            });
        }
        """
        
        await wrapper.execute_db_specific_operation('create_stored_procedure', {
            'procedure_id': 'updatePrice',
            'procedure_body': stored_proc
        })
        
        await wrapper.disconnect()
        print("Cosmos DB examples completed successfully!")
        
    except Exception as e:
        print(f"Cosmos DB example error: {e}")

async def blobstorage_examples():
    """Blob Storage wrapper examples"""
    print("\n=== Blob Storage Examples ===")
    
    config = DatabaseConfig(**EXAMPLE_CONFIGS['blobstorage'])
    config.additional_config['type'] = 'blobstorage'
    
    try:
        wrapper = DatabaseWrapperFactory.create_wrapper(config)
        await wrapper.connect()
        
        # Upload text blob
        print("1. Uploading text blob...")
        text_data = {
            'blob_name': 'welcome.txt',
            'data': 'Welcome to our application!',
            'content_type': 'text/plain',
            'metadata': {'author': 'admin', 'purpose': 'welcome_message'}
        }
        result = await wrapper.create('documents', text_data)
        print(f"Uploaded text blob: {result.data['blob_name']}")
        
        # Upload JSON blob
        print("2. Uploading JSON blob...")
        json_data = {
            'blob_name': 'config.json',
            'data': {
                'app_name': 'MyApp',
                'version': '1.0.0',
                'features': ['auth', 'logging', 'metrics']
            },
            'metadata': {'type': 'configuration', 'environment': 'production'}
        }
        result = await wrapper.create('documents', json_data)
        print(f"Uploaded JSON blob: {result.data['blob_name']}")
        
        # Upload multiple files
        print("3. Batch upload...")
        batch_files = [
            {
                'blob_name': f'log-{i}.txt',
                'data': f'Log entry {i}\nTimestamp: {datetime.now()}',
                'metadata': {'type': 'log', 'sequence': str(i)}
            }
            for i in range(1, 4)
        ]
        result = await wrapper.create('logs', batch_files)
        print(f"Uploaded {result.count} log files")
        
        # List blobs
        print("4. Listing blobs...")
        result = await wrapper.read('documents', {'include_content': False})
        print(f"Found {result.count} blobs in documents container")
        for blob in result.data:
            print(f"  - {blob['blob_name']} ({blob['size_bytes']} bytes)")
        
        # Download specific blob
        print("5. Downloading blob...")
        result = await wrapper.read('documents', {
            'blob_name': 'config.json',
            'include_content': True
        })
        if result.success:
            blob_data = result.data
            print(f"Downloaded {blob_data['blob_name']}: {blob_data['content']}")
        
        # Search by prefix
        print("6. Search by prefix...")
        result = await wrapper.read('logs', {
            'prefix': 'log-',
            'include_content': False
        })
        print(f"Found {result.count} log files")
        
        # Update blob metadata
        print("7. Updating blob metadata...")
        result = await wrapper.update('documents', 
            {'blob_name': 'welcome.txt'},
            {'metadata': {'author': 'admin', 'updated': datetime.now().isoformat()}}
        )
        print(f"Updated metadata: {result.success}")
        
        # Aggregate operations
        print("8. Aggregate by content type...")
        pipeline = [
            {'$group': {'_id': 'content_type'}}
        ]
        result = await wrapper.aggregate('documents', pipeline)
        print(f"Content type distribution: {result.data}")
        
        # Set blob tier (Azure-specific)
        print("9. Setting blob tier...")
        result = await wrapper.execute_db_specific_operation('set_blob_tier', {
            'container': 'documents',
            'blob_name': 'config.json',
            'tier': 'Cool'
        })
        print(f"Set blob tier: {result['success']}")
        
        # Create blob snapshot
        print("10. Creating blob snapshot...")
        result = await wrapper.execute_db_specific_operation('create_snapshot', {
            'container': 'documents',
            'blob_name': 'config.json'
        })
        print(f"Created snapshot: {result['snapshot']}")
        
        await wrapper.disconnect()
        print("Blob Storage examples completed successfully!")
        
    except Exception as e:
        print(f"Blob Storage example error: {e}")

async def factory_examples():
    """Database factory usage examples"""
    print("\n=== Factory Examples ===")
    
    # Create wrappers using factory methods
    print("1. Creating wrappers using factory...")
    
    # MongoDB from connection string
    mongo_wrapper = DatabaseWrapperFactory.create_from_url(
        "mongodb://localhost:27017/testdb",
        instance_id="mongo_test"
    )
    print(f"Created MongoDB wrapper: {mongo_wrapper.__class__.__name__}")
    
    # PostgreSQL with parameters
    pg_wrapper = DatabaseWrapperFactory.create_postgresql_wrapper(
        host="localhost",
        port=5432,
        database="testdb",
        username="user",
        password="pass",
        instance_id="pg_test"
    )
    print(f"Created PostgreSQL wrapper: {pg_wrapper.__class__.__name__}")
    
    # Redis with parameters
    redis_wrapper = DatabaseWrapperFactory.create_redis_wrapper(
        host="localhost",
        port=6379,
        database=0,
        instance_id="redis_test"
    )
    print(f"Created Redis wrapper: {redis_wrapper.__class__.__name__}")
    
    # List all registered wrappers
    print("2. Listing registered wrappers...")
    wrappers = DatabaseWrapperFactory.list_wrappers()
    for instance_id, info in wrappers.items():
        print(f"  {instance_id}: {info['type']} at {info['host']}:{info['port']}")
    
    # Get supported database types
    print("3. Supported database types...")
    types = DatabaseWrapperFactory.get_supported_types()
    print(f"Supported types: {', '.join(types)}")
    
    # Clean up
    print("4. Cleaning up wrappers...")
    DatabaseWrapperFactory.remove_wrapper("mongo_test")
    DatabaseWrapperFactory.remove_wrapper("pg_test") 
    DatabaseWrapperFactory.remove_wrapper("redis_test")
    print("Factory examples completed!")

async def backup_recovery_examples():
    """Backup and recovery examples across databases"""
    print("\n=== Backup & Recovery Examples ===")
    
    # This would typically work with real database connections
    print("Note: These examples require actual database connections")
    
    # MongoDB backup example
    print("1. MongoDB backup example...")
    try:
        config = DatabaseConfig(**EXAMPLE_CONFIGS['mongodb'])
        config.additional_config['type'] = 'mongodb'
        wrapper = DatabaseWrapperFactory.create_wrapper(config)
        
        # Create backup configuration
        backup_config = {
            'backup_type': 'full',
            'compression': True,
            'include_indexes': True,
            'collections': ['users', 'orders', 'products']
        }
        
        print(f"MongoDB backup config: {backup_config}")
        
    except Exception as e:
        print(f"MongoDB backup example (simulated): {e}")
    
    # PostgreSQL backup example
    print("2. PostgreSQL backup example...")
    try:
        config = DatabaseConfig(**EXAMPLE_CONFIGS['postgresql'])
        config.additional_config['type'] = 'postgresql'
        wrapper = DatabaseWrapperFactory.create_wrapper(config)
        
        backup_config = {
            'backup_type': 'pg_dump',
            'format': 'custom',
            'compress': True,
            'tables': ['users', 'orders', 'products']
        }
        
        print(f"PostgreSQL backup config: {backup_config}")
        
    except Exception as e:
        print(f"PostgreSQL backup example (simulated): {e}")

async def monitoring_examples():
    """Monitoring and performance examples"""
    print("\n=== Monitoring Examples ===")
    
    # Example of monitoring wrapper performance
    print("1. Performance monitoring setup...")
    
    configs = []
    for db_type in ['mongodb', 'postgresql', 'redis']:
        config = DatabaseConfig(**EXAMPLE_CONFIGS[db_type])
        config.additional_config['type'] = db_type
        config.instance_id = f"{db_type}_monitor"
        configs.append(config)
    
    wrappers = []
    for config in configs:
        try:
            wrapper = DatabaseWrapperFactory.create_wrapper(config)
            wrappers.append(wrapper)
            print(f"Created {config.additional_config['type']} wrapper for monitoring")
        except Exception as e:
            print(f"Failed to create {config.additional_config['type']} wrapper: {e}")
    
    # Simulate health checks
    print("2. Health check simulation...")
    for wrapper in wrappers:
        try:
            # Simulate connection
            wrapper.is_connected = True
            health_status = {
                'is_healthy': True,
                'response_time_ms': 25.5,
                'version': 'simulated',
                'additional_metrics': {'connections': 10, 'memory_mb': 256}
            }
            print(f"{wrapper.__class__.__name__}: {health_status}")
        except Exception as e:
            print(f"Health check failed for {wrapper.__class__.__name__}: {e}")
    
    print("3. Performance metrics simulation...")
    metrics = {
        'operations_per_second': 1500,
        'average_response_time_ms': 12.3,
        'cache_hit_ratio': 0.85,
        'active_connections': 25,
        'memory_usage_mb': 512
    }
    print(f"Example performance metrics: {metrics}")

async def streaming_examples():
    """Data streaming examples"""
    print("\n=== Streaming Examples ===")
    
    print("1. Streaming large datasets...")
    
    # Simulate streaming from MongoDB
    print("MongoDB streaming simulation:")
    try:
        config = DatabaseConfig(**EXAMPLE_CONFIGS['mongodb'])
        config.additional_config['type'] = 'mongodb'
        wrapper = DatabaseWrapperFactory.create_wrapper(config)
        
        # Simulate streaming batches
        batch_size = 1000
        total_batches = 5
        
        for batch_num in range(total_batches):
            # Simulate batch data
            batch_data = [
                {'id': i, 'data': f'Record {i}', 'batch': batch_num}
                for i in range(batch_num * batch_size, (batch_num + 1) * batch_size)
            ]
            print(f"  Batch {batch_num + 1}: {len(batch_data)} records")
            
        print(f"Total streamed: {total_batches * batch_size} records")
        
    except Exception as e:
        print(f"MongoDB streaming example: {e}")
    
    print("2. Real-time change streams simulation...")
    print("  Simulating MongoDB change stream events:")
    print("  - Document inserted: user_12345")
    print("  - Document updated: order_67890")
    print("  - Document deleted: session_abcdef")

async def main():
    """Run all examples"""
    print("Database Wrappers Comprehensive Examples")
    print("=" * 50)
    
    # Note: Most examples will fail without actual database connections
    # This is expected - they demonstrate the API usage patterns
    
    try:
        await factory_examples()
        await monitoring_examples()
        await streaming_examples()
        await backup_recovery_examples()
        
        # Uncomment to run database-specific examples with real connections:
        # await mongodb_examples()
        # await postgresql_examples()
        # await redis_examples()
        # await cosmosdb_examples()
        # await blobstorage_examples()
        
    except Exception as e:
        print(f"Example execution error: {e}")
    
    print("\n" + "=" * 50)
    print("Examples completed! (Most require actual database connections to run)")
    print("\nTo run with real databases:")
    print("1. Update connection configurations in EXAMPLE_CONFIGS")
    print("2. Install required packages: motor, asyncpg, aioredis, azure-cosmos, azure-storage-blob")
    print("3. Uncomment the database-specific example calls in main()")

if __name__ == "__main__":
    asyncio.run(main())
