from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Payroll(Base):
    __tablename__ = "payrolls"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month = Column(String, nullable=False)  # "2024-01"
    basic_salary = Column(Float, nullable=False)
    allowances = Column(Float, default=0)
    deductions = Column(Float, default=0)
    overtime_pay = Column(Float, default=0)
    bonus = Column(Float, default=0)
    net_salary = Column(Float, nullable=False)
    payment_date = Column(DateTime(timezone=True))
    status = Column(String, default="pending")  # pending, processed, paid
    payment_method = Column(String)  # bank_transfer, cash, check
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("Employee", back_populates="payrolls")
