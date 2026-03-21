from sqlalchemy import Column, Integer, String, Date, Text, Enum, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    EMPLOYEE = "employee"
    ADMIN = "admin"

class EmployeeData(Base):
    __tablename__ = "employees_data"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(15), nullable=True)
    password = Column(String(255), nullable=False)
    profile_pic = Column(String(255), nullable=True)
    gender = Column(String(10), nullable=True)
    dob = Column(Date, nullable=True)
    address = Column(Text, nullable=True)
    employee_id = Column(String(50), unique=True, nullable=True, index=True)
    department = Column(String(100), nullable=True)
    designation = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
