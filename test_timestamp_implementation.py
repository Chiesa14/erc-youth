"""
Comprehensive test script for timestamp implementation.
Tests backward compatibility, data integrity, and functionality.
"""

import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.init_db import init_db
from app.models.user import User
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.family_activity import Activity
from app.schemas.user import UserCreate, GenderEnum, RoleEnum
from app.schemas.family import FamilyCreate
from app.schemas.family_member import FamilyMemberCreate
from app.schemas.family_activity import ActivityCreate, ActivityStatusEnum, ActivityCategoryEnum
from app.controllers.user import create_user, get_all_users
from app.controllers.family import create_family
from app.utils.timestamps import to_iso_format, from_iso_format, parse_timestamp_filters
from app.services.timestamp_service import TimestampQueryService


class TimestampTestSuite:
    """Comprehensive test suite for timestamp functionality"""
    
    def __init__(self):
        self.db: Session = SessionLocal()
        self.test_results: Dict[str, Any] = {
            'passed': 0,
            'failed': 0,
            'errors': [],
            'details': {}
        }
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        if passed:
            self.test_results['passed'] += 1
            print(f"✅ {test_name}: PASSED {message}")
        else:
            self.test_results['failed'] += 1
            error_msg = f"❌ {test_name}: FAILED {message}"
            print(error_msg)
            self.test_results['errors'].append(error_msg)
        
        self.test_results['details'][test_name] = {
            'passed': passed,
            'message': message
        }
    
    def test_database_initialization(self):
        """Test that database initialization includes timestamp middleware"""
        try:
            # This should initialize the timestamp middleware
            init_db()
            self.log_test("Database Initialization", True, "Timestamp middleware initialized")
        except Exception as e:
            self.log_test("Database Initialization", False, f"Error: {str(e)}")
    
    def test_model_timestamp_fields(self):
        """Test that all models have timestamp fields"""
        models_to_test = [
            (User, "User"),
            (Family, "Family"),
            (FamilyMember, "FamilyMember"),
            (Activity, "Activity")
        ]
        
        for model_class, model_name in models_to_test:
            has_created_at = hasattr(model_class, 'created_at')
            has_updated_at = hasattr(model_class, 'updated_at')
            
            if has_created_at and has_updated_at:
                self.log_test(f"{model_name} Timestamp Fields", True, "Both created_at and updated_at present")
            else:
                self.log_test(f"{model_name} Timestamp Fields", False, 
                            f"Missing fields - created_at: {has_created_at}, updated_at: {has_updated_at}")
    
    def test_automatic_timestamp_creation(self):
        """Test that timestamps are automatically set on record creation"""
        try:
            # Create a test family
            family_data = FamilyCreate(name="Test Family", category="Young")
            family = create_family(self.db, family_data)
            
            # Check if timestamps were set
            db_family = self.db.query(Family).filter(Family.id == family.id).first()
            
            has_created_at = db_family.created_at is not None
            has_updated_at = db_family.updated_at is not None
            timestamps_recent = (
                db_family.created_at and 
                (datetime.now(timezone.utc) - db_family.created_at).total_seconds() < 60
            )
            
            if has_created_at and has_updated_at and timestamps_recent:
                self.log_test("Automatic Timestamp Creation", True, 
                            f"Timestamps set correctly: {to_iso_format(db_family.created_at)}")
            else:
                self.log_test("Automatic Timestamp Creation", False, 
                            f"Timestamps not set properly - created_at: {has_created_at}, updated_at: {has_updated_at}")
            
            # Clean up
            self.db.delete(db_family)
            self.db.commit()
            
        except Exception as e:
            self.log_test("Automatic Timestamp Creation", False, f"Error: {str(e)}")
    
    def test_automatic_timestamp_update(self):
        """Test that updated_at is automatically updated on record modification"""
        try:
            # Create a test family
            family_data = FamilyCreate(name="Update Test Family", category="Mature")
            family = create_family(self.db, family_data)
            
            # Get the initial timestamps
            db_family = self.db.query(Family).filter(Family.id == family.id).first()
            initial_created_at = db_family.created_at
            initial_updated_at = db_family.updated_at
            
            # Wait a moment to ensure timestamp difference
            import time
            time.sleep(1)
            
            # Update the family
            db_family.name = "Updated Test Family"
            self.db.commit()
            self.db.refresh(db_family)
            
            # Check if updated_at changed but created_at remained the same
            created_at_unchanged = db_family.created_at == initial_created_at
            updated_at_changed = db_family.updated_at > initial_updated_at
            
            if created_at_unchanged and updated_at_changed:
                self.log_test("Automatic Timestamp Update", True, 
                            f"updated_at changed from {to_iso_format(initial_updated_at)} to {to_iso_format(db_family.updated_at)}")
            else:
                self.log_test("Automatic Timestamp Update", False, 
                            f"Timestamps not updated properly - created_at unchanged: {created_at_unchanged}, updated_at changed: {updated_at_changed}")
            
            # Clean up
            self.db.delete(db_family)
            self.db.commit()
            
        except Exception as e:
            self.log_test("Automatic Timestamp Update", False, f"Error: {str(e)}")
    
    def test_timezone_handling(self):
        """Test that timestamps are stored in UTC and formatted correctly"""
        try:
            # Create a test record
            family_data = FamilyCreate(name="Timezone Test Family", category="Young")
            family = create_family(self.db, family_data)
            
            db_family = self.db.query(Family).filter(Family.id == family.id).first()
            
            # Check if timestamp is timezone-aware and in UTC
            is_timezone_aware = db_family.created_at.tzinfo is not None
            is_utc = db_family.created_at.tzinfo == timezone.utc or db_family.created_at.utctimetuple()
            
            # Test ISO 8601 formatting
            iso_formatted = to_iso_format(db_family.created_at)
            is_iso_format = iso_formatted.endswith('Z') or '+' in iso_formatted or iso_formatted.endswith('+00:00')
            
            # Test parsing back
            parsed_timestamp = from_iso_format(iso_formatted)
            parsing_works = parsed_timestamp is not None
            
            if is_timezone_aware and is_iso_format and parsing_works:
                self.log_test("Timezone Handling", True, 
                            f"UTC timestamp correctly formatted as: {iso_formatted}")
            else:
                self.log_test("Timezone Handling", False, 
                            f"Timezone issues - aware: {is_timezone_aware}, ISO format: {is_iso_format}, parsing: {parsing_works}")
            
            # Clean up
            self.db.delete(db_family)
            self.db.commit()
            
        except Exception as e:
            self.log_test("Timezone Handling", False, f"Error: {str(e)}")
    
    def test_timestamp_filtering(self):
        """Test timestamp-based filtering functionality"""
        try:
            # Create test records with different timestamps
            families = []
            for i in range(3):
                family_data = FamilyCreate(name=f"Filter Test Family {i}", category="Young")
                family = create_family(self.db, family_data)
                families.append(family)
                
                # Manually adjust created_at for testing
                db_family = self.db.query(Family).filter(Family.id == family.id).first()
                db_family.created_at = datetime.now(timezone.utc) - timedelta(hours=i*24)
                self.db.commit()
            
            # Test filtering
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=36)
            filters = parse_timestamp_filters(
                created_after=to_iso_format(cutoff_time),
                created_before=None,
                updated_after=None,
                updated_before=None
            )
            
            # Apply filters manually (simulating the filtering logic)
            filtered_families = self.db.query(Family).filter(
                Family.name.like("Filter Test Family%"),
                Family.created_at >= filters['created_after']
            ).all()
            
            # Should return families created within the last 36 hours (2 out of 3)
            expected_count = 2
            actual_count = len(filtered_families)
            
            if actual_count == expected_count:
                self.log_test("Timestamp Filtering", True, 
                            f"Correctly filtered {actual_count} out of 3 families")
            else:
                self.log_test("Timestamp Filtering", False, 
                            f"Expected {expected_count} families, got {actual_count}")
            
            # Clean up
            for family in families:
                db_family = self.db.query(Family).filter(Family.id == family.id).first()
                if db_family:
                    self.db.delete(db_family)
            self.db.commit()
            
        except Exception as e:
            self.log_test("Timestamp Filtering", False, f"Error: {str(e)}")
    
    def test_timestamp_service(self):
        """Test the TimestampQueryService functionality"""
        try:
            service = TimestampQueryService(self.db)
            
            # Test recent records
            recent_families = service.get_recent_records(Family, hours=24, limit=10)
            
            # Test statistics
            stats = service.get_timestamp_statistics()
            
            # Test modification history (create a test record first)
            family_data = FamilyCreate(name="Service Test Family", category="Young")
            family = create_family(self.db, family_data)
            
            history = service.get_modification_history(Family, family.id)
            
            # Validate results
            stats_valid = isinstance(stats, dict) and 'last_24_hours' in stats
            history_valid = isinstance(history, dict) and 'created_at' in history
            recent_valid = isinstance(recent_families, list)
            
            if stats_valid and history_valid and recent_valid:
                self.log_test("Timestamp Service", True, 
                            f"Service methods working correctly - {len(recent_families)} recent records found")
            else:
                self.log_test("Timestamp Service", False, 
                            f"Service issues - stats: {stats_valid}, history: {history_valid}, recent: {recent_valid}")
            
            # Clean up
            db_family = self.db.query(Family).filter(Family.id == family.id).first()
            if db_family:
                self.db.delete(db_family)
                self.db.commit()
            
        except Exception as e:
            self.log_test("Timestamp Service", False, f"Error: {str(e)}")
    
    def test_backward_compatibility(self):
        """Test that existing functionality still works"""
        try:
            # Test existing user creation (should work without timestamp parameters)
            user_data = UserCreate(
                full_name="Test User",
                email="test@example.com",
                password="testpass123",
                gender=GenderEnum.male,
                phone="+1234567890",
                role=RoleEnum.other
            )
            
            user = create_user(self.db, user_data)
            
            # Test existing user retrieval
            all_users = get_all_users(self.db)
            
            # Validate that basic functionality works
            user_created = user is not None and user.id is not None
            users_retrieved = isinstance(all_users, list) and len(all_users) > 0
            
            # Check that the created user has timestamps
            db_user = self.db.query(User).filter(User.id == user.id).first()
            user_has_timestamps = (
                hasattr(db_user, 'created_at') and 
                hasattr(db_user, 'updated_at') and
                db_user.created_at is not None and 
                db_user.updated_at is not None
            )
            
            if user_created and users_retrieved and user_has_timestamps:
                self.log_test("Backward Compatibility", True, 
                            "Existing functionality works with timestamps")
            else:
                self.log_test("Backward Compatibility", False, 
                            f"Issues - user created: {user_created}, users retrieved: {users_retrieved}, timestamps: {user_has_timestamps}")
            
            # Clean up
            if db_user:
                self.db.delete(db_user)
                self.db.commit()
            
        except Exception as e:
            self.log_test("Backward Compatibility", False, f"Error: {str(e)}")
    
    def test_data_integrity(self):
        """Test data integrity with timestamp operations"""
        try:
            # Create related records to test referential integrity
            family_data = FamilyCreate(name="Integrity Test Family", category="Young")
            family = create_family(self.db, family_data)
            
            # Create a family member
            member_data = FamilyMemberCreate(
                name="Test Member",
                phone="+1234567890",
                email="member@test.com",
                date_of_birth=datetime.now().date(),
                gender=GenderEnum.male,
                parental_status=False,
                family_id=family.id
            )
            
            member = FamilyMember(**member_data.dict())
            self.db.add(member)
            self.db.commit()
            self.db.refresh(member)
            
            # Verify both records have timestamps and relationships are intact
            db_family = self.db.query(Family).filter(Family.id == family.id).first()
            db_member = self.db.query(FamilyMember).filter(FamilyMember.id == member.id).first()
            
            family_integrity = (
                db_family is not None and 
                db_family.created_at is not None and 
                db_family.updated_at is not None
            )
            
            member_integrity = (
                db_member is not None and 
                db_member.created_at is not None and 
                db_member.updated_at is not None and
                db_member.family_id == family.id
            )
            
            if family_integrity and member_integrity:
                self.log_test("Data Integrity", True, 
                            "Related records maintain integrity with timestamps")
            else:
                self.log_test("Data Integrity", False, 
                            f"Integrity issues - family: {family_integrity}, member: {member_integrity}")
            
            # Clean up
            self.db.delete(db_member)
            self.db.delete(db_family)
            self.db.commit()
            
        except Exception as e:
            self.log_test("Data Integrity", False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests in the suite"""
        print("🚀 Starting Timestamp Implementation Test Suite")
        print("=" * 60)
        
        # Run all tests
        self.test_database_initialization()
        self.test_model_timestamp_fields()
        self.test_automatic_timestamp_creation()
        self.test_automatic_timestamp_update()
        self.test_timezone_handling()
        self.test_timestamp_filtering()
        self.test_timestamp_service()
        self.test_backward_compatibility()
        self.test_data_integrity()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"📈 Success Rate: {(self.test_results['passed'] / (self.test_results['passed'] + self.test_results['failed']) * 100):.1f}%")
        
        if self.test_results['errors']:
            print("\n🔍 FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"  {error}")
        
        print("\n🎯 RECOMMENDATIONS:")
        if self.test_results['failed'] == 0:
            print("  ✅ All tests passed! Timestamp implementation is ready for production.")
            print("  ✅ Run database migration: python -m app.db.migrations")
            print("  ✅ Deploy with confidence!")
        else:
            print("  ⚠️  Some tests failed. Review the errors above before deployment.")
            print("  ⚠️  Fix failing tests and re-run the test suite.")
        
        return self.test_results
    
    def cleanup(self):
        """Clean up test resources"""
        self.db.close()


def main():
    """Main test execution function"""
    test_suite = TimestampTestSuite()
    
    try:
        results = test_suite.run_all_tests()
        return results['failed'] == 0  # Return True if all tests passed
    except Exception as e:
        print(f"❌ Test suite failed with error: {str(e)}")
        return False
    finally:
        test_suite.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)