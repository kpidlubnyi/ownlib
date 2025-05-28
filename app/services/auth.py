from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.security import get_password_hash, verify_password, create_access_token


class AuthService:
    """Service for user authentication and authorization"""
    
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        """
        Registering a new user
        """
        hashed_password = get_password_hash(user_data.password)
        
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            is_active=True,
            created_at=datetime.now().date()
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        User authentication by email and password
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return user
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Receiving a user by email
        """
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """
        Receiving a user by username
        """
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """
        Receiving a user by ID
        """
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_user_token(user: User) -> str:
        """
        Creating a JWT token for a user
        """
        return create_access_token(subject=user.id)
    
    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> bool:
        """
        Deactivating a user
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = False
        db.commit()
        return True
    
    @staticmethod
    def activate_user(db: Session, user_id: int) -> bool:
        """
        User activation
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_active = True
        db.commit()
        return True
    
    @staticmethod
    def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        if not verify_password(old_password, user.hashed_password):
            return False
        
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        return True
    
    @staticmethod
    def check_email_availability(db: Session, email: str) -> bool:
        """
        Checking email availability for registration
        """
        existing_user = db.query(User).filter(User.email == email).first()
        return existing_user is None
    
    @staticmethod
    def check_username_availability(db: Session, username: str) -> bool:
        """
        Checking the availability of username for registration
        """
        existing_user = db.query(User).filter(User.username == username).first()
        return existing_user is None


auth_service = AuthService()