"""Database engine/session helpers. Production must use PostgreSQL."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


def make_engine(database_url=None):
    url = database_url or os.environ.get("FRAUDSHIELD_DATABASE_URL")
    if not url:
        raise RuntimeError("FRAUDSHIELD_DATABASE_URL must be configured.")
    return create_engine(url, pool_pre_ping=True, future=True)


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_schema(engine):
    """Development/test bootstrap only; production schema changes use migrations."""
    Base.metadata.create_all(engine)
