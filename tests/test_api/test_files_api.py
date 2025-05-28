import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Book, UserBook, BookFormat, User


@pytest.mark.files
class TestFilesAPI:
    """File operations API tests"""
    
    def test_upload_book_file_success(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session,
        sample_pdf_file: bytes,
        temp_upload_dir: Path
    ):
        """Test for successful upload of a book file"""
        files = {
            "file": ("test_book.pdf", BytesIO(sample_pdf_file), "application/pdf")
        }
        data = {
            "title": "Test Book Upload",
            "author": "Test Author",
            "language": "en"
        }
        
        with patch('app.config.UPLOAD_DIR_PATH', temp_upload_dir):
            response = client.post(
                "/api/files/upload-book",
                files=files,
                data=data,
                headers=auth_headers
            )
        
        assert response.status_code == 201
        result = response.json()
        
        assert result["title"] == "Test Book Upload"
        assert result["author"] == "Test Author"
        assert result["language"] == "en"
        assert result["format"] == "pdf"
        assert result["book_id"] is not None
        assert result["user_book_id"] is not None
        assert result["file_path"] is not None
        
        book = db_session.query(Book).filter(Book.id == result["book_id"]).first()
        assert book is not None
        assert book.title == "Test Book Upload"
        
        book_format = db_session.query(BookFormat).filter(BookFormat.book_id == book.id).first()
        assert book_format is not None
        assert book_format.format_type == "pdf"
        
        user_book = db_session.query(UserBook).filter(UserBook.id == result["user_book_id"]).first()
        assert user_book is not None
        assert user_book.is_local is True
        assert user_book.file_path is not None
    
    def test_upload_book_file_invalid_language(
        self,
        client: TestClient,
        auth_headers: dict,
        sample_pdf_file: bytes
    ):
        """Download test with incorrect language code"""
        files = {
            "file": ("test_book.pdf", BytesIO(sample_pdf_file), "application/pdf")
        }
        data = {
            "title": "Test Book",
            "language": "invalid-lang"
        }
        
        response = client.post(
            "/api/files/upload-book",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "two lowercase Latin letters" in response.json()["detail"]
    
    def test_upload_book_file_unsupported_format(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test uploading an unsupported file format"""
        files = {
            "file": ("test_book.doc", BytesIO(b"fake doc content"), "application/msword")
        }
        data = {
            "title": "Test Book",
            "language": "en"
        }
        
        response = client.post(
            "/api/files/upload-book",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Unsupported file format" in response.json()["detail"]
    
    def test_upload_book_file_without_file(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Upload test without a file"""
        data = {
            "title": "Test Book",
            "language": "en"
        }
        
        response = client.post(
            "/api/files/upload-book",
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_upload_book_file_different_formats(
        self,
        client: TestClient,
        auth_headers: dict,
        temp_upload_dir: Path
    ):
        """Test uploading files of different formats"""
        test_files = [
            ("test.pdf", b"%PDF-1.4...", "application/pdf"),
            ("test.epub", b"fake epub content", "application/epub+zip"),
            ("test.html", b"<html><body>Test</body></html>", "text/html"),
            ("test.txt", b"This is a test text file", "text/plain"),
        ]
        
        with patch('app.config.UPLOAD_DIR_PATH', temp_upload_dir):
            for filename, content, content_type in test_files:
                files = {
                    "file": (filename, BytesIO(content), content_type)
                }
                data = {
                    "title": f"Test Book {filename}",
                    "language": "en"
                }
                
                response = client.post(
                    "/api/files/upload-book",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
                
                assert response.status_code == 201, f"Failed for {filename}"
                result = response.json()
                expected_format = {
                    "test.pdf": "pdf",
                    "test.epub": "epub", 
                    "test.html": "html",
                    "test.txt": "text"
                }[filename]
                assert result["format"] == expected_format
        
    def test_delete_book_file_not_local(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user_book: UserBook
    ):
        """Test deleting a non-local book"""
        test_user_book.is_local = False
        
        response = client.delete(
            f"/api/files/books/{test_user_book.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not local" in response.json()["detail"]
    
    def test_delete_book_file_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test deleting a non-existent book"""
        response = client.delete(
            "/api/files/books/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    
    def test_remove_user_book_from_collection_online(
        self,
        client: TestClient,
        auth_headers: dict,
        db_session: Session,
        test_user_book: UserBook
    ):
        """Test removing an online book from the collection"""
        test_user_book.is_local = False
        test_user_book.file_path = None
        db_session.commit()
        
        response = client.delete(
            f"/api/files/user-books/{test_user_book.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        user_book = db_session.query(UserBook).filter(UserBook.id == test_user_book.id).first()
        assert user_book is None
    
    def test_get_user_book_file_details_success(
        self,
        client: TestClient,
        auth_headers: dict,
        test_user_book: UserBook,
        db_session: Session
    ):
        """Test for getting details of a user workbook file"""
        test_user_book.is_local = True
        test_user_book.file_path = "1/test_file.pdf"
        db_session.commit()
        
        response = client.get(
            f"/api/files/user-books/{test_user_book.id}/details",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == test_user_book.id
        assert data["is_local"] is True
        assert data["file_path"] == "1/test_file.pdf"
        assert data["book"] is not None
        assert data["book"]["title"] == test_user_book.book.title
    
    def test_get_user_book_file_details_not_found(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test for getting details of a non-existent book"""
        response = client.get(
            "/api/files/user-books/99999/details",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        
@pytest.mark.integration
class TestFilesIntegration:
    """Integration tests of file operations"""
        
    def test_multiple_users_file_isolation(
        self,
        client: TestClient,
        db_session: Session,
        sample_pdf_file: bytes,
        temp_upload_dir: Path
    ):
        """Test file isolation between users"""
        from app.utils.security import get_password_hash, create_access_token
        
        user1 = User(
            username="user1",
            email="user1@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        user2 = User(
            username="user2", 
            email="user2@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        db_session.add_all([user1, user2])
        db_session.commit()
        
        token1 = create_access_token(subject=user1.id)
        token2 = create_access_token(subject=user2.id)
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        with patch('app.config.UPLOAD_DIR_PATH', temp_upload_dir):
            files1 = {
                "file": ("user1_book.pdf", BytesIO(sample_pdf_file), "application/pdf")
            }
            data1 = {
                "title": "User 1 Book",
                "language": "en"
            }
            
            upload1_response = client.post(
                "/api/files/upload-book",
                files=files1,
                data=data1,
                headers=headers1
            )
            assert upload1_response.status_code == 201
            user1_book_id = upload1_response.json()["user_book_id"]
            
            files2 = {
                "file": ("user2_book.pdf", BytesIO(sample_pdf_file), "application/pdf")
            }
            data2 = {
                "title": "User 2 Book",
                "language": "en"
            }
            
            upload2_response = client.post(
                "/api/files/upload-book",
                files=files2,
                data=data2,
                headers=headers2
            )
            assert upload2_response.status_code == 201
            user2_book_id = upload2_response.json()["user_book_id"]
            
            stats1_response = client.get("/api/files/stats", headers=headers1)
            stats1_data = stats1_response.json()
            assert stats1_data["total_files"] == 1
            assert stats1_data["user_id"] == user1.id
            
            stats2_response = client.get("/api/files/stats", headers=headers2)
            stats2_data = stats2_response.json()
            assert stats2_data["total_files"] == 1
            assert stats2_data["user_id"] == user2.id
            
            user1_access_user2_response = client.get(
                f"/api/files/user-books/{user2_book_id}/details",
                headers=headers1
            )
            assert user1_access_user2_response.status_code == 404
            
            user1_delete_user2_response = client.delete(
                f"/api/files/books/{user2_book_id}",
                headers=headers1
            )
            assert user1_delete_user2_response.status_code == 404
            
            delete1_response = client.delete(
                f"/api/files/books/{user1_book_id}",
                headers=headers1
            )
            assert delete1_response.status_code == 204
            
            delete2_response = client.delete(
                f"/api/files/books/{user2_book_id}",
                headers=headers2
            )
            assert delete2_response.status_code == 204