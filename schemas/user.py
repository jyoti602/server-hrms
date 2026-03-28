from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from models.user import UserRole

class UserBase(BaseModel):
    company_id: Optional[int] = None
    email: EmailStr
    username: str
    full_name: str
    role: UserRole

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str
    company_slug: Optional[str] = None

class User(UserBase):
    id: int
    company_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    company_id: int
    tenant_slug: Optional[str] = None
    role: UserRole
    username: str
    email: EmailStr
    full_name: str

class TokenData(BaseModel):
    username: Optional[str] = None
    company_id: Optional[int] = None
