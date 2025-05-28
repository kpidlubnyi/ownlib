from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ReadingSession(Base):
    __tablename__ = "reading_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_book_id = Column(Integer, ForeignKey("user_books.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    pages_read = Column(Integer, nullable=True)

    user_book = relationship("UserBook", back_populates="reading_sessions")