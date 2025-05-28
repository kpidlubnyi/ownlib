import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models import Book, BookFormat, User, UserBook, ReadingSession
from app.schemas import BookCreate, BookFormatCreate, UserBookCreate
from app.utils.files import save_upload_file, get_file_info, remove_file
from app.services.activity import activity_service


class FileService:
    """Service for working with files"""
    
    @staticmethod
    def validate_language_code(language: Optional[str]) -> Optional[str]:
        """
        Validation of the language code.
        The language should be represented by two lowercase Latin letters.
        """
        if not language:
            return None
            
        language = language.strip().lower()
        
        if not re.match(r'^[a-z]{2}$', language):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=""
            )
        
        return language
    
    @staticmethod
    async def upload_book_file(
        db: Session, 
        file: UploadFile, 
        user: User,
        book_title: str, 
        book_language: str, 
        book_author: Optional[str] = None 
    ) -> Dict:
        """
        Uploads a book file with the required title and language.
        Creates a book record in the database and saves the file.
        """
        if not book_title or not book_title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The title of the book is required"
            )
        
        if not book_language or not book_language.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The language of the book is mandatory"
            )
        file_extension = file.filename.split('.')[-1].lower()
        allowed_formats = ["pdf", "epub", "html", "txt"]
        
        if file_extension not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format. Supported formats: {', '.join(allowed_formats)}"
            )
        
        validated_language = FileService.validate_language_code(book_language.strip())
        
        relative_path, file_path = save_upload_file(file, user.id)
        
        try:
            file_info = get_file_info(file_path)
        except Exception as e:
            file_info = {
                "file_extension": f".{file_extension}",
                "pages": None,
                "title": None,
                "author": None
            }
            print(f"Error reading a file: {e}")
        
        format_mapping = {
            ".pdf": "pdf",
            ".epub": "epub",
            ".html": "html",
            ".txt": "text"
        }
        format_type = format_mapping.get(file_info["file_extension"], "pdf")
        
        book_data = {
            "title": book_title.strip(),
            "author": book_author.strip() if book_author else "Unknown author",
            "description": None,
            "language": validated_language,
            "gutenberg_id": None,
            "cover_url": None
        }
        
        book_in = BookCreate(**book_data)
        db_book = Book(**book_in.dict())
        db.add(db_book)
        db.commit()
        db.refresh(db_book)

        try:
            activity_service.log_activity(
                db=db,
                user_id=user.id,
                activity_type="book_uploaded",
                book_id=db_book.id,
                details={
                    "book_title": db_book.title,
                    "book_author": db_book.author,
                    "book_language": db_book.language,
                    "format": format_type,
                    "file_size": file_info.get("file_size", 0),
                    "pages": file_info.get("pages")
                }
            )
        except Exception as e:
            print(f"Error logging book download activity: {e}")
        
        db_format = BookFormat(
            book_id=db_book.id,
            format_type=format_type,
            url=relative_path
        )
        db.add(db_format)
        
        db_user_book = UserBook(
            user_id=user.id,
            book_id=db_book.id,
            status="Want to read",
            bookmark_position=0,
            is_local=True,
            file_path=relative_path,
            added_at=datetime.now()
        )
        db.add(db_user_book)
        db.commit()
        db.refresh(db_user_book)
        
        return {
            "book_id": db_book.id,
            "title": db_book.title,
            "author": db_book.author,
            "language": db_book.language,
            "format": format_type,
            "file_path": relative_path,
            "pages": file_info.get("pages"),
            "user_book_id": db_user_book.id
        }
    
    @staticmethod
    def remove_book_file(db: Session, user_book_id: int, user_id: int) -> bool:
        """
        Deletes a workbook file and its associated database records.
        Deletes a file from the file system, all associated records, and read sessions.
        """
        user_book = db.query(UserBook).filter(
            UserBook.id == user_book_id,
            UserBook.user_id == user_id,
            UserBook.is_local == True  
        ).first()
        
        if not user_book or not user_book.file_path:
            return False
        
        book_id = user_book.book_id
        
        try:
            file_removed = remove_file(user_book.file_path)
            if not file_removed:
                print(f"Warning: file {user_book.file_path} could not be found to delete")
        except Exception as e:
            print(f"Error when deleting a file {user_book.file_path}: {e}")
        
        reading_sessions = db.query(ReadingSession).filter(
            ReadingSession.user_book_id == user_book_id
        ).all()
        
        for session in reading_sessions:
            db.delete(session)

        try:
            activity_service.log_activity(
                db=db,
                user_id=user_id,
                activity_type="book_removed",
                book_id=book_id,
                details={
                    "book_title": user_book.book.title,
                    "book_author": user_book.book.author,
                    "was_local": True,
                    "file_path": user_book.file_path
                }
            )
        except Exception as e:
            print(f"Error logging book deletion activity: {e}")
        
        db.delete(user_book)
        
        other_users_with_book = db.query(UserBook).filter(
            UserBook.book_id == book_id,
            UserBook.id != user_book_id
        ).count()
        
        if other_users_with_book == 0:
            book_formats = db.query(BookFormat).filter(BookFormat.book_id == book_id).all()
            for format in book_formats:
                db.delete(format)
            
            book = db.query(Book).filter(Book.id == book_id).first()
            if book:
                db.delete(book)
        
        db.commit()
        return True
    
    @staticmethod
    def remove_user_book_from_collection(db: Session, user_book_id: int, user_id: int) -> bool:
        """
        Deletes a book from the user's collection.
        For local books, it also deletes the file and records from the database.
        For online books, it simply deletes the connection to the user.
        """
        user_book = db.query(UserBook).filter(
            UserBook.id == user_book_id,
            UserBook.user_id == user_id
        ).first()
        
        if not user_book:
            return False
        
        if user_book.is_local:
            return FileService.remove_book_file(db, user_book_id, user_id)
        
        reading_sessions = db.query(ReadingSession).filter(
            ReadingSession.user_book_id == user_book_id
        ).all()
        
        for session in reading_sessions:
            db.delete(session)
        
        db.delete(user_book)
        db.commit()
        return True
    
    @staticmethod
    def get_user_book_details(db: Session, user_book_id: int, user_id: int) -> Optional[Dict]:
        """
        Get detailed information about a user's book
        """
        user_book = db.query(UserBook).filter(
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
                "cover_url": user_book.book.cover_url
            } if user_book.book else None
        }
    
    @staticmethod
    def cleanup_orphaned_books(db: Session) -> int:
        """
        Clearing orphan books (books without users).
        Returns the number of deleted books.
        """
        orphaned_books = db.query(Book).outerjoin(UserBook).filter(
            UserBook.book_id.is_(None)
        ).all()
        
        count = 0
        for book in orphaned_books:
            book_formats = db.query(BookFormat).filter(BookFormat.book_id == book.id).all()
            for format in book_formats:
                db.delete(format)
            
            db.delete(book)
            count += 1
        
        if count > 0:
            db.commit()
            print(f"Deleted {count} orphan books")
        
        return count
    
    @staticmethod
    def cleanup_orphaned_files(db: Session) -> int:
        """
        Clearing orphan files (files without records in the database).
        Returns the number of deleted files.
        """
        from pathlib import Path
        from app.config import UPLOAD_DIR_PATH
        
        if not UPLOAD_DIR_PATH.exists():
            return 0
        
        count = 0
        
        db_files = set()
        user_books = db.query(UserBook).filter(
            UserBook.is_local == True,
            UserBook.file_path.isnot(None)
        ).all()
        
        for user_book in user_books:
            if user_book.file_path:
                db_files.add(user_book.file_path)
        
        for user_dir in UPLOAD_DIR_PATH.iterdir():
            if user_dir.is_dir() and user_dir.name.isdigit():
                for file_path in user_dir.iterdir():
                    if file_path.is_file():
                        relative_path = f"{user_dir.name}/{file_path.name}"
                        
                        if relative_path not in db_files:
                            try:
                                file_path.unlink()
                                count += 1
                                print(f"Deleted an orphan file: {relative_path}")
                            except Exception as e:
                                print(f"File deletion error {relative_path}: {e}")
        
        return count


file_service = FileService()