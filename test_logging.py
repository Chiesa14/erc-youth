#!/usr/bin/env python3
"""
Test script to demonstrate the logging system functionality.
Run this script to see how the logging system works.
"""

import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock database session and user for testing
class MockDB:
    def __init__(self):
        self.logs = []
    
    def add(self, log_entry):
        self.logs.append(log_entry)
        logger.info(f"Added log entry: {log_entry.description}")
    
    def commit(self):
        logger.info("Database commit simulated")
    
    def refresh(self, log_entry):
        logger.info(f"Refreshed log entry: {log_entry.id}")
    
    def query(self, model):
        return MockQuery(self.logs)
    
    def close(self):
        logger.info("Database connection closed")

class MockQuery:
    def __init__(self, logs):
        self.logs = logs
    
    def filter(self, *args):
        return self
    
    def all(self):
        return self.logs
    
    def first(self):
        return self.logs[0] if self.logs else None

class MockUser:
    def __init__(self, user_id, full_name, family_id=None, family_name=None, family_category=None):
        self.id = user_id
        self.full_name = full_name
        self.family_id = family_id
        self.family_name = family_name
        self.family_category = family_category
        self.email = f"{full_name.lower().replace(' ', '.')}@example.com"
        self.role = "youth"

class MockFamily:
    def __init__(self, family_id, name, category):
        self.id = family_id
        self.name = name
        self.category = category

async def test_logging_system():
    """Test the logging system with mock data"""
    
    logger.info("=== Testing ERC Youth Logging System ===\n")
    
    # Create mock database and user
    db = MockDB()
    user = MockUser(1, "John Doe", 1, "Smith Family", "Youth")
    family = MockFamily(1, "Smith Family", "Youth")
    
    logger.info(f"Created mock user: {user.full_name}")
    logger.info(f"Created mock family: {family.name} ({family.category})\n")
    
    # Test basic logging service
    try:
        from app.services.logging_service import LoggingService
        
        logger.info("1. Testing basic activity logging...")
        log_entry = LoggingService.log_activity(
            db=db,
            user=user,
            action="TEST",
            description="Test activity for demonstration",
            table_name="test_table",
            record_id=123,
            details={"test_field": "test_value"},
            ip_address="192.168.1.100",
            user_agent="Test Browser/1.0"
        )
        logger.info(f"   ✓ Created log entry: {log_entry.description}\n")
        
        # Test predefined logging methods
        logger.info("2. Testing predefined logging methods...")
        
        # User creation log
        LoggingService.log_user_creation(db, user, "192.168.1.100", "Test Browser/1.0")
        logger.info("   ✓ Logged user creation")
        
        # Family creation log
        LoggingService.log_family_creation(db, user, family, "192.168.1.100", "Test Browser/1.0")
        logger.info("   ✓ Logged family creation")
        
        # Document upload log
        LoggingService.log_document_upload(db, user, 456, "test_document.pdf", "192.168.1.100", "Test Browser/1.0")
        logger.info("   ✓ Logged document upload")
        
        # Feedback submission log
        LoggingService.log_feedback_submission(db, user, 789, "general", "192.168.1.100", "Test Browser/1.0")
        logger.info("   ✓ Logged feedback submission\n")
        
        # Test action descriptions
        logger.info("3. Testing action descriptions...")
        descriptions = [
            ("CREATE", "user"),
            ("UPDATE", "profile"),
            ("DELETE", "document"),
            ("UPLOAD", "file"),
            ("LOGIN", "system")
        ]
        
        for action, table in descriptions:
            desc = LoggingService.get_action_description(action, table)
            logger.info(f"   {action} {table}: {desc}")
        
        logger.info("")
        
        # Test decorator functionality
        logger.info("4. Testing logging decorators...")
        
        from app.utils.logging_decorator import log_create, log_update, log_delete
        
        @log_create("test_table", "Created test record")
        def create_test_record(db, user):
            return {"id": 999, "name": "Test Record"}
        
        @log_update("test_table", "Updated test record")
        def update_test_record(db, user):
            return {"id": 999, "name": "Updated Test Record"}
        
        @log_delete("test_table", "Deleted test record")
        def delete_test_record(db, user):
            return {"id": 999, "deleted": True}
        
        # Execute decorated functions
        create_test_record(db, user)
        update_test_record(db, user)
        delete_test_record(db, user)
        
        logger.info("   ✓ All decorator tests passed\n")
        
        # Display all created logs
        logger.info("5. Summary of all log entries:")
        logger.info(f"   Total logs created: {len(db.logs)}")
        
        for i, log in enumerate(db.logs, 1):
            logger.info(f"   {i}. [{log.action}] {log.description}")
            logger.info(f"      User: {log.user_name} | Family: {log.family_name} | Table: {log.table_name}")
            logger.info(f"      IP: {log.ip_address} | Time: {log.created_at}")
            if log.details:
                logger.info(f"      Details: {log.details}")
            logger.info("")
        
        logger.info("=== Logging System Test Completed Successfully! ===")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.info("Make sure you're running this from the project root directory")
        logger.info("and that all dependencies are installed.")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

def test_middleware_simulation():
    """Simulate how the middleware would work"""
    
    logger.info("=== Testing Middleware Simulation ===\n")
    
    # Simulate request processing
    requests = [
        {"method": "POST", "path": "/api/users", "status": 201, "description": "User registration"},
        {"method": "GET", "path": "/api/families", "status": 200, "description": "View families"},
        {"method": "PUT", "path": "/api/users/1", "status": 200, "description": "Update user profile"},
        {"method": "DELETE", "path": "/api/documents/123", "status": 204, "description": "Delete document"},
        {"method": "POST", "path": "/api/login", "status": 200, "description": "User login"}
    ]
    
    for i, req in enumerate(requests, 1):
        logger.info(f"Request {i}: {req['method']} {req['path']}")
        logger.info(f"   Status: {req['status']}")
        logger.info(f"   Description: {req['description']}")
        
        # Determine if this would be logged
        should_log = False
        if req['method'] != "GET":
            should_log = True
        elif req['status'] >= 400:
            should_log = True
        elif any(req['path'].startswith(api_path) for api_path in ["/api/users", "/api/families"]):
            should_log = True
        
        logger.info(f"   Would be logged: {'Yes' if should_log else 'No'}\n")

if __name__ == "__main__":
    logger.info("Starting ERC Youth Logging System Tests...\n")
    
    # Test the logging system
    asyncio.run(test_logging_system())
    
    logger.info("\n" + "="*50 + "\n")
    
    # Test middleware simulation
    test_middleware_simulation()
    
    logger.info("\nAll tests completed!")
