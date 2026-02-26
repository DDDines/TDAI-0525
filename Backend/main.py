# Backend/main.py
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend import crud_fornecedores
from Backend import crud_product_types
from Backend import crud_produtos
from Backend import crud_users
from Backend import models
from Backend import schemas
from Backend.auth import router as auth_router_direct
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend.database import SessionLocal, engine, get_db

from Backend.routers.admin_analytics import router as admin_analytics_router
from Backend.routers.fornecedores import router as fornecedores_router
from Backend.routers.generation import router as generation_router
from Backend.routers.historico import router as historico_router
from Backend.routers.password_recovery import router as password_recovery_router
from Backend.routers.product_types import router as product_types_router
from Backend.routers.produtos import router as produtos_router
from Backend.routers.search import router as search_router
from Backend.routers.social_auth import router as social_auth_router
from Backend.routers.uso_ia import router as uso_ia_router
from Backend.routers.web_enrichment import router as web_enrichment_router

logger = get_logger(__name__)
logger.info(
    "Inicializando aplicacao. Certifique-se de rodar 'alembic upgrade head' antes de usar."
)


def _build_allowed_origins_impl() -> List[str]:
    exact_frontend_origin = "http://localhost:5173"
    default_cors_origins_list = [
        exact_frontend_origin,
        "http://127.0.0.1:5173",
        f"{exact_frontend_origin}/",
        "http://127.0.0.1:5173/",
        "http://localhost",
        "http://127.0.0.1",
    ]

    current_allowed_origins: List[str] = []
    try:
        if hasattr(settings, "BACKEND_CORS_ORIGINS") and settings.BACKEND_CORS_ORIGINS:
            normalized_env_origins = set()
            for origin_obj in settings.BACKEND_CORS_ORIGINS:
                origin_str = str(origin_obj)
                normalized_env_origins.add(origin_str.rstrip("/"))
                normalized_env_origins.add(origin_str)

            if not normalized_env_origins:
                current_allowed_origins = list(default_cors_origins_list)
            else:
                current_allowed_origins = sorted(list(normalized_env_origins))
                for default_origin in default_cors_origins_list:
                    if default_origin not in current_allowed_origins:
                        current_allowed_origins.append(default_origin)
                current_allowed_origins = sorted(list(set(current_allowed_origins)))
        else:
            current_allowed_origins = list(default_cors_origins_list)
    except Exception:
        current_allowed_origins = list(default_cors_origins_list)

    if exact_frontend_origin not in current_allowed_origins:
        current_allowed_origins.insert(0, exact_frontend_origin)

    return sorted(list(set(current_allowed_origins)))


def _ensure_static_files_path_impl() -> Path:
    static_files_path = Path(__file__).parent / "static"
    if not static_files_path.exists():
        static_files_path.mkdir(parents=True, exist_ok=True)
    return static_files_path


