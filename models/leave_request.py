import enum

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from db.database import Base

class LeaveStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class LeaveType(str, enum.Enum):
    CASUAL = "Casual"
    SICK = "Sick"
    ANNUAL = "Annual"
    MATERNITY = "Maternity"
    PATERNITY = "Paternity"
    EMERGENCY = "Emergency"

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), nullable=False, index=True)
    employee_name = Column(String(100), nullable=False)
    leave_type = Column(String(50), nullable=False, index=True)
    from_date = Column(DateTime, nullable=False)
    to_date = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default=LeaveStatus.PENDING.value, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = ({"extend_existing": True},)
