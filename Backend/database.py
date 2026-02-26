from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.core.config import settings


def _build_engine_args_impl(database_url: str):
    engine_args = {}
    if database_url.startswith("sqlite"):
        engine_args["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            engine_args["poolclass"] = StaticPool
    return engine_args


class _DatabaseWorkflow:
    def build_engine_args(self, database_url: str):
        return _build_engine_args_impl(database_url=database_url)

    def get_db(self):
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()


_database_workflow = _DatabaseWorkflow()
engine_args = _database_workflow.build_engine_args(settings.DATABASE_URL)
engine = create_engine(settings.DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    yield from _database_workflow.get_db()


class DatabaseLegacyService:
    def get_db(self, *args, **kwargs):
        yield from get_db(*args, **kwargs)


database_legacy_service = DatabaseLegacyService()
