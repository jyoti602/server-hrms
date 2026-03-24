from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentResponse(DepartmentBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeaveTypeOptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    max_days_per_year: int = Field(..., ge=0, le=365)
    carry_forward_enabled: bool = False
    max_carry_forward_days: int = Field(0, ge=0, le=365)


class LeaveTypeOptionCreate(LeaveTypeOptionBase):
    pass


class LeaveTypeOptionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    max_days_per_year: Optional[int] = Field(None, ge=0, le=365)
    carry_forward_enabled: Optional[bool] = None
    max_carry_forward_days: Optional[int] = Field(None, ge=0, le=365)
    is_active: Optional[bool] = None


class LeaveTypeOptionResponse(LeaveTypeOptionBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeaveBalanceResponse(BaseModel):
    leave_type: str
    max_days_per_year: int
    carry_forward_enabled: bool
    max_carry_forward_days: int
    carry_forward_days: int
    approved_days_taken: int
    remaining_balance: int
