from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models import User, UserBook
from app.services.activity import activity_service

router = APIRouter(prefix="/reading", tags=["reading"])


@router.put("/bookmark/{user_book_id}")
def update_bookmark(
    user_book_id: int,
    position: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Updating the bookmark position (manual input by the user).
    """
    user_book = db.query(UserBook).filter(
        UserBook.id == user_book_id,
        UserBook.user_id == current_user.id
    ).first()
    
    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found in the user's collection"
        )
    
    user_book.bookmark_position = position
    db.add(user_book)
    db.commit()
    db.refresh(user_book)
    
    try:
        activity_service.log_activity(
            db=db,
            user_id=current_user.id,
            activity_type="bookmark_updated",
            book_id=user_book.book_id,
            details={
                "position": position,
                "book_title": user_book.book.title if user_book.book else None,
                "manual_update": True
            }
        )
    except Exception as e:
        print(f"Error logging bookmark update activity: {e}")
    
    return {
        "user_book_id": user_book.id, 
        "bookmark_position": user_book.bookmark_position,
        "message": "The bookmark has been updated"
    }