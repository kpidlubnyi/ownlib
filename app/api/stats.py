from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models import User
from app.services.stats import stats_service
from app.services.activity import activity_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/reading")
def get_reading_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get general reading statistics.
    """
    return stats_service.get_user_reading_stats(db=db, user_id=current_user.id)


@router.get("/reading/history")
def get_reading_history(
    days: int = Query(30, ge=1, le=365, description="Number of days for the story"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get reading history for the last N days.
    """
    return stats_service.get_reading_history(
        db=db, 
        user_id=current_user.id, 
        days=days
    )


@router.get("/reading/progress/{user_book_id}")
def get_reading_progress(
    user_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get the reading progress of a specific book.
    """
    progress = stats_service.get_reading_progress(
        db=db, 
        user_id=current_user.id,
        user_book_id=user_book_id
    )
    
    if "error" in progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=progress["error"]
        )
    
    return progress

@router.get("/languages")
def get_language_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get book statistics by language.
    """
    return stats_service.get_language_statistics(db=db, user_id=current_user.id)


@router.get("/activities")
def get_user_activities(
    days: int = Query(30, ge=1, le=365, description="Number of days for the story"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get user activity statistics.
    """
    stats = activity_service.get_activity_statistics(
        db=db,
        user_id=current_user.id,
        days=days
    )
    
    recent = activity_service.get_recent_book_activities(
        db=db,
        user_id=current_user.id,
        limit=20
    )
    
    stats["recent_activities"] = recent
    
    return stats


@router.post("/log-activity")
def log_activity(
    activity_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Logging user activity manually (for export/import).
    """
    activity_service.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=activity_data.get("activity_type", "unknown"),
        book_id=activity_data.get("book_id"),
        details=activity_data.get("details", {})
    )
    
    return {"status": "success"}