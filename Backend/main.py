# Backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List, Optional, Any
import json
import traceback

import models
import schemas
import crud
from auth import router as auth_router_direct
from database import SessionLocal, engine, get_db
from core.config import settings
# from core import email_utils # Comentado se não estiver sendo usado diretamente neste arquivo

# Importa os routers da subpasta 'routers'
from routers import (
    produtos as produtos_router,
    fornecedores as fornecedores_router,
    generation as generation_router,
    web_enrichment as web_enrichment_router,
    uploads as uploads_router,
    product_types as product_types_router,
    uso_ia as uso_ia_router,
    password_recovery as password_recovery_router,
    admin_analytics as admin_analytics_router,
    social_auth as social_auth_router
)

try:
    print("INFO:     Tentando criar tabelas no banco de dados (models.Base.metadata.create_all)...")
    models.Base.metadata.create_all(bind=engine)
    print("INFO:     Criação/verificação de tabelas concluída.")
except Exception as e:
    print(f"ERRO: Falha ao criar/verificar tabelas: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="API para o sistema TDAI - Ferramenta de Descrição Assistida por IA.",
)

# --- INÍCIO DA SEÇÃO CORS MODIFICADA E REVISADA ---
# Configuração do CORS
exact_frontend_origin = "http://localhost:5173" # Origem exata do frontend como o navegador envia

# Lista de origens padrão, garantindo a inclusão da origem exata do frontend
# e outras variações comuns para desenvolvimento local.
default_cors_origins_list = [
    exact_frontend_origin,           # Ex: "http://localhost:5173"
    "http://127.0.0.1:5173",         # Equivalente comum para localhost
    exact_frontend_origin + "/",     # Com barra no final, por segurança: "http://localhost:5173/"
    "http://127.0.0.1:5173/",        # Equivalente com barra
    "http://localhost",              # Se você acessar o frontend por aqui diretamente em algum caso raro
    "http://127.0.0.1",              # (Menos comum para frontend Vite em dev)
]

current_allowed_origins = []

try:
    # settings.BACKEND_CORS_ORIGINS é List[AnyHttpUrl] carregada de core.config.py
    if hasattr(settings, 'BACKEND_CORS_ORIGINS') and settings.BACKEND_CORS_ORIGINS:
        # Processa as origens vindas das configurações (já são AnyHttpUrl)
        # Normaliza para strings e remove duplicatas potenciais após normalização
        normalized_env_origins = set()
        for origin_obj in settings.BACKEND_CORS_ORIGINS:
            origin_str = str(origin_obj)
            normalized_env_origins.add(origin_str.rstrip('/')) # Adiciona sem barra
            normalized_env_origins.add(origin_str)             # Adiciona com barra (se houver)

        if not normalized_env_origins:
            current_allowed_origins = list(default_cors_origins_list) # Usa cópia da lista padrão
            print("AVISO: settings.BACKEND_CORS_ORIGINS estava definido mas resultou em conjunto vazio após normalização. Usando CORS origins padrão.")
        else:
            current_allowed_origins = sorted(list(normalized_env_origins))
            print(f"INFO: Usando CORS origins de settings (normalizados): {current_allowed_origins}")
            # Garante que a origem exata do frontend (sem barra) e os padrões estejam lá,
            # caso o .env não os tenha ou os tenha de forma diferente.
            for default_org in default_cors_origins_list:
                if default_org not in current_allowed_origins:
                    current_allowed_origins.append(default_org)
            current_allowed_origins = sorted(list(set(current_allowed_origins))) # Remove duplicatas e ordena

    else: # Se BACKEND_CORS_ORIGINS não estiver definido ou for vazio em settings
        current_allowed_origins = list(default_cors_origins_list) # Usa cópia da lista padrão
        print("INFO: settings.BACKEND_CORS_ORIGINS não definido ou vazio. Usando CORS origins padrão.")

except AttributeError: # Se o atributo BACKEND_CORS_ORIGINS não existir em settings
    current_allowed_origins = list(default_cors_origins_list) # Usa cópia da lista padrão
    print("AVISO: Atributo settings.BACKEND_CORS_ORIGINS não encontrado em settings. Usando CORS origins padrão.")
except Exception as e_cors_setup: # Capturar outros erros inesperados na configuração
    current_allowed_origins = list(default_cors_origins_list) # Usa cópia da lista padrão
    print(f"ERRO CRÍTICO ao configurar CORS origins a partir de settings: {e_cors_setup}. Usando CORS origins padrão.")

