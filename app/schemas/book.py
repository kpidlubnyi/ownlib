from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, Field, HttpUrl


class BookFormatBase(BaseModel):
    format_type: Literal["pdf", "epub", "html", "text"]
    url: str


class BookFormatCreate(BookFormatBase):
    book_id: int


class BookFormatUpdate(BaseModel):
    format_type: Optional[Literal["pdf", "epub", "html", "text"]] = None
    url: Optional[str] = None


class BookFormatInDB(BookFormatBase):
    id: int
    book_id: int

    class Config:
        from_attributes = True


class BookBase(BaseModel):
    title: str
    author: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    gutenberg_id: Optional[int] = None
    cover_url: Optional[str] = None


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    gutenberg_id: Optional[int] = None
    cover_url: Optional[str] = None


class BookInDB(BookBase):
    id: int

    class Config:
        from_attributes = True


class Book(BookInDB):
    formats: List[BookFormatInDB] = []


class UserBookBase(BaseModel):
    status: Literal["Want to read", "reading", "read", "dropped"]
    bookmark_position: Optional[int] = None
    is_local: bool = False
    file_path: Optional[str] = None


class UserBookCreate(BaseModel):
    status: Literal["Want to read", "reading", "read", "dropped"]
    bookmark_position: Optional[int] = None
    is_local: bool = False
    file_path: Optional[str] = None


class UserBookUpdate(BaseModel):
    status: Optional[Literal["Want to read", "reading", "read", "dropped"]] = None
    bookmark_position: Optional[int] = None
    file_path: Optional[str] = None


class UserBookInDB(BaseModel):
    id: int
    user_id: int
    book_id: int
    status: Literal["Want to read", "reading", "read", "dropped"]
    bookmark_position: Optional[int] = None
    is_local: bool = False
    file_path: Optional[str] = None
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserBook(UserBookInDB):
    book: Book