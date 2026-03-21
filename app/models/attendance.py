from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    check_in = Column(Time)
    check_out = Column(Time)
    status = Column(String, nullable=False)  # present, absent, late, half_day
    work_hours = Column(Integer)  # in hours
    overtime_hours = Column(Integer, default=0)
    notes = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    employee = relationship("Employee", back_populates="attendance")
