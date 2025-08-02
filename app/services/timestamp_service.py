"""
Service for handling complex timestamp-based queries and operations.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.ext.declarative import DeclarativeMeta

from app.utils.timestamps import parse_timestamp_filters, to_iso_format
from app.models.user import User
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.family_activity import Activity
from app.models.announcement import Announcement
from app.models.shared_document import SharedDocument
from app.models.family_document import FamilyDocument


class TimestampQueryService:
    """Service for advanced timestamp-based queries"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_recent_records(
        self, 
        model_class: Type[DeclarativeMeta], 
        hours: int = 24,
        limit: int = 50
    ) -> List[Any]:
        """Get records created or updated within the last N hours"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = self.db.query(model_class).filter(
            or_(
                model_class.created_at >= cutoff_time,
                model_class.updated_at >= cutoff_time
            )
        ).order_by(desc(model_class.updated_at)).limit(limit)
        
        return query.all()
    
    def get_activity_timeline(
        self,
        family_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get a timeline of all activities across different models"""
        
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)
        
        timeline = {
            'users': [],
            'families': [],
            'family_members': [],
            'activities': [],
            'announcements': [],
            'documents': []
        }
        
        # Users
        user_query = self.db.query(User).filter(
            User.created_at.between(start_date, end_date)
        )
        if family_id:
            user_query = user_query.filter(User.family_id == family_id)
        
        for user in user_query.order_by(desc(User.created_at)).limit(limit):
            timeline['users'].append({
                'id': user.id,
                'type': 'user_created',
                'title': f"User {user.full_name} created",
                'timestamp': to_iso_format(user.created_at),
                'data': {
                    'user_id': user.id,
                    'full_name': user.full_name,
                    'role': user.role,
                    'family_id': user.family_id
                }
            })
        
        # Family Members
        if family_id:
            member_query = self.db.query(FamilyMember).filter(
                FamilyMember.family_id == family_id,
                FamilyMember.created_at.between(start_date, end_date)
            )
            
            for member in member_query.order_by(desc(FamilyMember.created_at)).limit(limit):
                timeline['family_members'].append({
                    'id': member.id,
                    'type': 'member_created',
                    'title': f"Family member {member.name} added",
                    'timestamp': to_iso_format(member.created_at),
                    'data': {
                        'member_id': member.id,
                        'name': member.name,
                        'family_id': member.family_id
                    }
                })
        
        # Activities
        activity_query = self.db.query(Activity).filter(
            Activity.created_at.between(start_date, end_date)
        )
        if family_id:
            activity_query = activity_query.filter(Activity.family_id == family_id)
        
        for activity in activity_query.order_by(desc(Activity.created_at)).limit(limit):
            timeline['activities'].append({
                'id': activity.id,
                'type': 'activity_created',
                'title': f"Activity: {activity.type}",
                'timestamp': to_iso_format(activity.created_at),
                'data': {
                    'activity_id': activity.id,
                    'type': activity.type,
                    'category': activity.category,
                    'status': activity.status,
                    'family_id': activity.family_id
                }
            })
        
        # Announcements
        announcement_query = self.db.query(Announcement).filter(
            Announcement.created_at.between(start_date, end_date)
        ).order_by(desc(Announcement.created_at)).limit(limit)
        
        for announcement in announcement_query:
            timeline['announcements'].append({
                'id': announcement.id,
                'type': 'announcement_created',
                'title': f"Announcement: {announcement.title}",
                'timestamp': to_iso_format(announcement.created_at),
                'data': {
                    'announcement_id': announcement.id,
                    'title': announcement.title,
                    'type': announcement.type,
                    'user_id': announcement.user_id
                }
            })
        
        return timeline
    
    def get_modification_history(
        self,
        model_class: Type[DeclarativeMeta],
        record_id: int,
        include_related: bool = False
    ) -> Dict[str, Any]:
        """Get modification history for a specific record"""
        
        record = self.db.query(model_class).filter(model_class.id == record_id).first()
        if not record:
            return {}
        
        history = {
            'record_id': record_id,
            'model': model_class.__name__,
            'created_at': to_iso_format(record.created_at),
            'updated_at': to_iso_format(record.updated_at),
            'last_modified': to_iso_format(record.updated_at),
            'age_hours': (datetime.now(timezone.utc) - record.created_at).total_seconds() / 3600,
            'modified_recently': (datetime.now(timezone.utc) - record.updated_at).total_seconds() < 3600,
        }
        
        # Add model-specific information
        if hasattr(record, 'name'):
            history['name'] = record.name
        elif hasattr(record, 'title'):
            history['title'] = record.title
        elif hasattr(record, 'full_name'):
            history['full_name'] = record.full_name
        
        return history
    
    def get_timestamp_statistics(self) -> Dict[str, Any]:
        """Get statistics about record creation and modification patterns"""
        
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        last_week = now - timedelta(days=7)
        last_month = now - timedelta(days=30)
        
        stats = {
            'last_24_hours': {},
            'last_week': {},
            'last_month': {},
            'total_records': {}
        }
        
        models = [User, Family, FamilyMember, Activity, Announcement, SharedDocument, FamilyDocument]
        
        for model in models:
            model_name = model.__name__.lower()
            
            # Last 24 hours
            stats['last_24_hours'][model_name] = {
                'created': self.db.query(model).filter(model.created_at >= last_24h).count(),
                'updated': self.db.query(model).filter(model.updated_at >= last_24h).count()
            }
            
            # Last week
            stats['last_week'][model_name] = {
                'created': self.db.query(model).filter(model.created_at >= last_week).count(),
                'updated': self.db.query(model).filter(model.updated_at >= last_week).count()
            }
            
            # Last month
            stats['last_month'][model_name] = {
                'created': self.db.query(model).filter(model.created_at >= last_month).count(),
                'updated': self.db.query(model).filter(model.updated_at >= last_month).count()
            }
            
            # Total records
            stats['total_records'][model_name] = self.db.query(model).count()
        
        return stats
    
    def find_stale_records(
        self,
        model_class: Type[DeclarativeMeta],
        days_threshold: int = 30
    ) -> List[Any]:
        """Find records that haven't been updated in a specified number of days"""
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        
        query = self.db.query(model_class).filter(
            model_class.updated_at < cutoff_date
        ).order_by(asc(model_class.updated_at))
        
        return query.all()
    
    def get_most_active_periods(
        self,
        model_class: Type[DeclarativeMeta],
        days: int = 30
    ) -> Dict[str, int]:
        """Get the most active periods for record creation/updates"""
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Group by hour of day
        hourly_activity = {}
        
        records = self.db.query(model_class).filter(
            model_class.created_at >= start_date
        ).all()
        
        for record in records:
            hour = record.created_at.hour
            hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
        
        return dict(sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True))