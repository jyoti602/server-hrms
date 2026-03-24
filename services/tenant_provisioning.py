from db.tenant import (
    TENANT_DB_HOST,
    TENANT_DB_PORT,
    TENANT_DB_USER,
    TenantBase,
    build_tenant_db_name,
    ensure_tenant_database,
    get_tenant_engine,
    get_tenant_session_factory,
)
from tenant_models.department import Department
from tenant_models.leave_type_option import LeaveTypeOption
from tenant_models.user import User, UserRole


DEFAULT_DEPARTMENTS = [
    "IT",
    "HR",
    "Finance",
    "Marketing",
    "Sales",
    "Operations",
]

DEFAULT_LEAVE_TYPES = [
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


def provision_tenant_database(
    company_slug: str,
    admin_email: str,
    admin_username: str,
    admin_full_name: str,
    hashed_password: str,
):
    database_name = build_tenant_db_name(company_slug)
    ensure_tenant_database(database_name)

    tenant_engine = get_tenant_engine(database_name)
    TenantBase.metadata.create_all(bind=tenant_engine)

    session_factory = get_tenant_session_factory(database_name)
    db = session_factory()
    try:
        if not db.query(User).filter(User.username == admin_username).first():
            db.add(
                User(
                    email=admin_email,
                    username=admin_username,
                    full_name=admin_full_name,
                    role=UserRole.ADMIN,
                    hashed_password=hashed_password,
                    is_active=True,
                )
            )

        if db.query(Department).count() == 0:
            for department_name in DEFAULT_DEPARTMENTS:
                db.add(Department(name=department_name, is_active=True))

        if db.query(LeaveTypeOption).count() == 0:
            for leave_type in DEFAULT_LEAVE_TYPES:
                db.add(LeaveTypeOption(**leave_type, is_active=True))

        db.commit()
    finally:
        db.close()

    return {
        "db_name": database_name,
        "db_host": TENANT_DB_HOST,
        "db_port": TENANT_DB_PORT,
        "db_user": TENANT_DB_USER,
    }
