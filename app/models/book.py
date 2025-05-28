from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    author = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    language = Column(String(32), nullable=True)
    gutenberg_id = Column(Integer, nullable=True)
    cover_url = Column(Text, nullable=True)

    formats = relationship("BookFormat", back_populates="book", cascade="all, delete")
    user_books = relationship("UserBook", back_populates="book", cascade="all, delete")
    activities = relationship("UserActivity", back_populates="book")

class BookFormat(Base):
    __tablename__ = "book_formats"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    format_type = Column(Enum("pdf", "epub", "html", "text", name="format_type_enum"), nullable=False)
    url = Column(Text, nullable=False)

    book = relationship("Book", back_populates="formats")


class UserBook(Base):
    __tablename__ = "user_books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum("Want to read", "reading", "read", "dropped", name="status_enum"), nullable=False)
    bookmark_position = Column(Integer, nullable=True)
    is_local = Column(Boolean, nullable=False, default=False)
    file_path = Column(Text, nullable=True)
    added_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="books")
    book = relationship("Book", back_populates="user_books")
    reading_sessions = relationship("ReadingSession", back_populates="user_book", cascade="all, delete")