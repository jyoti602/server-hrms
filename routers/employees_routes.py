from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.auth import get_current_active_user, get_password_hash, require_role
from db.database import get_db
from models.employee import Employee
from models.user import User, UserRole
from schemas.employee import Employee as EmployeeSchema, EmployeeCreate, EmployeeUpdate

router = APIRouter(prefix="/employees", tags=["employees"])


def get_employee_by_email(db: Session, email: str):
    return db.query(Employee).filter(Employee.email == email).first()


@router.get("/", response_model=List[EmployeeSchema])
def get_employees(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    return db.query(Employee).offset(skip).limit(limit).all()


@router.get("/me", response_model=EmployeeSchema)
def get_my_employee_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    employee = get_employee_by_email(db, current_user.email)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    return employee


@router.get("/{employee_id}", response_model=EmployeeSchema)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if current_user.role == UserRole.EMPLOYEE and employee.email != current_user.email:
        raise HTTPException(status_code=403, detail="Not authorized to view this employee")

    return employee


@router.post("/", response_model=EmployeeSchema)
def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    if db.query(Employee).filter(Employee.email == employee.email).first():
        raise HTTPException(status_code=400, detail="Employee email already exists")

    if db.query(User).filter(User.email == employee.email).first():
        raise HTTPException(status_code=400, detail="User email already exists")

    if db.query(User).filter(User.username == employee.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    db_user = User(
        email=employee.email,
        username=employee.username,
        full_name=employee.name,
        role=UserRole.EMPLOYEE,
        hashed_password=get_password_hash(employee.password),
        is_active=True,
    )
    db.add(db_user)

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
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee


@router.put("/me", response_model=EmployeeSchema)
def update_my_employee_profile(
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    employee = get_employee_by_email(db, current_user.email)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")

    update_data = employee_update.dict(exclude_unset=True)
    restricted_fields = {"department", "position", "status", "username", "password", "joining_date"}
    if any(field in update_data for field in restricted_fields):
        raise HTTPException(
            status_code=403,
            detail="Employees can only update their own basic profile details",
        )

    if "email" in update_data:
        email_in_use = (
            db.query(Employee)
            .filter(Employee.email == update_data["email"], Employee.id != employee.id)
            .first()
        )
        if email_in_use:
            raise HTTPException(status_code=400, detail="Employee email already exists")

        user_in_use = (
            db.query(User)
            .filter(User.email == update_data["email"], User.id != current_user.id)
            .first()
        )
        if user_in_use:
            raise HTTPException(status_code=400, detail="User email already exists")

        current_user.email = update_data["email"]

    if "name" in update_data:
        current_user.full_name = update_data["name"]

    for field in ("name", "email", "phone", "date_of_birth", "address", "emergency_contact"):
        if field in update_data:
            setattr(employee, field, update_data[field])

    db.commit()
    db.refresh(employee)
    return employee


@router.put("/{employee_id}", response_model=EmployeeSchema)
def update_employee(
    employee_id: int,
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    matched_user = db.query(User).filter(User.email == employee.email).first()

    if current_user.role == UserRole.EMPLOYEE:
        if employee.email != current_user.email:
            raise HTTPException(status_code=403, detail="Not authorized to update this employee")
        return update_my_employee_profile(employee_update, db, current_user)

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this employee")

    update_data = employee_update.dict(exclude_unset=True)

    if "email" in update_data:
        email_in_use = (
            db.query(Employee)
            .filter(Employee.email == update_data["email"], Employee.id != employee.id)
            .first()
        )
        if email_in_use:
            raise HTTPException(status_code=400, detail="Employee email already exists")

        user_in_use = (
            db.query(User)
            .filter(
                User.email == update_data["email"],
                User.id != (matched_user.id if matched_user else 0),
            )
            .first()
        )
        if user_in_use:
            raise HTTPException(status_code=400, detail="User email already exists")

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
                db.query(User)
                .filter(User.username == update_data["username"], User.id != matched_user.id)
                .first()
            )
            if username_in_use:
                raise HTTPException(status_code=400, detail="Username already exists")
            matched_user.username = update_data["username"]
        if "password" in update_data and update_data["password"]:
            matched_user.hashed_password = get_password_hash(update_data["password"])

    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    linked_user = db.query(User).filter(User.email == employee.email).first()
    if linked_user:
        db.delete(linked_user)

    db.delete(employee)
    db.commit()
    return {"message": "Employee deleted successfully"}
