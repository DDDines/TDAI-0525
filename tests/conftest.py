import os

import pytest

# Garantir DB de testes antes de carregar app/database.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from Backend.main import app
from Backend.database import get_db
from Backend.infrastructure.repositories.user_repository import UserRepository

os.environ.setdefault("FIRST_SUPERUSER_EMAIL", "admin@example.com")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "password")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "password")

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def _bind_get_db_override_per_module(request):
    """
    Evita vazamento de dependency override entre modulos de teste.

    Varios testes definem `override_get_db` no escopo de modulo; como todos usam o
    mesmo `Backend.main.app`, o ultimo override importado sobrescreve os demais.
    Este fixture reaplica o override do modulo atual antes de cada teste.
    """
    module_override = getattr(request.module, "override_get_db", None)
    previous_override = app.dependency_overrides.get(get_db)

    if module_override is not None:
        app.dependency_overrides[get_db] = module_override
    else:
        app.dependency_overrides.pop(get_db, None)

    try:
        yield
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_db] = previous_override
        else:
            app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def db_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from Backend.database import Base
    import Backend.schemas as schemas

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create default role and plan needed for user creation.
    user_repo = UserRepository(db)
    user_repo.create_role(role=schemas.RoleCreate(name="user", description="User role"))
    user_repo.create_plano(
        plano=schemas.PlanoCreate(
            nome="Gratuito",
            descricao="Plano basico gratuito",
            preco_mensal=0.0,
            limite_produtos=50,
            limite_enriquecimento_web=10,
            limite_geracao_ia=20,
            permite_api_externa=False,
            suporte_prioritario=False,
        ),
    )

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)
