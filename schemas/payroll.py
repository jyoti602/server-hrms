from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PayrollBase(BaseModel):
    month: str  # "2024-01"
    basic_salary: float
    allowances: float = 0
    deductions: float = 0
    overtime_pay: float = 0
    bonus: float = 0

class PayrollCreate(PayrollBase):
    employee_id: int
    net_salary: float

class PayrollUpdate(BaseModel):
    basic_salary: Optional[float] = None
    allowances: Optional[float] = None
    deductions: Optional[float] = None
    overtime_pay: Optional[float] = None
    bonus: Optional[float] = None
    net_salary: Optional[float] = None
    payment_date: Optional[datetime] = None
    status: Optional[str] = None  # pending, processed, paid
    payment_method: Optional[str] = None  # bank_transfer, cash, check

class Payroll(PayrollBase):
    id: int
    employee_id: int
    net_salary: float
    payment_date: Optional[datetime] = None
    status: str
    payment_method: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
