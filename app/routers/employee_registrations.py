from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..database import get_db
from ..models.employee_registration import EmployeeData, UserRole
from ..schemas.employee_registration import (
    EmployeeDataCreate,
    EmployeeDataResponse,
    EmployeeDataAdminResponse,
    EmployeeDataUpdate,
    RegistrationStats
)

router = APIRouter(prefix="/employee-registrations", tags=["employee-registrations"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# Login schemas
class LoginRequest(BaseModel):
    email: str
    password: str
    role: str = "employee"  # Default to employee

class LoginResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    employee_id: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    message: str

# Public endpoint for employee registration
@router.post("/register", response_model=EmployeeDataResponse)
def register_employee(
    registration: EmployeeDataCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new employee (public endpoint)
    """
    # Check if email already exists
    existing_email = db.query(EmployeeData).filter(
        EmployeeData.email == registration.email
    ).first()
    
    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Check if employee_id already exists (if provided)
    if registration.employee_id:
        existing_id = db.query(EmployeeData).filter(
            EmployeeData.employee_id == registration.employee_id
        ).first()
        
        if existing_id:
            raise HTTPException(
                status_code=400,
                detail="Employee ID already exists"
            )
    
    # Create new employee registration
    hashed_password = get_password_hash(registration.password)
    
    db_employee = EmployeeData(
        full_name=registration.full_name,
        email=registration.email,
        phone=registration.phone,
        password=hashed_password,
        profile_pic=registration.profile_pic,
        gender=registration.gender,
        dob=registration.dob,
        address=registration.address,
        employee_id=registration.employee_id,
        department=registration.department,
        designation=registration.designation,
        role=registration.role
    )
    
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    
    return {
        "id": db_employee.id,
        "full_name": db_employee.full_name,
        "email": db_employee.email,
        "phone": db_employee.phone,
        "profile_pic": db_employee.profile_pic,
        "gender": db_employee.gender,
        "dob": db_employee.dob.isoformat() if db_employee.dob else None,
        "address": db_employee.address,
        "employee_id": db_employee.employee_id,
        "department": db_employee.department,
        "designation": db_employee.designation,
        "role": db_employee.role.value,
        "created_at": db_employee.created_at.isoformat(),
        "updated_at": db_employee.updated_at.isoformat() if db_employee.updated_at else None
    }

# Admin endpoints
@router.get("/all", response_model=List[EmployeeDataAdminResponse])
def get_all_employees_admin(
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all employees for admin
    """
    query = db.query(EmployeeData)
    
    if role:
        query = query.filter(EmployeeData.role == role)
    
    employees = query.order_by(EmployeeData.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert to dict manually to avoid serialization issues
    result = []
    for emp in employees:
        result.append({
            "id": emp.id,
            "full_name": emp.full_name,
            "email": emp.email,
            "phone": emp.phone,
            "profile_pic": emp.profile_pic,
            "gender": emp.gender,
            "dob": emp.dob.isoformat() if emp.dob else None,
            "address": emp.address,
            "employee_id": emp.employee_id,
            "department": emp.department,
            "designation": emp.designation,
            "role": emp.role.value,
            "created_at": emp.created_at.isoformat(),
            "updated_at": emp.updated_at.isoformat() if emp.updated_at else None
        })
    
    return result

@router.get("/stats", response_model=RegistrationStats)
def get_employee_stats(db: Session = Depends(get_db)):
    """
    Get employee statistics for admin dashboard
    """
    total_employees = db.query(EmployeeData).filter(
        EmployeeData.role == UserRole.EMPLOYEE
    ).count()
    
    total_admins = db.query(EmployeeData).filter(
        EmployeeData.role == UserRole.ADMIN
    ).count()
    
    # Recent registrations (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_registrations = db.query(EmployeeData).filter(
        EmployeeData.created_at >= thirty_days_ago
    ).count()
    
    return {
        "total_employees": total_employees,
        "total_admins": total_admins,
        "recent_registrations": recent_registrations
    }

@router.get("/{employee_id}", response_model=EmployeeDataAdminResponse)
def get_employee_by_id(
    employee_id: int,
    db: Session = Depends(get_db)
):
    """
    Get specific employee by ID (admin only)
    """
    employee = db.query(EmployeeData).filter(
        EmployeeData.id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )
    
    return {
        "id": employee.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "phone": employee.phone,
        "profile_pic": employee.profile_pic,
        "gender": employee.gender,
        "dob": employee.dob.isoformat() if employee.dob else None,
        "address": employee.address,
        "employee_id": employee.employee_id,
        "department": employee.department,
        "designation": employee.designation,
        "role": employee.role.value,
        "created_at": employee.created_at.isoformat(),
        "updated_at": employee.updated_at.isoformat() if employee.updated_at else None
    }

@router.put("/{employee_id}", response_model=EmployeeDataAdminResponse)
def update_employee(
    employee_id: int,
    employee_update: EmployeeDataUpdate,
    db: Session = Depends(get_db)
):
    """
    Update employee details (admin only)
    """
    employee = db.query(EmployeeData).filter(
        EmployeeData.id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )
    
    # Update fields
    update_data = employee_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(employee, field):
            setattr(employee, field, value)
    
    employee.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(employee)
    
    return {
        "id": employee.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "phone": employee.phone,
        "profile_pic": employee.profile_pic,
        "gender": employee.gender,
        "dob": employee.dob.isoformat() if employee.dob else None,
        "address": employee.address,
        "employee_id": employee.employee_id,
        "department": employee.department,
        "designation": employee.designation,
        "role": employee.role.value,
        "created_at": employee.created_at.isoformat(),
        "updated_at": employee.updated_at.isoformat() if employee.updated_at else None
    }

@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an employee (admin only)
    """
    employee = db.query(EmployeeData).filter(
        EmployeeData.id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )
    
    db.delete(employee)
    db.commit()
    
    return {"message": "Employee deleted successfully"}

# Login endpoint
@router.post("/login", response_model=LoginResponse)
def login_employee(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login employee using registration data
    """
    # Find employee by email
    employee = db.query(EmployeeData).filter(
        EmployeeData.email == login_data.email
    ).first()
    
    if not employee:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, employee.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # Verify role matches
    if employee.role.value != login_data.role:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid role. This account is registered as {employee.role.value}"
        )
    
    return {
        "id": employee.id,
        "full_name": employee.full_name,
        "email": employee.email,
        "role": employee.role.value,
        "employee_id": employee.employee_id,
        "department": employee.department,
        "designation": employee.designation,
        "message": "Login successful"
    }
