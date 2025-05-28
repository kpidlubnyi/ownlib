import pytest
import uuid
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import User, Book, BookFormat, UserBook, ReadingSession, UserActivity


@pytest.mark.unit
class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, db_session: Session):
        """Test user creation"""
        unique_id = uuid.uuid4().hex[:8]
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password="hashedpassword",
            is_active=True,
            created_at=date.today()
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.username == f"testuser_{unique_id}"
        assert user.email == f"test_{unique_id}@example.com"
        assert user.is_active is True
        assert user.created_at == date.today()
    
    def test_user_unique_constraints(self, db_session: Session):
        """Test user unique constraints"""
        unique_id = uuid.uuid4().hex[:8]
        
        user1 = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password="hash1"
        )
        db_session.add(user1)
        db_session.commit()
        
        user2 = User(
            username=f"testuser_{unique_id}",
            email=f"another_{unique_id}@example.com",
            hashed_password="hash2"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
        
        user3 = User(
            username=f"anotheruser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password="hash3"
        )
        db_session.add(user3)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_user_default_values(self, db_session: Session):
        """Test user default values"""
        unique_id = uuid.uuid4().hex[:8]
        user = User(
            username=f"defaultuser_{unique_id}",
            email=f"default_{unique_id}@example.com",
            hashed_password="hash"
        )
        
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.is_active is True
        assert user.created_at == date.today()
    
    def test_user_relationships(self, db_session: Session):
        """Test user relationships"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"reluser_{unique_id}",
            email=f"rel_{unique_id}@example.com",
            hashed_password="hash"
        )
        db_session.add(user)
        
        book = Book(title=f"Test Book {unique_id}")
        db_session.add(book)
        db_session.flush()
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read"
        )
        db_session.add(user_book)
        
        activity = UserActivity(
            user_id=user.id,
            activity_type="book_added",
            book_id=book.id
        )
        db_session.add(activity)
        db_session.commit()
        
        assert len(user.books) == 1
        assert user.books[0].book_id == book.id
        
        assert len(user.activities) == 1
        assert user.activities[0].activity_type == "book_added"


@pytest.mark.unit
class TestBookModel:
    """Test Book model"""
    
    def test_create_book(self, db_session: Session):
        """Test book creation"""
        unique_id = uuid.uuid4().hex[:8]
        book = Book(
            title=f"Test Book {unique_id}",
            author=f"Test Author {unique_id}",
            description="Test description",
            language="en",
            gutenberg_id=int(unique_id[:6], 16),
            cover_url="https://example.com/cover.jpg"
        )
        
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        
        assert book.id is not None
        assert book.title == f"Test Book {unique_id}"
        assert book.author == f"Test Author {unique_id}"
        assert book.description == "Test description"
        assert book.language == "en"
        assert book.gutenberg_id == int(unique_id[:6], 16)
        assert book.cover_url == "https://example.com/cover.jpg"
    
    def test_book_minimal_data(self, db_session: Session):
        """Test book creation with minimal data"""
        unique_id = uuid.uuid4().hex[:8]
        book = Book(title=f"Minimal Book {unique_id}")
        
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)
        
        assert book.id is not None
        assert book.title == f"Minimal Book {unique_id}"
        assert book.author is None
        assert book.description is None
        assert book.language is None
        assert book.gutenberg_id is None
        assert book.cover_url is None
    
    def test_book_relationships(self, db_session: Session):
        """Test book relationships"""
        unique_id = uuid.uuid4().hex[:8]
        
        book = Book(title=f"Rel Book {unique_id}")
        db_session.add(book)
        
        user = User(
            username=f"reluser_{unique_id}",
            email=f"rel_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        book_format = BookFormat(
            book_id=book.id,
            format_type="pdf",
            url="https://example.com/book.pdf"
        )
        db_session.add(book_format)
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read"
        )
        db_session.add(user_book)
        
        activity = UserActivity(
            user_id=user.id,
            activity_type="book_added",
            book_id=book.id
        )
        db_session.add(activity)
        db_session.commit()
        
        assert len(book.formats) == 1
        assert book.formats[0].format_type == "pdf"
        
        assert len(book.user_books) == 1
        assert book.user_books[0].status == "Want to read"
        
        assert len(book.activities) == 1
        assert book.activities[0].activity_type == "book_added"
    
    def test_book_cascade_delete(self, db_session: Session):
        """Test book cascade delete"""
        unique_id = uuid.uuid4().hex[:8]
        
        book = Book(title=f"Cascade Book {unique_id}")
        db_session.add(book)
        
        user = User(
            username=f"cascadeuser_{unique_id}",
            email=f"cascade_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        book_format = BookFormat(
            book_id=book.id,
            format_type="pdf",
            url="https://example.com/book.pdf"
        )
        db_session.add(book_format)
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read"
        )
        db_session.add(user_book)
        db_session.commit()
        
        book_id = book.id
        format_id = book_format.id
        user_book_id = user_book.id
        
        db_session.delete(book)
        db_session.commit()
        
        assert db_session.query(Book).filter(Book.id == book_id).first() is None
        assert db_session.query(BookFormat).filter(BookFormat.id == format_id).first() is None
        assert db_session.query(UserBook).filter(UserBook.id == user_book_id).first() is None


@pytest.mark.unit
class TestBookFormatModel:
    """Test BookFormat model"""
    
    def test_create_book_format(self, db_session: Session, test_book: Book):
        """Test book format creation"""
        book_format = BookFormat(
            book_id=test_book.id,
            format_type="pdf",
            url="https://example.com/book.pdf"
        )
        
        db_session.add(book_format)
        db_session.commit()
        db_session.refresh(book_format)
        
        assert book_format.id is not None
        assert book_format.book_id == test_book.id
        assert book_format.format_type == "pdf"
        assert book_format.url == "https://example.com/book.pdf"
    
    def test_book_format_enum_constraint(self, db_session: Session, test_book: Book):
        """Test book format enum constraint"""
        valid_formats = ["pdf", "epub", "html", "text"]
        
        for format_type in valid_formats:
            book_format = BookFormat(
                book_id=test_book.id,
                format_type=format_type,
                url=f"https://example.com/book.{format_type}"
            )
            db_session.add(book_format)
        
        db_session.commit()
        
        formats = db_session.query(BookFormat).filter(BookFormat.book_id == test_book.id).all()
        assert len(formats) == 4
    
    def test_book_format_relationship(self, db_session: Session, test_book: Book):
        """Test book format relationship"""
        book_format = BookFormat(
            book_id=test_book.id,
            format_type="pdf",
            url="https://example.com/book.pdf"
        )
        
        db_session.add(book_format)
        db_session.commit()
        
        assert book_format.book is not None
        assert book_format.book.id == test_book.id
        assert book_format.book.title == test_book.title


@pytest.mark.unit
class TestUserBookModel:
    """Test UserBook model"""
    
    def test_create_user_book(self, db_session: Session):
        """Test user book creation"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"ubuser_{unique_id}",
            email=f"ub_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"UB Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="reading",
            bookmark_position=50,
            is_local=True,
            file_path="user1/book.pdf",
            added_at=datetime.now()
        )
        
        db_session.add(user_book)
        db_session.commit()
        db_session.refresh(user_book)
        
        assert user_book.id is not None
        assert user_book.user_id == user.id
        assert user_book.book_id == book.id
        assert user_book.status == "reading"
        assert user_book.bookmark_position == 50
        assert user_book.is_local is True
        assert user_book.file_path == "user1/book.pdf"
        assert user_book.added_at is not None
        
    def test_user_book_status_enum(self, db_session: Session):
        """Test user book status enum"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"enumuser_{unique_id}",
            email=f"enum_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        valid_statuses = ["Want to read", "reading", "read", "dropped"]
        
        for i, status in enumerate(valid_statuses):
            book = Book(title=f"Status Book {unique_id}_{i}")
            db_session.add(book)
            db_session.flush()
            
            user_book = UserBook(
                user_id=user.id,
                book_id=book.id,
                status=status
            )
            db_session.add(user_book)
            db_session.flush()
            
            assert user_book.status == status
        
    def test_user_book_relationships(self, db_session: Session):
        """Test user book relationships"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"reluser_{unique_id}",
            email=f"rel_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"Rel Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read"
        )
        db_session.add(user_book)
        db_session.flush()
        
        reading_session = ReadingSession(
            user_book_id=user_book.id,
            start_time=datetime.now(),
            end_time=datetime.now(),
            pages_read=10
        )
        db_session.add(reading_session)
        db_session.commit()
        
        assert user_book.user is not None
        assert user_book.book is not None
        assert len(user_book.reading_sessions) == 1
        assert user_book.reading_sessions[0].pages_read == 10


