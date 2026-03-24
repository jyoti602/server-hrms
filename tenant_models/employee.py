import enum

from sqlalchemy import Column, Date, DateTime, Integer, String
from sqlalchemy.sql import func

from db.tenant import TenantBase


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class Employee(TenantBase):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    phone = Column(String(20))
    department = Column(String(100), nullable=False)
    position = Column(String(255), nullable=False)
    date_of_birth = Column(Date)
    joining_date = Column(Date)
    address = Column(String(255))
    emergency_contact = Column(String(20))
    status = Column(String(50), nullable=False, default=EmployeeStatus.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
