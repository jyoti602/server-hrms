from datetime import datetime, timedelta
from typing import Optional
import os

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db.database import get_db
from db.tenant import get_tenant_session_factory
from models.tenant_database import TenantDatabase
from models.user import User, UserRole
from schemas.user import TokenData
from tenant_models.user import User as TenantUser

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )

def get_password_hash(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

def get_user(db: Session, username: str, company_id: int | None = None):
    if company_id is not None:
        tenant_database = (
            db.query(TenantDatabase)
            .filter(TenantDatabase.company_id == company_id, TenantDatabase.is_active.is_(True))
            .first()
        )
        if tenant_database:
            tenant_session = get_tenant_session_factory(tenant_database.db_name)()
            try:
                tenant_user = tenant_session.query(TenantUser).filter(TenantUser.username == username).first()
                if tenant_user:
                    setattr(tenant_user, "company_id", company_id)
                    return tenant_user
            finally:
                tenant_session.close()

    query = db.query(User).filter(User.username == username)
    if company_id is not None:
        query = query.filter(User.company_id == company_id)
    return query.first()

def authenticate_user(db: Session, username: str, password: str, company_id: int | None = None):
    user = get_user(db, username, company_id)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        company_id: int | None = payload.get("company_id")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, company_id=company_id)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username, company_id=token_data.company_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_role(required_role: UserRole):
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker
