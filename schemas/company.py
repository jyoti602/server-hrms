from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None


class Company(CompanyBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompanyRegistrationRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    company_slug: str = Field(..., min_length=2, max_length=100)
    company_email: str = Field(..., min_length=5, max_length=255)
    company_phone: Optional[str] = Field(None, max_length=20)
    admin_full_name: str = Field(..., min_length=2, max_length=255)
    admin_email: str = Field(..., min_length=5, max_length=255)
    admin_username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=255)


class CompanyRegistrationResponse(BaseModel):
    company_id: int
    company_name: str
    company_slug: str
    tenant_db_name: str
    admin_username: str
    message: str
