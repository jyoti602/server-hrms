from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    department: str
    position: str
    status: str = "Active"

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    position: Optional[str] = None
    status: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}

class Employee(EmployeeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}
