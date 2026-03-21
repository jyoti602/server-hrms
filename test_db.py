#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models.employee_simple import EmployeeSimple
from sqlalchemy import text

def test_database():
    print("Testing database connection...")
    
    # Test connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Test query
    try:
        db = SessionLocal()
        employees = db.query(EmployeeSimple).all()
        print(f"✅ Found {len(employees)} employees")
        
        for emp in employees:
            print(f"Employee: {emp.__dict__}")
            
        db.close()
    except Exception as e:
        print(f"❌ Query failed: {e}")

if __name__ == "__main__":
    test_database()
