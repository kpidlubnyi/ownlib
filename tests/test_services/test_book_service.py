import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.services.book import BookService, book_service
from app.models import Book, BookFormat, UserBook, User
from app.schemas import BookCreate, BookFormatCreate, UserBookCreate


@pytest.mark.unit
class TestBookService:
    """Test BookService"""
    
    def test_create_book(self, db_session: Session):
        """Test book creation"""
        unique_id = uuid.uuid4().hex[:8]
        book_data = BookCreate(
            title=f"Test Book {unique_id}",
            author=f"Test Author {unique_id}",
            description="Test description",
            language="en"
        )
        
        created_book = book_service.create_book(db_session, book_data)
        
        assert created_book.id is not None
        assert created_book.title == book_data.title
        assert created_book.author == book_data.author
        assert created_book.language == book_data.language
        
        db_book = db_session.query(Book).filter(Book.id == created_book.id).first()
        assert db_book is not None
        assert db_book.title == book_data.title
    
    def test_create_book_format(self, db_session: Session, test_book: Book):
        """Test book format creation"""
        format_data = BookFormatCreate(
            book_id=test_book.id,
            format_type="pdf",
            url="https://example.com/book.pdf"
        )
        
        created_format = book_service.create_book_format(db_session, format_data)
        
        assert created_format.id is not None
        assert created_format.book_id == test_book.id
        assert created_format.format_type == "pdf"
        assert created_format.url == format_data.url
    
    def test_get_book_exists(self, db_session: Session, test_book: Book):
        """Test getting existing book"""
        found_book = book_service.get_book(db_session, test_book.id)
        
        assert found_book is not None
        assert found_book.id == test_book.id
        assert found_book.title == test_book.title
    
    def test_get_book_not_exists(self, db_session: Session):
        """Test getting non-existent book"""
        found_book = book_service.get_book(db_session, 99999)
        assert found_book is None
    
    def test_get_books_catalog_empty(self, db_session: Session):
        """Test getting empty catalog"""
        result = book_service.get_books_catalog(db_session)
        
        assert result["total"] == 0
        assert result["books"] == []
        assert result["page"] == 1
        assert result["pages"] == 0
        assert result["has_next"] is False
        assert result["has_prev"] is False
    
    def test_get_books_catalog_with_books(self, db_session: Session):
        """Test catalog with books"""
        unique_id = uuid.uuid4().hex[:8]
        books = []
        for i in range(5):
            book = Book(
                title=f"Book {unique_id}_{i}",
                author=f"Author {unique_id}_{i}",
                language="en"
            )
            db_session.add(book)
            books.append(book)
        db_session.commit()
        
        result = book_service.get_books_catalog(db_session)
        
        assert result["total"] == 5
        assert len(result["books"]) == 5
        assert result["page"] == 1
        assert result["pages"] == 1
        assert result["has_next"] is False
        assert result["has_prev"] is False
    
    def test_get_books_catalog_pagination(self, db_session: Session):
        """Test catalog pagination"""
        unique_id = uuid.uuid4().hex[:8]
        for i in range(25):
            book = Book(title=f"Book {unique_id}_{i}", language="en")
            db_session.add(book)
        db_session.commit()
        
        result = book_service.get_books_catalog(db_session, skip=0, limit=10)
        assert result["total"] == 25
        assert len(result["books"]) == 10
        assert result["page"] == 1
        assert result["pages"] == 3
        assert result["has_next"] is True
        assert result["has_prev"] is False
        
        result = book_service.get_books_catalog(db_session, skip=10, limit=10)
        assert result["page"] == 2
        assert result["has_next"] is True
        assert result["has_prev"] is True
        
        result = book_service.get_books_catalog(db_session, skip=20, limit=10)
        assert result["page"] == 3
        assert len(result["books"]) == 5
        assert result["has_next"] is False
        assert result["has_prev"] is True
    
    def test_get_books_catalog_search(self, db_session: Session):
        """Test catalog search"""
        unique_id = uuid.uuid4().hex[:8]
        book1 = Book(title=f"Python Programming {unique_id}", author=f"John Doe {unique_id}")
        book2 = Book(title=f"JavaScript Guide {unique_id}", author=f"Jane Smith {unique_id}")
        book3 = Book(title=f"Data Science {unique_id}", description=f"Python for data analysis {unique_id}")
        
        db_session.add_all([book1, book2, book3])
        db_session.commit()
        
        result = book_service.get_books_catalog(db_session, search="Python")
        assert result["total"] == 2
        titles = [book["title"] for book in result["books"]]
        assert any("Python Programming" in title for title in titles)
        assert any("Data Science" in title for title in titles)
        
        result = book_service.get_books_catalog(db_session, search="Jane")
        assert result["total"] == 1
        assert any("Jane Smith" in book["author"] for book in result["books"])
        
        result = book_service.get_books_catalog(db_session, search="data analysis")
        assert result["total"] == 1
        assert any("Data Science" in book["title"] for book in result["books"])
    
    def test_get_books_catalog_filters(self, db_session: Session):
        """Test catalog filters"""
        unique_id = uuid.uuid4().hex[:8]
        book1 = Book(title=f"English Book {unique_id}", author=f"John Doe {unique_id}", language="en")
        book2 = Book(title=f"Ukrainian Book {unique_id}", author=f"Ivan Petrenko {unique_id}", language="uk")
        book3 = Book(title=f"Another English {unique_id}", author=f"Jane Smith {unique_id}", language="en")
        
        db_session.add_all([book1, book2, book3])
        db_session.commit()
        
        result = book_service.get_books_catalog(db_session, language="en")
        assert result["total"] == 2
        
        result = book_service.get_books_catalog(db_session, language="uk")
        assert result["total"] == 1
        assert any("Ukrainian Book" in book["title"] for book in result["books"])
        
        result = book_service.get_books_catalog(db_session, author="John")
        assert result["total"] == 1
        assert any("John Doe" in book["author"] for book in result["books"])
    
    def test_get_books_catalog_sorting(self, db_session: Session):
        """Test catalog sorting"""
        unique_id = uuid.uuid4().hex[:8]
        book1 = Book(title=f"Zebra {unique_id}", author=f"Alpha {unique_id}")
        book2 = Book(title=f"Alpha {unique_id}", author=f"Zebra {unique_id}")
        book3 = Book(title=f"Beta {unique_id}", author=f"Beta {unique_id}")
        
        db_session.add_all([book1, book2, book3])
        db_session.commit()
        
        result = book_service.get_books_catalog(db_session, sort_by="title", sort_order="asc")
        titles = [book["title"] for book in result["books"]]
        alpha_title = next(t for t in titles if "Alpha" in t)
        beta_title = next(t for t in titles if "Beta" in t)
        zebra_title = next(t for t in titles if "Zebra" in t)
        assert titles.index(alpha_title) < titles.index(beta_title) < titles.index(zebra_title)
        
        result = book_service.get_books_catalog(db_session, sort_by="title", sort_order="desc")
        titles = [book["title"] for book in result["books"]]
        alpha_title = next(t for t in titles if "Alpha" in t)
        beta_title = next(t for t in titles if "Beta" in t)
        zebra_title = next(t for t in titles if "Zebra" in t)
        assert titles.index(zebra_title) < titles.index(beta_title) < titles.index(alpha_title)
        
        result = book_service.get_books_catalog(db_session, sort_by="author", sort_order="asc")
        authors = [book["author"] for book in result["books"]]
        alpha_author = next(a for a in authors if "Alpha" in a)
        beta_author = next(a for a in authors if "Beta" in a)
        zebra_author = next(a for a in authors if "Zebra" in a)
        assert authors.index(alpha_author) < authors.index(beta_author) < authors.index(zebra_author)
    
    def test_get_available_languages(self, db_session: Session):
        """Test getting available languages"""
        unique_id = uuid.uuid4().hex[:8]
        book1 = Book(title=f"Book 1 {unique_id}", language="en")
        book2 = Book(title=f"Book 2 {unique_id}", language="uk")
        book3 = Book(title=f"Book 3 {unique_id}", language="en")
        book4 = Book(title=f"Book 4 {unique_id}", language=None)
        book5 = Book(title=f"Book 5 {unique_id}", language="")
        
        db_session.add_all([book1, book2, book3, book4, book5])
        db_session.commit()
        
        languages = book_service.get_available_languages(db_session)
        assert set(languages) == {"en", "uk"}
    
    def test_get_available_authors(self, db_session: Session):
        """Test getting available authors"""
        unique_id = uuid.uuid4().hex[:8]
        book1 = Book(title=f"Book 1 {unique_id}", author=f"John Doe {unique_id}")
        book2 = Book(title=f"Book 2 {unique_id}", author=f"Jane Smith {unique_id}")
        book3 = Book(title=f"Book 3 {unique_id}", author=f"John Doe {unique_id}")
        book4 = Book(title=f"Book 4 {unique_id}", author=None)
        book5 = Book(title=f"Book 5 {unique_id}", author="")
        
        db_session.add_all([book1, book2, book3, book4, book5])
        db_session.commit()
        
        authors = book_service.get_available_authors(db_session)
        expected_authors = {f"John Doe {unique_id}", f"Jane Smith {unique_id}"}
        assert set(authors) == expected_authors
        
        authors = book_service.get_available_authors(db_session, search="John")
        assert f"John Doe {unique_id}" in authors
        assert f"Jane Smith {unique_id}" not in authors
        
        authors = book_service.get_available_authors(db_session, limit=1)
        assert len(authors) == 1
    
    def test_add_book_to_user(self, db_session: Session):
        """Test adding book to user"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"Test Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        user_book_data = UserBookCreate(
            status="Want to read",
            bookmark_position=0,
            is_local=False
        )
        
        user_book = book_service.add_book_to_user(db_session, user, book.id, user_book_data)
        
        assert user_book.id is not None
        assert user_book.user_id == user.id
        assert user_book.book_id == book.id
        assert user_book.status == "Want to read"
        assert user_book.bookmark_position == 0
        assert user_book.is_local is False
        assert user_book.added_at is not None
    
    def test_add_book_to_user_duplicate(self, db_session: Session):
        """Test adding duplicate book to user"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"Test Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        existing_user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read",
            bookmark_position=0
        )
        db_session.add(existing_user_book)
        db_session.commit()
        
        user_book_data = UserBookCreate(
            status="reading",
            bookmark_position=50,
            is_local=False
        )
        
        updated_user_book = book_service.add_book_to_user(db_session, user, book.id, user_book_data)
        
        assert updated_user_book.id == existing_user_book.id
        assert updated_user_book.status == "reading"
        assert updated_user_book.bookmark_position == 50
    
    def test_get_user_books(self, db_session: Session):
        """Test getting user books"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"Test Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read"
        )
        db_session.add(user_book)
        db_session.commit()
        
        user_books = book_service.get_user_books(db_session, user.id)
        
        assert len(user_books) == 1
        assert user_books[0].id == user_book.id
        assert user_books[0].user_id == user.id
    
    def test_get_user_books_by_status(self, db_session: Session):
        """Test getting user books by status"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        books = []
        for i in range(3):
            book = Book(title=f"Book {unique_id}_{i}")
            db_session.add(book)
            books.append(book)
        db_session.flush()
        
        statuses = ["Want to read", "reading", "read"]
        for i, status in enumerate(statuses):
            user_book = UserBook(user_id=user.id, book_id=books[i].id, status=status)
            db_session.add(user_book)
        db_session.commit()
        
        reading_books = book_service.get_user_books(db_session, user.id, status_filter="reading")
        assert len(reading_books) == 1
        assert reading_books[0].status == "reading"
        
        all_books = book_service.get_user_books(db_session, user.id)
        assert len(all_books) == 3
    
    def test_remove_book_from_user(self, db_session: Session):
        """Test removing book from user"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"Test Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read"
        )
        db_session.add(user_book)
        db_session.commit()
        
        result = book_service.remove_book_from_user(db_session, user.id, book.id)
        assert result is True
        
        removed_user_book = db_session.query(UserBook).filter(
            UserBook.user_id == user.id,
            UserBook.book_id == book.id
        ).first()
        assert removed_user_book is None
    
    def test_remove_book_from_user_not_exists(self, db_session: Session):
        """Test removing non-existent book from user"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        result = book_service.remove_book_from_user(db_session, user.id, 99999)
        assert result is False
    
    def test_is_book_in_user_collection(self, db_session: Session):
        """Test checking if book is in user collection"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        book = Book(title=f"Test Book {unique_id}")
        db_session.add_all([user, book])
        db_session.flush()
        
        user_book = UserBook(
            user_id=user.id,
            book_id=book.id,
            status="Want to read"
        )
        db_session.add(user_book)
        db_session.commit()
        
        found_user_book = book_service.is_book_in_user_collection(db_session, user.id, book.id)
        assert found_user_book is not None
        assert found_user_book.id == user_book.id
        
        not_found_user_book = book_service.is_book_in_user_collection(db_session, user.id, 99999)
        assert not_found_user_book is None


@pytest.mark.integration
class TestBookServiceIntegration:
    """Integration tests for BookService"""
    
    def test_complex_catalog_query(self, db_session: Session):
        """Test complex catalog query"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        books_data = [
            (f"Python Programming {unique_id}", f"John Doe {unique_id}", f"Programming with Python {unique_id}", "en"),
            (f"JavaScript Guide {unique_id}", f"Jane Smith {unique_id}", f"Learn JavaScript {unique_id}", "en"),
            (f"Ukrainian Literature {unique_id}", f"Taras Shevchenko {unique_id}", f"Collection of works {unique_id}", "uk"),
            (f"Data Science {unique_id}", f"Bob Johnson {unique_id}", f"Python for data analysis {unique_id}", "en"),
            (f"Ruby Development {unique_id}", f"Alice Wilson {unique_id}", f"Web development with Ruby {unique_id}", "en"),
        ]
        
        books = []
        for title, author, description, language in books_data:
            book = Book(title=title, author=author, description=description, language=language)
            db_session.add(book)
            books.append(book)
        db_session.commit()
        
        user_book1 = UserBook(user_id=user.id, book_id=books[0].id, status="reading")
        user_book2 = UserBook(user_id=user.id, book_id=books[2].id, status="Want to read")
        db_session.add_all([user_book1, user_book2])
        db_session.commit()
        
        result = book_service.get_books_with_user_status(
            db_session,
            user.id,
            search="Python",
            language="en",
            sort_by="title",
            sort_order="asc"
        )
        
        assert result["total"] == 2
        titles = [book["title"] for book in result["books"]]
        data_science_title = next(t for t in titles if "Data Science" in t)
        python_title = next(t for t in titles if "Python Programming" in t)
        assert titles.index(data_science_title) < titles.index(python_title)
        
        python_book = next(book for book in result["books"] if "Python Programming" in book["title"])
        assert python_book["in_collection"] is True
        assert python_book["user_status"] == "reading"
        
        data_science_book = next(book for book in result["books"] if "Data Science" in book["title"])
        assert data_science_book["in_collection"] is False
        
        result = book_service.get_books_catalog(
            db_session,
            author="John",
            skip=0,
            limit=1
        )
        
        assert result["total"] >= 1
        assert len(result["books"]) == 1
        if result["total"] > 1:
            assert result["has_next"] is True
    
    def test_full_book_lifecycle(self, db_session: Session):
        """Test full book lifecycle"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=f"hash_{unique_id}"
        )
        db_session.add(user)
        db_session.flush()
        
        book_data = BookCreate(
            title=f"Lifecycle Book {unique_id}",
            author=f"Test Author {unique_id}",
            description="Test lifecycle",
            language="en"
        )
        
        book = book_service.create_book(db_session, book_data)
        assert book.id is not None
        
        format_data = BookFormatCreate(
            book_id=book.id,
            format_type="pdf",
            url=f"https://example.com/book_{unique_id}.pdf"
        )
        
        book_format = book_service.create_book_format(db_session, format_data)
        assert book_format.id is not None
        
        user_book_data = UserBookCreate(
            status="Want to read",
            bookmark_position=0,
            is_local=False
        )
        
        user_book = book_service.add_book_to_user(db_session, user, book.id, user_book_data)
        assert user_book.id is not None
        
        catalog = book_service.get_books_with_user_status(db_session, user.id)
        assert catalog["total"] >= 1
        book_in_catalog = next(b for b in catalog["books"] if b["id"] == book.id)
        assert book_in_catalog["in_collection"] is True
        assert book_in_catalog["user_status"] == "Want to read"
        
        updated_user_book_data = UserBookCreate(
            status="reading",
            bookmark_position=25,
            is_local=False
        )
        
        updated_user_book = book_service.add_book_to_user(
            db_session, user, book.id, updated_user_book_data
        )
        assert updated_user_book.status == "reading"
        assert updated_user_book.bookmark_position == 25
        
        book_detail = book_service.get_book_detail_with_user_status(db_session, book.id, user.id)
        assert book_detail["user_status"] == "reading"
        assert book_detail["bookmark_position"] == 25
        assert len(book_detail["formats"]) == 1
        assert book_detail["has_readable_formats"] is True
        
        removed = book_service.remove_book_from_user(db_session, user.id, book.id)
        assert removed is True
        
        final_catalog = book_service.get_books_with_user_status(db_session, user.id)
        book_after_removal = next((b for b in final_catalog["books"] if b["id"] == book.id), None)
        if book_after_removal:
            assert book_after_removal["in_collection"] is False
            assert book_after_removal["user_status"] is None