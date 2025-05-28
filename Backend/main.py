import os
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta, timezone # Adicionado timezone
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware

import models
import schemas
import crud
import auth 

# Importar engine diretamente de database
from database import get_db, SessionLocal, engine # << ADICIONADO 'engine' AQUI
from core.config import settings, pwd_context 

from routers import (
    fornecedores,
    produtos,
    password_recovery,
    uso_ia,
    generation,
    uploads,
    web_enrichment,
    admin_analytics,
    social_auth # Embora possa precisar de revisão, mantemos por enquanto
)
from routers import auth_utils

# --- Criação de Tabelas ---
# Esta linha irá criar todas as tabelas definidas em models.py que ainda não existem no banco de dados
# quando a aplicação é carregada pela primeira vez (ou quando esta linha é executada).
# Como apagaste a tabela 'produtos', ela será recriada agora.
try:
    print("INFO:     Tentando criar tabelas no banco de dados (models.Base.metadata.create_all)...")
    models.Base.metadata.create_all(bind=engine)
    print("INFO:     Criação/verificação de tabelas concluída.")
except Exception as e:
    print(f"ERRO CRÍTICO ao tentar criar tabelas com models.Base.metadata.create_all: {e}")
    # Considerar levantar a exceção aqui ou sair se a criação de tabelas for absolutamente crítica para o arranque.
    # raise

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="TDAI - Sistema Inteligente de Geração de Títulos e Descrições para Produtos de E-commerce.",
    openapi_url="/api/v1/openapi.json"
)

origins = [
    settings.FRONTEND_URL,
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY or "uma_chave_secreta_para_sessoes_muito_segura_se_a_outra_nao_estiver_setada"
)

# Include routers (API v1 prefix)
app.include_router(social_auth.router, prefix="/api/v1") # Mantido, mas notar que precisa de revisão
app.include_router(password_recovery.router, prefix="/api/v1")
app.include_router(fornecedores.router, prefix="/api/v1")
app.include_router(produtos.router, prefix="/api/v1")
app.include_router(uso_ia.router, prefix="/api/v1")
app.include_router(generation.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(web_enrichment.router, prefix="/api/v1")
app.include_router(admin_analytics.router, prefix="/api/v1")


@app.post("/api/v1/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Usuários"])
def create_new_user_endpoint(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuário com este email já está registrado."
        )
    default_role = crud.get_role_by_name(db, name="free_user")
    if not default_role: # Deveria ter sido criado no startup_event, mas como fallback
        default_role = crud.create_role(db, schemas.RoleCreate(name="free_user", description="Usuário com acesso básico"))
    
    default_plano = crud.get_plano_by_name(db, name="Gratuito")
    if not default_plano: # Deveria ter sido criado no startup_event
        default_plano = crud.create_plano(db, schemas.PlanoCreate(name="Gratuito", max_descricoes_mes=100, max_titulos_mes=500))
    
    return crud.create_user(
        db=db,
        user=user,
        plano_id=default_plano.id if default_plano else None,
        role_id=default_role.id if default_role else None
    )

@app.post("/api/v1/token", response_model=schemas.Token, tags=["Autenticação"])
async def login_for_access_token_endpoint(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user_auth_obj = auth.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user_auth_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user_auth_obj.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo.")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user_auth_obj.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/users/me/", response_model=schemas.User, tags=["Usuários"])
async def read_current_user_me_endpoint(current_user: models.User = Depends(auth_utils.get_current_active_user)):
    return current_user

@app.put("/api/v1/users/me/", response_model=schemas.User, tags=["Usuários"])
async def update_current_user_me_endpoint(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    if user_update.email and user_update.email != current_user.email:
        existing_user = crud.get_user_by_email(db, email=user_update.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este email já está em uso por outra conta.")
    
    updated_user = crud.update_user(db, user_id=current_user.id, user_update=user_update)
    if not updated_user:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado para atualização.")
    return updated_user

@app.post("/api/v1/users/me/change-password", response_model=schemas.Msg, tags=["Usuários"])
async def change_current_user_password_endpoint(
    password_data: schemas.UserUpdatePassword,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    if not auth.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")
    
    new_hashed_password = auth.get_password_hash(password_data.new_password)
    current_user.hashed_password = new_hashed_password
    current_user.updated_at = datetime.now(timezone.utc) 
    db.add(current_user)
    db.commit()
    return {"message": "Senha alterada com sucesso."}


@app.get("/api/v1/", tags=["Root"])
async def read_root():
    return {"message": f"Bem-vindo à API do {settings.PROJECT_NAME}!"}

@app.on_event("startup")
async def startup_event_create_defaults():
    # A criação das tabelas (models.Base.metadata.create_all) já foi movida para ser executada
    # no nível do módulo, ANTES da instanciação do app FastAPI.
    # Manteremos este evento de startup para criar roles, planos e o admin user,
    # assumindo que as tabelas já existem ou foram criadas.
    
    db = SessionLocal()
    try:
        print("INFO:     Executando evento de startup para criar defaults (roles, planos, admin user)...")
        # Verifica e cria roles
        if not crud.get_role_by_name(db, name="free_user"):
            crud.create_role(db, schemas.RoleCreate(name="free_user", description="Usuário com acesso básico/gratuito"))
            print("INFO:     Role 'free_user' criada.")
        if not crud.get_role_by_name(db, name="admin"):
            crud.create_role(db, schemas.RoleCreate(name="admin", description="Administrador do Sistema"))
            print("INFO:     Role 'admin' criada.")
        
        # Verifica e cria planos
        if not crud.get_plano_by_name(db, name="Gratuito"):
            crud.create_plano(db, schemas.PlanoCreate(name="Gratuito", max_descricoes_mes=100, max_titulos_mes=500))
            print("INFO:     Plano 'Gratuito' criado.")
        if not crud.get_plano_by_name(db, name="Ilimitado"):
            crud.create_plano(db, schemas.PlanoCreate(name="Ilimitado", max_descricoes_mes=9999999, max_titulos_mes=9999999*5)) # Usando valor grande para "ilimitado"
            print("INFO:     Plano 'Ilimitado' criado.")

        # Verifica e cria usuário admin
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "adminpassword")

        if admin_email and admin_password and not crud.get_user_by_email(db, email=admin_email):
            admin_user_in = schemas.UserCreate(
                email=admin_email,
                password=admin_password,
                nome="Admin TDAI"
            )
            admin_role = crud.get_role_by_name(db, name="admin")
            unlimited_plan = crud.get_plano_by_name(db, name="Ilimitado")
            
            created_admin = crud.create_user(
                db,
                user=admin_user_in,
                plano_id=unlimited_plan.id if unlimited_plan else None,
                role_id=admin_role.id if admin_role else None
            )
            # Torna o usuário admin um superusuário
            if created_admin:
                created_admin.is_superuser = True
                created_admin.is_active = True # Garante que está ativo
                db.add(created_admin)
                db.commit()
                print(f"INFO:     Usuário admin '{admin_email}' criado e definido como superuser.")
            else:
                print(f"AVISO:  Falha ao criar usuário admin '{admin_email}' no evento de startup.")
        print("INFO:     Evento de startup para defaults concluído.")
    except Exception as e:
        print(f"ERRO CRÍTICO durante o evento de startup (criação de defaults): {e}")
        # Considerar o que fazer aqui - se for um erro de DB não disponível, a app pode não funcionar.
    finally:
        db.close()