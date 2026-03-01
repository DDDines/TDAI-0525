from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.core.config import settings


class DatabaseSessionRuntime:
    """Encapsula configuracao de engine e ciclo de vida de sessoes."""

    @staticmethod
    def build_engine_args(database_url: str) -> dict:
        engine_args: dict = {}
        if database_url.startswith("sqlite"):
            engine_args["connect_args"] = {"check_same_thread": False}
            if ":memory:" in database_url:
                engine_args["poolclass"] = StaticPool
        return engine_args

    @staticmethod
    def session_scope(session_factory):
        db = session_factory()
        try:
            yield db
        finally:
            db.close()


engine_args = DatabaseSessionRuntime.build_engine_args(settings.DATABASE_URL)
engine = create_engine(settings.DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    yield from DatabaseSessionRuntime.session_scope(SessionLocal)
