# tdai_project/Backend/schemas.py
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional, List, Dict, Any, Union
import enum
from datetime import datetime

import models

# --- Role Schemas ---
class RoleBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = Field(None, max_length=255)

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    id: int

    class Config:
        from_attributes = True

# --- Plano Schemas ---
class PlanoBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    max_descricoes_mes: Optional[int] = Field(0, ge=0)
    max_titulos_mes: Optional[int] = Field(0, ge=0)

class PlanoCreate(PlanoBase):
    pass

class Plano(PlanoBase):
    id: int

    class Config:
        from_attributes = True

# --- Fornecedor Schemas ---
class FornecedorBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=100)
    site_url: Optional[HttpUrl] = None
    catalogo_pdf_path: Optional[str] = Field(None, max_length=255)
    link_busca_padrao: Optional[HttpUrl] = None

class FornecedorCreate(FornecedorBase):
    pass

class FornecedorUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    site_url: Optional[HttpUrl] = Field(None)
    catalogo_pdf_path: Optional[str] = Field(None, max_length=255)
    link_busca_padrao: Optional[HttpUrl] = Field(None)

class Fornecedor(FornecedorBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class FornecedorPage(BaseModel):
    items: List[Fornecedor]
    total_items: int
    limit: int
    skip: int

    class Config:
        from_attributes = True

# --- Produto Schemas ---
class ProdutoBase(BaseModel):
    nome_base: str = Field(..., min_length=1, max_length=255, description="Nome principal ou SKU do produto.")
    marca: Optional[str] = Field(None, max_length=100)
    categoria_original: Optional[str] = Field(None, max_length=100)
    dados_brutos: Optional[Dict[str, Any]] = Field(None, description="Dados originais ou enriquecidos de várias fontes.")

class ProdutoCreate(ProdutoBase):
    fornecedor_id: Optional[int] = None

class ProdutoUpdate(BaseModel):
    nome_base: Optional[str] = Field(None, min_length=1, max_length=255)
    marca: Optional[str] = Field(None, max_length=100)
    categoria_original: Optional[str] = Field(None, max_length=100)
    dados_brutos: Optional[Dict[str, Any]] = None
    descricao_principal_gerada: Optional[str] = None
    titulos_sugeridos: Optional[Dict[str, str]] = None
    fornecedor_id: Optional[int] = None
    status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum] = None
    log_enriquecimento_web: Optional[Dict[str, Any]] = None

class Produto(ProdutoBase):
    id: int
    user_id: int
    fornecedor: Optional[Fornecedor] = None
    descricao_principal_gerada: Optional[str] = None
    titulos_sugeridos: Optional[Dict[str, str]] = None
    status_enriquecimento_web: models.StatusEnriquecimentoEnum
    log_enriquecimento_web: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        use_enum_values = True

class ProdutoPage(BaseModel):
    items: List[Produto]
    total_items: int
    limit: int
    skip: int

    class Config:
        from_attributes = True

# --- UsoIA Schemas ---
class UsoIABase(BaseModel):
    tipo_geracao: str = Field(..., max_length=50)
    modelo_ia_usado: str = Field(..., max_length=50)
    prompt_utilizado: Optional[str] = None
    resultado_gerado: Optional[str] = None
    custo_aproximado_tokens: Optional[int] = Field(None, ge=0)

class UsoIACreate(UsoIABase):
    produto_id: Optional[int] = None

class UsoIA(UsoIABase):
    id: int
    user_id: int
    produto_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# NOVO SCHEMA ADICIONADO AQUI
class UsoIAPage(BaseModel):
    items: List[UsoIA]
    total_items: int
    limit: int
    skip: int

    class Config:
        from_attributes = True

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    nome: Optional[str] = Field(None, max_length=100)
    idioma_preferido: Optional[str] = Field("pt", max_length=10)
    chave_openai_pessoal: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nome: Optional[str] = Field(None, max_length=100)
    idioma_preferido: Optional[str] = Field(None, max_length=10)
    chave_openai_pessoal: Optional[str] = Field(None, max_length=100, description="Deixe em branco para não alterar. Envie string vazia para remover.")

class UserUpdatePassword(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=100)

class UserUpdateByAdmin(UserBase):
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    plano_id: Optional[int] = None
    role_id: Optional[int] = None

class User(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    plano: Optional[Plano] = None
    role: Optional[Role] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Token Schemas (para JWT) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Password Recovery Schemas ---
class PasswordRecoveryRequest(BaseModel):
    email: EmailStr = Field(..., description="Email do usuário para recuperação de senha.")

class PasswordResetRequest(BaseModel):
    token: str = Field(..., description="Token de reset recebido pelo usuário.")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nova senha, mínimo de 8 caracteres.")

class Msg(BaseModel):
    message: str

# --- File Upload and Processing Schemas ---
class FileProcessDetail(BaseModel):
    filename: str
    content_type: str
    status: str
    produtos_encontrados: int = 0
    mensagem: Optional[str] = None
    dados_extraidos: Optional[List[Dict[str, Any]]] = Field(None, exclude=True)

class FileProcessResponse(BaseModel):
    message: str
    details: List[FileProcessDetail] = []

# --- Admin Analytics Schemas ---
class TotalCounts(BaseModel):
    total_users: int
    total_produtos: int
    total_fornecedores: int
    total_usos_ia: int

class UsoIAPorPlano(BaseModel):
    plano_nome: Optional[str] = "Não atribuído"
    total_usos: int

class UsoIAPorTipo(BaseModel):
    tipo_geracao: str
    total_usos: int

class UserActivity(BaseModel):
    user_id: int
    user_email: EmailStr
    usos_ia_mes_corrente: int
    plano_nome: Optional[str] = "Não atribuído"