from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models import User
from app.schemas import User as UserSchema, UserUpdate
from app.utils.security import get_password_hash
from app.services.activity import activity_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserSchema)
def read_current_user(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get information about the current user.
    """
    return current_user


@router.put("/me", response_model=UserSchema)
def update_current_user(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update information about the current user.
    """
    if user_in.email and user_in.email != current_user.email:
        user = db.query(User).filter(User.email == user_in.email).first()
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )
    
    if user_in.username and user_in.username != current_user.username:
        user = db.query(User).filter(User.username == user_in.username).first()
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this name already exists"
            )
    
    update_data = user_in.dict(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type="profile_updated",
        details={
            "updated_fields": list(update_data.keys()),
            "username_changed": "username" in update_data,
            "email_changed": "email" in update_data,
            "password_changed": "password" in update_data
        }
    )
    
    return current_user