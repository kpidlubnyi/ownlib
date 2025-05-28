import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Book, BookFormat, UserBook, User


@pytest.mark.books
class TestBooksAPI:
    """Book API Tests"""
    
    def test_get_books_catalog_unauthorized(self, client: TestClient):
        """Test access to the catalog without authorization"""
        response = client.get("/api/books/catalog")
        assert response.status_code == 401
    
    def test_get_books_catalog_empty(self, client: TestClient, auth_headers: dict):
        """Test for getting an empty catalog"""
        response = client.get("/api/books/catalog", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["books"] == []
        assert data["page"] == 1
        assert data["pages"] == 0
    
    def test_get_books_catalog_with_books(
        self, 
        client: TestClient, 
        auth_headers: dict,
        test_book: Book,
        test_book_format: BookFormat
    ):
        """Test of receiving a catalog with books"""
        response = client.get("/api/books/catalog", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["books"]) == 1
        
        book_data = data["books"][0]
        assert book_data["id"] == test_book.id
        assert book_data["title"] == test_book.title
        assert book_data["author"] == test_book.author
        assert book_data["in_collection"] is False
        assert book_data["user_status"] is None
    
    def test_get_books_catalog_with_user_book(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user_book: UserBook
    ):
        """Test the catalog with the user book"""
        response = client.get("/api/books/catalog", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        
        book_data = data["books"][0]
        assert book_data["in_collection"] is True
        assert book_data["user_status"] == test_user_book.status
        assert book_data["user_book_id"] == test_user_book.id
    
    def test_get_books_catalog_pagination(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session
    ):
        """Catalog pagination test"""
        for i in range(25):
            book = Book(
                title=f"Book {i}",
                author=f"Author {i}",
                language="en"
            )
            db_session.add(book)
        db_session.commit()
        
        response = client.get("/api/books/catalog?limit=20", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["books"]) == 20
        assert data["page"] == 1
        assert data["pages"] == 2
        assert data["has_next"] is True
        assert data["has_prev"] is False
        
        response = client.get("/api/books/catalog?skip=20&limit=20", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["books"]) == 5
        assert data["page"] == 2
        assert data["has_next"] is False
        assert data["has_prev"] is True
    
    def test_get_books_catalog_search(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session
    ):
        """Catalog search test"""
        book1 = Book(title="Python Programming", author="John Doe", language="en")
        book2 = Book(title="JavaScript Guide", author="Jane Smith", language="en")
        book3 = Book(title="Data Science with Python", author="Bob Johnson", language="en")
        
        db_session.add_all([book1, book2, book3])
        db_session.commit()
        
        response = client.get("/api/books/catalog?search=Python", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        titles = [book["title"] for book in data["books"]]
        assert "Python Programming" in titles
        assert "Data Science with Python" in titles
        
        response = client.get("/api/books/catalog?search=Jane", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["books"][0]["author"] == "Jane Smith"
    
    def test_get_books_catalog_filters(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session
    ):
        """Test catalog filtering"""
        book1 = Book(title="English Book", author="English Author", language="en")
        book2 = Book(title="Ukrainian Book", author="Ukrainian Author", language="uk")
        book3 = Book(title="Another English", author="Another Author", language="en")
        
        db_session.add_all([book1, book2, book3])
        db_session.commit()
        
        response = client.get("/api/books/catalog?language=en", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        
        response = client.get("/api/books/catalog?author=English", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["books"][0]["author"] == "English Author"
    
    def test_get_books_catalog_sorting(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session
    ):
        """Test catalog sorting"""
        book1 = Book(title="Zebra Book", author="Alpha Author", language="en")
        book2 = Book(title="Alpha Book", author="Zebra Author", language="en")
        book3 = Book(title="Beta Book", author="Beta Author", language="en")
        
        db_session.add_all([book1, book2, book3])
        db_session.commit()
        
        response = client.get("/api/books/catalog?sort_by=title&sort_order=asc", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        titles = [book["title"] for book in data["books"]]
        assert titles == ["Alpha Book", "Beta Book", "Zebra Book"]
        
        response = client.get("/api/books/catalog?sort_by=author&sort_order=desc", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        authors = [book["author"] for book in data["books"]]
        assert authors == ["Zebra Author", "Beta Author", "Alpha Author"]
    
    def test_get_available_languages(self, client: TestClient, auth_headers: dict, db_session: Session):
        """Test for obtaining available languages"""
        book1 = Book(title="Book 1", language="en")
        book2 = Book(title="Book 2", language="uk")
        book3 = Book(title="Book 3", language="en")
        book4 = Book(title="Book 4", language=None)
        
        db_session.add_all([book1, book2, book3, book4])
        db_session.commit()
        
        response = client.get("/api/books/languages", headers=auth_headers)
        assert response.status_code == 200
        languages = response.json()
        assert set(languages) == {"en", "uk"}
    
    def test_get_available_authors(self, client: TestClient, auth_headers: dict, db_session: Session):
        """Test of getting available authors"""
        book1 = Book(title="Book 1", author="John Doe")
        book2 = Book(title="Book 2", author="Jane Smith")
        book3 = Book(title="Book 3", author="John Doe")
        book4 = Book(title="Book 4", author=None)
        
        db_session.add_all([book1, book2, book3, book4])
        db_session.commit()
        
        response = client.get("/api/books/authors", headers=auth_headers)
        assert response.status_code == 200
        authors = response.json()
        assert set(authors) == {"John Doe", "Jane Smith"}
        
        response = client.get("/api/books/authors?search=John", headers=auth_headers)
        assert response.status_code == 200
        authors = response.json()
        assert authors == ["John Doe"]
    
    def test_create_book(self, client: TestClient, auth_headers: dict, test_book_data: dict):
        """Test creating a book"""
        response = client.post("/api/books/", json=test_book_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == test_book_data["title"]
        assert data["author"] == test_book_data["author"]
        assert data["id"] is not None
    
    def test_get_book_by_id(self, client: TestClient, auth_headers: dict, test_book: Book):
        """Test of receiving a book by ID"""
        response = client.get(f"/api/books/{test_book.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_book.id
        assert data["title"] == test_book.title
        assert data["author"] == test_book.author
    
    def test_get_book_not_found(self, client: TestClient, auth_headers: dict):
        """Test for getting a non-existent book"""
        response = client.get("/api/books/99999", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_book_detail_with_user_status(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user_book: UserBook
    ):
        """Test getting detailed information about a book with user status"""
        book_id = test_user_book.book_id
        
        response = client.get(f"/api/books/{book_id}/detail", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == book_id
        assert data["in_collection"] is True
        assert data["user_status"] == test_user_book.status
        assert data["user_book_id"] == test_user_book.id
        assert data["bookmark_position"] == test_user_book.bookmark_position
        
    def test_add_book_to_collection(
        self,
        client: TestClient,
        auth_headers: dict,
        test_book: Book,
        db_session: Session
    ):
        """Test adding a book to the collection"""
        user_book_data = {
            "status": "Want to read",
            "bookmark_position": 0,
            "is_local": False
        }
        
        response = client.post(
            f"/api/books/user-books/{test_book.id}",
            json=user_book_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["status"] == "Want to read"
        
        user_book = db_session.query(UserBook).filter(
            UserBook.book_id == test_book.id
        ).first()
        assert user_book is not None
    
    def test_add_book_to_collection_duplicate(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user_book: UserBook
    ):
        """Test adding a book that is already in the collection"""
        user_book_data = {
            "status": "reading",
            "bookmark_position": 50,
            "is_local": False
        }
        
        response = client.post(
            f"/api/books/user-books/{test_user_book.book_id}",
            json=user_book_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reading"
        assert data["bookmark_position"] == 50
    
    def test_get_user_books(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user_book: UserBook
    ):
        """Test of receiving user books"""
        response = client.get("/api/books/user-books/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_user_book.id
        assert data[0]["book_id"] == test_user_book.book_id
    
    def test_get_user_books_by_status(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user_book: UserBook
    ):
        """Test of receiving user books by status"""
        response = client.get(
            f"/api/books/user-books/?status={test_user_book.status}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == test_user_book.status
        
        response = client.get("/api/books/user-books/?status=nonexistent", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_remove_book_from_collection(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user_book: UserBook,
        db_session: Session
    ):
        """Test removing a book from the collection"""
        book_id = test_user_book.book_id
        
        response = client.delete(f"/api/books/user-books/{book_id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        user_book = db_session.query(UserBook).filter(
            UserBook.book_id == book_id
        ).first()
        assert user_book is None
    
    def test_remove_book_not_in_collection(self, client: TestClient, auth_headers: dict, test_book: Book):
        """Test deleting a book that is not in the collection"""
        response = client.delete(f"/api/books/user-books/{test_book.id}", headers=auth_headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


@pytest.mark.integration
class TestBooksIntegration:
    """Integration tests for books"""
    
    def test_full_book_workflow(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session
    ):
        """Test the full cycle of working with a book"""
        book_data = {
            "title": "Workflow Book",
            "author": "Workflow Author",
            "description": "Test workflow",
            "language": "en"
        }
        
        create_response = client.post("/api/books/", json=book_data, headers=auth_headers)
        assert create_response.status_code == 201
        book_id = create_response.json()["id"]
        
        user_book_data = {
            "status": "Want to read",
            "bookmark_position": 0,
            "is_local": False
        }
        
        add_response = client.post(
            f"/api/books/user-books/{book_id}",
            json=user_book_data,
            headers=auth_headers
        )
        assert add_response.status_code == 200
        
        catalog_response = client.get("/api/books/catalog", headers=auth_headers)
        assert catalog_response.status_code == 200
        catalog_data = catalog_response.json()
        assert catalog_data["total"] == 1
        assert catalog_data["books"][0]["in_collection"] is True
        
        user_book_id = add_response.json()["id"]
        user = db_session.query(User).first()
        
        update_response = client.put(
            f"/api/library/{user.username}/books/{user_book_id}",
            json={"status": "reading", "bookmark_position": 25},
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        detail_response = client.get(f"/api/books/{book_id}/detail", headers=auth_headers)
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["user_status"] == "reading"
        assert detail_data["bookmark_position"] == 25
        
        remove_response = client.delete(f"/api/books/user-books/{book_id}", headers=auth_headers)
        assert remove_response.status_code == 204
        
        final_catalog_response = client.get("/api/books/catalog", headers=auth_headers)
        final_catalog_data = final_catalog_response.json()
        assert final_catalog_data["books"][0]["in_collection"] is False