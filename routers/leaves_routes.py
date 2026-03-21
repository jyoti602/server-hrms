from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from db.database import get_db
from models.leave import Leave
from models.employee import Employee
from models.user import User, UserRole
from schemas.leave import Leave as LeaveSchema, LeaveCreate, LeaveUpdate
from auth.auth import get_current_active_user, require_role

router = APIRouter(prefix="/leaves", tags=["leaves"])

@router.get("/", response_model=List[LeaveSchema])
def get_leaves(
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Leave)
    
    # Employees can only see their own leaves
    if current_user.role == UserRole.EMPLOYEE:
        employee = db.query(Employee).filter(Employee.email == current_user.email).first()
        if employee:
            query = query.filter(Leave.employee_id == employee.id)
        else:
            return []
    elif employee_id:
        query = query.filter(Leave.employee_id == employee_id)
    
    if status:
        query = query.filter(Leave.status == status)
    
    leaves = query.offset(skip).limit(limit).all()
    return leaves

@router.get("/{leave_id}", response_model=LeaveSchema)
def get_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    leave = db.query(Leave).filter(Leave.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    # Employees can only view their own leaves
    if current_user.role == UserRole.EMPLOYEE:
        employee = db.query(Employee).filter(Employee.email == current_user.email).first()
        if employee and leave.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this leave")
    
    return leave

@router.post("/", response_model=LeaveSchema)
def create_leave(
    leave: LeaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Employees can only create leaves for themselves
    if current_user.role == UserRole.EMPLOYEE:
        employee = db.query(Employee).filter(Employee.email == current_user.email).first()
        if employee:
            leave.employee_id = employee.id
        else:
            raise HTTPException(status_code=404, detail="Employee profile not found")
    
    db_leave = Leave(**leave.dict())
    db.add(db_leave)
    db.commit()
    db.refresh(db_leave)
    return db_leave

@router.put("/{leave_id}", response_model=LeaveSchema)
def update_leave(
    leave_id: int,
    leave_update: LeaveUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_leave = db.query(Leave).filter(Leave.id == leave_id).first()
    if not db_leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    # Only admins can approve/reject leaves
    if current_user.role == UserRole.ADMIN:
        update_data = leave_update.dict(exclude_unset=True)
        
        # If approving, set approved_by and approved_at
        if update_data.get("status") == "approved":
            current_employee = db.query(Employee).filter(Employee.email == current_user.email).first()
            if current_employee:
                update_data["approved_by"] = current_employee.id
                update_data["approved_at"] = datetime.utcnow()
        
        for field, value in update_data.items():
            setattr(db_leave, field, value)
    else:
        # Employees can only cancel their own pending leaves
        employee = db.query(Employee).filter(Employee.email == current_user.email).first()
        if employee and db_leave.employee_id == employee.id and db_leave.status == "pending":
            if leave_update.status == "cancelled":
                db_leave.status = "cancelled"
            else:
                raise HTTPException(status_code=403, detail="Employees can only cancel their pending leaves")
        else:
            raise HTTPException(status_code=403, detail="Not authorized to update this leave")
    
    db.commit()
    db.refresh(db_leave)
    return db_leave

@router.delete("/{leave_id}")
def delete_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    db_leave = db.query(Leave).filter(Leave.id == leave_id).first()
    if not db_leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    
    db.delete(db_leave)
    db.commit()
    return {"message": "Leave deleted successfully"}

@router.get("/pending/count")
def get_pending_leaves_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    count = db.query(Leave).filter(Leave.status == "pending").count()
    return {"pending_leaves": count}
