from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LeaveBase(BaseModel):
    leave_type: str  # sick, casual, annual, maternity
    start_date: datetime
    end_date: datetime
    total_days: float
    reason: Optional[str] = None

class LeaveCreate(LeaveBase):
    employee_id: int

class LeaveUpdate(BaseModel):
    status: Optional[str] = None  # pending, approved, rejected
    rejection_reason: Optional[str] = None

class Leave(LeaveBase):
    id: int
    employee_id: int
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
