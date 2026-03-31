from collections.abc import Generator
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.auth import get_current_active_user, get_password_hash, require_role
from db.database import get_db
from models.user import UserRole
from services.service_email import (
    SMTPConnectionFailure,
    SMTPConfigurationError,
    InvalidEmailError,
    send_employee_account_notification,
)
from schemas.employee import Employee as EmployeeSchema, EmployeeCreate, EmployeeUpdate
from tenant_context import get_tenant_db_session
from tenant_models.department import Department
from tenant_models.employee import Employee, EmployeeStatus
from tenant_models.user import User

router = APIRouter(prefix="/employees", tags=["employees"])


def get_current_tenant_db(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
) -> Generator[Session, None, None]:
    yield from get_tenant_db_session(current_user.company_id, db)


def get_employee_by_email(db: Session, email: str):
    return db.query(Employee).filter(Employee.email == email).first()


def validate_department_exists(db: Session, department_name: str):
    department = (
        db.query(Department)
        .filter(Department.name == department_name, Department.is_active.is_(True))
        .first()
    )
    if not department:
        raise HTTPException(status_code=400, detail="Please select a valid department")


@router.get("/", response_model=List[EmployeeSchema])
def get_employees(
    skip: int = 0,
    limit: int = 100,
    tenant_db: Session = Depends(get_current_tenant_db),
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    return tenant_db.query(Employee).offset(skip).limit(limit).all()


@router.get("/me", response_model=EmployeeSchema)
def get_my_employee_profile(
    tenant_db: Session = Depends(get_current_tenant_db),
    current_user=Depends(get_current_active_user),
):
    employee = get_employee_by_email(tenant_db, current_user.email)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    return employee


@router.get("/{employee_id}", response_model=EmployeeSchema)
def get_employee(
    employee_id: int,
    tenant_db: Session = Depends(get_current_tenant_db),
    current_user=Depends(get_current_active_user),
):
    employee = tenant_db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if current_user.role == UserRole.EMPLOYEE and employee.email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to view this employee")

    return employee


@router.post("/", response_model=EmployeeSchema)
def create_employee(
    employee: EmployeeCreate,
    tenant_db: Session = Depends(get_current_tenant_db),
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    validate_department_exists(tenant_db, employee.department)

    if tenant_db.query(Employee).filter(Employee.email == employee.email).first():
        raise HTTPException(status_code=400, detail="Employee email already exists")

    existing_user = tenant_db.query(User).filter(User.email == employee.email).first()
    if existing_user:
        account_label = "admin" if existing_user.role == UserRole.ADMIN else "employee"
        friendly_role = "an admin" if existing_user.role == UserRole.ADMIN else "an employee"
        raise HTTPException(
            status_code=400,
            detail=f"This email is already used by {friendly_role} login in this company",
        )

    if tenant_db.query(User).filter(User.username == employee.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    db_user = User(
        email=employee.email,
        username=employee.username,
        full_name=employee.name,
        role=UserRole.EMPLOYEE,
        hashed_password=get_password_hash(employee.password),
        is_active=True,
    )
    tenant_db.add(db_user)

    db_employee = Employee(
        name=employee.name,
        email=employee.email,
        phone=employee.phone,
        department=employee.department,
        position=employee.position,
        date_of_birth=employee.date_of_birth,
        joining_date=employee.joining_date,
        address=employee.address,
        emergency_contact=employee.emergency_contact,
        status=employee.status.value,
    )
    tenant_db.add(db_employee)

    try:
        tenant_db.flush()
        send_employee_account_notification(
            employee_email=employee.email,
            username=employee.username,
            password=employee.password,
        )
        tenant_db.commit()
    except IntegrityError as exc:
        tenant_db.rollback()
        raise HTTPException(status_code=400, detail="Employee email or username already exists") from exc
    except (SMTPConfigurationError, SMTPConnectionFailure, InvalidEmailError) as exc:
        tenant_db.rollback()
        status_code = 400 if isinstance(exc, InvalidEmailError) else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    tenant_db.refresh(db_employee)
    return db_employee


@router.put("/me", response_model=EmployeeSchema)
def update_my_employee_profile(
    employee_update: EmployeeUpdate,
    tenant_db: Session = Depends(get_current_tenant_db),
    current_user=Depends(get_current_active_user),
):
    employee = get_employee_by_email(tenant_db, current_user.email)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    update_data = employee_update.dict(exclude_unset=True)

    if "department" in update_data and update_data["department"]:
        validate_department_exists(tenant_db, update_data["department"])

    restricted_fields = {"department", "position", "status", "username", "password", "joining_date"}
    if any(field in update_data for field in restricted_fields):
        raise HTTPException(
            status_code=403,
            detail="Employees can only update their own basic profile details",
        )

    matched_user = tenant_db.query(User).filter(User.email == current_user.email).first()

    if "email" in update_data:
        email_in_use = (
            tenant_db.query(Employee)
            .filter(Employee.email == update_data["email"], Employee.id != employee.id)
            .first()
        )
        if email_in_use:
            raise HTTPException(status_code=400, detail="Employee email already exists")

        user_in_use = (
            tenant_db.query(User)
            .filter(User.email == update_data["email"], User.id != (matched_user.id if matched_user else 0))
            .first()
        )
        if user_in_use:
            friendly_role = "an admin" if user_in_use.role == UserRole.ADMIN else "an employee"
            raise HTTPException(
                status_code=400,
                detail=f"This email is already used by {friendly_role} login in this company",
            )

        if matched_user:
            matched_user.email = update_data["email"]
        current_user.email = update_data["email"]

    if "name" in update_data and matched_user:
        matched_user.full_name = update_data["name"]

    for field in ("name", "email", "phone", "date_of_birth", "address", "emergency_contact"):
        if field in update_data:
            setattr(employee, field, update_data[field])

    tenant_db.commit()
    tenant_db.refresh(employee)
    return employee


@router.put("/{employee_id}", response_model=EmployeeSchema)
def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    tenant_db: Session = Depends(get_current_tenant_db),
    current_user=Depends(get_current_active_user),
):
    employee = tenant_db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    matched_user = tenant_db.query(User).filter(User.email == employee.email).first()

    if current_user.role == UserRole.EMPLOYEE:
        if employee.email != current_user.email:
            raise HTTPException(status_code=403, detail="Not authorized to update this employee")
        return update_my_employee_profile(employee_update, tenant_db, current_user)

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this employee")

    update_data = employee_update.dict(exclude_unset=True)

    if "department" in update_data and update_data["department"]:
        validate_department_exists(tenant_db, update_data["department"])

    if "email" in update_data:
        email_in_use = (
            tenant_db.query(Employee)
            .filter(Employee.email == update_data["email"], Employee.id != employee.id)
            .first()
        )
        if email_in_use:
            raise HTTPException(status_code=400, detail="Employee email already exists")

        user_in_use = (
            tenant_db.query(User)
            .filter(User.email == update_data["email"], User.id != (matched_user.id if matched_user else 0))
            .first()
        )
        if user_in_use:
            friendly_role = "an admin" if user_in_use.role == UserRole.ADMIN else "an employee"
            raise HTTPException(
                status_code=400,
                detail=f"This email is already used by {friendly_role} login in this company",
            )

    for field in (
        "name",
        "email",
        "phone",
        "department",
        "position",
        "date_of_birth",
        "joining_date",
        "address",
        "emergency_contact",
        "status",
    ):
        if field in update_data:
            value = update_data[field]
            setattr(employee, field, value.value if field == "status" else value)

    if matched_user:
        if "name" in update_data:
            matched_user.full_name = update_data["name"]
        if "email" in update_data:
            matched_user.email = update_data["email"]
        if "username" in update_data:
            username_in_use = (
                tenant_db.query(User)
                .filter(User.username == update_data["username"], User.id != matched_user.id)
                .first()
            )
            if username_in_use:
                raise HTTPException(status_code=400, detail="Username already exists")
            matched_user.username = update_data["username"]
        if "password" in update_data and update_data["password"]:
            matched_user.hashed_password = get_password_hash(update_data["password"])

    tenant_db.commit()
    tenant_db.refresh(employee)
    return employee


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    tenant_db: Session = Depends(get_current_tenant_db),
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    employee = tenant_db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    linked_user = tenant_db.query(User).filter(User.email == employee.email).first()
    if linked_user:
        tenant_db.delete(linked_user)

    tenant_db.delete(employee)
    tenant_db.commit()
    return {"message": "Employee deleted successfully"}
