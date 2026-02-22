# Caminho: Backend/schemas.py

from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import (
    BaseModel,
    EmailStr,
    HttpUrl,
    Field,
    ConfigDict,
    field_validator,
    model_validator,
)
from datetime import datetime
import json  # Para validaÃ§Ã£o de JSON string

# Ã‰ crucial que a importaÃ§Ã£o de 'models' funcione corretamente.
# Se 'models' estiver no mesmo diretÃ³rio ou em um caminho Python reconhecido,
# a importaÃ§Ã£o direta pode funcionar. Caso contrÃ¡rio, pode ser necessÃ¡rio um ajuste
# relativo ou absoluto dependendo de como o projeto Ã© executado.
# Assumindo que 'models.py' estÃ¡ no mesmo diretÃ³rio (Backend) e Ã© acessÃ­vel:
from Backend.models import (
    StatusEnriquecimentoEnum,
    StatusGeracaoIAEnum,
    TipoAcaoEnum,
    TipoAcaoSistemaEnum,
    AttributeFieldTypeEnum,
)


# Schemas de AutenticaÃ§Ã£o e UsuÃ¡rio
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None  # Adicionado para identificar o usuÃ¡rio pelo ID


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserBase(BaseModel):
    email: EmailStr
    nome_completo: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    idioma_preferido: Optional[str] = "pt_BR"
    plano_id: Optional[int] = None
    role_id: Optional[int] = None
    chave_openai_pessoal: Optional[str] = None
    chave_google_gemini_pessoal: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserCreateOAuth(UserBase):  # Para criaÃ§Ã£o via OAuth
    provider: Optional[str] = None
    provider_user_id: Optional[str] = None
    # NÃ£o requer password na criaÃ§Ã£o OAuth


class UserUpdate(BaseModel):  # O que o prÃ³prio usuÃ¡rio pode atualizar
    email: Optional[EmailStr] = None
    nome_completo: Optional[str] = None
    password: Optional[str] = None  # Para alteraÃ§Ã£o de senha
    idioma_preferido: Optional[str] = None
    chave_openai_pessoal: Optional[str] = None
    chave_google_gemini_pessoal: Optional[str] = None


class UserUpdateByAdmin(
    UserUpdate
):  # O que um admin pode atualizar em qualquer usuÃ¡rio
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    plano_id: Optional[int] = None
    role_id: Optional[int] = None
    limite_produtos: Optional[int] = None
    limite_enriquecimento_web: Optional[int] = None
    limite_geracao_ia: Optional[int] = None
    data_expiracao_plano: Optional[datetime] = None


class UserUpdateOAuth(
    BaseModel
):  # Dados que podem ser atualizados via OAuth (ex: nome, se mudar no provedor)
    nome_completo: Optional[str] = None
    # Outros campos que o OAuth possa fornecer e queiramos atualizar


class UserChangePassword(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class UserResponse(UserBase):  # O que Ã© retornado pela API
    id: int
    created_at: datetime
    updated_at: datetime
    limite_produtos: Optional[int] = None
    limite_enriquecimento_web: Optional[int] = None
    limite_geracao_ia: Optional[int] = None
    data_expiracao_plano: Optional[datetime] = None
    # Adicionar informaÃ§Ãµes do plano e role se desejado na resposta
    plano: Optional["PlanoResponse"] = None  # type: ignore  # Evitar dependÃªncia circular
    # role: Optional[RoleResponse] = None  # Evitar dependÃªncia circular

    model_config = ConfigDict(from_attributes=True)

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# Schemas para Role
class RoleBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(RoleBase):
    name: Optional[str] = Field(
        None, min_length=3, max_length=50
    )  # Tornar opcional na atualizaÃ§Ã£o


class RoleResponse(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # users: List[UserResponse] = [] # Cuidado com recursÃ£o, talvez apenas IDs ou omitir

    model_config = ConfigDict(from_attributes=True)

# Schemas para Plano
class PlanoBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    descricao: Optional[str] = None
    preco_mensal: float = Field(..., ge=0)
    limite_produtos: int = Field(..., ge=0)
    limite_enriquecimento_web: int = Field(..., ge=0)
    limite_geracao_ia: int = Field(..., ge=0)
    permite_api_externa: bool = False
    suporte_prioritario: bool = False


class PlanoCreate(PlanoBase):
    pass


class PlanoUpdate(PlanoBase):
    nome: Optional[str] = Field(None, min_length=3, max_length=100)
    preco_mensal: Optional[float] = Field(None, ge=0)
    limite_produtos: Optional[int] = Field(None, ge=0)
    limite_enriquecimento_web: Optional[int] = Field(None, ge=0)
    limite_geracao_ia: Optional[int] = Field(None, ge=0)
    # Demais campos tambÃ©m opcionais na atualizaÃ§Ã£o, se desejado


class PlanoResponse(PlanoBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # users: List[UserResponse] = [] # Cuidado com recursÃ£o

    model_config = ConfigDict(from_attributes=True)

# Schemas para Fornecedor
class FornecedorBase(BaseModel):
    nome: str = Field(..., max_length=200)
    email_contato: Optional[EmailStr] = None
    telefone_contato: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = None
    site_url: Optional[str] = None  # Usando str para flexibilidade
    termos_contratuais: Optional[str] = None
    contato_principal: Optional[str] = Field(None, max_length=100)
    observacoes: Optional[str] = None
    link_busca_padrao: Optional[str] = None  # Usando str para flexibilidade
    default_column_mapping: Optional[Dict[str, str]] = None


class FornecedorCreate(FornecedorBase):
    pass


class FornecedorUpdate(FornecedorBase):
    # Tornar campos opcionais para atualizaÃ§Ã£o parcial
    nome: Optional[str] = Field(None, max_length=200)
    # Adicionar Optional para todos os outros campos se desejar atualizaÃ§Ã£o parcial


class FornecedorResponse(FornecedorBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    default_column_mapping: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)

class FornecedorPage(BaseModel):
    items: List[FornecedorResponse]
    total_items: int
    page: int
    limit: int


# Schemas para AttributeTemplate
class AttributeTemplateBase(BaseModel):
    attribute_key: str = Field(
        ...,
        description="Chave Ãºnica do atributo no template (ex: 'cor', 'tamanho_tela').",
    )
    label: str = Field(
        ...,
        description="Nome amigÃ¡vel do atributo para exibiÃ§Ã£o (ex: 'Cor', 'Tamanho da Tela').",
    )
    field_type: AttributeFieldTypeEnum = Field(
        AttributeFieldTypeEnum.TEXT,
        description="Tipo de campo para o atributo (text, number, boolean, select, multiselect, date).",
    )
    description: Optional[str] = Field(
        None, description="DescriÃ§Ã£o ou ajuda sobre o atributo."
    )
    default_value: Optional[str] = Field(
        None,
        description="Valor padrÃ£o para o atributo (string, pode precisar de conversÃ£o).",
    )
    options: Optional[Union[List[str], str]] = Field(
        None,
        description="Lista de opÃ§Ãµes para tipos 'select' ou 'multiselect', pode ser string JSON.",
    )
    is_required: bool = Field(False, description="Indica se o atributo Ã© obrigatÃ³rio.")
    is_filterable: bool = Field(
        False, description="Indica se o atributo pode ser usado para filtros."
    )
    display_order: int = Field(0, description="Ordem de exibiÃ§Ã£o do atributo.")

    @field_validator("options", mode="before")
    @classmethod
    def parse_json_options(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                if not isinstance(parsed_value, list):
                    raise ValueError(
                        "String JSON para 'options' deve representar uma lista."
                    )
                return parsed_value  # Retorna a lista Python
            except json.JSONDecodeError:
                raise ValueError("String para 'options' nÃ£o Ã© um JSON vÃ¡lido.")
        return value  # Se jÃ¡ for lista ou None, retorna como estÃ¡


class AttributeTemplateCreate(AttributeTemplateBase):
    pass  # product_type_id serÃ¡ atribuÃ­do no CRUD


class AttributeTemplateUpdate(AttributeTemplateBase):
    # Todos os campos sÃ£o opcionais na atualizaÃ§Ã£o
    attribute_key: Optional[str] = None
    label: Optional[str] = None
    field_type: Optional[AttributeFieldTypeEnum] = None
    # ... tornar todos os outros campos Optional


class AttributeTemplateResponse(AttributeTemplateBase):
    id: int
    product_type_id: int
    options: Optional[List[str]] = None  # Garante que a resposta seja uma lista

    model_config = ConfigDict(from_attributes=True)

# Schemas para ProductType
class ProductTypeBase(BaseModel):
    key_name: str = Field(
        ...,
        description="Chave Ãºnica para identificar o tipo de produto (ex: 'smartphones', 'camisetas_manga_longa').",
    )
    friendly_name: str = Field(
        ...,
        description="Nome amigÃ¡vel do tipo de produto (ex: 'Smartphones', 'Camisetas Manga Longa').",
    )
    description: Optional[str] = Field(
        None, description="DescriÃ§Ã£o do tipo de produto."
    )


class ProductTypeCreate(ProductTypeBase):
    attribute_templates: List[AttributeTemplateCreate] = []


class ProductTypeUpdate(ProductTypeBase):
    key_name: Optional[str] = None
    friendly_name: Optional[str] = None
    # attribute_templates: Opcionalmente, permitir atualizar/adicionar/remover atributos aqui,
    # mas geralmente Ã© melhor ter endpoints separados para gerenciar atributos de um tipo.


class ProductTypeResponse(ProductTypeBase):
    id: int
    user_id: Optional[int] = (
        None  # Tipos podem ser globais (user_id=None) ou especÃ­ficos do usuÃ¡rio
    )
    attribute_templates: List[AttributeTemplateResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Schemas para Produto
class ProdutoBase(BaseModel):
    nome_base: str = Field(
        ..., max_length=255, description="Nome principal ou base do produto."
    )
    nome_chat_api: Optional[str] = Field(
        None, max_length=255, description="Nome otimizado ou gerado pela IA."
    )
    descricao_original: Optional[str] = Field(
        None, description="DescriÃ§Ã£o original fornecida ou importada."
    )
    descricao_chat_api: Optional[str] = Field(
        None, description="DescriÃ§Ã£o otimizada ou gerada pela IA."
    )

    sku: Optional[str] = Field(
        None,
        max_length=100,
        description="SKU (Stock Keeping Unit) do produto.",
    )
    ean: Optional[str] = Field(
        None,
        max_length=13,
        description="EAN (European Article Number) / GTIN.",
    )
    ncm: Optional[str] = Field(
        None, max_length=8, description="NCM (Nomenclatura Comum do Mercosul)."
    )

    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)

    preco_custo: Optional[float] = Field(None, ge=0)
    preco_venda: Optional[float] = Field(None, ge=0)
    margem_lucro: Optional[float] = Field(None, description="Calculado ou informado.")

    estoque_disponivel: Optional[int] = Field(None, ge=0)
    peso_gramas: Optional[int] = Field(None, ge=0)
    dimensoes_cm: Optional[str] = Field(
        None, max_length=50, description="Ex: 10x15x20 (AxLxP)"
    )

    fornecedor_id: Optional[int] = None
    product_type_id: Optional[int] = None  # ID do Tipo de Produto associado

    categoria_original: Optional[str] = Field(None, max_length=150)
    categoria_mapeada: Optional[str] = Field(
        None, max_length=150
    )  # Categoria apÃ³s algum processamento/padronizaÃ§Ã£o
    tags_palavras_chave: Optional[List[str]] = Field(None)  # Lista de strings

    imagem_principal_url: Optional[str] = None
    imagens_secundarias_urls: Optional[List[str]] = Field(None)  # Lista de URLs
    video_url: Optional[str] = None

    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = (
        StatusEnriquecimentoEnum.NAO_INICIADO
    )
    status_titulo_ia: Optional[StatusGeracaoIAEnum] = StatusGeracaoIAEnum.NAO_INICIADO
    status_descricao_ia: Optional[StatusGeracaoIAEnum] = (
        StatusGeracaoIAEnum.NAO_INICIADO
    )

    dados_brutos_web: Optional[Dict[str, Any]] = Field(
        None, description="JSON com dados extraÃ­dos da web (textos, metadados)."
    )
    dynamic_attributes: Optional[Dict[str, Any]] = Field(
        None, description="Atributos dinÃ¢micos baseados no ProductType (JSON)."
    )

    # Log de enriquecimento web; estrutura flexÃ­vel (lista ou dict) mantida como JSON.
    log_enriquecimento_web: Optional[Any] = Field(
        None, description="Log do processo de enriquecimento web."
    )

    log_processamento: Optional[List[Dict[str, Any]]] = Field(
        None, description="Log de eventos de processamento do produto."
    )


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(ProdutoBase):
    nome_base: Optional[str] = Field(None, max_length=255)


class ProdutoResponse(ProdutoBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    fornecedor: Optional[FornecedorResponse] = None
    product_type: Optional[ProductTypeResponse] = None
    log_enriquecimento_web: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)

class ProdutoBatchDeleteRequest(BaseModel):
    produto_ids: List[int]


class ImportPreviewResponse(BaseModel):
    file_id: int
    num_pages: int = 0
    table_pages: List[int] = Field(default_factory=list)
    sample_rows: Union[Dict[int, str], List[Dict[str, Any]]] = Field(default_factory=dict)
    preview_images: List[Dict[str, Any]] = Field(default_factory=list)
    headers: Optional[List[str]] = None
    error: Optional[str] = None


class ImportCatalogoResponse(BaseModel):
    produtos_criados: List[ProdutoResponse]
    erros: List[Dict[str, Any]]


class UpdatedProductInfo(BaseModel):
    """Representa um produto atualizado durante a importaÃ§Ã£o."""

    before: ProdutoResponse
    after: ProdutoResponse


class CatalogImportResult(BaseModel):
    created: List[ProdutoResponse]
    updated: List[ProdutoResponse]
    errors: List[Dict[str, Any]]
    stats: Optional[Dict[str, Any]] = None
    log: Optional[List[str]] = None


class RegionExtractionResponse(BaseModel):
    produtos: List[Dict[str, Any]]
    log: Optional[List[str]] = None
    preview_headers: Optional[List[str]] = None
    preview_rows: Optional[List[Dict[str, Any]]] = None


class SinglePageExtractionResponse(BaseModel):
    image: str
    text: str
    table: Optional[List[List[Any]]] = None


class ProdutoPage(BaseModel):
    items: List[ProdutoResponse]
    total_items: int
    page: int
    limit: int


# Schemas para RegistroUsoIA
class RegistroUsoIABase(BaseModel):
    user_id: int
    produto_id: Optional[int] = None
    tipo_acao: TipoAcaoEnum
    provedor_ia: Optional[str] = None
    modelo_ia: Optional[str] = None
    prompt_utilizado: Optional[str] = None
    resposta_ia: Optional[str] = None
    tokens_prompt: Optional[int] = None
    tokens_resposta: Optional[int] = None
    custo_estimado_usd: Optional[float] = None
    creditos_consumidos: int = 1
    status: str = "SUCESSO"
    detalhes_erro: Optional[str] = None


class RegistroUsoIACreate(RegistroUsoIABase):
    pass


class RegistroUsoIAResponse(RegistroUsoIABase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UsoIAPage(BaseModel):
    items: List[RegistroUsoIAResponse]
    total_items: int
    page: int
    limit: int


# Schemas para RegistroHistorico
class RegistroHistoricoBase(BaseModel):
    user_id: Optional[int] = None
    entidade: str
    acao: TipoAcaoSistemaEnum
    entity_id: Optional[int] = None
    detalhes_json: Optional[dict] = None


class RegistroHistoricoCreate(RegistroHistoricoBase):
    pass


class RegistroHistoricoResponse(RegistroHistoricoBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HistoricoPage(BaseModel):
    items: List[RegistroHistoricoResponse]
    total_items: int
    page: int
    limit: int


class CatalogImportFileBase(BaseModel):
    original_filename: str
    stored_filename: str
    status: str
    total_pages: Optional[int] = None
    pages_processed: Optional[int] = None
    result_summary: Optional[Dict[str, Any]] = None


class CatalogImportFileCreate(CatalogImportFileBase):
    user_id: int
    fornecedor_id: Optional[int] = None


class CatalogImportFileResponse(CatalogImportFileBase):
    id: int
    user_id: int
    fornecedor_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CatalogImportStatus(BaseModel):
    """Status simplificado de importaÃ§Ã£o de catÃ¡logo."""

    status: Literal["PROCESSING", "DONE", "PARTIAL", "FAILED"]
    pages_total: int
    pages_processed: int


class CatalogImportFilePage(BaseModel):
    items: List[CatalogImportFileResponse]
    total_items: int
    page: int
    limit: int


class FornecedorImportJobBase(BaseModel):
    status: str
    result_summary: Optional[Dict[str, Any]] = None


class FornecedorImportJobResponse(FornecedorImportJobBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PdfPreviewResponse(BaseModel):
    """Preview data for PDF page images."""

    image_urls: List[str]
    total_pages: int
    import_file_id: int

    model_config = ConfigDict(from_attributes=True)

# --- Password Recovery Schemas ---
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


class UsoIAPorTipo(BaseModel):
    tipo_acao: str
    total_no_mes: int


class UserActivity(BaseModel):
    user_id: int
    email: EmailStr
    nome_completo: Optional[str] = None
    created_at: datetime
    total_produtos: Optional[int] = None
    total_geracoes_ia_mes_corrente: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class ProductStatusCount(BaseModel):
    status: StatusEnriquecimentoEnum
    total: int


class RecentActivity(BaseModel):
    id: int
    user_id: int
    user_email: Optional[EmailStr] = None
    tipo_acao: TipoAcaoEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ----- NOVOS SCHEMAS PARA SUGESTÃƒO DE ATRIBUTOS GEMINI -----
class SugestaoAtributoItem(BaseModel):
    chave_atributo: str = Field(
        ...,
        description="A chave do atributo para o qual o valor Ã© sugerido (ex: 'cor', 'material').",
    )
    valor_sugerido: str = Field(
        ..., description="O valor sugerido pela IA para o atributo."
    )


class SugestoesAtributosResponse(BaseModel):
    sugestoes_atributos: List[SugestaoAtributoItem] = Field(
        ..., description="Lista de sugestÃµes de atributos e seus valores."
    )
    produto_id: int = Field(
        ..., description="ID do produto para o qual as sugestÃµes foram geradas."
    )
    modelo_ia_utilizado: Optional[str] = Field(
        None, description="Modelo de IA utilizado para a sugestÃ£o."
    )


# --- Schemas para busca unificada ---
class SearchItem(BaseModel):
    id: int
    type: str
    name: str


class SearchResults(BaseModel):
    results: List[SearchItem]


# --- Utility Schemas ---
class Msg(BaseModel):
    msg: str


class FileProcessResponse(BaseModel):
    filename: str
    original_filename: Optional[str] = None
    url: str
    message: str = "File uploaded successfully"
    mimetype: Optional[str] = None
    size_bytes: Optional[int] = None


class SocialLoginConfig(BaseModel):
    """Indica quais provedores de login social estÃ£o configurados."""

    google_enabled: bool
    facebook_enabled: bool


class RegionExtractionRequest(BaseModel):
    import_file_id: int
    page_number: int
    region: List[float]


class CatalogRegionPreviewRequest(BaseModel):
    file_id: str
    page_number: int
    region: Optional[List[float]] = None


class PdfRegionBulkRequest(BaseModel):
    file_id: int
    region: List[float]
    pages: Optional[List[int]] = None
    all_pages: Optional[bool] = False


class CatalogPreview(BaseModel):
    columns: List[str]
    data: List[Dict[str, Any]]


# --- Rebuilds Finais ---
UserResponse.model_rebuild()
PlanoResponse.model_rebuild()
RoleResponse.model_rebuild()
FornecedorResponse.model_rebuild()
AttributeTemplateResponse.model_rebuild()
ProductTypeResponse.model_rebuild()
ProdutoResponse.model_rebuild()
ImportCatalogoResponse.model_rebuild()
UpdatedProductInfo.model_rebuild()
CatalogImportResult.model_rebuild()
RegionExtractionResponse.model_rebuild()
SinglePageExtractionResponse.model_rebuild()
RegistroUsoIAResponse.model_rebuild()
RegistroHistoricoResponse.model_rebuild()
CatalogImportFileResponse.model_rebuild()
UserActivity.model_rebuild()
SocialLoginConfig.model_rebuild()
PdfPreviewResponse.model_rebuild()
CatalogPreview.model_rebuild()
PdfRegionBulkRequest.model_rebuild()


