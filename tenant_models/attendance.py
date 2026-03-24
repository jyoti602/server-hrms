from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.sql import func

from db.tenant import TenantBase


class Attendance(TenantBase):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    check_in = Column(Time)
    lunch_start = Column(Time)
    lunch_end = Column(Time)
    check_out = Column(Time)
    status = Column(String(50), nullable=False)
    work_hours = Column(Integer)
    overtime_hours = Column(Integer, default=0)
    notes = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
