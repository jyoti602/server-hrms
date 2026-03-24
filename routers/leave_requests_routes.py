from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth.auth import get_current_active_user, require_role
from db.database import get_db
from models.leave_request import LeaveRequest, LeaveStatus
from models.leave_type_option import LeaveTypeOption
from models.user import User, UserRole
from tenant_context import get_tenant_db_session
from tenant_models.employee import Employee
from schemas.leave_request import (
    LeaveRequestCreate,
    LeaveRequestResponse,
    LeaveRequestUpdate,
)

router = APIRouter(prefix="/leave-requests", tags=["leave-requests"])


def get_current_tenant_db(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    yield from get_tenant_db_session(current_user.company_id, db)


def get_employee_by_id(db: Session, employee_id: int) -> Optional[Employee]:
    return (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )


def get_employee_for_user(db: Session, user: User) -> Optional[Employee]:
    return (
        db.query(Employee)
        .filter(Employee.email == user.email)
        .first()
    )


def validate_leave_dates(from_date, to_date):
    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="To date must be after from date",
        )


def validate_leave_type_exists(db: Session, leave_type_name: str, company_id: int):
    leave_type = (
        db.query(LeaveTypeOption)
        .filter(
            LeaveTypeOption.name == leave_type_name.strip(),
            LeaveTypeOption.company_id == company_id,
            LeaveTypeOption.is_active.is_(True),
        )
        .first()
    )
    if not leave_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select a valid leave type",
        )


@router.get("/all", response_model=List[LeaveRequestResponse])
def get_all_leave_requests_admin(
    status_filter: Optional[LeaveStatus] = Query(
        None,
        alias="status",
        description="Filter by status",
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    query = db.query(LeaveRequest).filter(LeaveRequest.company_id == current_user.company_id)

    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter.value)

    return query.order_by(LeaveRequest.created_at.desc()).offset(skip).limit(limit).all()


@router.put("/update-status/{leave_id}", response_model=LeaveRequestResponse)
def update_leave_status(
    leave_id: int,
    status_value: LeaveStatus = Query(..., alias="status", description="New status"),
    admin_comment: Optional[str] = Query(None, max_length=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    leave_request = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.id == leave_id,
            LeaveRequest.company_id == current_user.company_id,
        )
        .first()
    )
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")

    leave_request.status = status_value.value
    leave_request.admin_comment = admin_comment.strip() if admin_comment else None
    leave_request.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(leave_request)
    return leave_request


@router.post("/", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    leave_request: LeaveRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_db: Session = Depends(get_current_tenant_db),
):
    validate_leave_dates(leave_request.from_date, leave_request.to_date)
    normalized_leave_type = leave_request.leave_type.strip()
    validate_leave_type_exists(db, normalized_leave_type, current_user.company_id)

    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(tenant_db, current_user)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee profile not found")
    else:
        if not leave_request.employee_id:
            raise HTTPException(status_code=400, detail="Employee is required")

        try:
            employee_id = int(leave_request.employee_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid employee ID") from exc

        employee = get_employee_by_id(tenant_db, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

    db_leave_request = LeaveRequest(
        company_id=current_user.company_id,
        employee_id=str(employee.id),
        employee_name=employee.name,
        leave_type=normalized_leave_type,
        from_date=leave_request.from_date,
        to_date=leave_request.to_date,
        reason=leave_request.reason.strip(),
        status=LeaveStatus.PENDING.value,
        admin_comment=None,
        reviewed_at=None,
    )

    db.add(db_leave_request)
    db.commit()
    db.refresh(db_leave_request)
    return db_leave_request


@router.get("/", response_model=List[LeaveRequestResponse])
def get_leave_requests(
    employee_id: Optional[str] = Query(None, description="Filter by employee ID"),
    status_filter: Optional[LeaveStatus] = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_db: Session = Depends(get_current_tenant_db),
):
    query = db.query(LeaveRequest).filter(LeaveRequest.company_id == current_user.company_id)

    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(tenant_db, current_user)
        if not employee:
            return []
        query = query.filter(LeaveRequest.employee_id == str(employee.id))
    elif employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)

    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter.value)

    return query.order_by(LeaveRequest.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/employee/{employee_id}", response_model=List[LeaveRequestResponse])
def get_employee_leave_requests(
    employee_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_db: Session = Depends(get_current_tenant_db),
):
    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(tenant_db, current_user)
        if not employee or str(employee.id) != employee_id:
            raise HTTPException(status_code=403, detail="Not authorized to view these leave requests")

    return (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.company_id == current_user.company_id,
        )
        .order_by(LeaveRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{leave_id}", response_model=LeaveRequestResponse)
def get_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_db: Session = Depends(get_current_tenant_db),
):
    leave_request = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.id == leave_id,
            LeaveRequest.company_id == current_user.company_id,
        )
        .first()
    )
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(tenant_db, current_user)
        if not employee or leave_request.employee_id != str(employee.id):
            raise HTTPException(status_code=403, detail="Not authorized to view this leave request")

    return leave_request


@router.put("/{leave_id}", response_model=LeaveRequestResponse)
def update_leave_request(
    leave_id: int,
    leave_update: LeaveRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_db: Session = Depends(get_current_tenant_db),
):
    leave_request = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.id == leave_id,
            LeaveRequest.company_id == current_user.company_id,
        )
        .first()
    )
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if current_user.role == UserRole.ADMIN:
        if leave_update.status is not None:
            leave_request.status = leave_update.status.value
            leave_request.reviewed_at = datetime.utcnow()
        if leave_update.admin_comment is not None:
            leave_request.admin_comment = leave_update.admin_comment.strip() or None
    else:
        employee = get_employee_for_user(tenant_db, current_user)
        if not employee or leave_request.employee_id != str(employee.id):
            raise HTTPException(status_code=403, detail="Not authorized to update this leave request")
        if leave_request.status != LeaveStatus.PENDING.value:
            raise HTTPException(status_code=400, detail="Only pending leave requests can be updated")
        if leave_update.status != LeaveStatus.REJECTED:
            raise HTTPException(status_code=403, detail="Employees can only cancel their pending leave requests")
        leave_request.status = LeaveStatus.REJECTED.value

    db.commit()
    db.refresh(leave_request)
    return leave_request


@router.delete("/{leave_id}")
def delete_leave_request(
    leave_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_db: Session = Depends(get_current_tenant_db),
):
    leave_request = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.id == leave_id,
            LeaveRequest.company_id == current_user.company_id,
        )
        .first()
    )
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if current_user.role == UserRole.EMPLOYEE:
        employee = get_employee_for_user(tenant_db, current_user)
        if not employee or leave_request.employee_id != str(employee.id):
            raise HTTPException(status_code=403, detail="Not authorized to delete this leave request")
        if leave_request.status != LeaveStatus.PENDING.value:
            raise HTTPException(status_code=400, detail="Only pending leave requests can be deleted")

    db.delete(leave_request)
    db.commit()
    return {"message": "Leave request deleted successfully"}
