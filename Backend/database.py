# catalogai_project/Backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# CORREÇÃO: 'core' é uma subpasta de 'Backend/' (onde este arquivo database.py está,
# e que será o CWD quando rodarmos via run_backend.py).
# Então, importamos diretamente de 'core.config'.
from Backend.core.config import settings #

engine_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
