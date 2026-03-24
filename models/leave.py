from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base

class Leave(Base):
    __tablename__ = "leaves"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type = Column(String(50), nullable=False)  # sick, casual, annual, maternity
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    total_days = Column(Float, nullable=False)
    reason = Column(Text)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    approved_by = Column(Integer, ForeignKey("employees.id"))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    company = relationship("Company", back_populates="leaves")
    employee = relationship("Employee", back_populates="leaves", foreign_keys=[employee_id])
    approver = relationship("Employee", back_populates="approved_leaves", foreign_keys=[approved_by])