# Garante que a origem exata do frontend (sem barra) esteja na lista final,
# pois é assim que o header Origin geralmente chega.
if exact_frontend_origin not in current_allowed_origins:
    current_allowed_origins.insert(0, exact_frontend_origin) # Adiciona no início se faltar

# Remove duplicatas finais que possam ter sido introduzidas e ordena para consistência no log
final_unique_allowed_origins = sorted(list(set(current_allowed_origins)))

print(f"INFO: Final unique allowed_origins para CORSMiddleware: {final_unique_allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=final_unique_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, PUT, OPTIONS, etc.)
    allow_headers=["*"], # Permite todos os cabeçalhos (Authorization, Content-Type, etc.)
)
# --- FIM DA SEÇÃO CORS MODIFICADA E REVISADA ---


static_files_path = Path(__file__).parent / "static"
if not static_files_path.exists():
    static_files_path.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_files_path), name="static")


@app.on_event("startup")
async def startup_event_create_defaults():
    print("INFO:     Executando evento de startup para criar defaults (roles, planos, admin user, product types)...")
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
                print(f"INFO:     Role '{role.name}' criada.")
            if role.name == "admin":
                admin_role_obj = role
            elif role.name == "user":
                user_role_obj = role
        
        if not admin_role_obj:
            print("ERRO CRÍTICO: Role 'admin' não pôde ser encontrada ou criada. O usuário admin não terá privilégios.")
        if not user_role_obj:
            print("ERRO CRÍTICO: Role 'user' não pôde ser encontrada ou criada. Novos usuários podem ter problemas.")

        # 2. Criação de Planos
        plano_gratuito_data = schemas.PlanoCreate(
            nome="Gratuito",
            descricao="Plano básico gratuito com limitações.",
            preco_mensal=0,
            limite_produtos=settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO,
            limite_enriquecimento_web=settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO,
            limite_geracao_ia=settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO
        )
        plano_pro_data = schemas.PlanoCreate(
            nome="Pro",
            descricao="Plano profissional com mais limites e funcionalidades.",
            preco_mensal=49.90,
            limite_produtos=1000,
            limite_enriquecimento_web=500,
            limite_geracao_ia=1000,
            permite_api_externa=True,
            suporte_prioritario=True
        )

        planos_a_criar = [plano_gratuito_data, plano_pro_data]
        
        admin_plano_obj = None 
        plano_gratuito_obj = None 
        for plano_data in planos_a_criar:
            # FIX: Change 'name=plano_data.nome' to 'nome=plano_data.nome'
            plano = crud.get_plano_by_name(db, nome=plano_data.nome) # This line is the fix
            if not plano:
                plano = crud.create_plano(db, plano=plano_data)
                print(f"INFO:     Plano '{plano.nome}' criado.")
            if plano.nome == "Pro": 
                admin_plano_obj = plano
            if plano.nome == "Gratuito":
                plano_gratuito_obj = plano
        
        if not admin_plano_obj: 
            print("AVISO: Plano 'Pro' não encontrado para o usuário admin. Ele será associado ao plano 'Gratuito' se disponível, ou ficará sem plano.")
            admin_plano_obj = plano_gratuito_obj 
        if not plano_gratuito_obj:
            print("ERRO CRÍTICO: Plano 'Gratuito' não encontrado. Novos usuários podem não ser associados a um plano padrão.")

        # 3. Criação do Usuário Administrador
        admin_user = crud.get_user_by_email(db, email=settings.ADMIN_EMAIL)
        if not admin_user:
            if not admin_role_obj:
                   print(f"ERRO: Não foi possível criar o usuário admin '{settings.ADMIN_EMAIL}' porque o role 'admin' não existe.")
            else:
                user_in_data = {
                    "email": settings.ADMIN_EMAIL,
                    "password": settings.ADMIN_PASSWORD,
                    "nome_completo": "Administrador TDAI",
                    "plano_id": admin_plano_obj.id if admin_plano_obj else None,
                }
                if hasattr(settings, 'ADMIN_IDIOMA_PREFERIDO'):
                    user_in_data['idioma_preferido'] = settings.ADMIN_IDIOMA_PREFERIDO
                
                user_in_create = schemas.UserCreate(**user_in_data) # Renomeado para evitar conflito
                
                created_admin = crud.create_user(db, user=user_in_create, plano_id=user_in_create.plano_id, role_id=admin_role_obj.id)
                
                if created_admin:
                    created_admin.is_superuser = True 
                    db.add(created_admin) 
                    db.commit()
                    db.refresh(created_admin)
                    print(f"INFO:     Usuário administrador '{settings.ADMIN_EMAIL}' criado com sucesso (ID: {created_admin.id}, Superuser: {created_admin.is_superuser}, Role ID: {created_admin.role_id}, Plano ID: {created_admin.plano_id}).")
                else:
                    print(f"ERRO: Falha ao criar o usuário administrador '{settings.ADMIN_EMAIL}'.")
        else:
            print(f"INFO:     Usuário administrador '{settings.ADMIN_EMAIL}' já existe (ID: {admin_user.id}, Superuser: {admin_user.is_superuser}, Role ID: {admin_user.role_id}, Plano ID: {admin_user.plano_id}).")
            needs_update = False
            if admin_role_obj and admin_user.role_id != admin_role_obj.id:
                admin_user.role_id = admin_role_obj.id
                needs_update = True
                print(f"INFO:     Atualizando role do admin '{settings.ADMIN_EMAIL}' para ID {admin_role_obj.id}.")
            if not admin_user.is_superuser:
                admin_user.is_superuser = True
                needs_update = True
                print(f"INFO:     Atualizando admin '{settings.ADMIN_EMAIL}' para superuser.")
            if admin_plano_obj and admin_user.plano_id != admin_plano_obj.id:
                admin_user.plano_id = admin_plano_obj.id
                needs_update = True
                print(f"INFO:     Atualizando plano do admin '{settings.ADMIN_EMAIL}' para ID {admin_plano_obj.id} ({admin_plano_obj.nome}).")

            if needs_update:
                db.commit()
                db.refresh(admin_user)

        # 4. Criar Tipos de Produto e Atributos Padrão (Globais, user_id=None)
        product_types_data = [
            {
                "key_name": "eletronicos",
                "friendly_name": "Eletrônicos",
                "attributes": [
                    {"attribute_key": "marca", "label": "Marca", "field_type": models.AttributeFieldTypeEnum.TEXT, "is_required": True, "display_order": 0, "tooltip_text": "Marca do produto eletrônico"},
                    {"attribute_key": "voltagem", "label": "Voltagem", "field_type": models.AttributeFieldTypeEnum.SELECT, "options": ["110v", "220v", "Bivolt"], "is_required": True, "display_order": 1, "tooltip_text": "Selecione a voltagem"},
                    {"attribute_key": "cor_principal", "label": "Cor Principal", "field_type": models.AttributeFieldTypeEnum.TEXT, "is_required": False, "display_order": 2, "tooltip_text": "Cor predominante do produto"},
                ]
            },
            {
                "key_name": "vestuario",
                "friendly_name": "Vestuário",
                "attributes": [
                    {"attribute_key": "tamanho", "label": "Tamanho", "field_type": models.AttributeFieldTypeEnum.SELECT, "options": ["P", "M", "G", "GG", "XG"], "is_required": True, "display_order": 1, "tooltip_text": "Selecione o tamanho da peça"},
                    {"attribute_key": "cor", "label": "Cor", "field_type": models.AttributeFieldTypeEnum.TEXT, "is_required": True, "display_order": 2, "tooltip_text": "Cor da peça de vestuário"},
                    {"attribute_key": "material", "label": "Material Principal", "field_type": models.AttributeFieldTypeEnum.TEXT, "is_required": False, "display_order": 3, "tooltip_text": "Material principal da confecção"},
                ]
            }
        ]

        for pt_data in product_types_data:
            product_type = db.query(models.ProductType).filter(
                models.ProductType.key_name == pt_data["key_name"],
                models.ProductType.user_id == None 
            ).first()

            if not product_type:
                product_type_create_schema = schemas.ProductTypeCreate(
                    key_name=pt_data["key_name"],
                    friendly_name=pt_data["friendly_name"]
                )
                product_type = crud.create_product_type(db=db, product_type_data=product_type_create_schema, user_id=None)
                print(f"INFO:     Tipo de Produto Global '{product_type.friendly_name}' criado.")

                for attr_data in pt_data["attributes"]:
                    options_json_str = None
                    if "options" in attr_data and attr_data["options"] is not None:
                        options_json_str = json.dumps(attr_data["options"])

                    attribute_template_create_schema = schemas.AttributeTemplateCreate(
                        attribute_key=attr_data["attribute_key"],
                        label=attr_data["label"],
                        field_type=attr_data["field_type"], 
                        is_required=attr_data.get("is_required", False),
                        tooltip_text=attr_data.get("tooltip_text"),
                        default_value=attr_data.get("default_value"),
                        display_order=attr_data.get("display_order", 0),
                        options=options_json_str
                    )
                    crud.create_attribute_template(
                        db=db,
                        attribute_template_data=attribute_template_create_schema,
                        product_type_id=product_type.id
                    )
                    print(f"INFO:       Atributo '{attr_data['label']}' criado para '{product_type.friendly_name}'.")
            else:
                print(f"INFO:     Tipo de Produto Global '{pt_data['friendly_name']}' já existe.")

    except Exception as e_startup:
        print(f"ERRO CRÍTICO durante o evento de startup: {e_startup}")
        print(traceback.format_exc()) 
    finally:
        db.close()
    print("INFO:     Evento de startup para defaults concluído.")


