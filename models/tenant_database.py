from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class TenantDatabase(Base):
    __tablename__ = "tenant_databases"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, unique=True, index=True)
    db_name = Column(String(255), nullable=False, unique=True, index=True)
    db_host = Column(String(255), nullable=False)
    db_port = Column(String(20), nullable=False)
    db_user = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company = relationship("Company", back_populates="tenant_database")
