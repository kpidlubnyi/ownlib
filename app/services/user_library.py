from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import Session, joinedload

from app.models import UserBook, Book, User
from app.schemas import UserBookUpdate
from app.services.activity import activity_service


class UserLibraryService:
    """Service for working with a user's personal library"""
    
    @staticmethod
    def get_user_library(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "added_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get a user's personal library with filtering and search"""
        
        query = db.query(UserBook).join(Book).filter(UserBook.user_id == user_id)
        
        filters = []
        
        if status_filter:
            filters.append(UserBook.status == status_filter)
        
        if search:
            search_filter = or_(
                Book.title.ilike(f"%{search}%"),
                Book.author.ilike(f"%{search}%"),
                Book.description.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        if filters:
            query = query.filter(and_(*filters))
        
        total_count = query.count()
        
        if sort_by == "title":
            sort_column = Book.title
        elif sort_by == "author":
            sort_column = Book.author
        elif sort_by == "status":
            sort_column = UserBook.status
        elif sort_by == "added_at":
            sort_column = UserBook.added_at
        else:
            sort_column = UserBook.added_at
        
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        user_books = query.offset(skip).limit(limit).all()
        
        books_data = []
        for user_book in user_books:
            book_dict = {
                "id": user_book.id,
                "user_id": user_book.user_id,
                "book_id": user_book.book_id,
                "status": user_book.status,
                "bookmark_position": user_book.bookmark_position,
                "is_local": user_book.is_local,
                "file_path": user_book.file_path,
                "added_at": user_book.added_at.isoformat() if user_book.added_at else None,
                "book": {
                    "id": user_book.book.id,
                    "title": user_book.book.title,
                    "author": user_book.book.author,
                    "description": user_book.book.description,
                    "language": user_book.book.language,
                    "gutenberg_id": user_book.book.gutenberg_id,
                    "cover_url": user_book.book.cover_url,
                    "formats": [
                        {
                            "id": fmt.id,
                            "format_type": fmt.format_type,
                            "url": fmt.url
                        } for fmt in user_book.book.formats
                    ] if user_book.book.formats else []
                }
            }
            books_data.append(book_dict)
        
        return {
            "books": books_data,
            "total": total_count,
            "page": (skip // limit) + 1,
            "pages": (total_count + limit - 1) // limit,
            "per_page": limit,
            "has_next": skip + limit < total_count,
            "has_prev": skip > 0
        }
    
    @staticmethod
    def get_user_library_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """Get statistics on the user's personal library"""
        
        total_books = db.query(UserBook).filter(UserBook.user_id == user_id).count()
        
        status_counts = db.query(
            UserBook.status, 
            func.count(UserBook.id)
        ).filter(UserBook.user_id == user_id).group_by(UserBook.status).all()
        
        status_stats = {status: count for status, count in status_counts}
        
        local_books = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.is_local == True
        ).count()
        
        online_books = total_books - local_books
        
        books_with_progress = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.bookmark_position > 0
        ).count()
        
        recent_books_query = db.query(UserBook).join(Book).filter(
            UserBook.user_id == user_id
        ).order_by(desc(UserBook.added_at)).limit(5).all()

        recent_books = []
        for user_book in recent_books_query:
            recent_books.append({
                "id": user_book.book.id,  
                "title": user_book.book.title,
                "author": user_book.book.author,
                "cover_url": user_book.book.cover_url,
                "status": user_book.status,
                "added_at": user_book.added_at.isoformat() if user_book.added_at else None
            })
        
        return {
            "total_books": total_books,
            "status_breakdown": {
                "want_to_read": status_stats.get("Want to read", 0),
                "reading": status_stats.get("reading", 0),
                "read": status_stats.get("read", 0),
                "dropped": status_stats.get("dropped", 0)
            },
            "source_breakdown": {
                "local_books": local_books,
                "online_books": online_books
            },
            "books_with_progress": books_with_progress,
            "recent_additions": recent_books
        }
    
    @staticmethod
    def get_user_book_detail(
        db: Session, 
        user_id: int, 
        user_book_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a book in the user's library"""
        user_book = db.query(UserBook).join(Book).filter(
            UserBook.id == user_book_id,
            UserBook.user_id == user_id
        ).first()
        
        if not user_book:
            return None
        
        return {
            "id": user_book.id,
            "user_id": user_book.user_id,
            "book_id": user_book.book_id,
            "status": user_book.status,
            "bookmark_position": user_book.bookmark_position,
            "is_local": user_book.is_local,
            "file_path": user_book.file_path,
            "added_at": user_book.added_at.isoformat() if user_book.added_at else None,
            "book": {
                "id": user_book.book.id,
                "title": user_book.book.title,
                "author": user_book.book.author,
                "description": user_book.book.description,
                "language": user_book.book.language,
                "gutenberg_id": user_book.book.gutenberg_id,
                "cover_url": user_book.book.cover_url,
                "formats": [
                    {
                        "id": fmt.id,
                        "format_type": fmt.format_type,
                        "url": fmt.url
                    } for fmt in user_book.book.formats
                ] if user_book.book.formats else []
            }
        }
    
    @staticmethod
    def update_user_book(
        db: Session,
        user_id: int,
        user_book_id: int,
        update_data: UserBookUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update information about a book in the user's library"""
        user_book = db.query(UserBook).join(Book).filter(
            UserBook.id == user_book_id,
            UserBook.user_id == user_id
        ).first()
        
        if not user_book:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        old_status = user_book.status

        for field, value in update_dict.items():
            setattr(user_book, field, value)

        db.add(user_book)
        db.commit()
        db.refresh(user_book)

        if 'status' in update_dict and update_dict['status'] != old_status:
            activity_service.log_activity(
                db=db,
                user_id=user_id,
                activity_type="book_status_changed",
                book_id=user_book.book_id,
                details={
                    "old_status": old_status,
                    "new_status": update_dict['status'],
                    "book_title": user_book.book.title,
                    "book_author": user_book.book.author
                }
            )

        if 'bookmark_position' in update_dict:
            activity_service.log_activity(
                db=db,
                user_id=user_id,
                activity_type="bookmark_updated",
                book_id=user_book.book_id,
                details={
                    "position": update_dict['bookmark_position'],
                    "book_title": user_book.book.title
                }
            )
        
        return {
            "id": user_book.id,
            "user_id": user_book.user_id,
            "book_id": user_book.book_id,
            "status": user_book.status,
            "bookmark_position": user_book.bookmark_position,
            "is_local": user_book.is_local,
            "file_path": user_book.file_path,
            "added_at": user_book.added_at.isoformat() if user_book.added_at else None,
            "book": {
                "id": user_book.book.id,
                "title": user_book.book.title,
                "author": user_book.book.author,
                "description": user_book.book.description,
                "language": user_book.book.language,
                "gutenberg_id": user_book.book.gutenberg_id,
                "cover_url": user_book.book.cover_url
            }
        }
    
    @staticmethod
    def remove_book_from_library(
        db: Session, 
        user_id: int, 
        user_book_id: int
    ) -> bool:
        """Delete a book from a user's personal library"""
        user_book = db.query(UserBook).filter(
            UserBook.id == user_book_id,
            UserBook.user_id == user_id
        ).first()
        
        if not user_book:
            return False
        
        db.delete(user_book)
        db.commit()
        return True
    
    @staticmethod
    def get_books_by_status(
        db: Session,
        user_id: int,
        status: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Receive books from the user's library by a specific status"""
        user_books = db.query(UserBook).join(Book).filter(
            UserBook.user_id == user_id,
            UserBook.status == status
        ).offset(skip).limit(limit).all()
        
        books_data = []
        for user_book in user_books:
            books_data.append({
                "id": user_book.id,
                "user_id": user_book.user_id,
                "book_id": user_book.book_id,
                "status": user_book.status,
                "bookmark_position": user_book.bookmark_position,
                "is_local": user_book.is_local,
                "file_path": user_book.file_path,
                "added_at": user_book.added_at.isoformat() if user_book.added_at else None,
                "book": {
                    "id": user_book.book.id,
                    "title": user_book.book.title,
                    "author": user_book.book.author,
                    "description": user_book.book.description,
                    "language": user_book.book.language,
                    "gutenberg_id": user_book.book.gutenberg_id,
                    "cover_url": user_book.book.cover_url
                }
            })
        
        return books_data
    
    @staticmethod
    def get_user_reading_progress(db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Get reading progress for all user books"""
        
        user_books = db.query(UserBook).join(Book).filter(
            UserBook.user_id == user_id,
            UserBook.status.in_(["reading", "read"])
        ).all()
        
        progress_data = []
        
        for user_book in user_books:
            estimated_pages = 300  
            current_page = user_book.bookmark_position or 0
            
            if estimated_pages > 0:
                percentage = min((current_page / estimated_pages) * 100, 100)
            else:
                percentage = 0
            
            progress_data.append({
                "user_book_id": user_book.id,
                "book_id": user_book.book.id,
                "title": user_book.book.title,
                "author": user_book.book.author,
                "status": user_book.status,
                "current_page": current_page,
                "estimated_pages": estimated_pages,
                "percentage": round(percentage, 1),
                "last_read": user_book.added_at.isoformat() if user_book.added_at else None,
                "is_local": user_book.is_local
            })
        
        return progress_data
    
    @staticmethod
    def get_reading_activity(
        db: Session, 
        user_id: int, 
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get the user's reading activity for the last N days"""
        
        from datetime import datetime, timedelta
        start_date = datetime.now() - timedelta(days=days)
        
        recent_activity = db.query(UserBook).join(Book).filter(
            UserBook.user_id == user_id,
            UserBook.added_at >= start_date
        ).order_by(desc(UserBook.added_at)).all()
        
        activity_data = []
        for user_book in recent_activity:
            activity_data.append({
                "date": user_book.added_at.date().isoformat() if user_book.added_at else None,
                "action": "added_book",
                "book_title": user_book.book.title,
                "book_author": user_book.book.author,
                "status": user_book.status
            })
        
        return activity_data


user_library_service = UserLibraryService()