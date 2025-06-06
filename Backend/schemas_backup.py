# Backend/schemas.py
import json
from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import enum

from Backend.models import StatusEnriquecimentoEnum, StatusGeracaoIAEnum, AttributeFieldTypeEnum, TipoAcaoIAEnum

# --- Novos Enums e Schemas para Mídia e Log ---
class ImageMimeType(str, enum.Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"
    TIFF = "image/tiff"
    SVG = "image/svg+xml"
    # Adicione outros tipos MIME de imagem conforme necessário

class VideoMimeType(str, enum.Enum):
    MP4 = "video/mp4"
    WEBM = "video/webm"
    OGG = "video/ogg"
    # Adicione outros tipos MIME de vídeo conforme necessário

class MediaItemType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"

class ImageSchema(BaseModel):
    url: str # Pode ser HttpUrl se for sempre externa, mas str para caminho local também
    alt_text: Optional[str] = Field(None, max_length=255)
    is_main: bool = False
    display_order: int = Field(0, ge=0) # Para controlar a ordem de exibição na UI
    mimetype: Optional[ImageMimeType] = None # Adicionado para especificar o tipo da imagem
    size_bytes: Optional[int] = Field(None, ge=0) # Adicionado para armazenar o tamanho do arquivo
    uploaded_at: Optional[datetime] = None # Adicionado para registrar a data de upload
    filename: Optional[str] = Field(None, max_length=255) # Adicionado para o nome original do arquivo no upload

    class Config:
        from_attributes = True

class VideoSchema(BaseModel):
    url: HttpUrl # Geralmente URLs de vídeos (YouTube, Vimeo, etc.)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    display_order: int = Field(0, ge=0)
    mimetype: Optional[VideoMimeType] = None
    uploaded_at: Optional[datetime] = None # Adicionado para registrar a data de upload
    filename: Optional[str] = Field(None, max_length=255) # Para vídeos carregados diretamente

    class Config:
        from_attributes = True

class LogMessageSchema(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message: str = Field(..., max_length=1000)
    source: str = Field(..., max_length=50) # Ex: "web_enrichment", "ia_generation_titulo", "ia_generation_descricao", "user_edit", "system"
    status: str = Field(..., max_length=50) # Ex: "SUCESSO", "FALHA", "EM_PROGRESSO", "INFO", "AVISO"

    class Config:
        from_attributes = True

class ProductLogSchema(BaseModel):
    historico_mensagens: List[LogMessageSchema] = Field(default_factory=list)

    class Config:
        from_attributes = True

# --- Schema para Upload de Arquivos de Mídia (Resposta) ---
class FileUploadResponse(BaseModel):
    filename: str
    original_filename: Optional[str] = None # Adicionado
    url: str
    message: str = "File uploaded successfully"
    mimetype: Optional[str] = None # Pode ser ImageMimeType ou VideoMimeType, mas str é mais genérico para a resposta
    size_bytes: Optional[int] = None # Adicionado

    class Config:
        from_attributes = True
# --- Fim dos Novos Enums e Schemas para Mídia e Log ---


# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None
    user_id: Optional[int] = None

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
    plano_id: Optional[int] = None # Adicionado para permitir atualização de plano

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
    role_id: Optional[int] = None
    limite_produtos: Optional[int] = None
    limite_enriquecimento_web: Optional[int] = None
    limite_geracao_ia: Optional[int] = None
    data_expiracao_plano: Optional[datetime] = None
    provider: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserCreateComPlano(UserCreate):
    plano_id: Optional[int] = None


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
    contato_principal: Optional[str] = Field(None, max_length=100)
    email_contato: Optional[EmailStr] = None
    telefone_contato: Optional[str] = Field(None, max_length=20)
    site_url: Optional[HttpUrl] = None # URLs devem ser validadas como HttpUrl
    link_busca_padrao: Optional[HttpUrl] = None

class FornecedorCreate(FornecedorBase):
    pass

class FornecedorUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=150)
    contato_principal: Optional[str] = Field(None, max_length=100)
    email_contato: Optional[EmailStr] = None
    telefone_contato: Optional[str] = Field(None, max_length=20)
    site_url: Optional[HttpUrl] = None
    link_busca_padrao: Optional[HttpUrl] = None

class FornecedorResponse(FornecedorBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

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
    is_filtrable: Optional[bool] = Field(False, description="Se o atributo pode ser usado em filtros de busca")
    tooltip_text: Optional[str] = Field(None, max_length=255, description="Texto de ajuda exibido como tooltip")
    default_value: Optional[str] = Field(None, max_length=255, description="Valor padrão para o atributo")
    display_order: int = Field(0, description="Ordem de exibição do atributo no formulário")

class AttributeTemplateCreate(AttributeTemplateBase):
    pass

class AttributeTemplateUpdate(BaseModel):
    attribute_key: Optional[str] = Field(None, max_length=100)
    label: Optional[str] = Field(None, max_length=150)
    field_type: Optional[AttributeFieldTypeEnum] = None
    options: Optional[str] = None # Deve ser string JSON
    is_required: Optional[bool] = None
    is_filtrable: Optional[bool] = None
    tooltip_text: Optional[str] = Field(None, max_length=255)
    default_value: Optional[str] = Field(None, max_length=255)
    display_order: Optional[int] = None

class AttributeTemplateResponse(AttributeTemplateBase):
    id: int
    product_type_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- ProductType Schemas ---
class ProductTypeBase(BaseModel):
    key_name: str = Field(..., max_length=100, description="Chave única para o tipo de produto (ex: 'eletronicos', 'vestuario_adulto_masculino')")
    friendly_name: str = Field(..., max_length=150, description="Nome amigável para exibição (ex: 'Eletrônicos', 'Vestuário Adulto Masculino')")
    description: Optional[str] = Field(None, description="Descrição do tipo de produto")

class ProductTypeCreate(ProductTypeBase):
    attribute_templates: Optional[List[AttributeTemplateCreate]] = Field([], description="Lista de templates de atributos para este tipo de produto")

class ProductTypeUpdate(BaseModel):
    key_name: Optional[str] = Field(None, max_length=100)
    friendly_name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    # Para atualizar atributos, pode ser uma lista de AttributeTemplateUpdate ou um endpoint específico
    # attribute_templates: Optional[List[AttributeTemplateUpdate]] = None # Exemplo

class ProductTypeResponse(ProductTypeBase):
    id: int
    user_id: Optional[int] = None # Se for global, user_id é None
    attribute_templates: List[AttributeTemplateResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

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
    descricao_curta_orig: Optional[str] = Field(None, max_length=500, description="Descrição curta original do produto")
    descricao_chat_api: Optional[str] = Field(None, description="Descrição otimizada/alternativa pela IA")
    descricao_curta_chat_api: Optional[str] = Field(None, max_length=500, description="Descrição curta otimizada pela IA")

    sku: Optional[str] = Field(None, max_length=100)
    ean: Optional[str] = Field(None, max_length=100)
    ncm: Optional[str] = Field(None, max_length=20)

    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    categoria_original: Optional[str] = Field(None, max_length=150, description="Categoria original informada")
    categoria_mapeada: Optional[str] = Field(None, max_length=150, description="Categoria mapeada ou padronizada")

    preco_custo: Optional[float] = Field(None, ge=0)
    preco_venda: Optional[float] = Field(None, ge=0)
    preco_promocional: Optional[float] = Field(None, ge=0)
    estoque_disponivel: Optional[int] = Field(None, ge=0)

    peso_kg: Optional[float] = Field(None, ge=0)
    altura_cm: Optional[float] = Field(None, ge=0)
    largura_cm: Optional[float] = Field(None, ge=0)
    profundidade_cm: Optional[float] = Field(None, ge=0)

    # REMOVIDOS imagem_principal_url e imagens_secundarias_urls
    # imagem_principal_url: Optional[HttpUrl] = Field(None, description="URL da imagem principal do produto")
    # imagens_secundarias_urls: Optional[List[HttpUrl]] = Field(None, description="Lista de URLs de imagens secundárias")

    fornecedor_id: Optional[int] = None
    product_type_id: Optional[int] = None

    dynamic_attributes: Optional[Dict[str, Any]] = Field(None, description="Atributos dinâmicos como dicionário")
    dados_brutos: Optional[Dict[str, Any]] = Field(None, description="Dados brutos originais do produto como dicionário")

    ativo_marketplace: Optional[bool] = Field(False, description="Se o produto está ativo para publicação em marketplaces")
    data_publicacao_marketplace: Optional[datetime] = Field(None, description="Data da última publicação ou atualização no marketplace")

    # --- CAMPOS DE MÍDIA E LOG ADICIONADOS AQUI ---
    imagens_produto: List[ImageSchema] = Field(default_factory=list, description="Lista de imagens do produto com detalhes")
    videos_produto: List[VideoSchema] = Field(default_factory=list, description="Lista de vídeos do produto com detalhes")
    log_enriquecimento_web: Optional[ProductLogSchema] = Field(None, description="Histórico de logs de enriquecimento e IA para este produto")
    # --- FIM DOS CAMPOS DE MÍDIA E LOG ADICIONADOS ---


class ProdutoCreate(ProdutoBase):
    pass # ProdutoBase agora já contém os campos de mídia e log

class ProdutoUpdate(BaseModel): # Campos que podem ser atualizados
    nome_base: Optional[str] = Field(None, max_length=255)
    nome_chat_api: Optional[str] = Field(None, max_length=255)
    descricao_original: Optional[str] = None
    descricao_curta_orig: Optional[str] = Field(None, max_length=500)
    descricao_chat_api: Optional[str] = None
    descricao_curta_chat_api: Optional[str] = Field(None, max_length=500)

    sku: Optional[str] = Field(None, max_length=100)
    ean: Optional[str] = Field(None, max_length=100)
    ncm: Optional[str] = Field(None, max_length=20)
    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    categoria_original: Optional[str] = Field(None, max_length=150)
    categoria_mapeada: Optional[str] = Field(None, max_length=150)

    preco_custo: Optional[float] = Field(None, ge=0)
    preco_venda: Optional[float] = Field(None, ge=0)
    preco_promocional: Optional[float] = Field(None, ge=0)
    estoque_disponivel: Optional[int] = Field(None, ge=0)

    peso_kg: Optional[float] = Field(None, ge=0)
    altura_cm: Optional[float] = Field(None, ge=0)
    largura_cm: Optional[float] = Field(None, ge=0)
    profundidade_cm: Optional[float] = Field(None, ge=0)

    # REMOVIDOS imagem_principal_url e imagens_secundarias_urls
    # imagem_principal_url: Optional[HttpUrl] = None
    # imagens_secundarias_urls: Optional[List[HttpUrl]] = None

    fornecedor_id: Optional[int] = None
    product_type_id: Optional[int] = None
    dynamic_attributes: Optional[Dict[str, Any]] = None
    dados_brutos: Optional[Dict[str, Any]] = None

    ativo_marketplace: Optional[bool] = None
    data_publicacao_marketplace: Optional[datetime] = None

    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None
    status_titulo_ia: Optional[StatusGeracaoIAEnum] = None
    status_descricao_ia: Optional[StatusGeracaoIAEnum] = None

    # --- CAMPOS DE MÍDIA E LOG ADICIONADOS AQUI ---
    imagens_produto: Optional[List[ImageSchema]] = None
    videos_produto: Optional[List[VideoSchema]] = None
    log_enriquecimento_web: Optional[ProductLogSchema] = None
    # --- FIM DOS CAMPOS DE MÍDIA E LOG ADICIONADOS ---


class ProdutoResponse(ProdutoBase):
    id: int
    user_id: int

    created_at: datetime = Field(..., alias="data_criacao")
    updated_at: Optional[datetime] = Field(None, alias="data_atualizacao")

    status_enriquecimento_web: StatusEnriquecimentoEnum
    status_titulo_ia: StatusGeracaoIAEnum
    status_descricao_ia: StatusGeracaoIAEnum

    class Config:
        from_attributes = True
        populate_by_name = True


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


# --- RegistroUsoIA Schemas ---
class RegistroUsoIABase(BaseModel):
    tipo_acao: TipoAcaoIAEnum = Field(..., description="Tipo de ação de IA realizada")
    produto_id: Optional[int] = None
    provedor_ia: Optional[str] = Field(None, max_length=50)
    modelo_usado: Optional[str] = Field(None, max_length=100)
    prompt_utilizado: Optional[str] = Field(None, description="Prompt exato enviado à IA")
    resposta_ia_raw: Optional[str] = Field(None, description="Resposta bruta da IA")
    tokens_entrada: Optional[int] = Field(0, ge=0)
    tokens_saida: Optional[int] = Field(0, ge=0)
    custo_estimado: Optional[float] = Field(0.0, ge=0, description="Custo estimado da chamada à API IA")

class RegistroUsoIACreate(RegistroUsoIABase):
    user_id: int

class RegistroUsoIAResponse(RegistroUsoIABase):
    id: int
    user_id: int
    created_at: datetime = Field(..., alias="timestamp") # Atributo do modelo é created_at, alias para timestamp na saida

    class Config:
        from_attributes = True
        populate_by_name = True


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
    plano_id: Optional[int] = None
    nome_plano: str
    total_geracoes_ia_no_mes: int

class UsoIAPorUsuario(BaseModel):
    user_id: int
    email_usuario: EmailStr
    nome_plano: Optional[str] = "N/A"
    total_geracoes_ia_no_mes: int

class UsoIAPorTipo(BaseModel):
    tipo_acao: str # Enum.value
    total_no_mes: int

class UserActivity(BaseModel):
    user_id: int
    email: EmailStr
    nome_completo: Optional[str] = None
    created_at: datetime # Do modelo User
    # Campos que serão preenchidos no router a partir de dados do CRUD
    total_produtos: Optional[int] = None
    total_geracoes_ia_mes_corrente: Optional[int] = None

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
