from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from models.employee import EmployeeStatus


class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    department: str
    position: str
    date_of_birth: Optional[date] = None
    joining_date: Optional[date] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    username: str
    password: str
    status: EmployeeStatus = EmployeeStatus.ACTIVE


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    date_of_birth: Optional[date] = None
    joining_date: Optional[date] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    status: Optional[EmployeeStatus] = None
    username: Optional[str] = None
    password: Optional[str] = None


class Employee(EmployeeBase):
    id: int
    status: EmployeeStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
