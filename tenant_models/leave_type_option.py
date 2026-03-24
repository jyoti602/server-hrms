from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from db.tenant import TenantBase


class LeaveTypeOption(TenantBase):
    __tablename__ = "leave_type_options"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    max_days_per_year = Column(Integer, nullable=False, default=0)
    carry_forward_enabled = Column(Boolean, nullable=False, default=False)
    max_carry_forward_days = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
