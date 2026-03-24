from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth.auth import get_current_active_user, require_role
from db.database import get_db
from models.department import Department as CompanyDepartment
from models.employee import Employee
from models.leave_request import LeaveRequest, LeaveStatus
from models.leave_type_option import LeaveTypeOption
from models.user import User, UserRole
from tenant_context import get_tenant_db_session
from tenant_models.department import Department as TenantDepartment
from schemas.options import (
    DepartmentCreate,
    DepartmentResponse,
    LeaveBalanceResponse,
    LeaveTypeOptionCreate,
    LeaveTypeOptionResponse,
    LeaveTypeOptionUpdate,
)

router = APIRouter(prefix="/options", tags=["options"])


def get_employee_for_user(db: Session, user: User) -> Employee | None:
    return (
        db.query(Employee)
        .filter(Employee.email == user.email, Employee.company_id == user.company_id)
        .first()
    )


def get_current_tenant_db(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    yield from get_tenant_db_session(current_user.company_id, db)


def normalize_name(value: str) -> str:
    return " ".join(value.strip().split())


def count_days_in_year(start_date: date, end_date: date, year: int) -> int:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    overlap_start = max(start_date, year_start)
    overlap_end = min(end_date, year_end)
    if overlap_end < overlap_start:
        return 0
    return (overlap_end - overlap_start).days + 1


@router.get("/departments", response_model=List[DepartmentResponse])
def get_departments(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    tenant_db: Session = Depends(get_current_tenant_db),
):
    company_departments = (
        db.query(CompanyDepartment)
        .filter(CompanyDepartment.company_id == current_user.company_id)
        .order_by(CompanyDepartment.name.asc())
        .all()
    )
    tenant_departments = {
        department.name: department for department in tenant_db.query(TenantDepartment).all()
    }

    synced = False
    for company_department in company_departments:
        tenant_department = tenant_departments.get(company_department.name)
        if not tenant_department:
            tenant_db.add(
                TenantDepartment(
                    name=company_department.name,
                    description=company_department.description,
                    is_active=company_department.is_active,
                )
            )
            synced = True
            continue

        if tenant_department.description != company_department.description:
            tenant_department.description = company_department.description
            synced = True

        if tenant_department.is_active != company_department.is_active:
            tenant_department.is_active = company_department.is_active
            synced = True

    if synced:
        tenant_db.commit()

    query = tenant_db.query(TenantDepartment)
    if not include_inactive:
        query = query.filter(TenantDepartment.is_active.is_(True))
    return query.order_by(TenantDepartment.name.asc()).all()


@router.post("/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    department: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    tenant_db: Session = Depends(get_current_tenant_db),
):
    normalized_name = normalize_name(department.name)
    existing = tenant_db.query(TenantDepartment).filter(TenantDepartment.name == normalized_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department already exists")

    company_department = (
        db.query(CompanyDepartment)
        .filter(
            CompanyDepartment.name == normalized_name,
            CompanyDepartment.company_id == current_user.company_id,
        )
        .first()
    )

    description = department.description.strip() if department.description else None

    tenant_department = TenantDepartment(
        name=normalized_name,
        description=description,
        is_active=True,
    )
    tenant_db.add(tenant_department)

    if not company_department:
        company_department = CompanyDepartment(
            company_id=current_user.company_id,
            name=normalized_name,
            description=description,
            is_active=True,
        )
        db.add(company_department)

    tenant_db.commit()
    db.commit()
    tenant_db.refresh(tenant_department)
    return tenant_department


@router.get("/leave-types", response_model=List[LeaveTypeOptionResponse])
def get_leave_types(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(LeaveTypeOption)
    query = query.filter(LeaveTypeOption.company_id == current_user.company_id)
    if not include_inactive:
        query = query.filter(LeaveTypeOption.is_active.is_(True))
    return query.order_by(LeaveTypeOption.name.asc()).all()


@router.post("/leave-types", response_model=LeaveTypeOptionResponse, status_code=status.HTTP_201_CREATED)
def create_leave_type(
    leave_type: LeaveTypeOptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    normalized_name = normalize_name(leave_type.name)
    existing = (
        db.query(LeaveTypeOption)
        .filter(
            LeaveTypeOption.name == normalized_name,
            LeaveTypeOption.company_id == current_user.company_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Leave type already exists")

    max_carry_forward_days = (
        leave_type.max_carry_forward_days if leave_type.carry_forward_enabled else 0
    )
    if max_carry_forward_days > leave_type.max_days_per_year:
        raise HTTPException(
            status_code=400,
            detail="Carry forward days cannot exceed max days per year",
        )

    db_leave_type = LeaveTypeOption(
        company_id=current_user.company_id,
        name=normalized_name,
        description=leave_type.description.strip() if leave_type.description else None,
        max_days_per_year=leave_type.max_days_per_year,
        carry_forward_enabled=leave_type.carry_forward_enabled,
        max_carry_forward_days=max_carry_forward_days,
        is_active=True,
    )
    db.add(db_leave_type)
    db.commit()
    db.refresh(db_leave_type)
    return db_leave_type


@router.put("/leave-types/{leave_type_id}", response_model=LeaveTypeOptionResponse)
def update_leave_type(
    leave_type_id: int,
    leave_type_update: LeaveTypeOptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    db_leave_type = (
        db.query(LeaveTypeOption)
        .filter(
            LeaveTypeOption.id == leave_type_id,
            LeaveTypeOption.company_id == current_user.company_id,
        )
        .first()
    )
    if not db_leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")

    update_data = leave_type_update.dict(exclude_unset=True)

    if "name" in update_data:
        normalized_name = normalize_name(update_data["name"])
        existing = (
            db.query(LeaveTypeOption)
            .filter(
                LeaveTypeOption.name == normalized_name,
                LeaveTypeOption.company_id == current_user.company_id,
                LeaveTypeOption.id != leave_type_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Leave type already exists")
        update_data["name"] = normalized_name

    max_days = update_data.get("max_days_per_year", db_leave_type.max_days_per_year)
    carry_enabled = update_data.get("carry_forward_enabled", db_leave_type.carry_forward_enabled)
    max_carry = update_data.get("max_carry_forward_days", db_leave_type.max_carry_forward_days)
    if not carry_enabled:
        max_carry = 0
    if max_carry > max_days:
        raise HTTPException(status_code=400, detail="Carry forward days cannot exceed max days per year")

    update_data["max_carry_forward_days"] = max_carry

    for field, value in update_data.items():
        if field == "description" and value is not None:
            value = value.strip() or None
        setattr(db_leave_type, field, value)

    db.commit()
    db.refresh(db_leave_type)
    return db_leave_type


@router.delete("/leave-types/{leave_type_id}")
def delete_leave_type(
    leave_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    db_leave_type = (
        db.query(LeaveTypeOption)
        .filter(
            LeaveTypeOption.id == leave_type_id,
            LeaveTypeOption.company_id == current_user.company_id,
        )
        .first()
    )
    if not db_leave_type:
        raise HTTPException(status_code=404, detail="Leave type not found")

    in_use = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.leave_type == db_leave_type.name,
            LeaveRequest.company_id == current_user.company_id,
        )
        .first()
    )
    if in_use:
        raise HTTPException(
            status_code=400,
            detail="This leave type is already used in leave requests. Mark it inactive instead.",
        )

    db.delete(db_leave_type)
    db.commit()
    return {"message": "Leave type deleted successfully"}


@router.get("/leave-balances/me", response_model=List[LeaveBalanceResponse])
def get_my_leave_balances(
    year: int = Query(date.today().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    employee = get_employee_for_user(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    leave_types = (
        db.query(LeaveTypeOption)
        .filter(LeaveTypeOption.is_active.is_(True))
        .filter(LeaveTypeOption.company_id == current_user.company_id)
        .order_by(LeaveTypeOption.name.asc())
        .all()
    )
    approved_requests = (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == str(employee.id),
            LeaveRequest.company_id == current_user.company_id,
            LeaveRequest.status == LeaveStatus.APPROVED.value,
        )
        .all()
    )

    balances = []
    for leave_type in leave_types:
        approved_current = 0
        approved_previous = 0

        for request in approved_requests:
            if request.leave_type != leave_type.name:
                continue
            approved_current += count_days_in_year(request.from_date, request.to_date, year)
            approved_previous += count_days_in_year(request.from_date, request.to_date, year - 1)

        carry_forward_days = 0
        if leave_type.carry_forward_enabled:
            unused_previous = max(leave_type.max_days_per_year - approved_previous, 0)
            carry_forward_days = min(unused_previous, leave_type.max_carry_forward_days)

        remaining_balance = max(
            leave_type.max_days_per_year + carry_forward_days - approved_current,
            0,
        )

        balances.append(
            LeaveBalanceResponse(
                leave_type=leave_type.name,
                max_days_per_year=leave_type.max_days_per_year,
                carry_forward_enabled=leave_type.carry_forward_enabled,
                max_carry_forward_days=leave_type.max_carry_forward_days,
                carry_forward_days=carry_forward_days,
                approved_days_taken=approved_current,
                remaining_balance=remaining_balance,
            )
        )

    return balances
