from datetime import date
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(30), unique=True, nullable=False)
    email = Column(String(30), unique=True, nullable=False)
    hashed_password = Column(String(256), unique=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(Date, nullable=False, default=date.today)

    books = relationship("UserBook", back_populates="user", cascade="all, delete")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete")