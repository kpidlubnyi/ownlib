from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import Session, joinedload

from app.models import Book, BookFormat, UserBook, User
from app.schemas import BookCreate, BookFormatCreate, UserBookCreate
from app.services.gutendex import gutendex_service as gutenberg_service
from app.services.activity import activity_service

class BookService:
    """Service for working with books"""
    
    @staticmethod
    def create_book(db: Session, book_in: BookCreate) -> Book:
        """Creating a new book"""
        db_book = Book(**book_in.dict())
        db.add(db_book)
        db.commit()
        db.refresh(db_book)
        return db_book
    
    @staticmethod
    def create_book_format(db: Session, format_in: BookFormatCreate) -> BookFormat:
        """Create a new book format"""
        db_format = BookFormat(**format_in.dict())
        db.add(db_format)
        db.commit()
        db.refresh(db_format)
        return db_format
    
    @staticmethod
    def get_book(db: Session, book_id: int) -> Optional[Book]:
        """Receiving a book by ID"""
        return db.query(Book).filter(Book.id == book_id).first()
    
    @staticmethod
    def get_books_catalog(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        language: Optional[str] = None,
        author: Optional[str] = None,
        sort_by: str = "title",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """Get a catalog of books with search, filtering, and sorting"""
        
        from sqlalchemy.orm import joinedload
        query = db.query(Book).options(joinedload(Book.formats))
        
        filters = []
        
        if search:
            search_filter = or_(
                Book.title.ilike(f"%{search}%"),
                Book.author.ilike(f"%{search}%"),
                Book.description.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        if language:
            filters.append(Book.language == language)
        
        if author:
            filters.append(Book.author.ilike(f"%{author}%"))
        
        if filters:
            query = query.filter(and_(*filters))
        
        total_count = query.count()
        
        sort_column = getattr(Book, sort_by, Book.title)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        books = query.offset(skip).limit(limit).all()
        
        books_data = []
        for book in books:
            book_dict = {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "description": book.description,
                "language": book.language,
                "gutenberg_id": book.gutenberg_id,
                "cover_url": book.cover_url,
                "formats": [
                    {
                        "id": fmt.id,
                        "format_type": fmt.format_type,
                        "url": fmt.url
                    } for fmt in book.formats
                ] if book.formats else []
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
    def get_available_languages(db: Session) -> List[str]:
        """Get a list of available languages"""
        languages = db.query(Book.language).filter(
            Book.language.isnot(None),
            Book.language != ""
        ).distinct().all()
        
        return [lang[0] for lang in languages if lang[0]]
    
    @staticmethod
    def get_available_authors(
        db: Session, 
        search: Optional[str] = None, 
        limit: int = 50
    ) -> List[str]:
        """Get a list of available authors"""
        query = db.query(Book.author).filter(
            Book.author.isnot(None),
            Book.author != ""
        )
        
        if search:
            query = query.filter(Book.author.ilike(f"%{search}%"))
        
        authors = query.distinct().limit(limit).all()
        return [author[0] for author in authors if author[0]]
    
    @staticmethod
    def get_books(
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        title_filter: Optional[str] = None,
        author_filter: Optional[str] = None
    ) -> List[Book]:
        """Getting a list of books with the ability to filter (outdated method)"""
        query = db.query(Book)
        
        if title_filter:
            query = query.filter(Book.title.ilike(f"%{title_filter}%"))
        
        if author_filter:
            query = query.filter(Book.author.ilike(f"%{author_filter}%"))
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def add_book_to_user(
        db: Session, 
        user: User, 
        book_id: int, 
        user_book_in: UserBookCreate
    ) -> UserBook:
        """Add a book to a user's collection"""
        existing = db.query(UserBook).filter(
            UserBook.user_id == user.id,
            UserBook.book_id == book_id
        ).first()
        
        if existing:
            for key, value in user_book_in.dict(exclude_unset=True).items():
                if key != 'book_id': 
                    setattr(existing, key, value)
            db.add(existing)
            db.commit()
            db.refresh(existing)
            return existing
        
        user_book_data = user_book_in.dict()
        if 'book_id' in user_book_data:
            user_book_data.pop('book_id')
        
        db_user_book = UserBook(
            **user_book_data,
            user_id=user.id,
            book_id=book_id,  
            added_at=datetime.now()
        )
        db.add(db_user_book)
        db.commit()
        db.refresh(db_user_book)
        activity_service.log_activity(
            db=db,
            user_id=user.id,
            activity_type="book_added",
            book_id=book_id,
            details={
                "status": user_book_in.status,
                "book_title": db_user_book.book.title,
                "book_author": db_user_book.book.author
            }
        )
        return db_user_book
    
    @staticmethod
    def get_user_books(
        db: Session,
        user_id: int,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserBook]:
        """Retrieval of user books with the ability to filter by status"""
        query = db.query(UserBook).filter(UserBook.user_id == user_id)
        
        if status_filter:
            query = query.filter(UserBook.status == status_filter)
        
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def remove_book_from_user(db: Session, user_id: int, book_id: int) -> bool:
        """Delete a book from a user's collection"""
        user_book = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.book_id == book_id
        ).first()
        
        if not user_book:
            return False
        
        activity_service.log_activity(
            db=db,
            user_id=user_id,
            activity_type="book_removed",
            book_id=book_id,
            details={
                "book_title": user_book.book.title,
                "book_author": user_book.book.author
            }
        )
        
        db.delete(user_book)
        db.commit()
        return True
    
    @staticmethod
    def is_book_in_user_collection(db: Session, user_id: int, book_id: int) -> Optional[UserBook]:
        """Check if the book is in the user's collection"""
        return db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.book_id == book_id
        ).first()
    
    @staticmethod
    def get_books_with_user_status(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        language: Optional[str] = None,
        author: Optional[str] = None,
        sort_by: str = "title",
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """Get a catalog of books with information about the status in the user's collection"""
        
        catalog = BookService.get_books_catalog(
            db, skip, limit, search, language, author, sort_by, sort_order
        )
        
        book_ids = [book["id"] for book in catalog["books"]]
        
        if not book_ids:
            for book in catalog["books"]:
                book["user_status"] = None
                book["in_collection"] = False
                book["user_book_id"] = None
            return catalog
        
        user_books = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.book_id.in_(book_ids)
        ).all()
        
        user_book_status = {ub.book_id: ub for ub in user_books}
        
        for book in catalog["books"]:
            user_book = user_book_status.get(book["id"])
            book["user_status"] = user_book.status if user_book else None
            book["in_collection"] = user_book is not None
            book["user_book_id"] = user_book.id if user_book else None
        
        return catalog
    
    @staticmethod
    async def import_book_from_gutenberg(db: Session, gutenberg_id: int) -> Optional[Book]:
        """Import a book from Gutenberg by ID"""
        existing_book = db.query(Book).filter(Book.gutenberg_id == gutenberg_id).first()
        if existing_book:
            return existing_book
        
        try:
            gutenberg_book = await gutenberg_service.get_book_by_id(gutenberg_id)
            book_data = gutenberg_service.map_gutenberg_to_book(gutenberg_book)
            
            book_in = BookCreate(**book_data["book"])
            db_book = BookService.create_book(db, book_in)

            for format_data in book_data["formats"]:
                format_in = BookFormatCreate(**format_data, book_id=db_book.id)
                BookService.create_book_format(db, format_in)
            
            activity_service.log_activity(
                db=db,
                user_id=None,  
                activity_type="gutenberg_imported",
                book_id=db_book.id,
                details={
                    "gutenberg_id": gutenberg_id,
                    "book_title": db_book.title,
                    "book_author": db_book.author
                }
            )
            
            return db_book
        
        except Exception as e:
            print(f"Error importing a book from Gutenberg: {e}")
            return None
    
    @staticmethod
    def get_book_detail_with_user_status(
        db: Session, 
        book_id: int, 
        user_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get full information about the book with information about its status in the user's collection"""
        
        book = db.query(Book).options(joinedload(Book.formats)).filter(Book.id == book_id).first()
        
        if not book:
            return None
        
        user_book = db.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.book_id == book_id
        ).first()
        
        book_detail = {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "description": book.description,
            "language": book.language,
            "gutenberg_id": book.gutenberg_id,
            "cover_url": book.cover_url,
            "formats": [
                {
                    "id": fmt.id,
                    "format_type": fmt.format_type,
                    "url": fmt.url
                } for fmt in book.formats
            ] if book.formats else [],
            
            "in_collection": user_book is not None,
            "user_status": user_book.status if user_book else None,
            "user_book_id": user_book.id if user_book else None,
            "bookmark_position": user_book.bookmark_position if user_book else None,
            "is_local": user_book.is_local if user_book else False,
            "file_path": user_book.file_path if user_book else None,
            "added_at": user_book.added_at.isoformat() if user_book and user_book.added_at else None,
            
            "has_readable_formats": len([fmt for fmt in book.formats if fmt.format_type in ['pdf', 'epub', 'html', 'text']]) > 0 if book.formats else False,
            "available_formats": [fmt.format_type for fmt in book.formats] if book.formats else []
        }
        
        return book_detail


book_service = BookService()