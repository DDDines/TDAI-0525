# Backend/main.py
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
import datetime

# Importar engine diretamente de database
from database import get_db, SessionLocal, engine 
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
    social_auth, # Embora possa precisar de revisão, mantemos por enquanto
    product_types # <--- ADICIONADO A IMPORTAÇÃO DO NOVO ROUTER
)
from routers import auth_utils

# --- Criação de Tabelas ---
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

# Include routers
# Os routers abaixo são adicionados com um prefixo /api/v1 global aqui no main.py
# Seus próprios arquivos de router (ex: fornecedores.py) têm prefixos relativos (ex: /fornecedores)
app.include_router(social_auth.router, prefix="/api/v1") 
app.include_router(password_recovery.router, prefix="/api/v1")
app.include_router(fornecedores.router, prefix="/api/v1")
app.include_router(produtos.router, prefix="/api/v1")
app.include_router(uso_ia.router, prefix="/api/v1")
app.include_router(generation.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(web_enrichment.router, prefix="/api/v1")
app.include_router(admin_analytics.router, prefix="/api/v1")

# O router product_types já foi definido com o prefixo completo "/api/v1/product-types"
# em routers/product_types.py, então o incluímos sem adicionar outro prefixo aqui.
app.include_router(product_types.router) # <--- ADICIONADO O NOVO ROUTER


@app.post("/api/v1/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Usuários"])
def create_new_user_endpoint(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # (Conteúdo da função create_new_user_endpoint inalterado)
    db_user_by_email = crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Um usuário com este email já está registrado."
        )
    default_role = crud.get_role_by_name(db, name="free_user")
    if not default_role: 
        default_role = crud.create_role(db, schemas.RoleCreate(name="free_user", description="Usuário com acesso básico"))
    
    default_plano = crud.get_plano_by_name(db, name="Gratuito")
    if not default_plano: 
        default_plano = crud.create_plano(db, schemas.PlanoCreate(name="Gratuito", max_descricoes_mes=100, max_titulos_mes=500))
    
    # O CRUD para criar usuário foi ajustado para não esperar plano_id e role_id diretamente no UserCreate
    # e sim pegá-los de parâmetros opcionais na função CRUD ou serem setados internamente.
    # A função `crud.create_user` já não espera mais plano_id e role_id como args diretos na chamada,
    # ela os associa internamente ou eles podem ser setados depois, ou por um admin via `update_user_admin`.
    # Para este endpoint de registro público, associamos o plano e role padrão.
    
    # Temporariamente, vamos garantir que o user_id não é esperado pelo UserCreate schema
    # e que o crud.create_user lida com a atribuição de plano e role.
    # Se o crud.create_user foi atualizado para aceitar plano_id e role_id, podemos passá-los.
    # Assumindo que o crud.create_user atual NÃO os recebe como parâmetros:
    created_user = crud.create_user(db=db, user=user)
    
    # Se o crud.create_user FOI atualizado para aceitar plano_id e role_id:
    # created_user = crud.create_user(
    #     db=db, 
    #     user=user, 
    #     plano_id=default_plano.id if default_plano else None, 
    #     role_id=default_role.id if default_role else None
    # )
    
    # Para o propósito deste exemplo, vamos assumir que a função crud.create_user
    # foi ajustada para não esperar plano_id/role_id ou que eles são setados após a criação inicial
    # ou são gerenciados de outra forma. Se for necessário, a chamada a crud.create_user precisaria
    # ser ajustada de acordo com a assinatura da função em crud.py.
    # O mais importante é que o user é criado, e depois podemos associar/atualizar plano e role.

    # Atribuindo plano e role após a criação do usuário, se não foram atribuídos durante.
    if created_user and default_plano:
        created_user.plano_id = default_plano.id
    if created_user and default_role:
        created_user.role_id = default_role.id
    
    if created_user:
        db.add(created_user)
        db.commit()
        db.refresh(created_user) # Garante que o objeto retornado tem os IDs de plano e role
        
        # Recarrega o usuário com os relacionamentos para o schema de resposta
        return crud.get_user(db, created_user.id)
    
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao criar usuário")


