import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.database import Base
import Backend.crud as crud
import Backend.schemas as schemas

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture()
def db_session():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create default role and plan needed for user creation
    crud.create_role(db, schemas.RoleCreate(name="user", description="User role"))
    crud.create_plano(
        db,
        schemas.PlanoCreate(
            nome="Gratuito",
            descricao="Plano básico gratuito",
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
