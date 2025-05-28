from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy import func, distinct, and_
from sqlalchemy.orm import Session

from app.models import User, UserBook, ReadingSession, Book


class StatsService:
    """Service for working with reading statistics"""
    
    @staticmethod
    def get_user_reading_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """
        Get general user reading statistics.
        """
        user_sessions_query = (
            db.query(ReadingSession)
            .join(UserBook, ReadingSession.user_book_id == UserBook.id)
            .filter(UserBook.user_id == user_id)
        )
        
        total_sessions = user_sessions_query.count()
        
        total_time = 0
        finished_sessions = user_sessions_query.filter(ReadingSession.end_time != None).all()
        
        for session in finished_sessions:
            if session.end_time and session.start_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60
                total_time += duration
        
        total_pages = db.query(func.sum(UserBook.bookmark_position)).filter(
            UserBook.user_id == user_id,
            UserBook.bookmark_position > 0
        ).scalar() or 0
        
        completed_books = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.status == "read"
        ).count()
        
        dropped_books = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.status == "dropped"
        ).count()
        
        average_speed = 0
        if total_time > 0:
            average_speed = (total_pages / total_time) * 60
        
        reading_now = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.status == "reading"
        ).count()
        
        want_to_read = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.status == "Want to read"
        ).count()
        
        return {
            "total_sessions": total_sessions,
            "total_reading_time": round(total_time), 
            "total_pages_read": total_pages,
            "completed_books": completed_books,
            "dropped_books": dropped_books,  
            "average_reading_speed": round(average_speed, 2), 
            "reading_now": reading_now,
            "want_to_read": want_to_read
        }
    
    @staticmethod
    def get_reading_progress(db: Session, user_id: int, user_book_id: int) -> Dict[str, Any]:
        """
        Get the reading progress of a specific book.
        """
        user_book = db.query(UserBook).filter(
            UserBook.id == user_book_id,
            UserBook.user_id == user_id
        ).first()
        
        if not user_book:
            return {
                "error": "The book was not found in the user's collection"
            }
        
        book = db.query(Book).filter(Book.id == user_book.book_id).first()
        
        if not book:
            return {
                "error": "Book not found"
            }
        

        total_pages = 300 
        current_page = user_book.bookmark_position or 0
        
        percentage = (current_page / total_pages) * 100 if total_pages > 0 else 0
        
        total_time = 0
        sessions = db.query(ReadingSession).filter(
            ReadingSession.user_book_id == user_book_id,
            ReadingSession.end_time != None
        ).all()
        
        for session in sessions:
            if session.end_time and session.start_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60
                total_time += duration
        
        return {
            "book_id": book.id,
            "book_title": book.title,
            "current_page": current_page,
            "total_pages": total_pages,
            "percentage": round(percentage, 2),
            "time_spent": round(total_time),  
            "status": user_book.status
        }
    
    @staticmethod
    def get_language_statistics(db: Session, user_id: int) -> Dict[str, int]:
        """Get book statistics by language"""
        
        language_stats = db.query(
            Book.language,
            func.count(UserBook.id).label('count')
        ).join(
            UserBook, Book.id == UserBook.book_id
        ).filter(
            UserBook.user_id == user_id,
            Book.language.isnot(None)
        ).group_by(Book.language).all()
        
        return {lang: count for lang, count in language_stats}
    
    @staticmethod
    def get_reading_history(
        db: Session, 
        user_id: int, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get reading history for the last N days.
        """
        start_date = datetime.now() - timedelta(days=days)
        
        sessions = (
            db.query(
                ReadingSession.start_time,
                ReadingSession.end_time,
                ReadingSession.pages_read,
                UserBook.book_id,
                Book.title
            )
            .join(UserBook, ReadingSession.user_book_id == UserBook.id)
            .join(Book, UserBook.book_id == Book.id)
            .filter(
                UserBook.user_id == user_id,
                ReadingSession.start_time >= start_date,
                ReadingSession.end_time != None
            )
            .order_by(ReadingSession.start_time)
            .all()
        )
        
        history = []
        for session in sessions:
            if session.end_time and session.start_time:
                duration = (session.end_time - session.start_time).total_seconds() / 60
                
                history.append({
                    "date": session.start_time.date().isoformat(),
                    "book_id": session.book_id,
                    "book_title": session.title,
                    "duration_minutes": round(duration),
                    "pages_read": session.pages_read or 0
                })
        
        return history


stats_service = StatsService()