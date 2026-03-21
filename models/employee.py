import enum

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class EmployeeStatus(str, enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String(20))
    department = Column(String, nullable=False)
    position = Column(String, nullable=False)
    date_of_birth = Column(Date)
    joining_date = Column(Date)
    address = Column(String(255))
    emergency_contact = Column(String(20))
    status = Column(String, nullable=False, default=EmployeeStatus.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    attendance = relationship("Attendance", back_populates="employee")
    leaves = relationship("Leave", back_populates="employee", foreign_keys="Leave.employee_id")
    approved_leaves = relationship("Leave", back_populates="approver", foreign_keys="Leave.approved_by")
    payrolls = relationship("Payroll", back_populates="employee")
