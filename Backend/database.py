from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Optional

from Backend.core.config import settings

class _DatabaseWorkflow:
    def __init__(self, runtime: Optional["_DatabaseRuntime"] = None) -> None:
        self._runtime = runtime or _DatabaseRuntime()

    def build_engine_args(self, database_url: str):
        return self._runtime.build_engine_args(database_url=database_url)

    def get_db(self):
        yield from self._runtime.get_db()


class _DatabaseRuntime:
    def build_engine_args(self, database_url: str):
        engine_args = {}
        if database_url.startswith("sqlite"):
            engine_args["connect_args"] = {"check_same_thread": False}
            if ":memory:" in database_url:
                engine_args["poolclass"] = StaticPool
        return engine_args

    def get_db(self):
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

DatabaseWorkflow = _DatabaseWorkflow


def get_database_workflow() -> DatabaseWorkflow:
    return DatabaseWorkflow()


engine_args = get_database_workflow().build_engine_args(settings.DATABASE_URL)
engine = create_engine(settings.DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    yield from get_database_workflow().get_db()