async def _startup_event_create_defaults_impl() -> None:
    logger.info("Executando evento de startup para criar defaults (roles, planos, admin user, product types)...")
    db: Session = SessionLocal()

    if settings.AUTO_CREATE_TABLES:
        try:
            logger.info("AUTO_CREATE_TABLES habilitado - criando/verificando tabelas via SQLAlchemy...")
            models.Base.metadata.create_all(bind=engine)
            logger.info("Criacao/verificacao de tabelas concluida.")
        except Exception as exc:
            logger.error("Falha ao criar/verificar tabelas automaticamente: %s", exc)

    try:
        roles_a_criar = [
            {"name": "admin", "description": "Administrador do sistema com acesso total."},
            {"name": "user", "description": "Usuario padrao com acesso as funcionalidades do seu plano."},
        ]
        admin_role_obj = None
        user_role_obj = None

        for role_data in roles_a_criar:
            role = crud_users.get_role_by_name(db, name=role_data["name"])
            if not role:
                role = crud_users.create_role(db, role=schemas.RoleCreate(**role_data))
                logger.info("Role '%s' criada.", role.name)
            if role.name == "admin":
                admin_role_obj = role
            elif role.name == "user":
                user_role_obj = role

        if not admin_role_obj:
            logger.error("ERRO CRITICO: Role 'admin' nao pode ser encontrada ou criada.")
        if not user_role_obj:
            logger.error("ERRO CRITICO: Role 'user' nao pode ser encontrada ou criada.")

        plano_gratuito_data = schemas.PlanoCreate(
            nome="Gratuito",
            descricao="Plano basico gratuito com limitacoes.",
            preco_mensal=0.0,
            limite_produtos=settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO,
            limite_enriquecimento_web=settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO,
            limite_geracao_ia=settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO,
            permite_api_externa=False,
            suporte_prioritario=False,
        )
        plano_pro_data = schemas.PlanoCreate(
            nome="Pro",
            descricao="Plano profissional com mais limites e funcionalidades.",
            preco_mensal=49.90,
            limite_produtos=1000,
            limite_enriquecimento_web=500,
            limite_geracao_ia=2000,
            permite_api_externa=True,
            suporte_prioritario=True,
        )

        planos_a_criar = [plano_gratuito_data, plano_pro_data]
        admin_plano_obj = None
        plano_gratuito_obj = None

        for plano_data in planos_a_criar:
            plano = crud_users.get_plano_by_name(db, nome=plano_data.nome)
            if not plano:
                plano = crud_users.create_plano(db, plano=plano_data)
                logger.info("Plano '%s' criado.", plano.nome)
            if plano.nome == "Pro":
                admin_plano_obj = plano
            if plano.nome == "Gratuito":
                plano_gratuito_obj = plano

        if not admin_plano_obj:
            logger.warning(
                "AVISO: Plano 'Pro' nao encontrado para admin. Sera associado ao plano 'Gratuito' se disponivel."
            )
            admin_plano_obj = plano_gratuito_obj

        if not plano_gratuito_obj:
            logger.error(
                "ERRO CRITICO: Plano 'Gratuito' nao encontrado. Novos usuarios podem ficar sem plano padrao."
            )

        admin_user = crud_users.get_user_by_email(db, email=settings.ADMIN_EMAIL)
        if not admin_user:
            if not admin_role_obj:
                logger.error(
                    "ERRO: nao foi possivel criar admin '%s' porque role 'admin' nao existe.",
                    settings.ADMIN_EMAIL,
                )
            else:
                user_in_data = {
                    "email": settings.ADMIN_EMAIL,
                    "password": settings.ADMIN_PASSWORD,
                    "nome_completo": "Administrador CatalogAI",
                    "plano_id": admin_plano_obj.id if admin_plano_obj else None,
                }
                if hasattr(settings, "ADMIN_IDIOMA_PREFERIDO"):
                    user_in_data["idioma_preferido"] = settings.ADMIN_IDIOMA_PREFERIDO

                user_in_create = schemas.UserCreate(**user_in_data)
                created_admin = crud_users.create_user(db=db, user=user_in_create)
                if created_admin:
                    created_admin.is_superuser = True
                    if admin_role_obj:
                        created_admin.role_id = admin_role_obj.id

                    if admin_plano_obj and not created_admin.plano_id:
                        created_admin.plano_id = admin_plano_obj.id
                        created_admin.limite_produtos = admin_plano_obj.limite_produtos
                        created_admin.limite_enriquecimento_web = admin_plano_obj.limite_enriquecimento_web
                        created_admin.limite_geracao_ia = admin_plano_obj.limite_geracao_ia

                    db.add(created_admin)
                    db.commit()
                    db.refresh(created_admin)
                    admin_user = created_admin
                    logger.info("Usuario administrador '%s' criado com sucesso.", settings.ADMIN_EMAIL)
                else:
                    logger.error("ERRO: falha ao criar o usuario admin '%s'.", settings.ADMIN_EMAIL)
        else:
            logger.info("Usuario administrador '%s' ja existe.", settings.ADMIN_EMAIL)
            needs_update = False

            if admin_role_obj and admin_user.role_id != admin_role_obj.id:
                admin_user.role_id = admin_role_obj.id
                needs_update = True
                logger.info("Atualizando role do admin '%s'.", settings.ADMIN_EMAIL)

            if not admin_user.is_superuser:
                admin_user.is_superuser = True
                needs_update = True
                logger.info("Atualizando admin '%s' para superuser.", settings.ADMIN_EMAIL)

            admin_plano_obj = crud_users.get_plano_by_name(db, "Pro")
            if admin_plano_obj and admin_user.plano_id != admin_plano_obj.id:
                admin_user.plano_id = admin_plano_obj.id
                needs_update = True
                logger.info("Atualizando plano do admin '%s'.", settings.ADMIN_EMAIL)

            if needs_update:
                db.commit()
                db.refresh(admin_user)

        product_types_data = [
            {
                "key_name": "eletronicos",
                "friendly_name": "Eletronicos",
                "description": "Tipo padrao para produtos eletronicos.",
                "attribute_templates": [
                    {
                        "attribute_key": "marca",
                        "label": "Marca",
                        "field_type": models.AttributeFieldTypeEnum.TEXT,
                        "is_required": True,
                        "display_order": 0,
                        "description": "Marca do produto eletronico",
                    },
                    {
                        "attribute_key": "voltagem",
                        "label": "Voltagem",
                        "field_type": models.AttributeFieldTypeEnum.SELECT,
                        "options": '["110v", "220v", "Bivolt"]',
                        "is_required": True,
                        "display_order": 1,
                        "description": "Selecione a voltagem",
                    },
                    {
                        "attribute_key": "cor_principal",
                        "label": "Cor Principal",
                        "field_type": models.AttributeFieldTypeEnum.TEXT,
                        "is_required": False,
                        "display_order": 2,
                        "description": "Cor predominante do produto",
                    },
                ],
            },
            {
                "key_name": "vestuario",
                "friendly_name": "Vestuario",
                "description": "Tipo padrao para pecas de vestuario.",
                "attribute_templates": [
                    {
                        "attribute_key": "tamanho",
                        "label": "Tamanho",
                        "field_type": models.AttributeFieldTypeEnum.SELECT,
                        "options": '["P", "M", "G", "GG", "XG"]',
                        "is_required": True,
                        "display_order": 1,
                        "description": "Selecione o tamanho da peca",
                    },
                    {
                        "attribute_key": "cor",
                        "label": "Cor",
                        "field_type": models.AttributeFieldTypeEnum.TEXT,
                        "is_required": True,
                        "display_order": 2,
                        "description": "Cor da peca de vestuario",
                    },
                    {
                        "attribute_key": "material",
                        "label": "Material Principal",
                        "field_type": models.AttributeFieldTypeEnum.TEXT,
                        "is_required": False,
                        "display_order": 3,
                        "description": "Material principal da confeccao",
                    },
                ],
            },
        ]

        for pt_data in product_types_data:
            product_type_in_db = crud_product_types.get_product_type_by_key_name(
                db,
                key_name=pt_data["key_name"],
                user_id=None,
            )
            if not product_type_in_db:
                product_type_create_schema = schemas.ProductTypeCreate(**pt_data)
                crud_product_types.create_product_type(
                    db=db,
                    product_type_create=product_type_create_schema,
                    user_id=None,
                )
                logger.info("Tipo de Produto Global '%s' criado.", product_type_create_schema.friendly_name)
            else:
                logger.info("Tipo de Produto Global '%s' ja existe.", pt_data["friendly_name"])

        if admin_user:
            fornecedor_existente = (
                db.query(models.Fornecedor)
                .filter(
                    func.lower(models.Fornecedor.nome) == "uouu",
                    models.Fornecedor.user_id == admin_user.id,
                )
                .first()
            )
            if not fornecedor_existente:
                fornecedor_schema = schemas.FornecedorCreate(
                    nome="UouU",
                    site_url="www.uouu.com.br",
                )
                crud_fornecedores.create_fornecedor(
                    db=db,
                    fornecedor=fornecedor_schema,
                    user_id=admin_user.id,
                )
                logger.info("Fornecedor de exemplo 'UouU' criado para o administrador.")
            else:
                logger.info("Fornecedor de exemplo 'UouU' ja existe para o administrador.")

        if admin_user and db.query(models.Produto).count() == 0:
            exemplo_produto = schemas.ProdutoCreate(
                nome_base="Produto de Exemplo",
                descricao_original="Item criado automaticamente na inicializacao",
            )
            crud_produtos.create_produto(db=db, produto=exemplo_produto, user_id=admin_user.id)
            logger.info("Produto de exemplo criado para o administrador.")

    except Exception as startup_exc:
        logger.error("ERRO CRITICO durante o evento de startup: %s", startup_exc, exc_info=True)
    finally:
        db.close()

    logger.info("Evento de startup para defaults concluido.")