@app.post("/api/v1/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED, tags=["Usuários"])
def create_new_user(
    user_in: schemas.UserCreate, # Renomeado para evitar conflito com admin_user no escopo global
    db: Session = Depends(get_db)
):
    db_user_check = crud.get_user_by_email(db, email=user_in.email) # Renomeado para evitar conflito
    if db_user_check:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuário com este email já existe no sistema.",
        )
    
    plano_id_para_novo_usuario = user_in.plano_id
    # FIX: Change 'name="Gratuito"' to 'nome="Gratuito"'
    plano_gratuito_obj_check = crud.get_plano_by_name(db, nome="Gratuito") # This line is the fix

    if plano_id_para_novo_usuario is None:
        if plano_gratuito_obj_check:
            plano_id_para_novo_usuario = plano_gratuito_obj_check.id
        else: 
            print("ERRO CRÍTICO: Plano padrão 'Gratuito' não encontrado no DB durante a criação de novo usuário sem plano especificado.")
            plano_id_para_novo_usuario = None 


    role_user_check = crud.get_role_by_name(db, name="user") # Renomeado para evitar conflito
    if not role_user_check: 
        print("ERRO CRÍTICO: Role padrão 'user' não encontrado durante a criação de novo usuário.")
        raise HTTPException(status_code=500, detail="Erro de configuração do sistema: Role padrão 'user' não encontrado.")
    role_id_para_novo_usuario = role_user_check.id

    new_user_created = crud.create_user(db=db, user=user_in, plano_id=plano_id_para_novo_usuario, role_id=role_id_para_novo_usuario) # Renomeado para evitar conflito
    return new_user_created


