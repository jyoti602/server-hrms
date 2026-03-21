from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.database import engine, get_db
from models import user, attendance, leave, payroll
from models.attendance import Attendance
from models.leave import Leave
from models.leave_request import LeaveRequest
from models.payroll import Payroll

# Import routers
from routers import (
    auth_routes,
    attendance_routes,
    employees_routes,
    leave_requests_routes,
    leaves_routes,
    payroll_routes,
)
# Create database tables
# user.Base.metadata.create_all(bind=engine)  # Temporarily disabled
LeaveRequest.__table__.create(bind=engine, checkfirst=True)
Attendance.__table__.create(bind=engine, checkfirst=True)
Leave.__table__.create(bind=engine, checkfirst=True)
Payroll.__table__.create(bind=engine, checkfirst=True)

app = FastAPI(
    title="HRMS API",
    description="Human Resource Management System API",
    version="1.0.0"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(employees_routes.router)
app.include_router(leave_requests_routes.router)  # Add leave requests router
app.include_router(attendance_routes.router)
app.include_router(leaves_routes.router)
app.include_router(payroll_routes.router)

@app.get("/")
def read_root():
    return {"message": "HRMS API is running", "version": "1.0.0"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Try to execute a simple query to check database connection
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
