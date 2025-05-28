import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock
from datetime import date, datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

try:
    from app.main import app
    from app.database import get_db, Base
    from app.models import User, Book, BookFormat, UserBook, ReadingSession, UserActivity
    from app.utils.security import get_password_hash, create_access_token
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path}")
    raise


@pytest.fixture(scope="function")
def engine():
    """Create test database engine for each test function"""
    test_db_name = f"test_{uuid.uuid4().hex}.db"
    test_database_url = f"sqlite:///./{test_db_name}"
    
    engine = create_engine(
        test_database_url, 
        connect_args={"check_same_thread": False}
    )
    
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    Base.metadata.drop_all(bind=engine)
    
    if os.path.exists(test_db_name):
        os.remove(test_db_name)


@pytest.fixture
def db_session(engine) -> Generator[Session, None, None]:
    """Create isolated test database session"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create FastAPI test client with isolated database"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Generate unique test user data for each test"""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "testpassword123"
    }


@pytest.fixture
def test_user(db_session: Session, test_user_data) -> User:
    """Create test user in database"""
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        hashed_password=get_password_hash(test_user_data["password"]),
        is_active=True,
        created_at=date.today()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create JWT token for authorization"""
    token = create_access_token(subject=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_book_data():
    """Generate unique test book data"""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "title": f"Test Book {unique_id}",
        "author": f"Test Author {unique_id}",
        "description": f"Test description {unique_id}",
        "language": "en",
        "gutenberg_id": int(unique_id[:6], 16),
        "cover_url": f"https://example.com/cover_{unique_id}.jpg"
    }


@pytest.fixture
def test_book(db_session: Session, test_book_data) -> Book:
    """Create test book in database"""
    book = Book(**test_book_data)
    db_session.add(book)
    db_session.commit()
    db_session.refresh(book)
    return book


@pytest.fixture
def test_book_format(db_session: Session, test_book: Book) -> BookFormat:
    """Create test book format"""
    book_format = BookFormat(
        book_id=test_book.id,
        format_type="pdf",
        url="https://example.com/book.pdf"
    )
    db_session.add(book_format)
    db_session.commit()
    db_session.refresh(book_format)
    return book_format


@pytest.fixture
def test_user_book(db_session: Session, test_user: User, test_book: Book) -> UserBook:
    """Create user-book relationship"""
    user_book = UserBook(
        user_id=test_user.id,
        book_id=test_book.id,
        status="Want to read",
        bookmark_position=0,
        is_local=False,
        added_at=datetime.now()
    )
    db_session.add(user_book)
    db_session.commit()
    db_session.refresh(user_book)
    return user_book


@pytest.fixture
def test_reading_session(db_session: Session, test_user_book: UserBook) -> ReadingSession:
    """Create test reading session"""
    reading_session = ReadingSession(
        user_book_id=test_user_book.id,
        start_time=datetime.now(),
        end_time=datetime.now(),
        pages_read=10
    )
    db_session.add(reading_session)
    db_session.commit()
    db_session.refresh(reading_session)
    return reading_session


@pytest.fixture
def mock_gutenberg_response():
    """Mock Gutenberg API response"""
    return {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [{
            "id": 12345,
            "title": "Test Gutenberg Book",
            "authors": [{"name": "Gutenberg Author"}],
            "languages": ["en"],
            "formats": {
                "application/pdf": "https://example.com/book.pdf",
                "text/html": "https://example.com/book.html",
                "image/jpeg": "https://example.com/cover.jpg"
            }
        }]
    }


@pytest.fixture
def temp_upload_dir():
    """Create temporary upload directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        yield temp_path


@pytest.fixture
def sample_pdf_file():
    """Create simple PDF file for testing"""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000079 00000 n \n0000000173 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n301\n%%EOF"
    return pdf_content


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client"""
    mock_client = AsyncMock()
    return mock_client


@pytest.fixture
def mock_gutenberg_service():
    """Mock Gutenberg service"""
    mock = MagicMock()
    mock.search_books = AsyncMock()
    mock.get_book_by_id = AsyncMock()
    mock.map_gutenberg_to_book = MagicMock()
    return mock


@pytest.fixture
def mock_activity_service():
    """Mock Activity service"""
    mock = MagicMock()
    mock.log_activity = MagicMock()
    return mock


@pytest.fixture
def mock_file_service():
    """Mock File service"""
    mock = MagicMock()
    mock.upload_book_file = AsyncMock()
    mock.remove_book_file = MagicMock()
    return mock


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "e2e: end-to-end tests")
    config.addinivalue_line("markers", "slow: slow tests")
    config.addinivalue_line("markers", "auth: authentication tests")
    config.addinivalue_line("markers", "books: book tests")
    config.addinivalue_line("markers", "files: file tests")


class TestHelpers:
    """Helper functions for tests"""
    
    @staticmethod
    def create_test_file(content: bytes, filename: str = "test.pdf"):
        """Create test file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{filename.split('.')[-1]}") as tmp:
            tmp.write(content)
            return tmp.name
    
    @staticmethod
    def assert_datetime_close(dt1: datetime, dt2: datetime, delta_seconds: int = 5):
        """Assert that two datetimes are close to each other"""
        assert abs((dt1 - dt2).total_seconds()) <= delta_seconds


@pytest.fixture
def helpers():
    """Test helpers fixture"""
    return TestHelpers