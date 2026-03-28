from datetime import date, datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field

class LeaveStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class LeaveRequestBase(BaseModel):
    leave_type: str = Field(..., min_length=1, max_length=100, description="Type of leave")
    from_date: date = Field(..., description="Start date of leave")
    to_date: date = Field(..., description="End date of leave")
    reason: str = Field(..., min_length=10, max_length=1000, description="Reason for leave")

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}

class LeaveRequestCreate(LeaveRequestBase):
    employee_id: Optional[Union[str, int]] = Field(None, description="ID of the employee")
    employee_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name of the employee")

class LeaveRequestUpdate(BaseModel):
    status: Optional[LeaveStatus] = None
    admin_comment: Optional[str] = Field(None, max_length=1000)

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}

class LeaveRequestResponse(LeaveRequestBase):
    id: int
    employee_id: str
    employee_name: str
    status: LeaveStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    admin_comment: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        exclude = {'_sa_instance_state'}
