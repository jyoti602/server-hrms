from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class LeaveStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class LeaveType(str, Enum):
    CASUAL = "Casual"
    SICK = "Sick"
    ANNUAL = "Annual"
    MATERNITY = "Maternity"
    PATERNITY = "Paternity"
    EMERGENCY = "Emergency"

class LeaveRequestBase(BaseModel):
    employee_id: str = Field(..., max_length=50, description="ID of the employee")
    employee_name: str = Field(..., min_length=1, max_length=100, description="Name of the employee")
    leave_type: LeaveType = Field(..., description="Type of leave")
    from_date: datetime = Field(..., description="Start date of leave")
    to_date: datetime = Field(..., description="End date of leave")
    reason: str = Field(..., min_length=10, max_length=1000, description="Reason for leave")

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestUpdate(BaseModel):
    status: Optional[LeaveStatus] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}

class LeaveRequestResponse(LeaveRequestBase):
    id: int
    status: LeaveStatus
    created_at: str

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}

class LeaveRequestAdminResponse(BaseModel):
    id: int
    employee_id: str
    employee_name: str
    leave_type: LeaveType
    from_date: str
    to_date: str
    reason: str
    status: LeaveStatus
    created_at: str

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}
