from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from db.database import engine, get_db
from models import user, attendance, leave, payroll
from models.leave_request import LeaveRequest

# Import routers
from routers import auth, employees, attendance, leaves, payroll
from routers import employees_db  # Database-compatible version
from routers import leave_requests
# Create database tables
# user.Base.metadata.create_all(bind=engine)  # Temporarily disabled
LeaveRequest.__table__.create(bind=engine, checkfirst=True)  # Create leave_requests table
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
