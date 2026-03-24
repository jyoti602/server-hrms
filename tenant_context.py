from collections.abc import Generator
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from db.database import get_db
from db.tenant import get_tenant_session_factory
from models.company import Company
from models.tenant_database import TenantDatabase


def extract_tenant_slug(request: Request) -> Optional[str]:
    header_slug = request.headers.get("x-tenant-slug", "").strip().lower()
    if header_slug:
        return header_slug

    host = request.headers.get("host", "").split(":")[0].strip().lower()
    if not host or host in {"localhost", "127.0.0.1"}:
        return None

    if host.endswith(".localhost"):
        return host[: -len(".localhost")] or None

    parts = host.split(".")
    if len(parts) >= 3:
        return parts[0]

    return None


def get_company_by_slug(db: Session, slug: str) -> Optional[Company]:
    return db.query(Company).filter(Company.slug == slug, Company.is_active.is_(True)).first()


def get_tenant_database_for_company(db: Session, company_id: int) -> Optional[TenantDatabase]:
    return (
        db.query(TenantDatabase)
        .filter(TenantDatabase.company_id == company_id, TenantDatabase.is_active.is_(True))
        .first()
    )


def get_request_company(
    request: Request,
    db: Session = Depends(get_db),
    required: bool = False,
) -> Optional[Company]:
    company = getattr(request.state, "company", None)
    if company:
        return company

    tenant_slug = extract_tenant_slug(request)
    if tenant_slug:
        company = get_company_by_slug(db, tenant_slug)
        if company:
            request.state.company = company
            return company

    if required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context is required for this request",
        )
    return None


def get_tenant_db_session(company_id: int, db: Session) -> Generator[Session, None, None]:
    tenant_database = get_tenant_database_for_company(db, company_id)
    if not tenant_database:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tenant database is not configured for this company",
        )

    session_factory = get_tenant_session_factory(tenant_database.db_name)
    tenant_db = session_factory()
    try:
        yield tenant_db
    finally:
        tenant_db.close()
