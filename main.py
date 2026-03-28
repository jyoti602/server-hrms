from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from db.database import SessionLocal, engine, get_db
from models.company import Company
from models.department import Department
from models.user import User
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
Company.__table__.create(bind=engine, checkfirst=True)
TenantDatabase.__table__.create(bind=engine, checkfirst=True)
Department.__table__.create(bind=engine, checkfirst=True)
User.__table__.create(bind=engine, checkfirst=True)


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


def ensure_company_base_columns():
    with engine.begin() as connection:
        inspector = inspect(engine)
        if not inspector.has_table("companies"):
            return

        columns = {column["name"] for column in inspector.get_columns("companies")}
        if "address" not in columns:
            connection.execute(text("ALTER TABLE companies ADD COLUMN address VARCHAR(255) NULL"))


def ensure_company_columns(default_company_id: int):
    company_tables = [
        "users",
        "employees",
        "departments",
        "attendance",
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
        inspector = inspect(engine)

        if inspector.has_table("users"):
            user_indexes = connection.execute(text("SHOW INDEX FROM users")).mappings().all()
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

        if inspector.has_table("employees"):
            employee_indexes = connection.execute(text("SHOW INDEX FROM employees")).mappings().all()
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

        if inspector.has_table("departments"):
            department_indexes = connection.execute(text("SHOW INDEX FROM departments")).mappings().all()
            if any(
                index["Key_name"] == "ix_departments_name" and index["Non_unique"] == 0
                for index in department_indexes
            ):
                connection.execute(text("DROP INDEX ix_departments_name ON departments"))
                connection.execute(text("CREATE INDEX ix_departments_name ON departments (name)"))
default_company_id = ensure_default_company()
ensure_company_base_columns()
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
            for department_name in default_departments:
                db.add(
                    Department(
                        company_id=default_company_id,
                        name=department_name,
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
