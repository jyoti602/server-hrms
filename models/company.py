from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="company")
    employees = relationship("Employee", back_populates="company")
    departments = relationship("Department", back_populates="company")
    leave_type_options = relationship("LeaveTypeOption", back_populates="company")
    attendance_records = relationship("Attendance", back_populates="company")
    leave_requests = relationship("LeaveRequest", back_populates="company")
    leaves = relationship("Leave", back_populates="company")
    payrolls = relationship("Payroll", back_populates="company")
    tenant_database = relationship("TenantDatabase", back_populates="company", uselist=False)
