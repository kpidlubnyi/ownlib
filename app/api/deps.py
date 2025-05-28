from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.config import SECRET_KEY, ALGORITHM
from app.database import get_db
from app.models import User
from app.schemas import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Getting the current user based on the JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
        token_data = TokenPayload(sub=user_id)
    except JWTError:
        raise credentials_exception
    
    try:
        user = db.query(User).filter(User.id == token_data.sub).first()
        if user is None:
            raise credentials_exception
        
        return user
    except OperationalError as e:
        if "max_user_connections" in str(e) or "1226" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The error was caused by free database hosting in Paris. Please try again in a few seconds."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Temporary problems with the database. Please try again later."
            )


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Check if the current user is active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user