from typing import Any, List, Optional
import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models import User
from app.schemas import UserBookUpdate
from app.services.user_library import user_library_service
from app.services.file import file_service

router = APIRouter(prefix="/library", tags=["user-library"])


@router.get("/{username}/books/", response_model=dict)
def get_user_library(
    username: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of entries on the page"),
    status: Optional[str] = Query(None, description="Filter by status: 'Want to read', 'reading', 'read', 'dropped'"),
    search: Optional[str] = Query(None, description="Search by book title or author"),
    sort_by: Optional[str] = Query("added_at", description="Sorting: title, author, added_at, status"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Getting a user's personal library by username.
    The user can view only his own library.
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own library"
        )
    
    return user_library_service.get_user_library(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status_filter=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/{username}/books/stats", response_model=dict)
def get_user_library_stats(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get statistics on the user's personal library.
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can view only your library statistics"
        )
    
    return user_library_service.get_user_library_stats(
        db=db,
        user_id=current_user.id
    )


@router.get("/{username}/books/{user_book_id}", response_model=dict)
def get_user_book_detail(
    username: str,
    user_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get detailed information about a book in the user's library.
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own library"
        )
    
    user_book = user_library_service.get_user_book_detail(
        db=db,
        user_id=current_user.id,
        user_book_id=user_book_id
    )
    
    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found in your library"
        )
    
    return user_book


@router.put("/{username}/books/{user_book_id}", response_model=dict)
def update_user_book(
    username: str,
    user_book_id: int,
    update_data: UserBookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update information about a book in the user's library
    (status, bookmark position, etc.).
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own library"
        )
    
    user_book = user_library_service.update_user_book(
        db=db,
        user_id=current_user.id,
        user_book_id=user_book_id,
        update_data=update_data
    )
    
    if not user_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found in your library"
        )
    
    return user_book


@router.delete("/{username}/books/{user_book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_book_from_library(
    username: str,
    user_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    Deletes a book from the user's personal library.
    For local books, it also deletes the file from the disk and all related records.
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own library"
        )
    
    success = file_service.remove_user_book_from_collection(
        db=db,
        user_book_id=user_book_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found in your library"
        )


@router.get("/{username}/books/by-status/{book_status}", response_model=List[dict])
def get_books_by_status(
    username: str,
    book_status: str,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of entries on the page"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get books from the user's library by a specific status.
    Available statuses: 'Want to read', 'reading', 'read', 'dropped'
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own library"
        )
    
    valid_statuses = ["Want to read", "reading", "read", "dropped"]
    if book_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect status. Available statuses: {', '.join(valid_statuses)}"
        )
    
    return user_library_service.get_books_by_status(
        db=db,
        user_id=current_user.id,
        status=book_status,
        skip=skip,
        limit=limit
    )


@router.get("/{username}/books/reading-progress", response_model=List[dict])
def get_reading_progress(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get reading progress for all user books.
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own library"
        )
    
    return user_library_service.get_user_reading_progress(
        db=db,
        user_id=current_user.id
    )


@router.post("/{username}/cleanup", response_model=dict)
def cleanup_user_library(
    username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Clean up the user's library from orphan files and unnecessary records.
    Only for the library owner.
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only clear your own library"
        )
    
    try:
        orphaned_files = file_service.cleanup_orphaned_files(db)
        
        orphaned_books = file_service.cleanup_orphaned_books(db)
        
        return {
            "message": "Cleaning is completed successfully",
            "orphaned_files_removed": orphaned_files,
            "orphaned_books_removed": orphaned_books
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error when clearing the library: {str(e)}"
        )


@router.get("/{username}/books/{user_book_id}/file-info", response_model=dict)
def get_book_file_info(
    username: str,
    user_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get information about the book file (for local books).
    """
    if current_user.username != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own files"
        )
    
    book_details = file_service.get_user_book_details(
        db=db,
        user_book_id=user_book_id,
        user_id=current_user.id
    )
    
    if not book_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found in your library"
        )
    
    if not book_details["is_local"] or not book_details["file_path"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This book is not a local file"
        )
    
    from app.utils.files import get_file_path
    from pathlib import Path
    
    try:
        file_path = get_file_path(book_details["file_path"])
        
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book file not found on disk"
            )
        
        file_stats = file_path.stat()
        
        return {
            "file_path": book_details["file_path"],
            "file_size": file_stats.st_size,
            "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "file_exists": True,
            "book_info": book_details
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving file information: {str(e)}"
        )