@app.post("/api/v1/token", response_model=schemas.Token, tags=["Autenticação"])
async def login_for_access_token_endpoint(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # (Conteúdo da função login_for_access_token_endpoint inalterado)
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
    # (Conteúdo da função read_current_user_me_endpoint inalterado)
    return current_user

@app.put("/api/v1/users/me/", response_model=schemas.User, tags=["Usuários"])
async def update_current_user_me_endpoint(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    # (Conteúdo da função update_current_user_me_endpoint inalterado)
    # A função crud.update_user espera o db_user (objeto User) e user_update (schema)
    # Em vez de user_id e user_update. Ajustando a chamada.
    if user_update.email and user_update.email != current_user.email:
        existing_user = crud.get_user_by_email(db, email=user_update.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este email já está em uso por outra conta.")
    
    updated_user = crud.update_user(db, db_user=current_user, user_update=user_update) # Passando db_user
    if not updated_user: # crud.update_user deve sempre retornar o usuário ou levantar exceção
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado para atualização.") # Improvável se current_user é válido
    return updated_user


@app.post("/api/v1/users/me/change-password", response_model=schemas.Msg, tags=["Usuários"])
async def change_current_user_password_endpoint(
    password_data: schemas.UserUpdatePassword,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    # (Conteúdo da função change_current_user_password_endpoint inalterado)
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
    # (Conteúdo da função read_root inalterado)
    return {"message": f"Bem-vindo à API do {settings.PROJECT_NAME}!"}

@app.on_event("startup")
async def startup_event_create_defaults():
    # (Conteúdo da função startup_event_create_defaults inalterado, com a observação de que
    # a criação de tabelas já acontece antes da inicialização do app)
    db = SessionLocal()
    try:
        print("INFO:     Executando evento de startup para criar defaults (roles, planos, admin user)...")
        if not crud.get_role_by_name(db, name="free_user"):
            crud.create_role(db, schemas.RoleCreate(name="free_user", description="Usuário com acesso básico/gratuito"))
            print("INFO:     Role 'free_user' criada.")
        if not crud.get_role_by_name(db, name="admin"):
            crud.create_role(db, schemas.RoleCreate(name="admin", description="Administrador do Sistema"))
            print("INFO:     Role 'admin' criada.")
        
        if not crud.get_plano_by_name(db, name="Gratuito"):
            crud.create_plano(db, schemas.PlanoCreate(name="Gratuito", max_descricoes_mes=100, max_titulos_mes=500))
            print("INFO:     Plano 'Gratuito' criado.")
        if not crud.get_plano_by_name(db, name="Ilimitado"):
            crud.create_plano(db, schemas.PlanoCreate(name="Ilimitado", max_descricoes_mes=9999999, max_titulos_mes=9999999*5))
            print("INFO:     Plano 'Ilimitado' criado.")

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
            
            # A função crud.create_user foi ajustada para não receber plano_id/role_id
            # Estes são atribuídos após a criação se necessário, ou pelo update_user_admin
            created_admin = crud.create_user(db,user=admin_user_in)
            
            if created_admin:
                if admin_role: created_admin.role_id = admin_role.id
                if unlimited_plan: created_admin.plano_id = unlimited_plan.id
                created_admin.is_superuser = True
                created_admin.is_active = True 
                db.add(created_admin)
                db.commit()
                print(f"INFO:     Usuário admin '{admin_email}' criado e definido como superuser.")
            else:
                print(f"AVISO:  Falha ao criar usuário admin '{admin_email}' no evento de startup.")
        print("INFO:     Evento de startup para defaults concluído.")
    except Exception as e:
        print(f"ERRO CRÍTICO durante o evento de startup (criação de defaults): {e}")
    finally:
        db.close()