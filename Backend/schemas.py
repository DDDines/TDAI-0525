# Backend/schemas.py
from pydantic import BaseModel, EmailStr, HttpUrl, Field, Json
from typing import Optional, List, Dict, Any 
from datetime import datetime
import enum 

from models import StatusEnriquecimentoEnum, StatusGeracaoIAEnum, AttributeFieldTypeEnum 

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None 
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None 
    # scopes: List[str] = []

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    nome_completo: Optional[str] = Field(None, max_length=100) 
    idioma_preferido: Optional[str] = Field(None, max_length=10) 
    chave_openai_pessoal: Optional[str] = Field(None, max_length=255)
    chave_google_gemini_pessoal: Optional[str] = Field(None, max_length=255) 

class UserCreate(UserBase): 
    password: str = Field(..., min_length=8)
    plano_id: Optional[int] = None 

class UserCreateOAuth(UserBase):
    provider: str
    provider_user_id: str

class UserUpdate(UserBase): 
    password: Optional[str] = Field(None, min_length=8) 
    nome_completo: Optional[str] = Field(None, max_length=100)
    idioma_preferido: Optional[str] = Field(None, max_length=10)
    chave_openai_pessoal: Optional[str] = Field(None, max_length=255)
    chave_google_gemini_pessoal: Optional[str] = Field(None, max_length=255)
    plano_id: Optional[int] = None 

    class Config:
        from_attributes = True 

class UserUpdateOAuth(BaseModel): 
    nome_completo: Optional[str] = Field(None, max_length=100)
    idioma_preferido: Optional[str] = Field(None, max_length=10)
    chave_openai_pessoal: Optional[str] = Field(None, max_length=255)
    chave_google_gemini_pessoal: Optional[str] = Field(None, max_length=255)
    plano_id: Optional[int] = None

    class Config:
        from_attributes = True

class UserUpdateByAdmin(UserUpdate): 
    email: Optional[EmailStr] = None 
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    plano_id: Optional[int] = None
    limite_produtos: Optional[int] = None
    limite_enriquecimento_web: Optional[int] = None
    limite_geracao_ia: Optional[int] = None
    data_expiracao_plano: Optional[datetime] = None

class UserResponse(UserBase): 
    id: int
    is_active: bool
    is_superuser: bool
    plano_id: Optional[int] = None
    limite_produtos: Optional[int] = None
    limite_enriquecimento_web: Optional[int] = None
    limite_geracao_ia: Optional[int] = None
    data_expiracao_plano: Optional[datetime] = None
    provider: Optional[str] = None
    # created_at: datetime 
    # updated_at: Optional[datetime] = None 

    class Config:
        from_attributes = True

class UserCreateComPlano(UserCreate): 
    plano_id: Optional[int] = None 
    # is_superuser: bool = False 


