import enum

from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from db.tenant import TenantBase


class LeaveStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class LeaveRequest(TenantBase):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), nullable=False, index=True)
    employee_name = Column(String(100), nullable=False)
    leave_type = Column(String(100), nullable=False, index=True)
    from_date = Column(Date, nullable=False)
    to_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default=LeaveStatus.PENDING.value, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    admin_comment = Column(Text, nullable=True)
