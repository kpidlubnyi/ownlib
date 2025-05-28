from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models import User
from app.services.file import file_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload-book", status_code=status.HTTP_201_CREATED)
async def upload_book_file(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form(None),
    language: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Upload a book file with the required title and language.
    
    Parameters:
    - file: Book file (PDF, EPUB, HTML, TXT) - required
    - title: The title of the book (required)
    - author: Author of the book (optional)  
    - language: Book language code - 2 lowercase Latin letters - required (for example: en, uk, pl, ru)
    """
    return await file_service.upload_book_file(
        db=db,
        file=file,
        user=current_user,
        book_title=title,
        book_author=author,
        book_language=language
    )


@router.delete("/books/{user_book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book_file(
    user_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    Deletes a workbook file from the file system and all related records from the database.
    Works only with local books.
    """
    success = file_service.remove_book_file(
        db=db,
        user_book_id=user_book_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found, is not local, or you do not have permission to delete it"
        )


@router.delete("/user-books/{user_book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_book_from_collection(
    user_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    Deletes a book from the user's collection.
    For local books, it also deletes the file and records from the database.
    For online books, it simply deletes the connection to the user.
    """
    success = file_service.remove_user_book_from_collection(
        db=db,
        user_book_id=user_book_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found in your collection"
        )


@router.get("/user-books/{user_book_id}/details", response_model=dict)
def get_user_book_file_details(
    user_book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get detailed information about a user's workbook file
    """
    details = file_service.get_user_book_details(
        db=db,
        user_book_id=user_book_id,
        user_id=current_user.id
    )
    
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found in your collection"
        )
    
    return details


@router.post("/cleanup", response_model=dict)
def cleanup_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Clean up orphan files and orphan books.
    Only available to authorised users.
    """
    try:
        orphaned_files = file_service.cleanup_orphaned_files(db)
        
        orphaned_books = file_service.cleanup_orphaned_books(db)
        
        return {
            "message": "Cleaning completed successfully",
            "user_id": current_user.id,
            "orphaned_files_removed": orphaned_files,
            "orphaned_books_removed": orphaned_books
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during cleaning: {str(e)}"
        )


@router.get("/stats", response_model=dict)
def get_file_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get user file statistics
    """
    from app.models import UserBook
    from app.utils.files import get_file_path
    
    user_books = db.query(UserBook).filter(
        UserBook.user_id == current_user.id,
        UserBook.is_local == True,
        UserBook.file_path.isnot(None)
    ).all()
    
    total_files = len(user_books)
    total_size = 0
    existing_files = 0
    missing_files = 0
    
    file_formats = {}
    languages = {}
    
    for user_book in user_books:
        if user_book.file_path:
            try:
                file_path = get_file_path(user_book.file_path)
                if file_path.exists():
                    existing_files += 1
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    ext = file_path.suffix.lower()
                    file_formats[ext] = file_formats.get(ext, 0) + 1
                    
                    if user_book.book and user_book.book.language:
                        lang = user_book.book.language
                        languages[lang] = languages.get(lang, 0) + 1
                else:
                    missing_files += 1
            except Exception:
                missing_files += 1
    
    return {
        "user_id": current_user.id,
        "total_files": total_files,
        "existing_files": existing_files,
        "missing_files": missing_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "file_formats": file_formats,
        "languages": languages
    }