# --- Role Schemas ---
class RoleBase(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: int
    class Config:
        from_attributes = True

# --- Plano Schemas ---
class PlanoBase(BaseModel):
    nome: str = Field(..., max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    preco_mensal: float = Field(..., ge=0)
    limite_produtos: int = Field(..., ge=0)
    limite_enriquecimento_web: int = Field(..., ge=0)
    limite_geracao_ia: int = Field(..., ge=0)
    permite_api_externa: bool = False
    suporte_prioritario: bool = False

class PlanoCreate(PlanoBase):
    pass

class PlanoUpdate(BaseModel): 
    nome: Optional[str] = Field(None, max_length=100)
    descricao: Optional[str] = Field(None, max_length=500)
    preco_mensal: Optional[float] = Field(None, ge=0)
    limite_produtos: Optional[int] = Field(None, ge=0)
    limite_enriquecimento_web: Optional[int] = Field(None, ge=0)
    limite_geracao_ia: Optional[int] = Field(None, ge=0)
    permite_api_externa: Optional[bool] = None
    suporte_prioritario: Optional[bool] = None

class PlanoResponse(PlanoBase):
    id: int
    class Config:
        from_attributes = True


# --- Fornecedor Schemas ---
class FornecedorBase(BaseModel):
    nome: str = Field(..., max_length=150)
    contato: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = Field(None, max_length=255)
    site_url: Optional[HttpUrl] = None
    link_busca_padrao: Optional[HttpUrl] = None 

class FornecedorCreate(FornecedorBase):
    pass

class FornecedorUpdate(BaseModel): 
    nome: Optional[str] = Field(None, max_length=150)
    contato: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = Field(None, max_length=255)
    site_url: Optional[HttpUrl] = None
    link_busca_padrao: Optional[HttpUrl] = None

class FornecedorResponse(FornecedorBase):
    id: int
    user_id: int 
    # created_at: datetime 
    # updated_at: Optional[datetime] = None 

    class Config:
        from_attributes = True

class FornecedorPage(BaseModel): 
    items: List[FornecedorResponse]
    total_items: int
    page: int
    limit: int


# --- AttributeTemplate Schemas ---
class AttributeTemplateBase(BaseModel):
    attribute_key: str = Field(..., max_length=100, description="Chave única do atributo (ex: 'cor', 'tamanho_tela')")
    label: str = Field(..., max_length=150, description="Rótulo amigável para exibição (ex: 'Cor Principal', 'Tamanho da Tela (polegadas)')")
    field_type: AttributeFieldTypeEnum = Field(..., description="Tipo de campo (text, number, boolean, select, multiselect, date, textarea)")
    options: Optional[str] = Field(None, description="JSON string para field_type 'select' ou 'multiselect', ex: '[\"110V\", \"220V\"]' ou '[{\"value\": \"110\", \"label\": \"110V\"}]'")
    is_required: bool = False
    tooltip_text: Optional[str] = Field(None, max_length=255, description="Texto de ajuda exibido como tooltip")
    default_value: Optional[str] = Field(None, max_length=255, description="Valor padrão para o atributo")
    display_order: int = Field(0, description="Ordem de exibição do atributo no formulário")

class AttributeTemplateCreate(AttributeTemplateBase):
    pass 

class AttributeTemplateUpdate(BaseModel): 
    attribute_key: Optional[str] = Field(None, max_length=100)
    label: Optional[str] = Field(None, max_length=150)
    field_type: Optional[AttributeFieldTypeEnum] = None
    options: Optional[str] = None
    is_required: Optional[bool] = None
    tooltip_text: Optional[str] = Field(None, max_length=255)
    default_value: Optional[str] = Field(None, max_length=255)
    display_order: Optional[int] = None

class AttributeTemplateResponse(AttributeTemplateBase):
    id: int
    product_type_id: int 

    class Config:
        from_attributes = True


# --- ProductType Schemas ---
class ProductTypeBase(BaseModel):
    key_name: str = Field(..., max_length=100, description="Chave única para o tipo de produto (ex: 'eletronicos', 'vestuario_adulto_masculino')")
    friendly_name: str = Field(..., max_length=150, description="Nome amigável para exibição (ex: 'Eletrônicos', 'Vestuário Adulto Masculino')")

class ProductTypeCreate(ProductTypeBase):
    pass

class ProductTypeUpdate(BaseModel): 
    key_name: Optional[str] = Field(None, max_length=100)
    friendly_name: Optional[str] = Field(None, max_length=150)

class ProductTypeResponse(ProductTypeBase):
    id: int
    user_id: Optional[int] = None 
    attribute_templates: List[AttributeTemplateResponse] = []

    class Config:
        from_attributes = True

class ProductTypePage(BaseModel): 
    items: List[ProductTypeResponse]
    total_items: int
    page: int
    limit: int

# --- Produto Schemas ---
class ProdutoBase(BaseModel):
    nome_base: str = Field(..., max_length=255, description="Nome principal ou base do produto") 
    nome_chat_api: Optional[str] = Field(None, max_length=255, description="Nome otimizado/alternativo para IA ou exibição")
    descricao_original: Optional[str] = Field(None, description="Descrição original detalhada do produto")
    descricao_chat_api: Optional[str] = Field(None, description="Descrição otimizada/alternativa pela IA")
    
    sku: Optional[str] = Field(None, max_length=100) 
    ean: Optional[str] = Field(None, max_length=100) 
    ncm: Optional[str] = Field(None, max_length=20)  
    
    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    categoria_original: Optional[str] = Field(None, max_length=150, description="Categoria original informada")
    tags: Optional[str] = Field(None, description="Palavras-chave ou tags, separadas por vírgula ou JSON string array") 
    
    preco_custo: Optional[float] = Field(None, ge=0) 
    preco_venda: Optional[float] = Field(None, ge=0)
    margem_lucro: Optional[float] = Field(None, description="Margem de lucro percentual ou absoluta")
    estoque_disponivel: Optional[int] = Field(None, ge=0)
    
    peso_kg: Optional[float] = Field(None, ge=0)
    altura_cm: Optional[float] = Field(None, ge=0)
    largura_cm: Optional[float] = Field(None, ge=0)
    profundidade_cm: Optional[float] = Field(None, ge=0)
    
    imagem_principal_url: Optional[HttpUrl] = Field(None, description="URL da imagem principal do produto") 
    link_referencia_fornecedor: Optional[HttpUrl] = Field(None, description="Link para a página do produto no fornecedor")
    
    fornecedor_id: Optional[int] = None
    product_type_id: Optional[int] = None

    dynamic_attributes: Optional[Json[Dict[str, Any]]] = Field(None, description="Atributos dinâmicos como JSON string")


class ProdutoCreate(ProdutoBase):
    pass

class ProdutoUpdate(BaseModel): 
    nome_base: Optional[str] = Field(None, max_length=255)
    nome_chat_api: Optional[str] = Field(None, max_length=255)
    descricao_original: Optional[str] = None
    descricao_chat_api: Optional[str] = None
    sku: Optional[str] = Field(None, max_length=100)
    ean: Optional[str] = Field(None, max_length=100)
    ncm: Optional[str] = Field(None, max_length=20)
    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    categoria_original: Optional[str] = Field(None, max_length=150)
    tags: Optional[str] = None
    preco_custo: Optional[float] = Field(None, ge=0)
    preco_venda: Optional[float] = Field(None, ge=0)
    margem_lucro: Optional[float] = None
    estoque_disponivel: Optional[int] = Field(None, ge=0)
    peso_kg: Optional[float] = Field(None, ge=0)
    altura_cm: Optional[float] = Field(None, ge=0)
    largura_cm: Optional[float] = Field(None, ge=0)
    profundidade_cm: Optional[float] = Field(None, ge=0)
    imagem_principal_url: Optional[HttpUrl] = None
    link_referencia_fornecedor: Optional[HttpUrl] = None
    fornecedor_id: Optional[int] = None
    product_type_id: Optional[int] = None
    dynamic_attributes: Optional[Json[Dict[str, Any]]] = None

    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None
    status_titulo_ia: Optional[StatusGeracaoIAEnum] = None
    status_descricao_ia: Optional[StatusGeracaoIAEnum] = None


class ProdutoResponse(ProdutoBase):
    id: int
    user_id: int
    data_criacao: datetime
    data_atualizacao: datetime
    status_enriquecimento_web: StatusEnriquecimentoEnum
    status_titulo_ia: StatusGeracaoIAEnum
    status_descricao_ia: StatusGeracaoIAEnum

    class Config:
        from_attributes = True


class ProdutoPage(BaseModel): 
    items: List[ProdutoResponse]
    total_items: int
    page: int
    limit: int


# --- Schemas para Geração IA e Enriquecimento Web (Ações) ---
class GeracaoRequestBase(BaseModel):
    produto_id: int
    idioma_saida: Optional[str] = Field("pt-BR", description="Idioma desejado para a saída gerada.")


class GerarTituloRequest(GeracaoRequestBase):
    max_sugestoes: int = Field(3, ge=1, le=5, description="Número máximo de sugestões de títulos a gerar.")
    palavras_chave_foco: Optional[List[str]] = Field(None, description="Palavras-chave que devem ser priorizadas no título.")
    estilo_tom: Optional[str] = Field(None, description="Estilo/tom desejado para o título (ex: 'formal', 'criativo', 'otimizado_seo').")

class GerarDescricaoRequest(GeracaoRequestBase):
    min_palavras: Optional[int] = Field(None, ge=10, description="Número mínimo de palavras para a descrição.")
    max_palavras: Optional[int] = Field(None, ge=200, description="Número máximo de palavras para a descrição.")
    palavras_chave_foco: Optional[List[str]] = Field(None, description="Palavras-chave que devem ser priorizadas na descrição.")
    aspectos_destacar: Optional[List[str]] = Field(None, description="Aspectos específicos do produto a serem destacados.")
    publico_alvo: Optional[str] = Field(None, description="Público-alvo da descrição (ex: 'jovens', 'profissionais').")


class EnriquecimentoWebRequest(BaseModel):
    produto_id: int
    url_produto_fornecedor: HttpUrl 

# --- RegistroUsoIA Schemas ---
class RegistroUsoIABase(BaseModel):
    tipo_geracao: str = Field(..., description="Tipo de geração IA (ex: 'titulo_produto', 'descricao_produto', 'enriquecimento_web_parsed')")
    produto_id: Optional[int] = None 
    provedor_ia: Optional[str] = None
    modelo_ia: Optional[str] = None
    sucesso: bool = True
    detalhes_erro: Optional[str] = None
    input_text: Optional[str] = Field(None, description="Texto de entrada fornecido para a IA (prompt, etc.)")
    output_text: Optional[str] = Field(None, description="Texto de saída gerado pela IA")
    custo_aproximado: Optional[float] = Field(None, ge=0, description="Custo estimado da chamada à API IA, se aplicável")

class RegistroUsoIACreate(RegistroUsoIABase):
    pass

class RegistroUsoIAResponse(RegistroUsoIABase):
    id: int
    user_id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class RegistroUsoIAPage(BaseModel): 
    items: List[RegistroUsoIAResponse]
    total_items: int
    page: int
    limit: int

# --- Password Recovery Schemas ---
class EmailSchema(BaseModel):
    email: EmailStr

class PasswordResetSchema(BaseModel):
    new_password: str = Field(..., min_length=8)
    token: str

# --- Admin Analytics Schemas --- 
class TotalCounts(BaseModel): 
    total_usuarios: int
    total_produtos: int
    total_fornecedores: int
    total_geracoes_ia_mes: int
    total_enriquecimentos_mes: int

class UsoIAPorPlano(BaseModel):
    plano_id: int
    nome_plano: str
    total_geracoes_ia_no_mes: int
    # detalhe_por_tipo: Optional[Dict[str, int]] = None 

class UsoIAPorUsuario(BaseModel): 
    user_id: int
    email_usuario: EmailStr # Mudado de email para email_usuario para clareza
    nome_plano: Optional[str] = "N/A" # Mantido
    total_geracoes_ia_no_mes: int

class UsoIAPorTipo(BaseModel):
    tipo_geracao: str 
    total_no_mes: int

# NOVO SCHEMA ADICIONADO AQUI
class UserActivity(BaseModel):
    user_id: int
    email: EmailStr
    nome_completo: Optional[str] = None
    # last_login_at: Optional[datetime] = None # Campo para futuro, requer tracking no modelo User
    total_produtos: Optional[int] = None
    total_geracoes_ia_mes_corrente: Optional[int] = None
    # data_criacao_usuario: datetime # Pegar do modelo User

    class Config:
        from_attributes = True


# --- Schema para Mensagens Simples --- 
class Msg(BaseModel):
    msg: str

# --- Schema para Resposta de Processamento de Arquivo --- 
class FileProcessResponse(BaseModel):
    message: str
    total_products_in_file: Optional[int] = None
    products_created: Optional[int] = None
    products_updated: Optional[int] = None
    products_failed: Optional[int] = None
    errors: Optional[List[str]] = None