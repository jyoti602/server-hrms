from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models.leave_request import LeaveRequest, LeaveStatus, LeaveType
from ..schemas.leave_request import (
    LeaveRequestCreate, 
    LeaveRequestResponse, 
    LeaveRequestUpdate, 
    LeaveRequestAdminResponse
)

router = APIRouter(prefix="/leave-requests", tags=["leave-requests"])

# Admin-specific endpoints
@router.get("/all")
def get_all_leave_requests_admin(
    status: Optional[LeaveStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all leave requests for admin
    """
    query = db.query(LeaveRequest)
    
    if status:
        query = query.filter(LeaveRequest.status == status.value)
    
    leave_requests = query.order_by(LeaveRequest.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert to dict manually to avoid serialization issues
    result = []
    for lr in leave_requests:
        result.append({
            "id": lr.id,
            "employee_id": lr.employee_id,
            "employee_name": lr.employee_name,
            "leave_type": lr.leave_type,
            "from_date": lr.from_date.isoformat(),
            "to_date": lr.to_date.isoformat(),
            "reason": lr.reason,
            "status": lr.status,
            "created_at": lr.created_at.isoformat()
        })
    
    return result

@router.put("/update-status/{leave_id}")
def update_leave_status(
    leave_id: int,
    status: LeaveStatus = Query(..., description="New status (Approved/Rejected)"),
    db: Session = Depends(get_db)
):
    """
    Update leave request status (admin endpoint)
    """
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave_request:
        raise HTTPException(
            status_code=404, 
            detail="Leave request not found"
        )
    
    # Update status
    leave_request.status = status.value
    
    db.commit()
    db.refresh(leave_request)
    
    return {
        "id": leave_request.id,
        "employee_id": leave_request.employee_id,
        "employee_name": leave_request.employee_name,
        "leave_type": leave_request.leave_type,
        "from_date": leave_request.from_date.isoformat(),
        "to_date": leave_request.to_date.isoformat(),
        "reason": leave_request.reason,
        "status": leave_request.status,
        "created_at": leave_request.created_at.isoformat()
    }

@router.post("/")
def create_leave_request(
    leave_request: LeaveRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new leave request
    """
    # Validate that to_date is after from_date
    if leave_request.to_date < leave_request.from_date:
        raise HTTPException(
            status_code=400, 
            detail="To date must be after from date"
        )
    
    # Create leave request
    db_leave_request = LeaveRequest(
        employee_id=leave_request.employee_id,
        employee_name=leave_request.employee_name,
        leave_type=leave_request.leave_type.value,
        from_date=leave_request.from_date,
        to_date=leave_request.to_date,
        reason=leave_request.reason,
        status=LeaveStatus.PENDING.value
    )
    
    db.add(db_leave_request)
    db.commit()
    db.refresh(db_leave_request)
    
    return {
        "id": db_leave_request.id,
        "employee_id": db_leave_request.employee_id,
        "employee_name": db_leave_request.employee_name,
        "leave_type": db_leave_request.leave_type,
        "from_date": db_leave_request.from_date.isoformat(),
        "to_date": db_leave_request.to_date.isoformat(),
        "reason": db_leave_request.reason,
        "status": db_leave_request.status,
        "created_at": db_leave_request.created_at.isoformat()
    }

@router.get("/", response_model=List[LeaveRequestResponse])
def get_leave_requests(
    employee_id: Optional[str] = Query(None, description="Filter by employee ID"),
    status: Optional[LeaveStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get leave requests with optional filtering
    """
    query = db.query(LeaveRequest)
    
    if employee_id:
        query = query.filter(LeaveRequest.employee_id == employee_id)
    
    if status:
        query = query.filter(LeaveRequest.status == status.value)
    
    leave_requests = query.order_by(LeaveRequest.created_at.desc()).offset(skip).limit(limit).all()
    
    # Convert to dict manually to avoid serialization issues
    result = []
    for lr in leave_requests:
        result.append({
            "id": lr.id,
            "employee_id": lr.employee_id,
            "employee_name": lr.employee_name,
            "leave_type": lr.leave_type,
            "from_date": lr.from_date.isoformat(),
            "to_date": lr.to_date.isoformat(),
            "reason": lr.reason,
            "status": lr.status,
            "created_at": lr.created_at.isoformat()
        })
    
    return result

@router.get("/{leave_id}", response_model=LeaveRequestResponse)
def get_leave_request(
    leave_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific leave request by ID
    """
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave_request:
        raise HTTPException(
            status_code=404, 
            detail="Leave request not found"
        )
    
    return {
        "id": leave_request.id,
        "employee_id": leave_request.employee_id,
        "employee_name": leave_request.employee_name,
        "leave_type": leave_request.leave_type,
        "from_date": leave_request.from_date.isoformat(),
        "to_date": leave_request.to_date.isoformat(),
        "reason": leave_request.reason,
        "status": leave_request.status,
        "created_at": leave_request.created_at.isoformat()
    }

@router.put("/{leave_id}", response_model=LeaveRequestResponse)
def update_leave_request(
    leave_id: int,
    leave_update: LeaveRequestUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a leave request (typically for admin approval/rejection)
    """
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave_request:
        raise HTTPException(
            status_code=404, 
            detail="Leave request not found"
        )
    
    update_data = leave_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(leave_request, field, value.value if isinstance(value, LeaveStatus) else value)
    
    db.commit()
    db.refresh(leave_request)
    
    return {
        "id": leave_request.id,
        "employee_id": leave_request.employee_id,
        "employee_name": leave_request.employee_name,
        "leave_type": leave_request.leave_type,
        "from_date": leave_request.from_date.isoformat(),
        "to_date": leave_request.to_date.isoformat(),
        "reason": leave_request.reason,
        "status": leave_request.status,
        "created_at": leave_request.created_at.isoformat()
    }

@router.delete("/{leave_id}")
def delete_leave_request(
    leave_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a leave request
    """
    leave_request = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave_request:
        raise HTTPException(
            status_code=404, 
            detail="Leave request not found"
        )
    
    db.delete(leave_request)
    db.commit()
    
    return {"message": "Leave request deleted successfully"}

@router.get("/employee/{employee_id}", response_model=List[LeaveRequestResponse])
def get_employee_leave_requests(
    employee_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all leave requests for a specific employee
    """
    leave_requests = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id
    ).order_by(LeaveRequest.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for lr in leave_requests:
        result.append({
            "id": lr.id,
            "employee_id": lr.employee_id,
            "employee_name": lr.employee_name,
            "leave_type": lr.leave_type,
            "from_date": lr.from_date,
            "to_date": lr.to_date,
            "reason": lr.reason,
            "status": lr.status,
            "created_at": lr.created_at
        })
    
    return result
