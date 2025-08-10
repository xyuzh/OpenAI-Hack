#!/usr/bin/env python3
"""
Test RabbitMQ connection and Celery configuration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_rabbitmq_connection():
    """Test direct RabbitMQ connection"""
    try:
        import pika
        
        # Get connection parameters from environment
        host = os.getenv('RABBITMQ_HOST', 'localhost')
        port = int(os.getenv('RABBITMQ_PORT', '5672'))
        username = os.getenv('RABBITMQ_USERNAME', 'guest')
        password = os.getenv('RABBITMQ_PASSWORD', 'guest')
        
        print(f"Testing RabbitMQ connection to {host}:{port}...")
        
        # Create connection
        credentials = pika.PlainCredentials(username, password)
        parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=credentials
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        print("✅ Successfully connected to RabbitMQ!")
        print(f"   Host: {host}:{port}")
        print(f"   User: {username}")
        
        # Declare a test queue
        queue_name = 'test_queue'
        channel.queue_declare(queue=queue_name, durable=False)
        print(f"✅ Successfully declared queue: {queue_name}")
        
        # Clean up
        channel.queue_delete(queue=queue_name)
        connection.close()
        
        return True
        
    except ImportError:
        print("❌ pika library not installed. Run: pip install pika")
        return False
    except Exception as e:
        print(f"❌ Failed to connect to RabbitMQ: {e}")
        print("\nMake sure RabbitMQ is running:")
        print("  brew services start rabbitmq")
        print("  or")
        print("  rabbitmq-server")
        return False

def test_redis_connection():
    """Test Redis connection"""
    try:
        import redis
        
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', '6379'))
        db = int(os.getenv('REDIS_DB', '0'))
        
        print(f"\nTesting Redis connection to {host}:{port}...")
        
        client = redis.Redis(host=host, port=port, db=db)
        client.ping()
        
        print("✅ Successfully connected to Redis!")
        print(f"   Host: {host}:{port}")
        print(f"   DB: {db}")
        
        return True
        
    except ImportError:
        print("❌ redis library not installed. Run: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        print("\nMake sure Redis is running:")
        print("  brew services start redis")
        print("  or")
        print("  redis-server")
        return False

def test_celery_import():
    """Test if Celery can be imported and configured"""
    try:
        print("\nTesting Celery configuration...")
        
        from modem.core.celery_app import celery_app
        
        print("✅ Successfully imported Celery app!")
        print(f"   Broker: {celery_app.conf.broker_url[:30]}...")
        print(f"   Task serializer: {celery_app.conf.task_serializer}")
        print(f"   Result serializer: {celery_app.conf.result_serializer}")
        
        # List registered tasks
        print("\n📋 Registered Celery tasks:")
        for task_name in sorted(celery_app.tasks.keys()):
            if not task_name.startswith('celery.'):
                print(f"   - {task_name}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import Celery app: {e}")
        return False
    except Exception as e:
        print(f"❌ Error with Celery configuration: {e}")
        return False

def check_environment_variables():
    """Check if required environment variables are set"""
    print("\nChecking environment variables...")
    
    required_vars = [
        'OPENAI_API_KEY',
        'RABBITMQ_HOST',
        'RABBITMQ_PORT',
        'RABBITMQ_USERNAME',
        'RABBITMQ_PASSWORD',
        'REDIS_HOST',
        'REDIS_PORT',
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_') or value == 'placeholder':
            missing.append(var)
            print(f"   ❌ {var}: Not configured")
        else:
            if 'KEY' in var or 'PASSWORD' in var:
                print(f"   ✅ {var}: ***{value[-4:]}")
            else:
                print(f"   ✅ {var}: {value}")
    
    if missing:
        print(f"\n⚠️  Missing or unconfigured variables: {', '.join(missing)}")
        print("Please update your .env file")
        return False
    
    return True

def main():
    print("=" * 60)
    print("RabbitMQ and Celery Configuration Test")
    print("=" * 60)
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    # Test connections
    rabbitmq_ok = test_rabbitmq_connection()
    redis_ok = test_redis_connection()
    celery_ok = test_celery_import()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Environment Variables: {'✅ OK' if env_ok else '❌ Missing'}")
    print(f"RabbitMQ Connection:   {'✅ OK' if rabbitmq_ok else '❌ Failed'}")
    print(f"Redis Connection:      {'✅ OK' if redis_ok else '❌ Failed'}")
    print(f"Celery Configuration:  {'✅ OK' if celery_ok else '❌ Failed'}")
    
    if all([env_ok, rabbitmq_ok, redis_ok, celery_ok]):
        print("\n🎉 All tests passed! Your environment is ready.")
        print("\nYou can now run:")
        print("  ./start_services.sh")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())