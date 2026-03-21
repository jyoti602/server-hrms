from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from models.employee import EmployeeStatus

class EmployeeBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    department: str
    position: str
    salary: float

class EmployeeCreate(EmployeeBase):
    employee_id: str
    user_id: int
    hire_date: datetime

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    salary: Optional[float] = None
    is_active: Optional[EmployeeStatus] = None

class Employee(EmployeeBase):
    id: int
    employee_id: str
    user_id: int
    hire_date: datetime
    is_active: EmployeeStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
