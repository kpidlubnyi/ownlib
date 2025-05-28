from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.models import UserActivity, User, Book


class ActivityService:
    """Service for working with user activity"""
    
    @staticmethod
    def log_activity(
        db: Session,
        user_id: int,
        activity_type: str,
        book_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> UserActivity:
        """Logging of user activity"""
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            book_id=book_id,
            details=details,
            created_at=datetime.now()
        )
        
        db.add(activity)
        db.commit()
        db.refresh(activity)
        
        return activity
    
    @staticmethod
    def get_user_activities(
        db: Session,
        user_id: int,
        days: int = 30,
        activity_types: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[UserActivity]:
        """Get user activity for the last N days"""
        start_date = datetime.now() - timedelta(days=days)
        
        query = db.query(UserActivity).filter(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= start_date
        )
        
        if activity_types:
            query = query.filter(UserActivity.activity_type.in_(activity_types))
        
        return query.order_by(desc(UserActivity.created_at)).limit(limit).all()
    
    @staticmethod
    def get_activity_statistics(
        db: Session,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get user activity statistics"""
        start_date = datetime.now() - timedelta(days=days)
        
        total_activities = db.query(func.count(UserActivity.id)).filter(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= start_date
        ).scalar() or 0
        
        activities_by_type = db.query(
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count')
        ).filter(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= start_date
        ).group_by(UserActivity.activity_type).all()
        
        daily_activities = db.query(
            func.date(UserActivity.created_at).label('date'),
            func.count(UserActivity.id).label('count')
        ).filter(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= start_date
        ).group_by(func.date(UserActivity.created_at)).all()
        
        hourly_activities = db.query(
            func.hour(UserActivity.created_at).label('hour'),
            func.count(UserActivity.id).label('count')
        ).filter(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= start_date
        ).group_by(func.hour(UserActivity.created_at)).all()
        
        return {
            "total_activities": total_activities,
            "activities_by_type": {
                activity_type: count 
                for activity_type, count in activities_by_type
            },
            "daily_activities": [
                {
                    "date": date.isoformat() if date else None,
                    "count": count
                }
                for date, count in daily_activities
            ],
            "hourly_activities": {
                hour: count
                for hour, count in hourly_activities
            },
            "period_days": days
        }
    
    @staticmethod
    def get_recent_book_activities(
        db: Session,
        user_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent activity with books"""
        activities = db.query(UserActivity).join(
            Book, UserActivity.book_id == Book.id, isouter=True
        ).filter(
            UserActivity.user_id == user_id,
            UserActivity.book_id.isnot(None)
        ).order_by(desc(UserActivity.created_at)).limit(limit).all()
        
        result = []
        for activity in activities:
            result.append({
                "id": activity.id,
                "activity_type": activity.activity_type,
                "book_id": activity.book_id,
                "book_title": activity.book.title if activity.book else None,
                "book_author": activity.book.author if activity.book else None,
                "details": activity.details,
                "created_at": activity.created_at.isoformat()
            })
        
        return result
    
    @staticmethod
    def cleanup_old_activities(
        db: Session,
        days_to_keep: int = 365
    ) -> int:
        """Delete old activity records"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        deleted = db.query(UserActivity).filter(
            UserActivity.created_at < cutoff_date
        ).delete()
        
        db.commit()
        return deleted


activity_service = ActivityService()