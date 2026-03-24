from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from db.database import SessionLocal, engine, get_db
from models import attendance, leave, payroll, user
from models.attendance import Attendance
from models.company import Company
from models.department import Department
from models.leave import Leave
from models.leave_request import LeaveRequest
from models.leave_type_option import LeaveTypeOption
from models.payroll import Payroll
from models.tenant_database import TenantDatabase
from tenant_context import extract_tenant_slug, get_company_by_slug

# Import routers
from routers import (
    auth_routes,
    attendance_routes,
    company_routes,
    employees_routes,
    leave_requests_routes,
    leaves_routes,
    options_routes,
    payroll_routes,
)
# Create database tables
# user.Base.metadata.create_all(bind=engine)  # Temporarily disabled
Company.__table__.create(bind=engine, checkfirst=True)
TenantDatabase.__table__.create(bind=engine, checkfirst=True)
LeaveRequest.__table__.create(bind=engine, checkfirst=True)
Attendance.__table__.create(bind=engine, checkfirst=True)
Leave.__table__.create(bind=engine, checkfirst=True)
Payroll.__table__.create(bind=engine, checkfirst=True)
Department.__table__.create(bind=engine, checkfirst=True)
LeaveTypeOption.__table__.create(bind=engine, checkfirst=True)


def ensure_default_company() -> int:
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT id FROM companies WHERE slug = 'default' LIMIT 1")
        ).fetchone()
        if row:
            return row[0]

        connection.execute(
            text(
                "INSERT INTO companies (name, slug, email, phone, is_active) "
                "VALUES (:name, :slug, :email, :phone, :is_active)"
            ),
            {
                "name": "Default Company",
                "slug": "default",
                "email": None,
                "phone": None,
                "is_active": True,
            },
        )
        row = connection.execute(
            text("SELECT id FROM companies WHERE slug = 'default' LIMIT 1")
        ).fetchone()
        return row[0]


def ensure_company_columns(default_company_id: int):
    company_tables = [
        "users",
        "employees",
        "departments",
        "leave_type_options",
        "attendance",
        "leave_requests",
        "payrolls",
        "leaves",
    ]

    with engine.begin() as connection:
        for table_name in company_tables:
            inspector = inspect(engine)
            if not inspector.has_table(table_name):
                continue

            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if "company_id" not in columns:
                try:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN company_id INT NULL")
                    )
                except OperationalError as exc:
                    if "Duplicate column name" not in str(exc):
                        raise

            connection.execute(
                text(
                    f"UPDATE {table_name} SET company_id = :company_id "
                    "WHERE company_id IS NULL"
                ),
                {"company_id": default_company_id},
            )


def ensure_multitenant_indexes():
    with engine.begin() as connection:
        employee_indexes = connection.execute(text("SHOW INDEX FROM employees")).mappings().all()
        user_indexes = connection.execute(text("SHOW INDEX FROM users")).mappings().all()
        department_indexes = connection.execute(text("SHOW INDEX FROM departments")).mappings().all()
        leave_type_indexes = connection.execute(text("SHOW INDEX FROM leave_type_options")).mappings().all()

        if any(
            index["Key_name"] == "ix_users_email" and index["Non_unique"] == 0
            for index in user_indexes
        ):
            connection.execute(text("ALTER TABLE users DROP INDEX ix_users_email"))

        if any(
            index["Key_name"] == "ix_users_username" and index["Non_unique"] == 0
            for index in user_indexes
        ):
            connection.execute(text("ALTER TABLE users DROP INDEX ix_users_username"))

        existing_user_index_names = {index["Key_name"] for index in user_indexes}
        if "uq_users_company_email" not in existing_user_index_names:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX uq_users_company_email "
                    "ON users (company_id, email)"
                )
            )
        if "uq_users_company_username" not in existing_user_index_names:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX uq_users_company_username "
                    "ON users (company_id, username)"
                )
            )

        if any(
            index["Key_name"] == "email" and index["Non_unique"] == 0
            for index in employee_indexes
        ):
            connection.execute(text("ALTER TABLE employees DROP INDEX email"))

        existing_employee_index_names = {index["Key_name"] for index in employee_indexes}
        if "uq_employees_company_email" not in existing_employee_index_names:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX uq_employees_company_email "
                    "ON employees (company_id, email)"
                )
            )

        if any(
            index["Key_name"] == "ix_departments_name" and index["Non_unique"] == 0
            for index in department_indexes
        ):
            connection.execute(text("DROP INDEX ix_departments_name ON departments"))
            connection.execute(text("CREATE INDEX ix_departments_name ON departments (name)"))

        if any(
            index["Key_name"] == "ix_leave_type_options_name" and index["Non_unique"] == 0
            for index in leave_type_indexes
        ):
            connection.execute(text("DROP INDEX ix_leave_type_options_name ON leave_type_options"))
            connection.execute(
                text("CREATE INDEX ix_leave_type_options_name ON leave_type_options (name)")
            )


