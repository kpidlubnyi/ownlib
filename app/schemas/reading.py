from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ReadingSessionBase(BaseModel):
    user_book_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    pages_read: Optional[int] = None


class ReadingSessionCreate(ReadingSessionBase):
    pass


class ReadingSessionUpdate(BaseModel):
    end_time: Optional[datetime] = None
    pages_read: Optional[int] = None


class ReadingSessionInDB(ReadingSessionBase):
    id: int

    class Config:
        from_attributes = True


class ReadingSession(ReadingSessionInDB):
    pass


class ReadingStat(BaseModel):
    total_reading_time: int 
    total_pages_read: int
    total_books_read: int
    average_reading_speed: float 


class ReadingProgress(BaseModel):
    book_id: int
    book_title: str
    current_page: int
    total_pages: int
    percentage: float 
    time_spent: int  