def _create_new_user_impl(user_in: schemas.UserCreate, db: Session) -> models.User:
    db_user_check = crud_users.get_user_by_email(db, email=user_in.email)
    if db_user_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuario com este email ja existe no sistema.",
        )

    plano_id_para_novo_usuario = user_in.plano_id
    plano_gratuito_obj_check = crud_users.get_plano_by_name(db, nome="Gratuito")

    if plano_id_para_novo_usuario is None:
        if plano_gratuito_obj_check:
            plano_id_para_novo_usuario = plano_gratuito_obj_check.id
        else:
            logger.error("ERRO CRITICO: Plano padrao 'Gratuito' nao encontrado no banco.")
            plano_id_para_novo_usuario = None

    role_user_check = crud_users.get_role_by_name(db, name="user")
    if not role_user_check:
        logger.error("ERRO CRITICO: Role padrao 'user' nao encontrado.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro de configuracao do sistema: Role padrao 'user' nao encontrado.",
        )

    user_in.role_id = role_user_check.id
    user_in.plano_id = plano_id_para_novo_usuario
    return crud_users.create_user(db=db, user=user_in)


class _MainBootstrapWorkflow:
    def build_allowed_origins(self) -> List[str]:
        return _build_allowed_origins_impl()

    def ensure_static_files_path(self) -> Path:
        return _ensure_static_files_path_impl()

    async def startup_event_create_defaults(self) -> None:
        await _startup_event_create_defaults_impl()

    def create_new_user(self, user_in: schemas.UserCreate, db: Session) -> models.User:
        return _create_new_user_impl(user_in=user_in, db=db)


