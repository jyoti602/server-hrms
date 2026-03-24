from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from db.database import get_db
from models.employee import Employee, EmployeeStatus
from models.payroll import Payroll
from models.user import User, UserRole
from schemas.payroll import Payroll as PayrollSchema, PayrollCreate, PayrollUpdate
from auth.auth import get_current_active_user, require_role

router = APIRouter(prefix="/payroll", tags=["payroll"])

@router.get("/", response_model=List[PayrollSchema])
def get_payrolls(
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = None,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Payroll).filter(Payroll.company_id == current_user.company_id)
    
    # Employees can only see their own payroll
    if current_user.role == UserRole.EMPLOYEE:
        employee = (
            db.query(Employee)
            .filter(Employee.email == current_user.email, Employee.company_id == current_user.company_id)
            .first()
        )
        if employee:
            query = query.filter(Payroll.employee_id == employee.id)
        else:
            return []
    elif employee_id:
        query = query.filter(Payroll.employee_id == employee_id)
    
    if month:
        query = query.filter(Payroll.month == month)
    
    payrolls = query.offset(skip).limit(limit).all()
    return payrolls

@router.get("/{payroll_id}", response_model=PayrollSchema)
def get_payroll(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    payroll = (
        db.query(Payroll)
        .filter(Payroll.id == payroll_id, Payroll.company_id == current_user.company_id)
        .first()
    )
    if not payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    
    # Employees can only view their own payroll
    if current_user.role == UserRole.EMPLOYEE:
        employee = (
            db.query(Employee)
            .filter(Employee.email == current_user.email, Employee.company_id == current_user.company_id)
            .first()
        )
        if employee and payroll.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this payroll")
    
    return payroll

@router.post("/", response_model=PayrollSchema)
def create_payroll(
    payroll: PayrollCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    # Check if payroll already exists for this employee and month
    existing_payroll = db.query(Payroll).filter(
        Payroll.company_id == current_user.company_id,
        Payroll.employee_id == payroll.employee_id,
        Payroll.month == payroll.month
    ).first()
    
    if existing_payroll:
        raise HTTPException(
            status_code=400,
            detail="Payroll already exists for this employee and month"
        )
    
    db_payroll = Payroll(company_id=current_user.company_id, **payroll.dict())
    db.add(db_payroll)
    db.commit()
    db.refresh(db_payroll)
    return db_payroll

@router.put("/{payroll_id}", response_model=PayrollSchema)
def update_payroll(
    payroll_id: int,
    payroll_update: PayrollUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    db_payroll = (
        db.query(Payroll)
        .filter(Payroll.id == payroll_id, Payroll.company_id == current_user.company_id)
        .first()
    )
    if not db_payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    
    update_data = payroll_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_payroll, field, value)
    
    db.commit()
    db.refresh(db_payroll)
    return db_payroll

@router.delete("/{payroll_id}")
def delete_payroll(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    db_payroll = (
        db.query(Payroll)
        .filter(Payroll.id == payroll_id, Payroll.company_id == current_user.company_id)
        .first()
    )
    if not db_payroll:
        raise HTTPException(status_code=404, detail="Payroll not found")
    
    db.delete(db_payroll)
    db.commit()
    return {"message": "Payroll deleted successfully"}

@router.get("/monthly/{month}")
def get_monthly_payroll_summary(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    payrolls = (
        db.query(Payroll)
        .filter(Payroll.company_id == current_user.company_id, Payroll.month == month)
        .all()
    )
    
    total_payroll = sum(p.net_salary for p in payrolls)
    total_employees = len(payrolls)
    processed_count = len([p for p in payrolls if p.status == "processed"])
    paid_count = len([p for p in payrolls if p.status == "paid"])
    
    return {
        "month": month,
        "total_payroll": total_payroll,
        "total_employees": total_employees,
        "processed_count": processed_count,
        "paid_count": paid_count,
        "pending_count": total_employees - processed_count
    }

@router.post("/generate-bulk")
def generate_bulk_payroll(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    # Get all active employees
    employees = (
        db.query(Employee)
        .filter(
            Employee.company_id == current_user.company_id,
            Employee.status == EmployeeStatus.ACTIVE.value,
        )
        .all()
    )
    
    created_payrolls = []
    for employee in employees:
        # Check if payroll already exists
        existing = db.query(Payroll).filter(
            Payroll.company_id == current_user.company_id,
            Payroll.employee_id == employee.id,
            Payroll.month == month
        ).first()
        
        if not existing:
            payroll = Payroll(
                company_id=current_user.company_id,
                employee_id=employee.id,
                month=month,
                basic_salary=0,
                allowances=0,
                deductions=0,
                overtime_pay=0,
                bonus=0,
                net_salary=0,
                status="pending"
            )
            db.add(payroll)
            created_payrolls.append(payroll)
    
    db.commit()
    
    return {
        "message": f"Generated payroll for {len(created_payrolls)} employees",
        "payrolls": len(created_payrolls)
    }
