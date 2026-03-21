from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import engine, get_db
from app.models import user, attendance, leave, payroll
from app.models.employee_simple import EmployeeSimple
from app.models.leave_request import LeaveRequest
from app.models.employee_registration import EmployeeData

# Import routers
from app.routers import auth, employees, attendance, leaves, payroll
from app.routers import employees_db  # Database-compatible version
from app.routers import leave_requests
from app.routers import employee_registrations

# Create database tables
# user.Base.metadata.create_all(bind=engine)  # Temporarily disabled
EmployeeSimple.__table__.create(bind=engine, checkfirst=True)  # Create employees table
LeaveRequest.__table__.create(bind=engine, checkfirst=True)  # Create leave_requests table
EmployeeData.__table__.create(bind=engine, checkfirst=True)  # Create employees_data table
# attendance.Base.metadata.create_all(bind=engine)  # Temporarily disabled
# leave.Base.metadata.create_all(bind=engine)  # Temporarily disabled
# payroll.Base.metadata.create_all(bind=engine)  # Temporarily disabled

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
app.include_router(auth.router)
app.include_router(employees_db.router)  # Use database-compatible version
app.include_router(leave_requests.router)  # Add leave requests router
app.include_router(employee_registrations.router)  # Add employee registrations router
app.include_router(attendance.router)
app.include_router(leaves.router)
app.include_router(payroll.router)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
