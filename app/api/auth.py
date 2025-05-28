from datetime import timedelta, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import get_db
from app.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.models import User
from app.schemas import Token, UserCreate
from app.utils.security import authenticate_user, create_access_token, get_password_hash
from app.services.activity import activity_service

router = APIRouter(prefix="/auth", tags=["auth"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    new_password: str = Field(..., min_length=8)


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Registering a new user and issuing a JWT token.
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email is already registered"
        )
    
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this name is already registered"
        )
    
    try:
        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=db_user.id, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        db.rollback()
        
        if "Duplicate entry" in str(e) and "email" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user with this email is already registered"
            )
        elif "Duplicate entry" in str(e) and "username" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this name is already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation error"
            )

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """
    OAuth2 compliant login to receive a JWT token.
    WARNING: In the 'username' field, you need to pass the email!
    """
    try:
        user = None
        
        if "@" in form_data.username:
            user = authenticate_user(db, form_data.username, form_data.password)
        
        if not user:
            user_by_username = db.query(User).filter(User.username == form_data.username).first()
            if user_by_username and authenticate_user(db, user_by_username.email, form_data.password):
                user = user_by_username
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.id, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login error"
        )


@router.post("/forgot-password", response_model=dict)
def request_password_reset(
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Check if a user with the given email exists.
    If yes - allow proceeding to the next step.
    """
    user = db.query(User).filter(User.email == reset_request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email was not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated"
        )
    
    return {
        "message": "User found. You can set a new password.",
        "email": reset_request.email
    }


@router.post("/reset-password", response_model=dict)
def reset_password(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
) -> Any:
    """
    Reset user password.
    """
    user = db.query(User).filter(User.email == reset_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated"
        )
    
    try:
        user.hashed_password = get_password_hash(reset_data.new_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        
        activity_service.log_activity(
            db=db,
            user_id=user.id,
            activity_type="profile_updated",
            details={
                "action": "password_reset",
                "reset_date": datetime.now().isoformat()
            }
        )
        
        return {
            "message": "Password successfully changed!",
            "success": True
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change error"
        )