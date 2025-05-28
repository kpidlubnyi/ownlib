from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models import User, Book
from app.schemas import BookCreate, Book as BookSchema, UserBookCreate, UserBook
from app.services.book import book_service
from app.services.gutendex import gutendex_service as gutenberg_service

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/catalog", response_model=dict)
def get_books_catalog_with_user_status(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of entries on the page"),
    search: Optional[str] = Query(None, description="Search by title or author"),
    language: Optional[str] = Query(None, description="Filter by language"),
    author: Optional[str] = Query(None, description="Filter by author"),
    sort_by: Optional[str] = Query("title", description="Sorting: title, author, created_at"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get a catalogue of books with information about the status in the user's collection.
    """
    return book_service.get_books_with_user_status(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        search=search,
        language=language,
        author=author,
        sort_by=sort_by,
        sort_order=sort_order
    )
def read_books(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of entries on the page"),
    search: Optional[str] = Query(None, description="Search by title or author"),
    language: Optional[str] = Query(None, description="Filter by language"),
    author: Optional[str] = Query(None, description="Filter by author"),
    sort_by: Optional[str] = Query("title", description="Sorting: title, author, created_at"),
    sort_order: Optional[str] = Query("asc", description="Sort order: asc, desc"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get a catalogue of books with search and filtering.
    """
    return book_service.get_books_catalog(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        language=language,
        author=author,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/languages", response_model=List[str])
def get_available_languages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get a list of available languages for filtering.
    """
    return book_service.get_available_languages(db=db)


@router.get("/authors", response_model=List[str])
def get_available_authors(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search for authors"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of authors"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get a list of available authors for filtering.
    """
    return book_service.get_available_authors(db=db, search=search, limit=limit)


@router.post("/", response_model=BookSchema, status_code=status.HTTP_201_CREATED)
def create_book(
    book_in: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Creating a new book.
    """
    return book_service.create_book(db=db, book_in=book_in)


@router.get("/search", response_model=dict)
async def search_books(
    query: str = Query(None, description="Search query"),
    languages: Optional[List[str]] = Query(None, description="Filter by language"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(32, ge=1, le=100, description="Number of elements on the page"),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Search for books via the Gutenberg API.
    """
    return await gutenberg_service.search_books(
        search_query=query,
        languages=languages,
        page=page,
        limit=limit
    )


@router.get("/gutenberg/{gutenberg_id}", response_model=BookSchema)
async def import_gutenberg_book(
    gutenberg_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Import a book from Project Gutenberg by its ID.
    """
    book = await book_service.import_book_from_gutenberg(db=db, gutenberg_id=gutenberg_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found or could not be imported"
        )
    return book


@router.get("/{book_id}", response_model=BookSchema)
def read_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Receiving a book by ID.
    """
    book = book_service.get_book(db=db, book_id=book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    return book


@router.post("/user-books/{book_id}", response_model=UserBook)
def add_book_to_collection(
    book_id: int,
    user_book_in: UserBookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Add a book to a user's collection.
    """
    book = book_service.get_book(db=db, book_id=book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    return book_service.add_book_to_user(
        db=db,
        user=current_user,
        book_id=book_id,
        user_book_in=user_book_in
    )


@router.get("/user-books/", response_model=List[UserBook])
def read_user_books(
    status: Optional[str] = Query(None, description="Filter by book status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve books from a user's collection.
    """
    return book_service.get_user_books(
        db=db,
        user_id=current_user.id,
        status_filter=status,
        skip=skip,
        limit=limit
    )


@router.delete("/user-books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_book_from_collection(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> None:
    """
    Delete a book from a user's collection.
    """
    success = book_service.remove_book_from_user(
        db=db,
        user_id=current_user.id,
        book_id=book_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The book was not found in the user's collection"
        )
    
@router.get("/{book_id}/detail", response_model=dict)
def get_book_detail_with_user_status(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get full information about the book with information about its status in the user's collection.
    """
    book_detail = book_service.get_book_detail_with_user_status(
        db=db, 
        book_id=book_id, 
        user_id=current_user.id
    )
    
    if not book_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
    
    return book_detail