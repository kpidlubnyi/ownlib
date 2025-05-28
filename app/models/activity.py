from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship

from app.database import Base


class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(
        Enum(
            "book_added",           
            "book_removed",      
            "book_status_changed",  
            "book_uploaded",      
            "reading_session",    
            "bookmark_updated",     
            "data_exported",       
            "data_imported",        
            "profile_updated",     
            "gutenberg_imported",  
            name="activity_type_enum"
        ),
        nullable=False
    )
    book_id = Column(Integer, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    details = Column(JSON, nullable=True) 
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    user = relationship("User", back_populates="activities")
    book = relationship("Book", back_populates="activities")