from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, date

from db.database import get_db
from models.attendance import Attendance
from models.employee import Employee
from models.user import User, UserRole
from schemas.attendance import Attendance as AttendanceSchema, AttendanceCreate, AttendanceUpdate
from auth.auth import get_current_active_user, require_role

router = APIRouter(prefix="/attendance", tags=["attendance"])

@router.get("/", response_model=List[AttendanceSchema])
def get_attendance(
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Attendance)
    
    # Employees can only see their own attendance
    if current_user.role == UserRole.EMPLOYEE:
        employee = db.query(Employee).filter(Employee.email == current_user.email).first()
        if employee:
            query = query.filter(Attendance.employee_id == employee.id)
        else:
            return []
    elif employee_id:
        query = query.filter(Attendance.employee_id == employee_id)
    
    if start_date:
        query = query.filter(Attendance.date >= start_date)
    if end_date:
        query = query.filter(Attendance.date <= end_date)
    
    attendance = query.offset(skip).limit(limit).all()
    return attendance

@router.get("/{attendance_id}", response_model=AttendanceSchema)
def get_attendance_record(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Employees can only view their own attendance
    if current_user.role == UserRole.EMPLOYEE:
        employee = db.query(Employee).filter(Employee.email == current_user.email).first()
        if employee and attendance.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this attendance")
    
    return attendance

@router.post("/", response_model=AttendanceSchema)
def create_attendance(
    attendance: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    db_attendance = Attendance(**attendance.dict())
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

@router.put("/{attendance_id}", response_model=AttendanceSchema)
def update_attendance(
    attendance_id: int,
    attendance_update: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    db_attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    update_data = attendance_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_attendance, field, value)
    
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

@router.delete("/{attendance_id}")
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    db_attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not db_attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    db.delete(db_attendance)
    db.commit()
    return {"message": "Attendance record deleted successfully"}

@router.get("/stats/{employee_id}")
def get_attendance_stats(
    employee_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Employees can only view their own stats
    if current_user.role == UserRole.EMPLOYEE:
        employee = db.query(Employee).filter(Employee.email == current_user.email).first()
        if employee and employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Not authorized to view these stats")
    
    attendance_records = db.query(Attendance).filter(
        Attendance.employee_id == employee_id,
        Attendance.date.between(
            datetime(year, month, 1),
            datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
        )
    ).all()
    
    total_days = len(attendance_records)
    present_days = len([a for a in attendance_records if a.status == "present"])
    absent_days = len([a for a in attendance_records if a.status == "absent"])
    late_days = len([a for a in attendance_records if a.status == "late"])
    half_days = len([a for a in attendance_records if a.status == "half_day"])
    
    return {
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "late_days": late_days,
        "half_days": half_days,
        "attendance_percentage": (present_days / total_days * 100) if total_days > 0 else 0
    }
