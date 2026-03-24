from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.user import User, UserRole
from tenant_context import get_tenant_db_session
from tenant_models.attendance import Attendance
from tenant_models.employee import Employee
from schemas.attendance import (
    Attendance as AttendanceSchema,
    AttendanceActionResponse,
    AttendanceCreate,
    AttendanceUpdate,
)
from auth.auth import get_current_active_user, require_role

router = APIRouter(prefix="/attendance", tags=["attendance"])


def get_current_tenant_db(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    yield from get_tenant_db_session(current_user.company_id, db)


def get_employee_for_user(db: Session, current_user: User) -> Optional[Employee]:
    return (
        db.query(Employee)
        .filter(
            Employee.email == current_user.email,
        )
        .first()
    )


def get_today_bounds() -> tuple[datetime, datetime]:
    now = datetime.now()
    start_of_day = datetime(now.year, now.month, now.day)
    end_of_day = datetime(now.year, now.month, now.day, 23, 59, 59, 999999)
    return start_of_day, end_of_day


def get_today_attendance_record(db: Session, employee_id: int) -> Optional[Attendance]:
    start_of_day, end_of_day = get_today_bounds()
    return (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start_of_day,
            Attendance.date <= end_of_day,
        )
        .first()
    )

@router.get("/", response_model=List[AttendanceSchema])
def get_attendance(
    skip: int = 0,
    limit: int = 100,
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Attendance)
    
    # Employees can only see their own attendance
    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(db, current_user)
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

@router.get("/today", response_model=Optional[AttendanceSchema])
def get_today_attendance(
    employee_id: Optional[int] = None,
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(db, current_user)
        if not employee:
            return None
        employee_id = employee.id
    elif employee_id is None:
        raise HTTPException(status_code=400, detail="employee_id is required for admin")

    return get_today_attendance_record(db, employee_id)


@router.post("/check-in", response_model=AttendanceActionResponse)
def check_in(
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(require_role(UserRole.EMPLOYEE)),
):
    employee = get_employee_for_user(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    existing_record = get_today_attendance_record(db, employee.id)

    if existing_record and existing_record.check_in:
        raise HTTPException(status_code=400, detail="Check-in already recorded for today")

    now = datetime.now()
    if existing_record:
        existing_record.date = now
        existing_record.check_in = now.time().replace(microsecond=0)
        existing_record.status = "Present"
        attendance = existing_record
    else:
        attendance = Attendance(
            employee_id=employee.id,
            date=now,
            check_in=now.time().replace(microsecond=0),
            status="Present",
            overtime_hours=0,
        )
        db.add(attendance)

    db.commit()
    db.refresh(attendance)
    return {"message": "Check-in recorded successfully", "attendance": attendance}


@router.post("/lunch-start", response_model=AttendanceActionResponse)
def lunch_start(
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(require_role(UserRole.EMPLOYEE)),
):
    employee = get_employee_for_user(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    attendance = get_today_attendance_record(db, employee.id)
    if not attendance or not attendance.check_in:
        raise HTTPException(status_code=400, detail="Please check in before starting lunch")

    if attendance.check_out:
        raise HTTPException(status_code=400, detail="Cannot start lunch after check-out")

    if attendance.lunch_start and not attendance.lunch_end:
        raise HTTPException(status_code=400, detail="Lunch break already started")

    if attendance.lunch_start and attendance.lunch_end:
        raise HTTPException(status_code=400, detail="Lunch break already completed for today")

    attendance.lunch_start = datetime.now().time().replace(microsecond=0)
    db.commit()
    db.refresh(attendance)
    return {"message": "Lunch break started", "attendance": attendance}


@router.post("/lunch-end", response_model=AttendanceActionResponse)
def lunch_end(
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(require_role(UserRole.EMPLOYEE)),
):
    employee = get_employee_for_user(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    attendance = get_today_attendance_record(db, employee.id)
    if not attendance or not attendance.check_in:
        raise HTTPException(status_code=400, detail="Please check in before ending lunch")

    if not attendance.lunch_start:
        raise HTTPException(status_code=400, detail="Lunch break has not started")

    if attendance.lunch_end:
        raise HTTPException(status_code=400, detail="Lunch break already ended")

    if attendance.check_out:
        raise HTTPException(status_code=400, detail="Cannot end lunch after check-out")

    attendance.lunch_end = datetime.now().time().replace(microsecond=0)
    db.commit()
    db.refresh(attendance)
    return {"message": "Lunch break ended", "attendance": attendance}


@router.post("/check-out", response_model=AttendanceActionResponse)
def check_out(
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(require_role(UserRole.EMPLOYEE)),
):
    employee = get_employee_for_user(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    attendance = get_today_attendance_record(db, employee.id)

    if not attendance or not attendance.check_in:
        raise HTTPException(status_code=400, detail="Please check in before checking out")

    if attendance.check_out:
        raise HTTPException(status_code=400, detail="Check-out already recorded for today")

    now = datetime.now()
    attendance.check_out = now.time().replace(microsecond=0)

    check_in_datetime = datetime.combine(now.date(), attendance.check_in)
    lunch_break_hours = 0
    if attendance.lunch_start and attendance.lunch_end:
        lunch_start_datetime = datetime.combine(now.date(), attendance.lunch_start)
        lunch_end_datetime = datetime.combine(now.date(), attendance.lunch_end)
        lunch_break_hours = max((lunch_end_datetime - lunch_start_datetime).total_seconds() / 3600, 0)

    duration_hours = max((now - check_in_datetime).total_seconds() / 3600 - lunch_break_hours, 0)
    attendance.work_hours = int(duration_hours)
    attendance.overtime_hours = max(int(duration_hours - 8), 0)

    db.commit()
    db.refresh(attendance)
    return {"message": "Check-out recorded successfully", "attendance": attendance}


@router.get("/{attendance_id}", response_model=AttendanceSchema)
def get_attendance_record(
    attendance_id: int,
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(get_current_active_user)
):
    attendance = (
        db.query(Attendance)
        .filter(Attendance.id == attendance_id)
        .first()
    )
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Employees can only view their own attendance
    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(db, current_user)
        if employee and attendance.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this attendance")
    
    return attendance

@router.post("/", response_model=AttendanceSchema)
def create_attendance(
    attendance: AttendanceCreate,
    db: Session = Depends(get_current_tenant_db),
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
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    db_attendance = (
        db.query(Attendance)
        .filter(Attendance.id == attendance_id)
        .first()
    )
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
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    db_attendance = (
        db.query(Attendance)
        .filter(Attendance.id == attendance_id)
        .first()
    )
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
    db: Session = Depends(get_current_tenant_db),
    current_user: User = Depends(get_current_active_user)
):
    # Employees can only view their own stats
    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(db, current_user)
        if employee and employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Not authorized to view these stats")
    
    attendance_records = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == employee_id,
            Attendance.date.between(
                datetime(year, month, 1),
                datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1),
            ),
        )
        .all()
    )
    
    total_days = len(attendance_records)
    present_days = len([a for a in attendance_records if a.status.lower() == "present"])
    absent_days = len([a for a in attendance_records if a.status.lower() == "absent"])
    late_days = len([a for a in attendance_records if a.status.lower() == "late"])
    half_days = len([a for a in attendance_records if a.status.lower() == "half_day"])
    
    return {
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "late_days": late_days,
        "half_days": half_days,
        "attendance_percentage": (present_days / total_days * 100) if total_days > 0 else 0
    }
