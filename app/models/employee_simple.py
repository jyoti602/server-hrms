from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Create a separate Base for EmployeeSimple to avoid conflicts
EmployeeBase = declarative_base()

class EmployeeSimple(EmployeeBase):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    department = Column(String(100), nullable=False, index=True)
    position = Column(String(255), nullable=False)
    status = Column(String(10), nullable=False, default='Active', index=True)  # 'Active' or 'Inactive'
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_email', 'email'),
        Index('idx_department', 'department'),
        Index('idx_status', 'status'),
    )
