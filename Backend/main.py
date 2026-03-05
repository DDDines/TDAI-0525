"""Bootstrap principal da API e composicao da aplicacao em modo OOP."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional, Tuple
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session
from Backend import models
from Backend import schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.auth import router as auth_router_direct
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend.database import SessionLocal, engine
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository
from Backend.infrastructure.repositories.user_repository import UserRepository
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
logger.info("Inicializando aplicacao. Certifique-se de rodar 'alembic upgrade head' antes de usar.")

class MainBootstrapRuntime:
    """Runtime OO responsavel por bootstrap da aplicacao e defaults de dominio."""

    def build_allowed_origins(self) -> List[str]:
        """Build the allowed CORS origins combining env configuration and safe defaults."""
        exact_frontend_origin = 'http://localhost:5173'
        default_cors_origins_list = [exact_frontend_origin, 'http://127.0.0.1:5173', f'{exact_frontend_origin}/', 'http://127.0.0.1:5173/', 'http://localhost', 'http://127.0.0.1']
        allowed_origins: List[str] = []
        try:
            env_origins = getattr(settings, 'BACKEND_CORS_ORIGINS', None)
            if env_origins:
                normalized_env_origins = set()
                for origin_obj in env_origins:
                    origin_str = str(origin_obj)
                    normalized_env_origins.add(origin_str.rstrip('/'))
                    normalized_env_origins.add(origin_str)
                if normalized_env_origins:
                    allowed_origins = sorted(normalized_env_origins)
                    for default_origin in default_cors_origins_list:
                        if default_origin not in allowed_origins:
                            allowed_origins.append(default_origin)
                    allowed_origins = sorted(set(allowed_origins))
                else:
                    allowed_origins = list(default_cors_origins_list)
            else:
                allowed_origins = list(default_cors_origins_list)
        except Exception:
            allowed_origins = list(default_cors_origins_list)
        if exact_frontend_origin not in allowed_origins:
            allowed_origins.insert(0, exact_frontend_origin)
        return sorted(set(allowed_origins))

    def ensure_static_files_path(self) -> Path:
        """Ensure the local static directory exists and return its absolute path."""
        static_files_path = Path(__file__).parent / 'static'
        if not static_files_path.exists():
            static_files_path.mkdir(parents=True, exist_ok=True)
        return static_files_path

    async def startup_event_create_defaults(self) -> None:
        """Run startup bootstrap to ensure roles, plans, admin user and sample seed data."""
        logger.info('Executando startup para criar defaults (roles, planos, admin, product types)...')
        session: Session = SessionLocal()
        try:
            if settings.AUTO_CREATE_TABLES:
                self._ensure_tables()
            user_repo = UserRepository(session)
            product_type_repo = ProductTypeRepository(session)
            fornecedor_repo = FornecedorRepository(session)
            product_repo = ProductRepository(session)
            admin_role_obj, _ = self._ensure_roles(user_repo=user_repo)
            admin_plano_obj, plano_gratuito_obj = self._ensure_planos(user_repo=user_repo)
            admin_user = self._ensure_admin_user(session=session, user_repo=user_repo, admin_role_obj=admin_role_obj, admin_plano_obj=admin_plano_obj, plano_gratuito_obj=plano_gratuito_obj)
            self._ensure_global_product_types(product_type_repo=product_type_repo)
            self._ensure_default_supplier(session=session, admin_user=admin_user, fornecedor_repo=fornecedor_repo)
            self._ensure_default_product(session=session, admin_user=admin_user, product_repo=product_repo)
        except Exception as startup_exc:
            logger.error('ERRO CRITICO durante startup defaults: %s', startup_exc, exc_info=True)
        finally:
            session.close()
        logger.info('Evento de startup para defaults concluido.')

    def create_new_user(self, *, user_in: schemas.UserCreate, session: Session) -> models.User:
        """Create a user enforcing uniqueness and assigning default role/plan before persistence."""
        user_repo = UserRepository(session)
        if user_repo.get_user_by_email(email=user_in.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Um usuario com este email ja existe no sistema.')
        self._assign_default_role_and_plan(user_repo=user_repo, user_in=user_in)
        return user_repo.create_user(user=user_in)

    @staticmethod
    def _ensure_tables() -> None:
        """Create database tables when AUTO_CREATE_TABLES is enabled."""
        try:
            logger.info('AUTO_CREATE_TABLES habilitado - criando/verificando tabelas...')
            models.Base.metadata.create_all(bind=engine)
            logger.info('Criacao/verificacao de tabelas concluida.')
        except Exception as exc:
            logger.error('Falha ao criar/verificar tabelas automaticamente: %s', exc)

    @staticmethod
    def _ensure_roles(*, user_repo: UserRepository) -> Tuple[Optional[models.Role], Optional[models.Role]]:
        """Ensure core roles exist and return references to admin and user roles."""
        roles_a_criar = [{'name': 'admin', 'description': 'Administrador do sistema com acesso total.'}, {'name': 'user', 'description': 'Usuario padrao com acesso as funcionalidades do seu plano.'}]
        admin_role_obj: Optional[models.Role] = None
        user_role_obj: Optional[models.Role] = None
        for role_data in roles_a_criar:
            role = user_repo.get_role_by_name(name=role_data['name'])
            if not role:
                role = user_repo.create_role(role=schemas.RoleCreate(**role_data))
                logger.info("Role '%s' criada.", role.name)
            if role.name == 'admin':
                admin_role_obj = role
            elif role.name == 'user':
                user_role_obj = role
        if not admin_role_obj:
            logger.error("ERRO CRITICO: role 'admin' nao pode ser encontrada ou criada.")
        if not user_role_obj:
            logger.error("ERRO CRITICO: role 'user' nao pode ser encontrada ou criada.")
        return (admin_role_obj, user_role_obj)

    @staticmethod
    def _ensure_planos(*, user_repo: UserRepository) -> Tuple[Optional[models.Plano], Optional[models.Plano]]:
        """Ensure default plans exist and return references to Pro and Free plans."""
        plano_gratuito_data = schemas.PlanoCreate(nome='Gratuito', descricao='Plano basico gratuito com limitacoes.', preco_mensal=0.0, limite_produtos=settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO, limite_enriquecimento_web=settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO, limite_geracao_ia=settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO, permite_api_externa=False, suporte_prioritario=False)
        plano_pro_data = schemas.PlanoCreate(nome='Pro', descricao='Plano profissional com mais limites e funcionalidades.', preco_mensal=49.9, limite_produtos=1000, limite_enriquecimento_web=500, limite_geracao_ia=2000, permite_api_externa=True, suporte_prioritario=True)
        admin_plano_obj: Optional[models.Plano] = None
        plano_gratuito_obj: Optional[models.Plano] = None
        for plano_data in (plano_gratuito_data, plano_pro_data):
            plano = user_repo.get_plano_by_name(nome=plano_data.nome)
            if not plano:
                plano = user_repo.create_plano(plano=plano_data)
                logger.info("Plano '%s' criado.", plano.nome)
            if plano.nome == 'Pro':
                admin_plano_obj = plano
            if plano.nome == 'Gratuito':
                plano_gratuito_obj = plano
        if not admin_plano_obj:
            logger.warning("AVISO: Plano 'Pro' nao encontrado para admin. Sera usado 'Gratuito' se disponivel.")
            admin_plano_obj = plano_gratuito_obj
        if not plano_gratuito_obj:
            logger.error("ERRO CRITICO: Plano 'Gratuito' nao encontrado.")
        return (admin_plano_obj, plano_gratuito_obj)

    def _ensure_admin_user(self, *, session: Session, user_repo: UserRepository, admin_role_obj: Optional[models.Role], admin_plano_obj: Optional[models.Plano], plano_gratuito_obj: Optional[models.Plano]) -> Optional[models.User]:
        """Create or normalize the admin user, role and plan assignment."""
        admin_user = user_repo.get_user_by_email(email=settings.ADMIN_EMAIL)
        if not admin_user:
            if not admin_role_obj:
                logger.error("ERRO: nao foi possivel criar admin '%s' porque role 'admin' nao existe.", settings.ADMIN_EMAIL)
                return None
            user_in_data = {'email': settings.ADMIN_EMAIL, 'password': settings.ADMIN_PASSWORD, 'nome_completo': 'Administrador CatalogAI', 'plano_id': admin_plano_obj.id if admin_plano_obj else None}
            if hasattr(settings, 'ADMIN_IDIOMA_PREFERIDO'):
                user_in_data['idioma_preferido'] = settings.ADMIN_IDIOMA_PREFERIDO
            created_admin = user_repo.create_user(user=schemas.UserCreate(**user_in_data))
            created_admin.is_superuser = True
            created_admin.role_id = admin_role_obj.id
            if admin_plano_obj and (not created_admin.plano_id):
                created_admin.plano_id = admin_plano_obj.id
                created_admin.limite_produtos = admin_plano_obj.limite_produtos
                created_admin.limite_enriquecimento_web = admin_plano_obj.limite_enriquecimento_web
                created_admin.limite_geracao_ia = admin_plano_obj.limite_geracao_ia
            elif plano_gratuito_obj and (not created_admin.plano_id):
                created_admin.plano_id = plano_gratuito_obj.id
            session.add(created_admin)
            session.commit()
            session.refresh(created_admin)
            logger.info("Usuario administrador '%s' criado com sucesso.", settings.ADMIN_EMAIL)
            return created_admin
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
        plano_pro = user_repo.get_plano_by_name(nome='Pro')
        if plano_pro and admin_user.plano_id != plano_pro.id:
            admin_user.plano_id = plano_pro.id
            needs_update = True
            logger.info("Atualizando plano do admin '%s'.", settings.ADMIN_EMAIL)
        if needs_update:
            session.commit()
            session.refresh(admin_user)
        return admin_user

    @staticmethod
    def _ensure_global_product_types(*, product_type_repo: ProductTypeRepository) -> None:
        """Seed default global product types if they are missing."""
        product_types_data = [{'key_name': 'eletronicos', 'friendly_name': 'Eletronicos', 'description': 'Tipo padrao para produtos eletronicos.', 'attribute_templates': [{'attribute_key': 'marca', 'label': 'Marca', 'field_type': models.AttributeFieldTypeEnum.TEXT, 'is_required': True, 'display_order': 0, 'description': 'Marca do produto eletronico'}, {'attribute_key': 'voltagem', 'label': 'Voltagem', 'field_type': models.AttributeFieldTypeEnum.SELECT, 'options': '["110v", "220v", "Bivolt"]', 'is_required': True, 'display_order': 1, 'description': 'Selecione a voltagem'}, {'attribute_key': 'cor_principal', 'label': 'Cor Principal', 'field_type': models.AttributeFieldTypeEnum.TEXT, 'is_required': False, 'display_order': 2, 'description': 'Cor predominante do produto'}]}, {'key_name': 'vestuario', 'friendly_name': 'Vestuario', 'description': 'Tipo padrao para pecas de vestuario.', 'attribute_templates': [{'attribute_key': 'tamanho', 'label': 'Tamanho', 'field_type': models.AttributeFieldTypeEnum.SELECT, 'options': '["P", "M", "G", "GG", "XG"]', 'is_required': True, 'display_order': 1, 'description': 'Selecione o tamanho da peca'}, {'attribute_key': 'cor', 'label': 'Cor', 'field_type': models.AttributeFieldTypeEnum.TEXT, 'is_required': True, 'display_order': 2, 'description': 'Cor da peca de vestuario'}, {'attribute_key': 'material', 'label': 'Material Principal', 'field_type': models.AttributeFieldTypeEnum.TEXT, 'is_required': False, 'display_order': 3, 'description': 'Material principal da confeccao'}]}]
        for pt_data in product_types_data:
            product_type_in_db = product_type_repo.get_product_type_by_key_name(key_name=pt_data['key_name'], user_id=None)
            if product_type_in_db:
                logger.info("Tipo de Produto Global '%s' ja existe.", pt_data['friendly_name'])
                continue
            created = product_type_repo.create_product_type(product_type_create=schemas.ProductTypeCreate(**pt_data), user_id=None)
            logger.info("Tipo de Produto Global '%s' criado.", created.friendly_name)

    @staticmethod
    def _ensure_default_supplier(*, session: Session, admin_user: Optional[models.User], fornecedor_repo: FornecedorRepository) -> None:
        """Seed a default supplier for the admin account when absent."""
        if not admin_user:
            return
        fornecedor_existente = session.query(models.Fornecedor).filter(func.lower(models.Fornecedor.nome) == 'uouu', models.Fornecedor.user_id == admin_user.id).first()
        if fornecedor_existente:
            logger.info("Fornecedor de exemplo 'UouU' ja existe para o administrador.")
            return
        fornecedor_repo.create_fornecedor(fornecedor=schemas.FornecedorCreate(nome='UouU', site_url='www.uouu.com.br'), user_id=admin_user.id)
        logger.info("Fornecedor de exemplo 'UouU' criado para o administrador.")

    @staticmethod
    def _ensure_default_product(*, session: Session, admin_user: Optional[models.User], product_repo: ProductRepository) -> None:
        """Seed one default product when the catalog is empty."""
        if not admin_user:
            return
        if session.query(models.Produto).count() != 0:
            return
        product_repo.create_produto(produto=schemas.ProdutoCreate(nome_base='Produto de Exemplo', descricao_original='Item criado automaticamente na inicializacao'), user_id=admin_user.id)
        logger.info('Produto de exemplo criado para o administrador.')

    @staticmethod
    def _assign_default_role_and_plan(*, user_repo: UserRepository, user_in: schemas.UserCreate) -> None:
        """Assign fallback role and plan for newly created users."""
        plano_id_para_novo_usuario = user_in.plano_id
        plano_gratuito_obj_check = user_repo.get_plano_by_name(nome='Gratuito')
        if plano_id_para_novo_usuario is None:
            if plano_gratuito_obj_check:
                plano_id_para_novo_usuario = plano_gratuito_obj_check.id
            else:
                logger.error("ERRO CRITICO: Plano padrao 'Gratuito' nao encontrado no banco.")
                plano_id_para_novo_usuario = None
        role_user_check = user_repo.get_role_by_name(name='user')
        if not role_user_check:
            logger.error("ERRO CRITICO: Role padrao 'user' nao encontrado.")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro de configuracao do sistema: Role padrao 'user' nao encontrado.")
        user_in.role_id = role_user_check.id
        user_in.plano_id = plano_id_para_novo_usuario

class MainBootstrapWorkflow:
    """Workflow/escopo request-scoped para o fluxo de bootstrap da API."""

    def __init__(self, runtime: Optional[MainBootstrapRuntime]=None) -> None:
        """Store runtime dependency used by the workflow facade."""
        self._runtime = runtime or MainBootstrapRuntime()

    def build_allowed_origins(self) -> List[str]:
        """Expose runtime CORS origin resolution."""
        return self._runtime.build_allowed_origins()

    def ensure_static_files_path(self) -> Path:
        """Expose runtime static directory bootstrap."""
        return self._runtime.ensure_static_files_path()

    async def startup_event_create_defaults(self) -> None:
        """Expose runtime startup bootstrap for initial defaults."""
        await self._runtime.startup_event_create_defaults()

    def create_new_user(self, user_in: schemas.UserCreate, session: Session) -> models.User:
        """Expose runtime user creation flow used by HTTP endpoints."""
        return self._runtime.create_new_user(user_in=user_in, session=session)

class _MainLifecycleEntries:

    @staticmethod
    async def lifespan(_app: FastAPI):
        """Execute startup initialization before serving requests."""
        await MainBootstrapWorkflow().startup_event_create_defaults()
        yield

    @staticmethod
    async def startup_event_create_defaults() -> None:
        """Entrada de compatibilidade para testes/workflows de bootstrap."""
        await MainBootstrapWorkflow().startup_event_create_defaults()
lifespan = asynccontextmanager(_MainLifecycleEntries.lifespan)
app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION, description='API para o sistema CatalogAI - Ferramenta de Descricao Assistida por IA.', lifespan=lifespan)
final_unique_allowed_origins = MainBootstrapWorkflow().build_allowed_origins()
logger.info('Final unique allowed_origins para CORSMiddleware: %s', final_unique_allowed_origins)
app.add_middleware(CORSMiddleware, allow_origins=final_unique_allowed_origins, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
static_files_path = MainBootstrapWorkflow().ensure_static_files_path()
app.mount('/static', StaticFiles(directory=static_files_path), name='static')

class _EndpointHandlers:

    @app.post('/api/v1/users/', response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED, tags=['Usuarios'])
    def create_new_user(
        user_in: schemas.UserCreate,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ):
        """Create a user through the bootstrap workflow."""
        return MainBootstrapWorkflow().create_new_user(user_in=user_in, session=session)

    @app.get('/', tags=['Raiz'])
    async def root():
        """Return a simple welcome payload for root endpoint."""
        return {'message': f'Bem-vindo a API do {settings.PROJECT_NAME}!'}

    @app.get('/health', status_code=status.HTTP_200_OK, tags=['Health Check'])
    async def health_check():
        """Return a lightweight health check status."""
        return {'status': 'ok'}
app.include_router(auth_router_direct, prefix=settings.API_V1_STR + '/auth', tags=['Autenticacao e Usuarios'])
app.include_router(social_auth_router, prefix=settings.API_V1_STR + '/auth', tags=['Autenticacao Social'])
app.include_router(produtos_router, prefix=settings.API_V1_STR, tags=['Produtos'])
app.include_router(fornecedores_router, prefix=settings.API_V1_STR, tags=['Fornecedores'])
app.include_router(generation_router, prefix=settings.API_V1_STR, tags=['Geracao de Conteudo IA'])
app.include_router(web_enrichment_router, prefix=settings.API_V1_STR, tags=['Enriquecimento Web'])
app.include_router(product_types_router, prefix=settings.API_V1_STR, tags=['Tipos de Produto e Templates'])
app.include_router(search_router, prefix=settings.API_V1_STR, tags=['Busca'])
app.include_router(uso_ia_router, prefix=settings.API_V1_STR, tags=['Registro de Uso de IA'])
app.include_router(historico_router, prefix=settings.API_V1_STR, tags=['Historico'])
app.include_router(password_recovery_router, prefix=settings.API_V1_STR, tags=['Recuperacao de Senha'])
app.include_router(admin_analytics_router, prefix=settings.API_V1_STR + '/admin/analytics', tags=['Analytics (Admin)'])

