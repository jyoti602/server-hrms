from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String)
    department = Column(String, nullable=False)
    position = Column(String, nullable=False)
    salary = Column(Float, nullable=False)
    hire_date = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(String, default="active")  # active, inactive, terminated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="employee")
    attendance = relationship("Attendance", back_populates="employee")
    leaves = relationship("Leave", back_populates="employee", foreign_keys="Leave.employee_id")
    approved_leaves = relationship("Leave", back_populates="approver", foreign_keys="Leave.approved_by")
    payrolls = relationship("Payroll", back_populates="employee")
