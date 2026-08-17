"""
Database engine and session setup.

One table doesn't justify Alembic or a repository layer on top of the
ORM - the service layer just talks to SQLAlchemy models directly.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist yet. Called once on app startup."""
    from app import models  # noqa: F401 (ensures models are registered)

    Base.metadata.create_all(bind=engine)