# Inclusão dos routers da aplicação
app.include_router(auth_router_direct, prefix="/api/v1/auth", tags=["Autenticação e Usuários"])
app.include_router(social_auth_router.router, prefix="/api/v1/auth", tags=["Autenticação Social"])

app.include_router(produtos_router.router, prefix="/api/v1", tags=["Produtos"])
app.include_router(fornecedores_router.router, prefix="/api/v1", tags=["Fornecedores"])
app.include_router(generation_router.router, prefix="/api/v1/geracao", tags=["Geração de Conteúdo IA"])
app.include_router(web_enrichment_router.router, prefix="/api/v1/enriquecimento-web", tags=["Enriquecimento Web"])
app.include_router(uploads_router.router, prefix="/api/v1/uploads", tags=["Uploads de Arquivos"])
app.include_router(product_types_router.router, prefix="/api/v1", tags=["Tipos de Produto e Templates"])
app.include_router(uso_ia_router.router, prefix="/api/v1", tags=["Registro de Uso de IA"])
app.include_router(password_recovery_router.router, prefix="/api/v1/auth", tags=["Recuperação de Senha"])
app.include_router(admin_analytics_router.router, prefix="/api/v1/admin/analytics", tags=["Analytics (Admin)"])


@app.get("/", tags=["Raiz"])
async def root():
    return {"message": f"Bem-vindo à API do {settings.PROJECT_NAME}!"}

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
async def health_check():
    return {"status": "ok"}