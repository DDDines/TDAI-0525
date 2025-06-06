# Backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List, Optional, Any
import json
import traceback
import logging

import models
import schemas
import crud
from auth import router as auth_router_direct
from database import SessionLocal, engine, get_db
from core.config import settings

# Importa os routers da subpasta 'routers'
from routers.produtos import router as produtos_router
from routers.fornecedores import router as fornecedores_router
from routers.generation import router as generation_router
from routers.web_enrichment import router as web_enrichment_router
from routers.uploads import router as uploads_router
from routers.product_types import router as product_types_router
from routers.uso_ia import router as uso_ia_router
from routers.password_recovery import router as password_recovery_router
from routers.admin_analytics import router as admin_analytics_router
from routers.social_auth import router as social_auth_router

from core.config import logger


try:
    logger.info("Tentando criar tabelas no banco de dados (models.Base.metadata.create_all)...")
    # A LINHA ABAIXO FOI COMENTADA PARA EVITAR ERROS COM O RELOADER DO UVICORN.
    # O GERENCIAMENTO DO SCHEMA DO BANCO DE DADOS DEVE SER FEITO VIA ALEMBIC.
    # models.Base.metadata.create_all(bind=engine)
    logger.info("Criação/verificação de tabelas concluída.")
except Exception as e:
    logger.error("Falha ao criar/verificar tabelas: %s", e)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="API para o sistema TDAI - Ferramenta de Descrição Assistida por IA.",
)

# Configuração do CORS
# (Código CORS mantido como na correção anterior, já está correto)
exact_frontend_origin = "http://localhost:5173"
default_cors_origins_list = [
    exact_frontend_origin, "http://127.0.0.1:5173",
    exact_frontend_origin + "/", "http://127.0.0.1:5173/",
    "http://localhost", "http://127.0.0.1",
]
current_allowed_origins = []
try:
    if hasattr(settings, 'BACKEND_CORS_ORIGINS') and settings.BACKEND_CORS_ORIGINS:
        normalized_env_origins = set()
        for origin_obj in settings.BACKEND_CORS_ORIGINS:
            origin_str = str(origin_obj)
            normalized_env_origins.add(origin_str.rstrip('/'))
            normalized_env_origins.add(origin_str)
        if not normalized_env_origins:
            current_allowed_origins = list(default_cors_origins_list)
        else:
            current_allowed_origins = sorted(list(normalized_env_origins))
            for default_org in default_cors_origins_list:
                if default_org not in current_allowed_origins:
                    current_allowed_origins.append(default_org)
            current_allowed_origins = sorted(list(set(current_allowed_origins)))
    else:
        current_allowed_origins = list(default_cors_origins_list)
except Exception:
    current_allowed_origins = list(default_cors_origins_list)
if exact_frontend_origin not in current_allowed_origins:
    current_allowed_origins.insert(0, exact_frontend_origin)
final_unique_allowed_origins = sorted(list(set(current_allowed_origins)))
logger.info(
    "Final unique allowed_origins para CORSMiddleware: %s",
    final_unique_allowed_origins,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=final_unique_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


static_files_path = Path(__file__).parent / "static"
if not static_files_path.exists():
    static_files_path.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_files_path), name="static")


@app.on_event("startup")
async def startup_event_create_defaults():
    logger.info("Executando evento de startup para criar defaults (roles, planos, admin user, product types)...")
    db: Session = SessionLocal()
    try:
        # 1. Criação de Roles
        roles_a_criar = [
            {"name": "admin", "description": "Administrador do sistema com acesso total."},
            {"name": "user", "description": "Usuário padrão com acesso às funcionalidades do seu plano."},
        ]
        admin_role_obj = None
        user_role_obj = None
        for role_data in roles_a_criar:
            role = crud.get_role_by_name(db, name=role_data["name"])
            if not role:
                role = crud.create_role(db, role=schemas.RoleCreate(**role_data))
                logger.info(f"Role '{role.name}' criada.")
            if role.name == "admin":
                admin_role_obj = role
            elif role.name == "user":
                user_role_obj = role
        
        if not admin_role_obj:
            logger.error("ERRO CRÍTICO: Role 'admin' não pôde ser encontrada ou criada.")
        if not user_role_obj:
            logger.error("ERRO CRÍTICO: Role 'user' não pôde ser encontrada ou criada.")

        # 2. Criação de Planos (Corrigido)
        plano_gratuito_data = schemas.PlanoCreate(
            nome="Gratuito",
            descricao="Plano básico gratuito com limitações.",
            preco_mensal=0.0,
            limite_produtos=settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO,
            limite_enriquecimento_web=settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO,
            limite_geracao_ia=settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO,
            permite_api_externa=False,
            suporte_prioritario=False
        )
        plano_pro_data = schemas.PlanoCreate(
            nome="Pro",
            descricao="Plano profissional com mais limites e funcionalidades.",
            preco_mensal=49.90,
            limite_produtos=1000,
            limite_enriquecimento_web=500,
            limite_geracao_ia=2000,
            permite_api_externa=True,
            suporte_prioritario=True
        )

        planos_a_criar = [plano_gratuito_data, plano_pro_data]
        
        admin_plano_obj = None 
        plano_gratuito_obj = None 
        for plano_data in planos_a_criar:
            plano = crud.get_plano_by_name(db, nome=plano_data.nome)
            if not plano:
                plano = crud.create_plano(db, plano=plano_data)
                logger.info(f"Plano '{plano.nome}' criado.")
            if plano.nome == "Pro": 
                admin_plano_obj = plano
            if plano.nome == "Gratuito":
                plano_gratuito_obj = plano
        
        if not admin_plano_obj: 
            logger.warning("AVISO: Plano 'Pro' não encontrado para o usuário admin. Ele será associado ao plano 'Gratuito' se disponível, ou ficará sem plano.")
            admin_plano_obj = plano_gratuito_obj 
        if not plano_gratuito_obj:
            logger.error("ERRO CRÍTICO: Plano 'Gratuito' não encontrado. Novos usuários podem não ser associados a um plano padrão.")

        # 3. Criação do Usuário Administrador
        admin_user = crud.get_user_by_email(db, email=settings.ADMIN_EMAIL)
        if not admin_user:
            if not admin_role_obj:
                   logger.error(f"ERRO: Não foi possível criar o usuário admin '{settings.ADMIN_EMAIL}' porque o role 'admin' não existe.")
            else:
                user_in_data = {
                    "email": settings.ADMIN_EMAIL,
                    "password": settings.ADMIN_PASSWORD,
                    "nome_completo": "Administrador TDAI",
                    "plano_id": admin_plano_obj.id if admin_plano_obj else None,
                }
                if hasattr(settings, 'ADMIN_IDIOMA_PREFERIDO'):
                    user_in_data['idioma_preferido'] = settings.ADMIN_IDIOMA_PREFERIDO
                
                user_in_create = schemas.UserCreate(**user_in_data)
                
                created_admin = crud.create_user(db=db, user=user_in_create)
                
                if created_admin:
                    created_admin.is_superuser = True 
                    if admin_role_obj:
                        created_admin.role_id = admin_role_obj.id
                    
                    if admin_plano_obj and not created_admin.plano_id:
                        created_admin.plano_id = admin_plano_obj.id
                        # Sincroniza limites do plano no usuário
                        created_admin.limite_produtos = admin_plano_obj.limite_produtos
                        created_admin.limite_enriquecimento_web = admin_plano_obj.limite_enriquecimento_web
                        created_admin.limite_geracao_ia = admin_plano_obj.limite_geracao_ia
                    
                    db.add(created_admin) 
                    db.commit()
                    db.refresh(created_admin)
                    logger.info(f"Usuário administrador '{settings.ADMIN_EMAIL}' criado com sucesso.")
                else:
                    logger.error(f"ERRO: Falha ao criar o usuário administrador '{settings.ADMIN_EMAIL}'.")
        else:
            logger.info(f"Usuário administrador '{settings.ADMIN_EMAIL}' já existe.")
            needs_update = False
            if admin_role_obj and admin_user.role_id != admin_role_obj.id:
                admin_user.role_id = admin_role_obj.id
                needs_update = True
                logger.info(f"Atualizando role do admin '{settings.ADMIN_EMAIL}'.")
            if not admin_user.is_superuser:
                admin_user.is_superuser = True
                needs_update = True
                logger.info(f"Atualizando admin '{settings.ADMIN_EMAIL}' para superuser.")
            
            admin_plano_obj = crud.get_plano_by_name(db, "Pro")
            if admin_plano_obj and admin_user.plano_id != admin_plano_obj.id:
                admin_user.plano_id = admin_plano_obj.id
                needs_update = True
                logger.info(f"Atualizando plano do admin '{settings.ADMIN_EMAIL}'.")

            if needs_update:
                db.commit()
                db.refresh(admin_user)

        # 4. Criar Tipos de Produto e Atributos Padrão (Globais, user_id=None)
        product_types_data = [
            {
                "key_name": "eletronicos",
                "friendly_name": "Eletrônicos",
                "description": "Tipo padrão para produtos eletrônicos.",
                "attribute_templates": [
                    {"attribute_key": "marca", "label": "Marca", "field_type": models.AttributeFieldTypeEnum.TEXT, "is_required": True, "display_order": 0, "description": "Marca do produto eletrônico"},
                    {"attribute_key": "voltagem", "label": "Voltagem", "field_type": models.AttributeFieldTypeEnum.SELECT, "options": '["110v", "220v", "Bivolt"]', "is_required": True, "display_order": 1, "description": "Selecione a voltagem"},
                    {"attribute_key": "cor_principal", "label": "Cor Principal", "field_type": models.AttributeFieldTypeEnum.TEXT, "is_required": False, "display_order": 2, "description": "Cor predominante do produto"},
                ]
            },
            {
                "key_name": "vestuario",
                "friendly_name": "Vestuário",
                "description": "Tipo padrão para peças de vestuário.",
                "attribute_templates": [
                    {"attribute_key": "tamanho", "label": "Tamanho", "field_type": models.AttributeFieldTypeEnum.SELECT, "options": '["P", "M", "G", "GG", "XG"]', "is_required": True, "display_order": 1, "description": "Selecione o tamanho da peça"},
                    {"attribute_key": "cor", "label": "Cor", "field_type": models.AttributeFieldTypeEnum.TEXT, "is_required": True, "display_order": 2, "description": "Cor da peça de vestuário"},
                    {"attribute_key": "material", "label": "Material Principal", "field_type": models.AttributeFieldTypeEnum.TEXT, "is_required": False, "display_order": 3, "description": "Material principal da confecção"},
                ]
            }
        ]

        for pt_data in product_types_data:
            product_type_in_db = crud.get_product_type_by_key_name(db, key_name=pt_data["key_name"], user_id=None) 

            if not product_type_in_db:
                product_type_create_schema = schemas.ProductTypeCreate(**pt_data)
                crud.create_product_type(db=db, product_type_create=product_type_create_schema, user_id=None)
                logger.info(f"Tipo de Produto Global '{product_type_create_schema.friendly_name}' criado.")
            else:
                logger.info(f"Tipo de Produto Global '{pt_data['friendly_name']}' já existe.")

    except Exception as e_startup:
        logger.error(f"ERRO CRÍTICO durante o evento de startup: {e_startup}", exc_info=True)
    finally:
        db.close()
    logger.info("Evento de startup para defaults concluído.")


@app.post("/api/v1/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED, tags=["Usuários"])
def create_new_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    db_user_check = crud.get_user_by_email(db, email=user_in.email)
    if db_user_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuário com este email já existe no sistema.",
        )
    
    plano_id_para_novo_usuario = user_in.plano_id
    plano_gratuito_obj_check = crud.get_plano_by_name(db, nome="Gratuito")

    if plano_id_para_novo_usuario is None:
        if plano_gratuito_obj_check:
            plano_id_para_novo_usuario = plano_gratuito_obj_check.id
        else: 
            logger.error("ERRO CRÍTICO: Plano padrão 'Gratuito' não encontrado no DB.")
            plano_id_para_novo_usuario = None 

    role_user_check = crud.get_role_by_name(db, name="user")
    if not role_user_check: 
        logger.error("ERRO CRÍTICO: Role padrão 'user' não encontrado.")
        raise HTTPException(status_code=500, detail="Erro de configuração do sistema: Role padrão 'user' não encontrado.")
    
    user_in.role_id = role_user_check.id
    user_in.plano_id = plano_id_para_novo_usuario
    
    new_user_created = crud.create_user(db=db, user=user_in)
    
    return new_user_created


# --- INÍCIO DA CORREÇÃO ---
# Inclusão dos routers da aplicação com prefixo /api/v1
# A rota de autenticação de token precisa do prefixo /auth
app.include_router(auth_router_direct, prefix=settings.API_V1_STR + "/auth", tags=["Autenticação e Usuários"])
# --- FIM DA CORREÇÃO ---

app.include_router(social_auth_router, prefix=settings.API_V1_STR + "/auth", tags=["Autenticação Social"])
app.include_router(produtos_router, prefix=settings.API_V1_STR, tags=["Produtos"])
app.include_router(fornecedores_router, prefix=settings.API_V1_STR, tags=["Fornecedores"])
app.include_router(generation_router, prefix=settings.API_V1_STR, tags=["Geração de Conteúdo IA"])
app.include_router(web_enrichment_router, prefix=settings.API_V1_STR, tags=["Enriquecimento Web"])
app.include_router(uploads_router, prefix=settings.API_V1_STR, tags=["Uploads de Arquivos"])
app.include_router(product_types_router, prefix=settings.API_V1_STR, tags=["Tipos de Produto e Templates"])
app.include_router(uso_ia_router, prefix=settings.API_V1_STR, tags=["Registro de Uso de IA"])
app.include_router(password_recovery_router, prefix=settings.API_V1_STR, tags=["Recuperação de Senha"])
app.include_router(admin_analytics_router, prefix=settings.API_V1_STR + "/admin/analytics", tags=["Analytics (Admin)"])

@app.get("/", tags=["Raiz"])
async def root():
    return {"message": f"Bem-vindo à API do {settings.PROJECT_NAME}!"}

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
async def health_check():
    return {"status": "ok"}
