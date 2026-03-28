from datetime import timedelta
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from db.database import get_db
from models.company import Company
from models.user import User
from tenant_context import get_request_company
from schemas.user import UserCreate, UserLogin, User as UserSchema, Token
from auth.auth import (
    authenticate_user, create_access_token, get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def get_default_company(db: Session) -> Company:
    company = db.query(Company).filter(Company.slug == "default").first()
    if not company:
        company = Company(name="Default Company", slug="default", is_active=True)
        db.add(company)
        db.commit()
        db.refresh(company)
    return company


def normalize_company_slug(value: str) -> str:
    return value.strip().lower().replace(" ", "-")


def resolve_login_company(
    db: Session,
    company_slug: str | None,
) -> Company | None:
    if company_slug:
        company = (
            db.query(Company)
            .filter(Company.slug == normalize_company_slug(company_slug), Company.is_active.is_(True))
            .first()
        )
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company workspace not found",
            )
        return company

    return get_default_company(db)


async def parse_login_payload(request: Request) -> UserLogin:
    content_type = request.headers.get("content-type", "").lower()
    raw_payload = {}

    if "application/json" in content_type or content_type.startswith("text/plain"):
        raw_body = (await request.body()).decode("utf-8").strip()
        if raw_body:
            try:
                raw_payload = json.loads(raw_body)
            except json.JSONDecodeError:
                raw_payload = {}

    if not raw_payload:
        raw_payload = dict(await request.form())

    username = (raw_payload.get("username") or "").strip()
    password = raw_payload.get("password") or ""
    company_slug = (
        (raw_payload.get("company_slug") or "").strip()
        or request.headers.get("x-tenant-slug", "").strip()
        or None
    )

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )

    return UserLogin(
        username=username,
        password=password,
        company_slug=company_slug,
    )

@router.post("/register", response_model=UserSchema)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_company: Company | None = Depends(get_request_company),
):
    company_id = user.company_id or (current_company.id if current_company else get_default_company(db).id)

    db_user = (
        db.query(User)
        .filter(User.email == user.email, User.company_id == company_id)
        .first()
    )
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    db_user = (
        db.query(User)
        .filter(User.username == user.username, User.company_id == company_id)
        .first()
    )
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )
    
    hashed_password = get_password_hash(user.password)

    db_user = User(
        company_id=company_id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await parse_login_payload(request)
    company = resolve_login_company(db, payload.company_slug)

    user = authenticate_user(db, payload.username, payload.password, company.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "company_id": user.company_id},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "company_id": user.company_id,
        "tenant_slug": company.slug,
        "role": user.role,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
    }
