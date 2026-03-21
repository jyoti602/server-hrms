#!/usr/bin/env python3
"""
Test script to verify HRMS API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health Check: {response.status_code} - {response.json()}")
        return True
    except Exception as e:
        print(f"Health Check Failed: {e}")
        return False

def test_get_employees():
    """Test get employees endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/employees/")
        print(f"Get Employees: {response.status_code} - {len(response.json())} employees found")
        return True
    except Exception as e:
        print(f"Get Employees Failed: {e}")
        return False

def test_create_employee():
    """Test create employee endpoint"""
    try:
        employee_data = {
            "employee_id": "TEST001",
            "user_id": 1,
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
            "phone": "+1234567890",
            "department": "IT",
            "position": "Test Engineer",
            "salary": 75000.0,
            "hire_date": "2024-01-15T00:00:00Z",
            "is_active": "active"
        }
        
        response = requests.post(f"{BASE_URL}/api/employees/", json=employee_data)
        print(f"Create Employee: {response.status_code} - {response.json()}")
        return True
    except Exception as e:
        print(f"Create Employee Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing HRMS API Endpoints")
    print("=" * 50)
    
    tests = [
        test_health_check,
        test_get_employees,
        test_create_employee
    ]
    
    results = []
    for test in tests:
        print(f"\n📋 Running {test.__name__}...")
        result = test()
        results.append(result)
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All tests passed! API is working correctly.")
    else:
        print("❌ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