main_bootstrap_workflow = _MainBootstrapWorkflow()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await main_bootstrap_workflow.startup_event_create_defaults()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="API para o sistema CatalogAI - Ferramenta de Descricao Assistida por IA.",
    lifespan=lifespan,
)


final_unique_allowed_origins = main_bootstrap_workflow.build_allowed_origins()
logger.info("Final unique allowed_origins para CORSMiddleware: %s", final_unique_allowed_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=final_unique_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


static_files_path = main_bootstrap_workflow.ensure_static_files_path()
app.mount("/static", StaticFiles(directory=static_files_path), name="static")


async def startup_event_create_defaults() -> None:
    await main_bootstrap_workflow.startup_event_create_defaults()


@app.post(
    "/api/v1/users/",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Usuarios"],
)
def create_new_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    return main_bootstrap_workflow.create_new_user(user_in=user_in, db=db)


app.include_router(auth_router_direct, prefix=settings.API_V1_STR + "/auth", tags=["Autenticacao e Usuarios"])
app.include_router(social_auth_router, prefix=settings.API_V1_STR + "/auth", tags=["Autenticacao Social"])
app.include_router(produtos_router, prefix=settings.API_V1_STR, tags=["Produtos"])
app.include_router(fornecedores_router, prefix=settings.API_V1_STR, tags=["Fornecedores"])
app.include_router(generation_router, prefix=settings.API_V1_STR, tags=["Geracao de Conteudo IA"])
app.include_router(web_enrichment_router, prefix=settings.API_V1_STR, tags=["Enriquecimento Web"])
app.include_router(product_types_router, prefix=settings.API_V1_STR, tags=["Tipos de Produto e Templates"])
app.include_router(search_router, prefix=settings.API_V1_STR, tags=["Busca"])
app.include_router(uso_ia_router, prefix=settings.API_V1_STR, tags=["Registro de Uso de IA"])
app.include_router(historico_router, prefix=settings.API_V1_STR, tags=["Historico"])
app.include_router(password_recovery_router, prefix=settings.API_V1_STR, tags=["Recuperacao de Senha"])
app.include_router(admin_analytics_router, prefix=settings.API_V1_STR + "/admin/analytics", tags=["Analytics (Admin)"])


@app.get("/", tags=["Raiz"])
async def root():
    return {"message": f"Bem-vindo a API do {settings.PROJECT_NAME}!"}


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
async def health_check():
    return {"status": "ok"}


class MainLegacyService:
    async def startup_event_create_defaults(self) -> None:
        await startup_event_create_defaults()

    def create_new_user(self, *args, **kwargs):
        return create_new_user(*args, **kwargs)


main_legacy_service = MainLegacyService()