@pytest.mark.unit
class TestReadingSessionModel:
    """Test ReadingSession model"""
    
    def test_create_reading_session(self, db_session: Session):
        """Test reading session creation"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"rsuser_{unique_id}",
            email=f"rs_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"RS Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="reading"
        )
        db_session.add(user_book)
        db_session.flush()
        
        start_time = datetime.now()
        end_time = datetime.now()
        
        reading_session = ReadingSession(
            user_book_id=user_book.id,
            start_time=start_time,
            end_time=end_time,
            pages_read=25
        )
        
        db_session.add(reading_session)
        db_session.commit()
        db_session.refresh(reading_session)
        
        assert reading_session.id is not None
        assert reading_session.user_book_id == user_book.id
        assert reading_session.start_time == start_time
        assert reading_session.end_time == end_time
        assert reading_session.pages_read == 25
    
    def test_reading_session_optional_fields(self, db_session: Session, test_user_book: UserBook):
        """Test reading session optional fields"""
        reading_session = ReadingSession(
            user_book_id=test_user_book.id,
            start_time=datetime.now()
        )
        
        db_session.add(reading_session)
        db_session.commit()
        db_session.refresh(reading_session)
        
        assert reading_session.end_time is None
        assert reading_session.pages_read is None
    
    def test_reading_session_relationship(self, db_session: Session, test_user_book: UserBook):
        """Test reading session relationship"""
        reading_session = ReadingSession(
            user_book_id=test_user_book.id,
            start_time=datetime.now()
        )
        
        db_session.add(reading_session)
        db_session.commit()
        
        assert reading_session.user_book is not None
        assert reading_session.user_book.id == test_user_book.id


@pytest.mark.unit
class TestUserActivityModel:
    """Test UserActivity model"""
    
    def test_create_user_activity(self, db_session: Session):
        """Test user activity creation"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"actuser_{unique_id}",
            email=f"act_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"Activity Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        details = {"status": "reading", "book_title": f"Activity Book {unique_id}"}
        
        activity = UserActivity(
            user_id=user.id,
            activity_type="book_status_changed",
            book_id=book.id,
            details=details,
            created_at=datetime.now()
        )
        
        db_session.add(activity)
        db_session.commit()
        db_session.refresh(activity)
        
        assert activity.id is not None
        assert activity.user_id == user.id
        assert activity.activity_type == "book_status_changed"
        assert activity.book_id == book.id
        assert activity.details == details
        assert activity.created_at is not None
    
    def test_user_activity_enum_types(self, db_session: Session):
        """Test user activity enum types"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"enumuser_{unique_id}",
            email=f"enum_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        valid_types = [
            "book_added", "book_removed", "book_status_changed",
            "book_uploaded", "reading_session", "bookmark_updated",
            "data_exported", "data_imported", "profile_updated",
            "gutenberg_imported"
        ]
        
        for i, activity_type in enumerate(valid_types):
            activity = UserActivity(
                user_id=user.id,
                activity_type=activity_type,
                created_at=datetime.now()
            )
            db_session.add(activity)
            db_session.flush()
            
            assert activity.activity_type == activity_type
            
            db_session.delete(activity)
            db_session.flush()
    
    def test_user_activity_optional_book(self, db_session: Session):
        """Test user activity without book"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"optuser_{unique_id}",
            email=f"opt_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        activity = UserActivity(
            user_id=user.id,
            activity_type="profile_updated",
            details={"updated_fields": ["username"]},
            created_at=datetime.now()
        )
        
        db_session.add(activity)
        db_session.commit()
        db_session.refresh(activity)
        
        assert activity.book_id is None
        assert activity.book is None
    
    def test_user_activity_relationships(self, db_session: Session):
        """Test user activity relationships"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"reluser_{unique_id}",
            email=f"rel_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"Activity Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        activity = UserActivity(
            user_id=user.id,
            activity_type="book_added",
            book_id=book.id,
            created_at=datetime.now()
        )
        
        db_session.add(activity)
        db_session.commit()
        
        assert activity.user is not None
        assert activity.user.id == user.id
        assert activity.book is not None
        assert activity.book.id == book.id


@pytest.mark.integration
class TestModelsIntegration:
    """Integration tests for models"""
    
    def test_complete_data_model_workflow(self, db_session: Session):
        """Test complete data model workflow"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"workflow_user_{unique_id}",
            email=f"workflow_{unique_id}@example.com",
            hashed_password=f"hashed_password_{unique_id}",
            is_active=True
        )
        db_session.add(user)
        db_session.flush()
        
        book = Book(
            title=f"Workflow Book {unique_id}",
            author=f"Workflow Author {unique_id}",
            description="Complete workflow test",
            language="en",
            gutenberg_id=int(unique_id[:6], 16)
        )
        db_session.add(book)
        db_session.flush()
        
        formats = [
            BookFormat(book_id=book.id, format_type="pdf", url=f"http://example.com/book_{unique_id}.pdf"),
            BookFormat(book_id=book.id, format_type="epub", url=f"http://example.com/book_{unique_id}.epub"),
        ]
        db_session.add_all(formats)
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read",
            bookmark_position=0,
            is_local=False
        )
        db_session.add(user_book)
        db_session.flush()
        
        add_activity = UserActivity(
            user_id=user.id,
            activity_type="book_added",
            book_id=book.id,
            details={"book_title": book.title, "status": "Want to read"}
        )
        db_session.add(add_activity)
        
        reading_session = ReadingSession(
            user_book_id=user_book.id,
            start_time=datetime.now(),
            end_time=datetime.now(),
            pages_read=50
        )
        db_session.add(reading_session)
        
        user_book.status = "reading"
        user_book.bookmark_position = 50
        
        status_activity = UserActivity(
            user_id=user.id,
            activity_type="book_status_changed",
            book_id=book.id,
            details={
                "old_status": "Want to read",
                "new_status": "reading",
                "bookmark": 50
            }
        )
        db_session.add(status_activity)
        
        db_session.commit()
        
        assert len(user.books) == 1
        assert len(user.activities) == 2
        assert len(book.formats) == 2
        assert len(book.user_books) == 1
        assert len(book.activities) == 2
        assert len(user_book.reading_sessions) == 1
        
        assert user.books[0].status == "reading"
        assert user.books[0].bookmark_position == 50
        assert book.formats[0].format_type in ["pdf", "epub"]
        assert user.activities[0].activity_type in ["book_added", "book_status_changed"]
        assert reading_session.pages_read == 50
    
    def test_cascade_delete_complex(self, db_session: Session):
        """Test complex cascade delete"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"cascade_user_{unique_id}",
            email=f"cascade_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        book = Book(title=f"Cascade Book {unique_id}")
        db_session.add(book)
        db_session.flush()
        
        book_format = BookFormat(
            book_id=book.id,
            format_type="pdf",
            url=f"http://example.com/book_{unique_id}.pdf"
        )
        db_session.add(book_format)
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="reading"
        )
        db_session.add(user_book)
        db_session.flush()
        
        reading_session = ReadingSession(
            user_book_id=user_book.id,
            start_time=datetime.now()
        )
        db_session.add(reading_session)
        
        activities = [
            UserActivity(user_id=user.id, activity_type="book_added", book_id=book.id),
            UserActivity(user_id=user.id, activity_type="reading_session", book_id=book.id),
        ]
        db_session.add_all(activities)
        db_session.commit()
        
        user_id = user.id
        book_id = book.id
        format_id = book_format.id
        user_book_id = user_book.id
        session_id = reading_session.id
        activity_ids = [a.id for a in activities]
        
        db_session.delete(user)
        db_session.commit()
        
        assert db_session.query(User).filter(User.id == user_id).first() is None
        assert db_session.query(UserBook).filter(UserBook.id == user_book_id).first() is None
        assert db_session.query(ReadingSession).filter(ReadingSession.id == session_id).first() is None
        assert db_session.query(UserActivity).filter(UserActivity.id.in_(activity_ids)).count() == 0
        
        assert db_session.query(Book).filter(Book.id == book_id).first() is not None
        assert db_session.query(BookFormat).filter(BookFormat.id == format_id).first() is not None