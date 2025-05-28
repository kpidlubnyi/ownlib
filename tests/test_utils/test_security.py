import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy.orm import Session

from app.utils.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    authenticate_user
)
from app.models import User


@pytest.mark.unit
class TestSecurityUtils:
    """Test security utility functions"""
    
    def test_get_password_hash(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 50
        assert hashed.startswith("$2b$")
    
    def test_verify_password_correct(self):
        """Test correct password verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test incorrect password verification"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_invalid_hash(self):
        """Test verification with invalid hash"""
        password = "testpassword123"
        invalid_hash = "invalid_hash"
        
        assert verify_password(password, invalid_hash) is False
    
    def test_create_access_token_default_expiry(self):
        """Test access token creation with default expiry"""
        user_id = 123
        token = create_access_token(subject=user_id)
        
        assert isinstance(token, str)
        assert len(token) > 100
        
        parts = token.split('.')
        assert len(parts) == 3
    
    def test_create_access_token_custom_expiry(self):
        """Test access token creation with custom expiry"""
        user_id = 123
        expires_delta = timedelta(hours=2)
        token = create_access_token(subject=user_id, expires_delta=expires_delta)
        
        assert isinstance(token, str)
        assert len(token) > 100
    
    def test_create_access_token_string_subject(self):
        """Test access token creation with string subject"""
        user_email = "test@example.com"
        token = create_access_token(subject=user_email)
        
        assert isinstance(token, str)
        assert len(token) > 100
    
    def test_authenticate_user_success(self, db_session: Session):
        """Test successful user authentication"""
        unique_id = uuid.uuid4().hex[:8]
        password = "testpassword123"
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=get_password_hash(password),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        authenticated_user = authenticate_user(db_session, user.email, password)
        
        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.email == user.email
    
    def test_authenticate_user_wrong_password(self, db_session: Session):
        """Test authentication with wrong password"""
        unique_id = uuid.uuid4().hex[:8]
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=get_password_hash("correctpassword"),
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        
        authenticated_user = authenticate_user(db_session, user.email, "wrongpassword")
        
        assert authenticated_user is None
    
    def test_authenticate_user_nonexistent_email(self, db_session: Session):
        """Test authentication with non-existent email"""
        authenticated_user = authenticate_user(
            db_session,
            "nonexistent@example.com",
            "password123"
        )
        
        assert authenticated_user is None
    
    def test_authenticate_user_inactive(self, db_session: Session):
        """Test authentication of inactive user"""
        unique_id = uuid.uuid4().hex[:8]
        password = "testpassword123"
        
        user = User(
            username=f"testuser_{unique_id}",
            email=f"test_{unique_id}@example.com",
            hashed_password=get_password_hash(password),
            is_active=False
        )
        db_session.add(user)
        db_session.commit()
        
        authenticated_user = authenticate_user(db_session, user.email, password)
        
        assert authenticated_user is not None
        assert authenticated_user.is_active is False
    
    def test_password_hash_consistency(self):
        """Test password hash consistency"""
        password = "testpassword123"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        hash3 = get_password_hash(password)
        
        assert hash1 != hash2
        assert hash2 != hash3
        assert hash1 != hash3
        
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
        assert verify_password(password, hash3) is True
    
    def test_password_edge_cases(self):
        """Test password edge cases"""
        empty_password = ""
        empty_hash = get_password_hash(empty_password)
        assert verify_password(empty_password, empty_hash) is True
        assert verify_password("nonempty", empty_hash) is False
        
        long_password = "a" * 1000
        long_hash = get_password_hash(long_password)
        assert verify_password(long_password, long_hash) is True
        
        special_password = "пароль123!@#$%^&*()_+-=[]{}|;':\",./<>?"
        special_hash = get_password_hash(special_password)
        assert verify_password(special_password, special_hash) is True
    
    @patch('app.utils.security.ACCESS_TOKEN_EXPIRE_MINUTES', 1440)
    def test_token_expiry_configuration(self):
        """Test token expiry configuration"""
        user_id = 123
        
        token = create_access_token(subject=user_id)
        assert isinstance(token, str)
        
        custom_expiry = timedelta(minutes=30)
        custom_token = create_access_token(subject=user_id, expires_delta=custom_expiry)
        assert isinstance(custom_token, str)


@pytest.mark.integration
class TestSecurityIntegration:
    """Integration tests for security"""
    
    def test_full_auth_cycle(self, db_session: Session):
        """Test full authentication cycle"""
        unique_id = uuid.uuid4().hex[:8]
        original_password = "testpassword123"
        hashed_password = get_password_hash(original_password)
        
        user = User(
            username=f"authtest_{unique_id}",
            email=f"authtest_{unique_id}@example.com",
            hashed_password=hashed_password,
            is_active=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        authenticated_user = authenticate_user(db_session, user.email, original_password)
        
        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        
        token = create_access_token(subject=authenticated_user.id)
        assert isinstance(token, str)
        
        wrong_auth = authenticate_user(db_session, user.email, "wrongpassword")
        assert wrong_auth is None
        
        test_passwords = [
            ("testpassword123", True),
            ("TestPassword123", False),
            ("testpassword124", False),
            ("", False),
            ("testpassword", False),
        ]
        
        for test_pass, should_work in test_passwords:
            result = authenticate_user(db_session, user.email, test_pass)
            if should_work:
                assert result is not None, f"Password '{test_pass}' should work"
            else:
                assert result is None, f"Password '{test_pass}' should not work"
    
    def test_multiple_users_isolation(self, db_session: Session):
        """Test user isolation"""
        unique_id = uuid.uuid4().hex[:8]
        password = "samepassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        user1 = User(
            username=f"user1_{unique_id}",
            email=f"user1_{unique_id}@example.com",
            hashed_password=hash1,
            is_active=True
        )
        user2 = User(
            username=f"user2_{unique_id}",
            email=f"user2_{unique_id}@example.com",
            hashed_password=hash2,
            is_active=True
        )
        
        db_session.add_all([user1, user2])
        db_session.commit()
        
        assert hash1 != hash2
        
        auth1 = authenticate_user(db_session, user1.email, password)
        auth2 = authenticate_user(db_session, user2.email, password)
        
        assert auth1 is not None
        assert auth2 is not None
        assert auth1.id != auth2.id
        
        cross_auth1 = authenticate_user(db_session, user1.email, "wrongpassword")
        cross_auth2 = authenticate_user(db_session, user2.email, "wrongpassword")
        
        assert cross_auth1 is None
        assert cross_auth2 is None
    