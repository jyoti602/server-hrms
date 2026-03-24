from pydantic import BaseModel
from typing import Optional
from datetime import datetime, time

class AttendanceBase(BaseModel):
    date: datetime
    status: str  # present, absent, late, half_day
    notes: Optional[str] = None

class AttendanceCreate(AttendanceBase):
    employee_id: int
    check_in: Optional[time] = None
    lunch_start: Optional[time] = None
    lunch_end: Optional[time] = None
    check_out: Optional[time] = None
    work_hours: Optional[int] = None
    overtime_hours: Optional[int] = 0

class AttendanceUpdate(BaseModel):
    check_in: Optional[time] = None
    lunch_start: Optional[time] = None
    lunch_end: Optional[time] = None
    check_out: Optional[time] = None
    status: Optional[str] = None
    work_hours: Optional[int] = None
    overtime_hours: Optional[int] = None
    notes: Optional[str] = None

class Attendance(AttendanceBase):
    id: int
    employee_id: int
    check_in: Optional[time] = None
    lunch_start: Optional[time] = None
    lunch_end: Optional[time] = None
    check_out: Optional[time] = None
    work_hours: Optional[int] = None
    overtime_hours: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AttendanceActionResponse(BaseModel):
    message: str
    attendance: Attendance
