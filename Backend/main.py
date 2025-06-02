# Backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles 
from sqlalchemy.orm import Session
from pathlib import Path 

import models
import schemas
import crud
# Importa o router diretamente do módulo auth (que agora define 'router')
from auth import router as auth_router_direct 
from database import SessionLocal, engine, get_db 
from core.config import settings 
from core import email_utils 

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost", "http://localhost:5173", "http://127.0.0.1"],
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
    print("INFO:     Executando evento de startup para criar defaults (roles, planos, admin user)...")
    db: Session = SessionLocal()
    try:
        roles_a_criar = [
            {"name": "admin", "description": "Administrador do sistema com acesso total."},
            {"name": "user", "description": "Usuário padrão com acesso às funcionalidades do seu plano."},
        ]
        for role_data in roles_a_criar:
            role = crud.get_role_by_name(db, name=role_data["name"])
            if not role:
                crud.create_role(db, role=schemas.RoleCreate(**role_data))
                print(f"INFO:     Role '{role_data['name']}' criada.")

        planos_a_criar = [
            schemas.PlanoCreate(nome="Gratuito", descricao="Plano básico gratuito com limitações.", preco_mensal=0, limite_produtos=settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO, limite_enriquecimento_web=settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO, limite_geracao_ia=settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO),
            schemas.PlanoCreate(nome="Pro", descricao="Plano profissional com mais limites e funcionalidades.", preco_mensal=49.90, limite_produtos=1000, limite_enriquecimento_web=500, limite_geracao_ia=1000, permite_api_externa=True, suporte_prioritario=True),
        ]
        for plano_data in planos_a_criar:
            plano = crud.get_plano_by_nome(db, nome=plano_data.nome)
            if not plano:
                crud.create_plano(db, plano=plano_data)
                print(f"INFO:     Plano '{plano_data.nome}' criado.")
        
        admin_user = crud.get_user_by_email(db, email=settings.ADMIN_EMAIL)
        if not admin_user:
            admin_plano = crud.get_plano_by_nome(db, nome="Pro") 
            admin_role = crud.get_role_by_name(db, name="admin")

            user_in = schemas.UserCreate( 
                email=settings.ADMIN_EMAIL,
                password=settings.ADMIN_PASSWORD, 
                nome_completo="Administrador TDAI", 
                plano_id=admin_plano.id if admin_plano else None
            )
            created_admin = crud.create_user(db, user=user_in, plano_id=user_in.plano_id, role_id=admin_role.id if admin_role else None)
            if created_admin: 
                created_admin.is_superuser = True
                # Se o modelo User tiver um campo role_id e um relacionamento 'role'
                if admin_role and hasattr(created_admin, 'role_id'):
                    created_admin.role_id = admin_role.id
                db.commit()
                print(f"INFO:     Usuário administrador '{settings.ADMIN_EMAIL}' criado com sucesso.")
    finally:
        db.close()
    print("INFO:     Evento de startup para defaults concluído.")


@app.post("/api/v1/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED, tags=["Usuários"]) 
def create_new_user(
    user_in: schemas.UserCreate, 
    db: Session = Depends(get_db)
):
    db_user = crud.get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuário com este email já existe no sistema.",
        )
    plano_gratuito = crud.get_plano_by_nome(db, nome="Gratuito")
    plano_id_para_novo_usuario = user_in.plano_id 
    if plano_id_para_novo_usuario is None and plano_gratuito: 
        plano_id_para_novo_usuario = plano_gratuito.id
    
    new_user = crud.create_user(db=db, user=user_in, plano_id=plano_id_para_novo_usuario)
    return new_user 


# Inclusão dos routers da aplicação
app.include_router(auth_router_direct, prefix="/api/v1/auth", tags=["Autenticação e Usuários"]) 
app.include_router(social_auth_router.router, prefix="/api/v1/auth", tags=["Autenticação Social"]) # Mantém o mesmo prefixo para /google, /facebook

app.include_router(produtos_router.router, prefix="/api/v1", tags=["Produtos"]) 
app.include_router(fornecedores_router.router, prefix="/api/v1", tags=["Fornecedores"]) 
app.include_router(generation_router.router, prefix="/api/v1/geracao", tags=["Geração de Conteúdo IA"])
app.include_router(web_enrichment_router.router, prefix="/api/v1/enriquecimento-web", tags=["Enriquecimento Web"])
app.include_router(uploads_router.router, prefix="/api/v1/uploads", tags=["Uploads de Arquivos"])
app.include_router(product_types_router.router, prefix="/api/v1", tags=["Tipos de Produto e Templates"]) 
app.include_router(uso_ia_router.router, prefix="/api/v1", tags=["Registro de Uso de IA"]) 
app.include_router(password_recovery_router.router, prefix="/api/v1/auth", tags=["Recuperação de Senha"]) # Mantém o mesmo prefixo
app.include_router(admin_analytics_router.router, prefix="/api/v1/admin/analytics", tags=["Analytics (Admin)"])


@app.get("/", tags=["Raiz"])
async def root():
    return {"message": f"Bem-vindo à API do {settings.PROJECT_NAME}!"}

@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health Check"])
async def health_check():
    return {"status": "ok"}