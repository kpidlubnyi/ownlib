from datetime import datetime, timedelta
from typing import Optional, Union, Any

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checking the password against the hash"""
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        print(f"Password verification: {result}")  
        return result
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Getting a password hash"""
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creating a JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """User authentication by email and password"""
    print(f"Trying to authenticate user with email: {email}")  
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"User not found with email: {email}") 
        return None
    
    print(f"User found: {user.username}, checking password...")  
    
    if not verify_password(password, user.hashed_password):
        print("Password verification failed") 
        return None
    
    print("Authentication successful!")  
    return user