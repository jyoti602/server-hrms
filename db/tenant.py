import os
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

TENANT_DB_HOST = os.getenv("TENANT_DB_HOST", os.getenv("DB_HOST", "localhost"))
TENANT_DB_PORT = os.getenv("TENANT_DB_PORT", os.getenv("DB_PORT", "3306"))
TENANT_DB_USER = os.getenv("TENANT_DB_USER", os.getenv("DB_USER", "root"))
TENANT_DB_PASSWORD = os.getenv("TENANT_DB_PASSWORD", os.getenv("DB_PASSWORD", "password"))
TENANT_DB_PREFIX = os.getenv("TENANT_DB_PREFIX", "tenant_db")
TENANT_SERVER_DATABASE = os.getenv("TENANT_SERVER_DATABASE", "information_schema")

TenantBase = declarative_base()


def build_tenant_db_name(company_slug: str) -> str:
    safe_slug = company_slug.strip().lower().replace("-", "_")
    return f"{TENANT_DB_PREFIX}_{safe_slug}"


def build_tenant_database_url(database_name: str) -> str:
    password = quote_plus(TENANT_DB_PASSWORD)
    return (
        f"mysql+pymysql://{TENANT_DB_USER}:{password}"
        f"@{TENANT_DB_HOST}:{TENANT_DB_PORT}/{database_name}"
    )


def build_server_database_url() -> str:
    password = quote_plus(TENANT_DB_PASSWORD)
    return (
        f"mysql+pymysql://{TENANT_DB_USER}:{password}"
        f"@{TENANT_DB_HOST}:{TENANT_DB_PORT}/"
    )


def get_server_engine():
    return create_engine(build_server_database_url())


def ensure_tenant_database(database_name: str):
    server_engine = get_server_engine()
    with server_engine.begin() as connection:
        connection.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database_name}`"))


@lru_cache(maxsize=64)
def get_tenant_engine(database_name: str):
    return create_engine(build_tenant_database_url(database_name))


@lru_cache(maxsize=64)
def get_tenant_session_factory(database_name: str):
    return sessionmaker(autocommit=False, autoflush=False, bind=get_tenant_engine(database_name))