def ensure_leave_request_columns():
    inspector = inspect(engine)
    if not inspector.has_table("leave_requests"):
        return

    columns = {column["name"] for column in inspector.get_columns("leave_requests")}

    with engine.begin() as connection:
        if "updated_at" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE leave_requests "
                    "ADD COLUMN updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP "
                    "ON UPDATE CURRENT_TIMESTAMP"
                )
            )
        if "reviewed_at" not in columns:
            connection.execute(
                text("ALTER TABLE leave_requests ADD COLUMN reviewed_at DATETIME NULL")
            )
        if "admin_comment" not in columns:
            connection.execute(
                text("ALTER TABLE leave_requests ADD COLUMN admin_comment TEXT NULL")
            )


ensure_leave_request_columns()
default_company_id = ensure_default_company()
ensure_company_columns(default_company_id)
ensure_multitenant_indexes()


def seed_master_data():
    db = SessionLocal()
    try:
        if db.query(Department).filter(Department.company_id == default_company_id).count() == 0:
            default_departments = [
                "IT",
                "HR",
                "Finance",
                "Marketing",
                "Sales",
                "Operations",
            ]
            existing_employee_departments = {
                value[0]
                for value in db.execute(
                    text("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL")
                ).all()
                if value[0]
            }
            for department_name in sorted(set(default_departments) | existing_employee_departments):
                db.add(
                    Department(
                        company_id=default_company_id,
                        name=department_name,
                        is_active=True,
                    )
                )

        if (
            db.query(LeaveTypeOption)
            .filter(LeaveTypeOption.company_id == default_company_id)
            .count()
            == 0
        ):
            default_leave_types = [
                {
                    "name": "Casual",
                    "max_days_per_year": 12,
                    "carry_forward_enabled": True,
                    "max_carry_forward_days": 5,
                },
                {
                    "name": "Sick",
                    "max_days_per_year": 10,
                    "carry_forward_enabled": False,
                    "max_carry_forward_days": 0,
                },
                {
                    "name": "Annual",
                    "max_days_per_year": 18,
                    "carry_forward_enabled": True,
                    "max_carry_forward_days": 10,
                },
                {
                    "name": "Maternity",
                    "max_days_per_year": 90,
                    "carry_forward_enabled": False,
                    "max_carry_forward_days": 0,
                },
                {
                    "name": "Paternity",
                    "max_days_per_year": 15,
                    "carry_forward_enabled": False,
                    "max_carry_forward_days": 0,
                },
                {
                    "name": "Emergency",
                    "max_days_per_year": 5,
                    "carry_forward_enabled": False,
                    "max_carry_forward_days": 0,
                },
            ]
            for leave_type in default_leave_types:
                db.add(
                    LeaveTypeOption(
                        company_id=default_company_id,
                        **leave_type,
                        is_active=True,
                    )
                )

        db.commit()
    finally:
        db.close()


seed_master_data()

app = FastAPI(
    title="HRMS API",
    description="Human Resource Management System API",
    version="1.0.0"
)


@app.middleware("http")
async def resolve_company_middleware(request, call_next):
    tenant_slug = extract_tenant_slug(request)
    request.state.tenant_slug = tenant_slug
    request.state.company = None

    if tenant_slug:
        db = SessionLocal()
        try:
            company = get_company_by_slug(db, tenant_slug)
            if not company:
                return JSONResponse(
                    content={"detail": "Company workspace not found"},
                    status_code=404,
                )
            request.state.company = company
        finally:
            db.close()

    return await call_next(request)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # React dev servers
    allow_origin_regex=r"^http://([a-zA-Z0-9-]+)\.localhost:(5173|3000)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(company_routes.router)
app.include_router(employees_routes.router)
app.include_router(leave_requests_routes.router)  # Add leave requests router
app.include_router(attendance_routes.router)
app.include_router(leaves_routes.router)
app.include_router(payroll_routes.router)
app.include_router(options_routes.router)

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
