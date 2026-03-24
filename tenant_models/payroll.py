from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.sql import func

from db.tenant import TenantBase


class Payroll(TenantBase):
    __tablename__ = "payrolls"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    month = Column(String(20), nullable=False)
    basic_salary = Column(Float, nullable=False)
    allowances = Column(Float, default=0)
    deductions = Column(Float, default=0)
    overtime_pay = Column(Float, default=0)
    bonus = Column(Float, default=0)
    net_salary = Column(Float, nullable=False)
    payment_date = Column(DateTime(timezone=True))
    status = Column(String(50), default="pending")
    payment_method = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
