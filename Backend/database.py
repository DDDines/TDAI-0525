"""Module database.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.core.config import settings


engine_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.DATABASE_URL:
        engine_args["poolclass"] = StaticPool

engine = create_engine(settings.DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Execute get_db.

    This callable is documented to make behavior explicit for readers.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
