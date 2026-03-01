"""Inicializacao de dados padrao da plataforma via workflow OO."""
from __future__ import annotations
import logging
from typing import Optional, Tuple
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from Backend import schemas
from Backend.core.config import settings
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository
from Backend.infrastructure.repositories.user_repository import UserRepository
from Backend.models import AttributeFieldTypeEnum, Fornecedor, Produto, Role, User
logger = logging.getLogger(__name__)

class InitialDataRuntime:
    """Runtime OO responsavel por inicializar dados base do sistema."""

    def create_initial_data(self, db: Session):
        logger.info('Verificando/criando dados iniciais (roles, planos, admin)...')
        user_repo = UserRepository(db)
        product_type_repo = ProductTypeRepository(db)
        fornecedor_repo = FornecedorRepository(db)
        product_repo = ProductRepository(db)
        self._ensure_default_roles(user_repo=user_repo)
        self._ensure_default_plans(user_repo=user_repo)
        admin_user = self._ensure_admin_user(db=db, user_repo=user_repo)
        self._ensure_global_product_types(product_type_repo=product_type_repo)
        self._ensure_default_supplier(db=db, admin_user=admin_user, fornecedor_repo=fornecedor_repo)
        self._ensure_default_product(db=db, user_repo=user_repo, product_repo=product_repo)
        logger.info('Criacao/verificacao de dados iniciais concluida.')

    @staticmethod
    def _ensure_default_roles(*, user_repo: UserRepository) -> Tuple[Optional[Role], Optional[Role]]:
        roles_padrao = [{'name': 'admin', 'description': 'Administrador do sistema'}, {'name': 'user', 'description': 'Usuario padrao da plataforma'}]
        admin_role: Optional[Role] = None
        user_role: Optional[Role] = None
        for role_data in roles_padrao:
            role = user_repo.get_role_by_name(name=role_data['name'])
            if not role:
                role = user_repo.create_role(role=schemas.RoleCreate(**role_data))
                logger.info("Role '%s' criada.", role_data['name'])
            if role.name == 'admin':
                admin_role = role
            if role.name == 'user':
                user_role = role
        return (admin_role, user_role)

    @staticmethod
    def _ensure_default_plans(*, user_repo: UserRepository) -> None:
        planos_padrao = [{'nome': 'Gratuito', 'descricao': 'Plano basico com limitacoes.', 'preco_mensal': 0.0, 'limite_produtos': settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO, 'limite_enriquecimento_web': settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO, 'limite_geracao_ia': settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO, 'permite_api_externa': False, 'suporte_prioritario': False}, {'nome': 'Pro', 'descricao': 'Plano profissional com mais limites e funcionalidades.', 'preco_mensal': 99.9, 'limite_produtos': 1000, 'limite_enriquecimento_web': 500, 'limite_geracao_ia': 2000, 'permite_api_externa': True, 'suporte_prioritario': True}]
        for plano_data in planos_padrao:
            plano = user_repo.get_plano_by_name(nome=plano_data['nome'])
            if plano:
                continue
            user_repo.create_plano(plano=schemas.PlanoCreate(**plano_data))
            logger.info("Plano '%s' criado.", plano_data['nome'])

    def _ensure_admin_user(self, *, db: Session, user_repo: UserRepository) -> Optional[User]:
        admin_email = settings.FIRST_SUPERUSER_EMAIL
        admin_password = settings.FIRST_SUPERUSER_PASSWORD
        admin_user = user_repo.get_user_by_email(email=admin_email)
        if admin_user:
            logger.info("Usuario administrador '%s' ja existe.", admin_email)
            return admin_user
        admin_role = user_repo.get_role_by_name(name='admin')
        admin_plano = user_repo.get_plano_by_name(nome='Pro')
        db_admin_user = user_repo.create_user(user=schemas.UserCreate(email=admin_email, password=admin_password, nome_completo='Admin CatalogAI', plano_id=admin_plano.id if admin_plano else None))
        db_admin_user.is_superuser = True
        if admin_role:
            db_admin_user.role_id = admin_role.id
        db.commit()
        db.refresh(db_admin_user)
        logger.info("Usuario administrador '%s' criado com sucesso.", admin_email)
        return db_admin_user

    @staticmethod
    def _ensure_global_product_types(*, product_type_repo: ProductTypeRepository) -> None:
        tipos_produto_globais = [{'key_name': 'eletronicos', 'friendly_name': 'Eletronicos', 'description': 'Tipo padrao para produtos eletronicos.', 'attribute_templates': [schemas.AttributeTemplateCreate(attribute_key='voltagem', label='Voltagem', field_type=AttributeFieldTypeEnum.SELECT, options='["110V", "220V", "Bivolt"]', is_required=True, display_order=1), schemas.AttributeTemplateCreate(attribute_key='cor_predominante', label='Cor Predominante', field_type=AttributeFieldTypeEnum.TEXT, is_required=False, display_order=2), schemas.AttributeTemplateCreate(attribute_key='garantia_meses', label='Garantia (meses)', field_type=AttributeFieldTypeEnum.NUMBER, default_value='12', display_order=3)]}, {'key_name': 'vestuario', 'friendly_name': 'Vestuario', 'description': 'Tipo padrao para pecas de vestuario.', 'attribute_templates': [schemas.AttributeTemplateCreate(attribute_key='tamanho', label='Tamanho', field_type=AttributeFieldTypeEnum.SELECT, options='["P", "M", "G", "GG"]', is_required=True, display_order=1), schemas.AttributeTemplateCreate(attribute_key='cor_produto', label='Cor', field_type=AttributeFieldTypeEnum.TEXT, is_required=True, display_order=2), schemas.AttributeTemplateCreate(attribute_key='material_principal', label='Material Principal', field_type=AttributeFieldTypeEnum.TEXT, display_order=3), schemas.AttributeTemplateCreate(attribute_key='genero_vestuario', label='Genero', field_type=AttributeFieldTypeEnum.SELECT, options='["Masculino", "Feminino", "Unissex"]', display_order=4)]}]
        for pt_data in tipos_produto_globais:
            pt_create_schema = schemas.ProductTypeCreate(**pt_data)
            existing_pt = product_type_repo.get_product_type_by_key_name(key_name=pt_create_schema.key_name, user_id=None)
            if existing_pt:
                logger.info("Tipo de Produto Global '%s' ja existe.", pt_create_schema.friendly_name)
                continue
            try:
                product_type_repo.create_product_type(product_type_create=pt_create_schema, user_id=None)
                logger.info("Tipo de Produto Global '%s' criado.", pt_create_schema.friendly_name)
            except IntegrityError as exc:
                logger.warning("Nao foi possivel criar o tipo de produto global '%s': %s", pt_create_schema.key_name, exc)
            except Exception as exc:
                logger.error("Erro inesperado ao criar tipo de produto global '%s': %s", pt_create_schema.key_name, exc, exc_info=True)

    @staticmethod
    def _ensure_default_supplier(*, db: Session, admin_user: Optional[User], fornecedor_repo: FornecedorRepository) -> None:
        if not admin_user:
            return
        fornecedor_existente = db.query(Fornecedor).filter(func.lower(Fornecedor.nome) == 'uouu', Fornecedor.user_id == admin_user.id).first()
        if fornecedor_existente:
            logger.info("Fornecedor de exemplo 'UouU' ja existe para o administrador.")
            return
        fornecedor_repo.create_fornecedor(fornecedor=schemas.FornecedorCreate(nome='UouU', site_url='www.uouu.com.br'), user_id=admin_user.id)
        logger.info("Fornecedor de exemplo 'UouU' criado para o administrador.")

    @staticmethod
    def _ensure_default_product(*, db: Session, user_repo: UserRepository, product_repo: ProductRepository) -> None:
        if db.query(Produto).count() != 0:
            return
        admin_user = user_repo.get_user_by_email(email=settings.FIRST_SUPERUSER_EMAIL)
        if not admin_user:
            return
        product_repo.create_produto(produto=schemas.ProdutoCreate(nome_base='Produto de Exemplo', descricao_original='Item criado automaticamente na inicializacao'), user_id=admin_user.id)
        logger.info('Produto de exemplo criado para o administrador.')

class InitialDataWorkflow:
    """Workflow/escopo request-scoped para criacao de dados iniciais."""

    def __init__(self, runtime: Optional[InitialDataRuntime]=None) -> None:
        self._runtime = runtime or InitialDataRuntime()

    def create_initial_data(self, db: Session):
        return self._runtime.create_initial_data(db=db)

class _InitialDataEntryPoints:

    @staticmethod
    def create_initial_data(db: Session):
        """Entrada publica de compatibilidade para rotinas de seed."""
        return InitialDataWorkflow().create_initial_data(db=db)
