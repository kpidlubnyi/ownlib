from datetime import date
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr = Field(..., max_length=30)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    email: Optional[EmailStr] = Field(None, max_length=30)
    password: Optional[str] = Field(None, min_length=8)


class UserInDB(UserBase):
    id: int
    is_active: bool
    created_at: date

    class Config:
        from_attributes = True


class User(UserInDB):
    pass


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[int] = None