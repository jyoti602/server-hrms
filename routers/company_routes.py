from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth.auth import get_password_hash
from db.database import get_db
from models.company import Company
from models.department import Department
from models.leave_type_option import LeaveTypeOption
from models.tenant_database import TenantDatabase
from models.user import User, UserRole
from tenant_context import get_request_company
from services.tenant_provisioning import provision_tenant_database
from schemas.company import Company as CompanySchema, CompanyRegistrationRequest, CompanyRegistrationResponse

router = APIRouter(prefix="/companies", tags=["companies"])


def normalize_slug(value: str) -> str:
    return value.strip().lower().replace(" ", "-")


def get_current_request_company(
    request: Request,
    db: Session = Depends(get_db),
):
    return get_request_company(request, db=db, required=True)


@router.get("/current", response_model=CompanySchema)
def get_current_company(
    company: Company = Depends(get_current_request_company),
):
    return company


@router.post("/register", response_model=CompanyRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_company(
    payload: CompanyRegistrationRequest,
    db: Session = Depends(get_db),
):
    company_name = payload.company_name.strip()
    normalized_slug = normalize_slug(payload.company_slug)
    company_email = payload.company_email.strip()
    admin_email = payload.admin_email.strip()
    admin_username = payload.admin_username.strip()
    admin_full_name = payload.admin_full_name.strip()

    existing_company = db.query(Company).filter(Company.slug == normalized_slug).first()
    if existing_company:
        raise HTTPException(status_code=400, detail="Company slug already exists")

    existing_company_by_name = db.query(Company).filter(Company.name == company_name).first()
    if existing_company_by_name:
        raise HTTPException(status_code=400, detail="Company name already exists")

    company = Company(
        name=company_name,
        slug=normalized_slug,
        email=company_email,
        phone=payload.company_phone.strip() if payload.company_phone else None,
        is_active=True,
    )
    db.add(company)
    try:
        db.flush()

        if db.query(TenantDatabase).filter(TenantDatabase.company_id == company.id).first():
            raise HTTPException(
                status_code=400,
                detail="Tenant database already exists for this company",
            )

        hashed_password = get_password_hash(payload.password)
        tenant_database = provision_tenant_database(
            company_slug=normalized_slug,
            admin_email=admin_email,
            admin_username=admin_username,
            admin_full_name=admin_full_name,
            hashed_password=hashed_password,
        )

        db.add(
            TenantDatabase(
                company_id=company.id,
                db_name=tenant_database["db_name"],
                db_host=tenant_database["db_host"],
                db_port=tenant_database["db_port"],
                db_user=tenant_database["db_user"],
                is_active=True,
            )
        )

        admin_user = User(
            company_id=company.id,
            email=admin_email,
            username=admin_username,
            full_name=admin_full_name,
            role=UserRole.ADMIN,
            hashed_password=hashed_password,
            is_active=True,
        )
        db.add(admin_user)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Company name or slug already exists")

    return {
        "company_id": company.id,
        "company_name": company.name,
        "company_slug": company.slug,
        "tenant_db_name": tenant_database["db_name"],
        "admin_username": admin_user.username,
        "message": "Company workspace created successfully",
    }
