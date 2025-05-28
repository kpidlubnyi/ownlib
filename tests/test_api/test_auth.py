import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.utils.security import verify_password


@pytest.mark.auth
class TestAuthAPI:
    """Authorization API tests"""
    
    def test_register_success(self, client: TestClient, db_session: Session):
        """Test of successful registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        
        user = db_session.query(User).filter(User.email == user_data["email"]).first()
        assert user is not None
        assert user.username == user_data["username"]
        assert user.is_active is True
        assert verify_password(user_data["password"], user.hashed_password)
    
    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Тест реєстрації з дублікатом email"""
        user_data = {
            "username": "anotheruser",
            "email": test_user.email,
            "password": "password123"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client: TestClient, test_user: User):
        """Registration test with a duplicate username"""
        user_data = {
            "username": test_user.username,
            "email": "another@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_register_invalid_data(self, client: TestClient):
        """Registration test with incorrect data"""
        response = client.post("/api/auth/register", json={})
        assert response.status_code == 422
        
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        })
        assert response.status_code == 422
        
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"
        })
        assert response.status_code == 422
    
    def test_login_success(self, client: TestClient, test_user: User, test_user_data: dict):
        """Test of successful login"""
        form_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/auth/login", data=form_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_with_username(self, client: TestClient, test_user: User, test_user_data: dict):
        """Test login via username"""
        form_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/auth/login", data=form_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Login test with incorrect password"""
        form_data = {
            "username": test_user.email,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/auth/login", data=form_data)
        
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login of a non-existent user"""
        form_data = {
            "username": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/auth/login", data=form_data)
        
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]
    
    def test_login_inactive_user(self, client: TestClient, test_user: User, test_user_data: dict, db_session: Session):
        """Inactive user login test"""
        test_user.is_active = False
        db_session.commit()
        
        form_data = {
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/auth/login", data=form_data)
        
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]
    
    def test_forgot_password_success(self, client: TestClient, test_user: User):
        """Test for a successful password recovery request"""
        data = {"email": test_user.email}
        
        response = client.post("/api/auth/forgot-password", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert "found" in result["message"]
        assert result["email"] == test_user.email
    
    def test_forgot_password_nonexistent_user(self, client: TestClient):
        """Test password recovery request for a non-existent user"""
        data = {"email": "nonexistent@example.com"}
        
        response = client.post("/api/auth/forgot-password", json=data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_forgot_password_inactive_user(self, client: TestClient, test_user: User, db_session: Session):
        """Test password recovery request for an inactive user"""
        test_user.is_active = False
        db_session.commit()
        
        data = {"email": test_user.email}
        
        response = client.post("/api/auth/forgot-password", json=data)
        
        assert response.status_code == 400
        assert "deactivated" in response.json()["detail"]
    
    def test_reset_password_success(self, client: TestClient, test_user: User, db_session: Session):
        """Test for successful password reset"""
        new_password = "newpassword123"
        data = {
            "email": test_user.email,
            "new_password": new_password
        }
        
        response = client.post("/api/auth/reset-password", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
        assert "successfully changed" in result["message"]
        
        db_session.refresh(test_user)
        assert verify_password(new_password, test_user.hashed_password)
    
    def test_reset_password_nonexistent_user(self, client: TestClient):
        """Password reset test for a non-existent user"""
        data = {
            "email": "nonexistent@example.com",
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/auth/reset-password", json=data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_reset_password_inactive_user(self, client: TestClient, test_user: User, db_session: Session):
        """Test password reset for an inactive user"""
        test_user.is_active = False
        db_session.commit()
        
        data = {
            "email": test_user.email,
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/auth/reset-password", json=data)
        
        assert response.status_code == 400
        assert "deactivated" in response.json()["detail"]
    
    def test_reset_password_too_short(self, client: TestClient, test_user: User):
        """Test password reset with a password that is too short"""
        data = {
            "email": test_user.email,
            "new_password": "123"
        }
        
        response = client.post("/api/auth/reset-password", json=data)
        
        assert response.status_code == 422


@pytest.mark.integration
class TestAuthIntegration:
    """Integration authorization tests"""
    
    def test_full_auth_flow(self, client: TestClient, db_session: Session):
        """Full authorization cycle test"""
        user_data = {
            "username": "flowuser",
            "email": "flowuser@example.com",
            "password": "password123"
        }
        
        register_response = client.post("/api/auth/register", json=user_data)
        assert register_response.status_code == 201
        token1 = register_response.json()["access_token"]
        
        login_data = {
            "username": user_data["email"],
            "password": user_data["password"]
        }
        
        login_response = client.post("/api/auth/login", data=login_data)
        assert login_response.status_code == 200
        token2 = login_response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token2}"}
        profile_response = client.get("/api/users/me", headers=headers)
        assert profile_response.status_code == 200
        
        profile_data = profile_response.json()
        assert profile_data["username"] == user_data["username"]
        assert profile_data["email"] == user_data["email"]
        
        reset_data = {
            "email": user_data["email"],
            "new_password": "newpassword456"
        }
        
        reset_response = client.post("/api/auth/reset-password", json=reset_data)
        assert reset_response.status_code == 200
        
        new_login_data = {
            "username": user_data["email"],
            "password": "newpassword456"
        }
        
        new_login_response = client.post("/api/auth/login", data=new_login_data)
        assert new_login_response.status_code == 200
        
        old_login_response = client.post("/api/auth/login", data=login_data)
        assert old_login_response.status_code == 401