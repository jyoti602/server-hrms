from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime, date
from ..models.employee_registration import UserRole

# Base schema with common fields
class EmployeeDataBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    profile_pic: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    address: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    role: UserRole = UserRole.EMPLOYEE

# Schema for registration (employee fills this)
class EmployeeDataCreate(EmployeeDataBase):
    password: str
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

# Schema for updating employee data
class EmployeeDataUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    profile_pic: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[date] = None
    address: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    role: Optional[UserRole] = None

# Response schema (what we return to frontend)
class EmployeeDataResponse(EmployeeDataBase):
    id: int
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state', 'password'}

# Admin response schema with more details
class EmployeeDataAdminResponse(EmployeeDataResponse):
    pass

# Schema for registration statistics
class RegistrationStats(BaseModel):
    total_employees: int
    total_admins: int
    recent_registrations: int
