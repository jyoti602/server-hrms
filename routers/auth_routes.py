from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from db.database import get_db
from models.company import Company
from models.user import User
from tenant_context import get_request_company
from schemas.user import UserCreate, User as UserSchema, Token
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
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db),
    current_company: Company | None = Depends(get_request_company),
):
    company = current_company
    if company is None and request is not None and request.headers.get("host", "").split(":")[0] in {"localhost", "127.0.0.1"}:
        company = get_default_company(db)

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context is required. Use the company domain or send X-Tenant-Slug.",
        )

    user = authenticate_user(db, form_data.username, form_data.password, company.id)
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
