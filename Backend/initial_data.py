import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from Backend.core.config import settings
from Backend import schemas
from Backend.models import Fornecedor, Produto, AttributeFieldTypeEnum
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository
from Backend.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


def _create_initial_data_core(db: Session):
    logger.info("Verificando/criando dados iniciais (roles, planos, admin)...")
    user_repo = UserRepository(db)
    product_type_repo = ProductTypeRepository(db)
    fornecedor_repo = FornecedorRepository(db)
    product_repo = ProductRepository(db)

    roles_padrao = [
        {"name": "admin", "description": "Administrador do sistema"},
        {"name": "user", "description": "UsuÃƒÂ¡rio padrÃƒÂ£o da plataforma"},
    ]
    for role_data in roles_padrao:
        role = user_repo.get_role_by_name(name=role_data["name"])
        if not role:
            user_repo.create_role(
                role=schemas.RoleCreate(**role_data),
            )
            logger.info(f"Role '{role_data['name']}' criada.")

    planos_padrao = [
        {
            "nome": "Gratuito", "descricao": "Plano bÃƒÂ¡sico com limitaÃƒÂ§ÃƒÂµes.",
            "preco_mensal": 0.0, "limite_produtos": settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO,
            "limite_enriquecimento_web": settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO,
            "limite_geracao_ia": settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO,
            "permite_api_externa": False, "suporte_prioritario": False
        },
        {
            "nome": "Pro", "descricao": "Plano profissional com mais limites e funcionalidades.",
            "preco_mensal": 99.90, "limite_produtos": 1000,
            "limite_enriquecimento_web": 500, "limite_geracao_ia": 2000,
            "permite_api_externa": True, "suporte_prioritario": True
        },
    ]
    for plano_data in planos_padrao:
        plano = user_repo.get_plano_by_name(nome=plano_data["nome"])
        if not plano:
            user_repo.create_plano(
                plano=schemas.PlanoCreate(**plano_data),
            )
            logger.info(f"Plano '{plano_data['nome']}' criado.")

    admin_email = settings.FIRST_SUPERUSER_EMAIL
    admin_password = settings.FIRST_SUPERUSER_PASSWORD
    admin_user = user_repo.get_user_by_email(email=admin_email)
    if not admin_user:
        admin_role = user_repo.get_role_by_name(name="admin")
        admin_plano = user_repo.get_plano_by_name(nome="Pro")

        user_in = schemas.UserCreate(
            email=admin_email,
            password=admin_password,
            nome_completo="Admin CatalogAI",
            plano_id=admin_plano.id if admin_plano else None
        )
        db_admin_user = user_repo.create_user(user=user_in)
        db_admin_user.is_superuser = True
        if admin_role:
            db_admin_user.role_id = admin_role.id

        db.commit()
        db.refresh(db_admin_user)
        admin_user = db_admin_user
        logger.info(f"UsuÃƒÂ¡rio administrador '{admin_email}' criado com sucesso.")
    else:
        logger.info(f"UsuÃƒÂ¡rio administrador '{admin_email}' jÃƒÂ¡ existe.")

    tipos_produto_globais = [
        {
            "key_name": "eletronicos",
            "friendly_name": "EletrÃƒÂ´nicos",
            "description": "Tipo padrÃƒÂ£o para produtos eletrÃƒÂ´nicos.",
            "attribute_templates": [
                schemas.AttributeTemplateCreate(attribute_key="voltagem", label="Voltagem", field_type=AttributeFieldTypeEnum.SELECT, options='["110V", "220V", "Bivolt"]', is_required=True, display_order=1),
                schemas.AttributeTemplateCreate(attribute_key="cor_predominante", label="Cor Predominante", field_type=AttributeFieldTypeEnum.TEXT, is_required=False, display_order=2),
                schemas.AttributeTemplateCreate(attribute_key="garantia_meses", label="Garantia (meses)", field_type=AttributeFieldTypeEnum.NUMBER, default_value="12", display_order=3),
            ]
        },
        {
            "key_name": "vestuario",
            "friendly_name": "VestuÃƒÂ¡rio",
            "description": "Tipo padrÃƒÂ£o para peÃƒÂ§as de vestuÃƒÂ¡rio.",
            "attribute_templates": [
                schemas.AttributeTemplateCreate(
                    attribute_key="tamanho",
                    label="Tamanho",
                    field_type=AttributeFieldTypeEnum.SELECT,
                    options='["P", "M", "G", "GG"]',
                    is_required=True,
                    display_order=1
                ),
                schemas.AttributeTemplateCreate(
                    attribute_key="cor_produto",
                    label="Cor",
                    field_type=AttributeFieldTypeEnum.TEXT,
                    is_required=True,
                    display_order=2
                ),
                schemas.AttributeTemplateCreate(
                    attribute_key="material_principal",
                    label="Material Principal",
                    field_type=AttributeFieldTypeEnum.TEXT,
                    display_order=3
                ),
                schemas.AttributeTemplateCreate(
                    attribute_key="genero_vestuario",
                    label="GÃƒÂªnero",
                    field_type=AttributeFieldTypeEnum.SELECT,
                    options='["Masculino", "Feminino", "Unissex"]',
                    display_order=4
                ),
            ]
        }
    ]

    for pt_data in tipos_produto_globais:
        pt_create_schema = schemas.ProductTypeCreate(**pt_data)
        existing_pt = product_type_repo.get_product_type_by_key_name(
            key_name=pt_create_schema.key_name,
            user_id=None,
        )
        if not existing_pt:
            try:
                product_type_repo.create_product_type(
                    product_type_create=pt_create_schema,
                    user_id=None,
                )
                logger.info(f"Tipo de Produto Global '{pt_create_schema.friendly_name}' criado.")
            except IntegrityError as e:
                logger.warning(f"NÃƒÂ£o foi possÃƒÂ­vel criar o tipo de produto global '{pt_create_schema.key_name}': {e}")
            except Exception as e:
                logger.error(f"Erro inesperado ao criar tipo de produto global '{pt_create_schema.key_name}': {e}", exc_info=True)
        else:
            logger.info(f"Tipo de Produto Global '{pt_create_schema.friendly_name}' jÃƒÂ¡ existe.")

    if admin_user:
        fornecedor_existente = db.query(Fornecedor).filter(
            func.lower(Fornecedor.nome) == "uouu",
            Fornecedor.user_id == admin_user.id,
        ).first()
        if not fornecedor_existente:
            fornecedor_schema = schemas.FornecedorCreate(
                nome="UouU",
                site_url="www.uouu.com.br",
            )
            fornecedor_repo.create_fornecedor(
                fornecedor=fornecedor_schema,
                user_id=admin_user.id,
            )
            logger.info("Fornecedor de exemplo 'UouU' criado para o administrador.")
        else:
            logger.info("Fornecedor de exemplo 'UouU' jÃƒÂ¡ existe para o administrador.")

    if db.query(Produto).count() == 0:
        admin_user = user_repo.get_user_by_email(email=admin_email)
        if admin_user:
            exemplo = schemas.ProdutoCreate(
                nome_base="Produto de Exemplo",
                descricao_original="Item criado automaticamente na inicializaÃƒÂ§ÃƒÂ£o"
            )
            product_repo.create_produto(
                produto=exemplo,
                user_id=admin_user.id,
            )
            logger.info("Produto de exemplo criado para o administrador.")

    logger.info("CriaÃƒÂ§ÃƒÂ£o/verificaÃƒÂ§ÃƒÂ£o de dados iniciais concluÃƒÂ­da.")


class _InitialDataWorkflow:
    def __init__(self, runtime: Optional["_InitialDataRuntime"] = None) -> None:
        self._runtime = runtime or _InitialDataRuntime()

    def create_initial_data(self, db: Session):
        return self._runtime.create_initial_data(db=db)


class _InitialDataRuntime:
    def create_initial_data(self, db: Session):
        return _create_initial_data_core(db=db)

InitialDataWorkflow = _InitialDataWorkflow


def get_initial_data_workflow() -> InitialDataWorkflow:
    return InitialDataWorkflow()


def create_initial_data(db: Session):
    return get_initial_data_workflow().create_initial_data(db=db)





