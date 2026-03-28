# HRMS Backend API

FastAPI-based backend for the Human Resource Management System.

## Features

- **Authentication**: JWT-based authentication with role-based access control
- **Employee Management**: CRUD operations for employee data
- **Attendance Tracking**: Manage employee attendance with statistics
- **Leave Management**: Apply, approve, and track leave requests
- **Payroll System**: Generate and manage payroll with bulk operations
- **Database**: SQLAlchemy ORM with Alembic migrations

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file with the following variables:

```env
DATABASE_URL=postgresql://hrms_user:hrms_password@localhost/hrms_db
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Database Setup

**Option 1: PostgreSQL (Recommended)**
```bash
# Create database
createdb hrms_db

# Create user
createuser hrms_user
psql -c "ALTER USER hrms_user WITH PASSWORD 'hrms_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE hrms_db TO hrms_user;"
```

**Option 2: SQLite (Development)**
Change `DATABASE_URL` in `.env` to:
```env
DATABASE_URL=sqlite:///./hrms.db
```

### 4. Database Migrations

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 5. Run the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get access token

Login accepts either JSON or form data. Include `company_slug` when the frontend is deployed on a shared domain:

```json
{
  "username": "admin",
  "password": "secret",
  "company_slug": "it-technology"
}
```

### Employees (Admin only for full access)
- `GET /employees` - List all employees
- `GET /employees/{id}` - Get employee by ID
- `POST /employees` - Create new employee
- `PUT /employees/{id}` - Update employee
- `DELETE /employees/{id}` - Delete employee

### Attendance
- `GET /attendance` - List attendance records
- `GET /attendance/{id}` - Get attendance by ID
- `POST /attendance` - Create attendance record (Admin)
- `PUT /attendance/{id}` - Update attendance (Admin)
- `DELETE /attendance/{id}` - Delete attendance (Admin)
- `GET /attendance/stats/{employee_id}` - Get attendance statistics

### Leaves
- `GET /leaves` - List leave requests
- `GET /leaves/{id}` - Get leave by ID
- `POST /leaves` - Create leave request
- `PUT /leaves/{id}` - Update leave (approve/reject)
- `DELETE /leaves/{id}` - Delete leave (Admin)
- `GET /leaves/pending/count` - Get pending leaves count (Admin)

### Payroll
- `GET /payroll` - List payroll records
- `GET /payroll/{id}` - Get payroll by ID
- `POST /payroll` - Create payroll (Admin)
- `PUT /payroll/{id}` - Update payroll (Admin)
- `DELETE /payroll/{id}` - Delete payroll (Admin)
- `GET /payroll/monthly/{month}` - Get monthly payroll summary (Admin)
- `POST /payroll/generate-bulk` - Generate bulk payroll (Admin)

## Authentication

The API uses JWT tokens for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_token>
```

## Role-Based Access Control

- **Admin**: Full access to all endpoints
- **Employee**: Limited access to own data only

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app
```

## Project Structure

```
backend-system/
├── app/
│   ├── __init__.py
│   ├── database.py          # Database configuration
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── employee.py
│   │   ├── attendance.py
│   │   ├── leave.py
│   │   └── payroll.py
│   ├── schemas/             # Pydantic models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── employee.py
│   │   ├── attendance.py
│   │   ├── leave.py
│   │   └── payroll.py
│   ├── auth/                # Authentication utilities
│   │   ├── __init__.py
│   │   └── auth.py
│   └── routers/             # API routes
│       ├── __init__.py
│       ├── auth.py
│       ├── employees.py
│       ├── attendance.py
│       ├── leaves.py
│       └── payroll.py
├── alembic/                 # Database migrations
├── main.py                  # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md               # This file
```

## Development Notes

- The API supports CORS for frontend development
- Database models include relationships for data integrity
- All endpoints include proper error handling
- Input validation using Pydantic schemas
- Password hashing using bcrypt
- JWT tokens with configurable expiration
