import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from Backend.core.config import settings
from Backend import schemas
from Backend.models import Fornecedor, Produto, AttributeFieldTypeEnum
from Backend.crud_users import create_role, get_role_by_name, create_plano, get_plano_by_name, create_user, get_user_by_email
from Backend.crud_fornecedores import create_fornecedor
from Backend.crud_produtos import create_produto
from Backend.crud_product_types import create_product_type, get_product_type_by_key_name

logger = logging.getLogger(__name__)


def _create_initial_data_core(db: Session):
    logger.info("Verificando/criando dados iniciais (roles, planos, admin)...")

    roles_padrao = [
        {"name": "admin", "description": "Administrador do sistema"},
        {"name": "user", "description": "UsuÃ¡rio padrÃ£o da plataforma"},
    ]
    for role_data in roles_padrao:
        role = get_role_by_name(db, role_data["name"])
        if not role:
            create_role(db, schemas.RoleCreate(**role_data))
            logger.info(f"Role '{role_data['name']}' criada.")

    planos_padrao = [
        {
            "nome": "Gratuito", "descricao": "Plano bÃ¡sico com limitaÃ§Ãµes.",
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
        plano = get_plano_by_name(db, plano_data["nome"])
        if not plano:
            create_plano(db, schemas.PlanoCreate(**plano_data))
            logger.info(f"Plano '{plano_data['nome']}' criado.")

    admin_email = settings.FIRST_SUPERUSER_EMAIL
    admin_password = settings.FIRST_SUPERUSER_PASSWORD
    admin_user = get_user_by_email(db, admin_email)
    if not admin_user:
        admin_role = get_role_by_name(db, "admin")
        admin_plano = get_plano_by_name(db, "Pro")

        user_in = schemas.UserCreate(
            email=admin_email,
            password=admin_password,
            nome_completo="Admin CatalogAI",
            plano_id=admin_plano.id if admin_plano else None
        )
        db_admin_user = create_user(db, user_in)
        db_admin_user.is_superuser = True
        if admin_role:
            db_admin_user.role_id = admin_role.id

        db.commit()
        db.refresh(db_admin_user)
        admin_user = db_admin_user
        logger.info(f"UsuÃ¡rio administrador '{admin_email}' criado com sucesso.")
    else:
        logger.info(f"UsuÃ¡rio administrador '{admin_email}' jÃ¡ existe.")

    tipos_produto_globais = [
        {
            "key_name": "eletronicos",
            "friendly_name": "EletrÃ´nicos",
            "description": "Tipo padrÃ£o para produtos eletrÃ´nicos.",
            "attribute_templates": [
                schemas.AttributeTemplateCreate(attribute_key="voltagem", label="Voltagem", field_type=AttributeFieldTypeEnum.SELECT, options='["110V", "220V", "Bivolt"]', is_required=True, display_order=1),
                schemas.AttributeTemplateCreate(attribute_key="cor_predominante", label="Cor Predominante", field_type=AttributeFieldTypeEnum.TEXT, is_required=False, display_order=2),
                schemas.AttributeTemplateCreate(attribute_key="garantia_meses", label="Garantia (meses)", field_type=AttributeFieldTypeEnum.NUMBER, default_value="12", display_order=3),
            ]
        },
        {
            "key_name": "vestuario",
            "friendly_name": "VestuÃ¡rio",
            "description": "Tipo padrÃ£o para peÃ§as de vestuÃ¡rio.",
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
                    label="GÃªnero",
                    field_type=AttributeFieldTypeEnum.SELECT,
                    options='["Masculino", "Feminino", "Unissex"]',
                    display_order=4
                ),
            ]
        }
    ]

    for pt_data in tipos_produto_globais:
        pt_create_schema = schemas.ProductTypeCreate(**pt_data)
        existing_pt = get_product_type_by_key_name(db, key_name=pt_create_schema.key_name, user_id=None)
        if not existing_pt:
            try:
                create_product_type(db, product_type_create=pt_create_schema, user_id=None)
                logger.info(f"Tipo de Produto Global '{pt_create_schema.friendly_name}' criado.")
            except IntegrityError as e:
                logger.warning(f"NÃ£o foi possÃ­vel criar o tipo de produto global '{pt_create_schema.key_name}': {e}")
            except Exception as e:
                logger.error(f"Erro inesperado ao criar tipo de produto global '{pt_create_schema.key_name}': {e}", exc_info=True)
        else:
            logger.info(f"Tipo de Produto Global '{pt_create_schema.friendly_name}' jÃ¡ existe.")

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
            create_fornecedor(db, fornecedor_schema, user_id=admin_user.id)
            logger.info("Fornecedor de exemplo 'UouU' criado para o administrador.")
        else:
            logger.info("Fornecedor de exemplo 'UouU' jÃ¡ existe para o administrador.")

    if db.query(Produto).count() == 0:
        admin_user = get_user_by_email(db, admin_email)
        if admin_user:
            exemplo = schemas.ProdutoCreate(
                nome_base="Produto de Exemplo",
                descricao_original="Item criado automaticamente na inicializaÃ§Ã£o"
            )
            create_produto(db, exemplo, user_id=admin_user.id)
            logger.info("Produto de exemplo criado para o administrador.")

    logger.info("CriaÃ§Ã£o/verificaÃ§Ã£o de dados iniciais concluÃ­da.")


class _InitialDataWorkflow:
    def __init__(self, runtime: Optional["_InitialDataRuntime"] = None) -> None:
        self._runtime = runtime or _InitialDataRuntime()

    def create_initial_data(self, db: Session):
        return self._runtime.create_initial_data(db=db)


class _InitialDataRuntime:
    def create_initial_data(self, db: Session):
        return _create_initial_data_core(db=db)


_initial_data_workflow = _InitialDataWorkflow()


def create_initial_data(db: Session):
    return _initial_data_workflow.create_initial_data(db=db)


class InitialDataLegacyService:
    def create_initial_data(self, *args, **kwargs):
        return create_initial_data(*args, **kwargs)


