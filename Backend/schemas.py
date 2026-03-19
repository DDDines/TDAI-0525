# Caminho: Backend/schemas.py
"""Document schemas module responsibilities and runtime integration points."""


from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum
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
import json  # Para validação de JSON string

# É crucial que a importação de 'models' funcione corretamente.
# Se 'models' estiver no mesmo diretório ou em um caminho Python reconhecido,
# a importação direta pode funcionar. Caso contrário, pode ser necessário um ajuste
# relativo ou absoluto dependendo de como o projeto é executado.
# Assumindo que 'models.py' está no mesmo diretório (Backend) e é acessível:
from Backend.models import (
    AIPolicyModeEnum,
    AIPolicyScopeEnum,
    StatusEnriquecimentoEnum,
    StatusGeracaoIAEnum,
    TipoAcaoEnum,
    TipoAcaoSistemaEnum,
    AttributeFieldTypeEnum,
    ExternalCredentialProviderEnum,
    ExternalCredentialScopeEnum,
)


# Schemas de Autenticação e Usuário
class Token(BaseModel):
    """Represent Token and centralize its responsibilities inside this module."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Represent Token Data and centralize its responsibilities inside this module."""
    email: Optional[str] = None
    user_id: Optional[int] = None  # Adicionado para identificar o usuário pelo ID


class RefreshTokenRequest(BaseModel):
    """Represent Refresh Token Request and centralize its responsibilities inside this module."""
    refresh_token: str


class UserBase(BaseModel):
    """Represent User Base and centralize its responsibilities inside this module."""
    email: EmailStr
    nome_completo: Optional[str] = None
    nome_empresa: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    idioma_preferido: Optional[str] = "pt_BR"
    plano_id: Optional[int] = None
    role_id: Optional[int] = None
    chave_openai_pessoal: Optional[str] = None
    chave_google_gemini_pessoal: Optional[str] = None


class UserCreate(UserBase):
    """Represent User Create and centralize its responsibilities inside this module."""
    password: str


class UserCreateOAuth(UserBase):  # Para criação via OAuth
    """Represent User Create OAuth and centralize its responsibilities inside this module."""
    provider: Optional[str] = None
    provider_user_id: Optional[str] = None
    # Não requer password na criação OAuth


class UserUpdate(BaseModel):  # O que o próprio usuário pode atualizar
    """Represent User Update and centralize its responsibilities inside this module."""
    email: Optional[EmailStr] = None
    nome_completo: Optional[str] = None
    nome_empresa: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None  # Para alteracao de senha
    idioma_preferido: Optional[str] = None
    chave_openai_pessoal: Optional[str] = None
    chave_google_gemini_pessoal: Optional[str] = None


class UserUpdateByAdmin(
    UserUpdate
):  # O que um admin pode atualizar em qualquer usuário
    """Represent User Update By Admin and centralize its responsibilities inside this module."""
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
    """Represent User Update OAuth and centralize its responsibilities inside this module."""
    nome_completo: Optional[str] = None
    avatar_url: Optional[str] = None
    # Outros campos que o OAuth possa fornecer e queiramos atualizar


class UserChangePassword(BaseModel):
    """Represent User Change Password and centralize its responsibilities inside this module."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class UserResponse(UserBase):  # O que é retornado pela API
    """Represent User Response and centralize its responsibilities inside this module."""
    id: int
    created_at: datetime
    updated_at: datetime
    limite_produtos: Optional[int] = None
    limite_enriquecimento_web: Optional[int] = None
    limite_geracao_ia: Optional[int] = None
    data_expiracao_plano: Optional[datetime] = None
    product_experience_mode: Literal["basic", "complete"] = "basic"
    # Adicionar informações do plano e role se desejado na resposta
    plano: Optional["PlanoResponse"] = None  # type: ignore  # Evitar dependência circular
    # role: Optional[RoleResponse] = None  # Evitar dependência circular

    model_config = ConfigDict(from_attributes=True)

class PasswordResetRequest(BaseModel):
    """Represent Password Reset Request and centralize its responsibilities inside this module."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Represent Password Reset Confirm and centralize its responsibilities inside this module."""
    token: str
    new_password: str


# Schemas para Role
class RoleBase(BaseModel):
    """Represent Role Base and centralize its responsibilities inside this module."""
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Represent Role Create and centralize its responsibilities inside this module."""
    pass


class RoleUpdate(RoleBase):
    """Represent Role Update and centralize its responsibilities inside this module."""
    name: Optional[str] = Field(
        None, min_length=3, max_length=50
    )  # Tornar opcional na atualização


class RoleResponse(RoleBase):
    """Represent Role Response and centralize its responsibilities inside this module."""
    id: int
    created_at: datetime
    updated_at: datetime
    # users: List[UserResponse] = [] # Cuidado com recursão, talvez apenas IDs ou omitir

    model_config = ConfigDict(from_attributes=True)

# Schemas para Plano
class PlanoBase(BaseModel):
    """Represent Plano Base and centralize its responsibilities inside this module."""
    nome: str = Field(..., min_length=3, max_length=100)
    descricao: Optional[str] = None
    preco_mensal: float = Field(..., ge=0)
    limite_produtos: int = Field(..., ge=0)
    limite_enriquecimento_web: int = Field(..., ge=0)
    limite_geracao_ia: int = Field(..., ge=0)
    permite_api_externa: bool = False
    suporte_prioritario: bool = False


class PlanoCreate(PlanoBase):
    """Represent Plano Create and centralize its responsibilities inside this module."""
    pass


class PlanoUpdate(PlanoBase):
    """Represent Plano Update and centralize its responsibilities inside this module."""
    nome: Optional[str] = Field(None, min_length=3, max_length=100)
    preco_mensal: Optional[float] = Field(None, ge=0)
    limite_produtos: Optional[int] = Field(None, ge=0)
    limite_enriquecimento_web: Optional[int] = Field(None, ge=0)
    limite_geracao_ia: Optional[int] = Field(None, ge=0)
    # Demais campos também opcionais na atualização, se desejado


class PlanoResponse(PlanoBase):
    """Represent Plano Response and centralize its responsibilities inside this module."""
    id: int
    created_at: datetime
    updated_at: datetime
    # users: List[UserResponse] = [] # Cuidado com recursão

    model_config = ConfigDict(from_attributes=True)

# Schemas para Fornecedor
class FornecedorBase(BaseModel):
    """Represent Fornecedor Base and centralize its responsibilities inside this module."""
    nome: str = Field(..., max_length=200)
    email_contato: Optional[EmailStr] = None
    telefone_contato: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = None
    site_url: Optional[str] = None  # Usando str para flexibilidade
    logo_url: Optional[str] = None
    termos_contratuais: Optional[str] = None
    contato_principal: Optional[str] = Field(None, max_length=100)
    observacoes: Optional[str] = None
    link_busca_padrao: Optional[str] = None  # Usando str para flexibilidade
    default_column_mapping: Optional[Dict[str, str]] = None


class FornecedorCreate(FornecedorBase):
    """Represent Fornecedor Create and centralize its responsibilities inside this module."""
    pass


class FornecedorUpdate(FornecedorBase):
    # Tornar campos opcionais para atualização parcial
    """Represent Fornecedor Update and centralize its responsibilities inside this module."""
    nome: Optional[str] = Field(None, max_length=200)
    # Adicionar Optional para todos os outros campos se desejar atualização parcial


class FornecedorResponse(FornecedorBase):
    """Represent Fornecedor Response and centralize its responsibilities inside this module."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    default_column_mapping: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)

class FornecedorPage(BaseModel):
    """Represent Fornecedor Page and centralize its responsibilities inside this module."""
    items: List[FornecedorResponse]
    total_items: int
    page: int
    limit: int


class FornecedorLogoResolveRequest(BaseModel):
    """Payload para resolver logo a partir do site do fornecedor."""

    site_url: str = Field(..., min_length=3, max_length=500)


class FornecedorLogoResolveResponse(BaseModel):
    """Resposta com o logo resolvido para o fornecedor."""

    logo_url: Optional[str] = None
    resolved_site_url: str
    source: str


class FilteredIdsResponse(BaseModel):
    """Represent a lightweight ID listing for current filtered results."""

    ids: List[int]
    total_items: int


# Schemas para AttributeTemplate
class AttributeTemplateBase(BaseModel):
    """Represent Attribute Template Base and centralize its responsibilities inside this module."""
    attribute_key: str = Field(
        ...,
        description="Chave única do atributo no template (ex: 'cor', 'tamanho_tela').",
    )
    label: str = Field(
        ...,
        description="Nome amigável do atributo para exibição (ex: 'Cor', 'Tamanho da Tela').",
    )
    field_type: AttributeFieldTypeEnum = Field(
        AttributeFieldTypeEnum.TEXT,
        description="Tipo de campo para o atributo (text, number, boolean, select, multiselect, date).",
    )
    description: Optional[str] = Field(
        None, description="Descrição ou ajuda sobre o atributo."
    )
    default_value: Optional[str] = Field(
        None,
        description="Valor padrão para o atributo (string, pode precisar de conversão).",
    )
    options: Optional[Union[List[str], str]] = Field(
        None,
        description="Lista de opções para tipos 'select' ou 'multiselect', pode ser string JSON.",
    )
    is_required: bool = Field(False, description="Indica se o atributo é obrigatório.")
    is_filterable: bool = Field(
        False, description="Indica se o atributo pode ser usado para filtros."
    )
    collect_in_ai: bool = Field(
        True,
        description="Indica se o atributo deve orientar coleta e sugestoes no modo IA.",
    )
    display_order: int = Field(0, description="Ordem de exibição do atributo.")

    @field_validator("options", mode="before")
    @classmethod
    def parse_json_options(cls, value: Any) -> Any:
        """Parse json options into structured data used by downstream logic."""
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                if not isinstance(parsed_value, list):
                    raise ValueError(
                        "String JSON para 'options' deve representar uma lista."
                    )
                return parsed_value  # Retorna a lista Python
            except json.JSONDecodeError:
                raise ValueError("String para 'options' não é um JSON válido.")
        return value  # Se já for lista ou None, retorna como está

    @model_validator(mode="after")
    def validate_select_options(self) -> "AttributeTemplateBase":
        """Ensure SELECT and MULTISELECT fields always have a non-empty options list."""
        from Backend.models import AttributeFieldTypeEnum as _FT
        select_types = {_FT.SELECT, _FT.MULTISELECT}
        if self.field_type in select_types:
            if not self.options:
                raise ValueError(
                    f"Atributos do tipo '{self.field_type.value}' precisam ter "
                    "pelo menos uma opção definida no campo 'options'."
                )
        return self


class AttributeTemplateCreate(AttributeTemplateBase):
    """Represent Attribute Template Create and centralize its responsibilities inside this module."""
    pass  # product_type_id será atribuído no CRUD


class AttributeTemplateUpdate(AttributeTemplateBase):
    # Todos os campos são opcionais na atualização
    """Represent Attribute Template Update and centralize its responsibilities inside this module."""
    attribute_key: Optional[str] = None
    label: Optional[str] = None
    field_type: Optional[AttributeFieldTypeEnum] = None
    # ... tornar todos os outros campos Optional


class AttributeTemplateResponse(AttributeTemplateBase):
    """Represent Attribute Template Response and centralize its responsibilities inside this module."""
    id: int
    product_type_id: int
    options: Optional[List[str]] = None  # Garante que a resposta seja uma lista

    model_config = ConfigDict(from_attributes=True)

# Schemas para ProductType
class ProductTypeBase(BaseModel):
    """Represent Product Type Base and centralize its responsibilities inside this module."""
    key_name: str = Field(
        ...,
        description="Chave única para identificar o tipo de produto (ex: 'smartphones', 'camisetas_manga_longa').",
    )
    friendly_name: str = Field(
        ...,
        description="Nome amigável do tipo de produto (ex: 'Smartphones', 'Camisetas Manga Longa').",
    )
    description: Optional[str] = Field(
        None, description="Descrição do tipo de produto."
    )


class ProductTypeCreate(ProductTypeBase):
    """Represent Product Type Create and centralize its responsibilities inside this module."""
    attribute_templates: List[AttributeTemplateCreate] = []


class ProductTypeUpdate(ProductTypeBase):
    """Represent Product Type Update and centralize its responsibilities inside this module."""
    key_name: Optional[str] = None
    friendly_name: Optional[str] = None
    # attribute_templates: Opcionalmente, permitir atualizar/adicionar/remover atributos aqui,
    # mas geralmente é melhor ter endpoints separados para gerenciar atributos de um tipo.


class ProductTypeResponse(ProductTypeBase):
    """Represent Product Type Response and centralize its responsibilities inside this module."""
    id: int
    user_id: Optional[int] = (
        None  # Tipos podem ser globais (user_id=None) ou específicos do usuário
    )
    attribute_templates: List[AttributeTemplateResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Schemas para Produto
class ProdutoBase(BaseModel):
    """Represent Produto Base and centralize its responsibilities inside this module."""
    nome_base: str = Field(
        ..., max_length=255, description="Nome principal ou base do produto."
    )
    nome_chat_api: Optional[str] = Field(
        None, max_length=255, description="Nome otimizado ou gerado pela IA."
    )
    descricao_original: Optional[str] = Field(
        None, description="Descrição original fornecida ou importada."
    )
    descricao_chat_api: Optional[str] = Field(
        None, description="Descrição otimizada ou gerada pela IA."
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
    )  # Categoria após algum processamento/padronização
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
        None, description="JSON com dados extraídos da web (textos, metadados)."
    )
    dynamic_attributes: Optional[Dict[str, Any]] = Field(
        None, description="Atributos dinâmicos baseados no ProductType (JSON)."
    )

    # Log de enriquecimento web; estrutura flexível (lista ou dict) mantida como JSON.
    log_enriquecimento_web: Optional[Any] = Field(
        None, description="Log do processo de enriquecimento web."
    )

    log_processamento: Optional[List[Dict[str, Any]]] = Field(
        None, description="Log de eventos de processamento do produto."
    )

    import_quality_score: Optional[float] = Field(
        None, description="Score de qualidade calculado na importação (0–100)."
    )


class ProdutoCreate(ProdutoBase):
    """Represent Produto Create and centralize its responsibilities inside this module."""
    pass


class ProdutoUpdate(ProdutoBase):
    """Represent Produto Update and centralize its responsibilities inside this module."""
    nome_base: Optional[str] = Field(None, max_length=255)


class ProdutoResponse(ProdutoBase):
    """Represent Produto Response and centralize its responsibilities inside this module."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    titulos_sugeridos: Optional[List[str]] = None
    fornecedor: Optional[FornecedorResponse] = None
    product_type: Optional[ProductTypeResponse] = None
    log_enriquecimento_web: Optional[Any] = None
    conteudo_canais: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class ProdutoBatchDeleteRequest(BaseModel):
    """Represent Produto Batch Delete Request and centralize its responsibilities inside this module."""
    produto_ids: List[int]


class ImportPreviewResponse(BaseModel):
    """Represent Import Preview Response and centralize its responsibilities inside this module."""
    file_id: int
    num_pages: int = 0
    table_pages: List[int] = Field(default_factory=list)
    sample_rows: Union[Dict[int, str], List[Dict[str, Any]]] = Field(default_factory=dict)
    preview_images: List[Dict[str, Any]] = Field(default_factory=list)
    headers: Optional[List[str]] = None
    error: Optional[str] = None


class ImportCatalogoResponse(BaseModel):
    """Represent Import Catalogo Response and centralize its responsibilities inside this module."""
    produtos_criados: List[ProdutoResponse]
    erros: List[Dict[str, Any]]


class UpdatedProductInfo(BaseModel):
    """Representa um produto atualizado durante a importação."""

    before: ProdutoResponse
    after: ProdutoResponse


class CatalogImportResult(BaseModel):
    """Represent Catalog Import Result and centralize its responsibilities inside this module."""
    created: List[ProdutoResponse]
    updated: List[ProdutoResponse]
    errors: List[Dict[str, Any]]
    stats: Optional[Dict[str, Any]] = None
    log: Optional[List[str]] = None


class CatalogImportResultPending(BaseModel):
    """Represent Catalog Import Result Pending and centralize its responsibilities inside this module."""
    ready: bool = False
    status: str
    detail: str


class ImportValidationRuleResponse(BaseModel):
    """Schema de resposta para regras de validacao aprendidas."""
    id: int
    user_id: int
    fornecedor_id: Optional[int] = None
    rule_type: str
    action: str
    min_quality_score: Optional[float] = None
    times_applied: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportQuarantineItemResponse(BaseModel):
    """Produto quarentenado aguardando revisao do usuario."""
    index: int
    nome_base: Optional[str] = None
    sku: Optional[str] = None
    quality_score: Optional[float] = None
    reason: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class ImportReviewApproveRequest(BaseModel):
    """Payload para aprovar um item quarentenado."""
    remember: bool = False
    min_quality_score: Optional[float] = None


class ImportReviewBatchApproveRequest(BaseModel):
    """Payload para aprovacao em lote por threshold de score."""
    min_quality_score: float = 45.0
    remember: bool = False


class RegionExtractionResponse(BaseModel):
    """Represent Region Extraction Response and centralize its responsibilities inside this module."""
    produtos: List[Dict[str, Any]]
    log: Optional[List[str]] = None
    preview_headers: Optional[List[str]] = None
    preview_rows: Optional[List[Dict[str, Any]]] = None


class SinglePageExtractionResponse(BaseModel):
    """Represent Single Page Extraction Response and centralize its responsibilities inside this module."""
    image: str
    text: str
    table: Optional[List[List[Any]]] = None


class ProdutoPage(BaseModel):
    """Represent Produto Page and centralize its responsibilities inside this module."""
    items: List[ProdutoResponse]
    total_items: int
    page: int
    limit: int


# Schemas para RegistroUsoIA
class RegistroUsoIABase(BaseModel):
    """Represent Registro Uso IABase and centralize its responsibilities inside this module."""
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
    """Represent Registro Uso IACreate and centralize its responsibilities inside this module."""
    pass


class RegistroUsoIAResponse(RegistroUsoIABase):
    """Represent Registro Uso IAResponse and centralize its responsibilities inside this module."""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UsoIAPage(BaseModel):
    """Represent Uso IAPage and centralize its responsibilities inside this module."""
    items: List[RegistroUsoIAResponse]
    total_items: int
    page: int
    limit: int


# Schemas para RegistroHistorico
class RegistroHistoricoBase(BaseModel):
    """Represent Registro Historico Base and centralize its responsibilities inside this module."""
    user_id: Optional[int] = None
    entidade: str
    acao: TipoAcaoSistemaEnum
    entity_id: Optional[int] = None
    detalhes_json: Optional[dict] = None


class RegistroHistoricoCreate(RegistroHistoricoBase):
    """Represent Registro Historico Create and centralize its responsibilities inside this module."""
    pass


class RegistroHistoricoResponse(RegistroHistoricoBase):
    """Represent Registro Historico Response and centralize its responsibilities inside this module."""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HistoricoPage(BaseModel):
    """Represent Historico Page and centralize its responsibilities inside this module."""
    items: List[RegistroHistoricoResponse]
    total_items: int
    page: int
    limit: int


class CatalogImportFileBase(BaseModel):
    """Represent Catalog Import File Base and centralize its responsibilities inside this module."""
    original_filename: str
    stored_filename: str
    status: str
    total_pages: Optional[int] = None
    pages_processed: Optional[int] = None
    result_summary: Optional[Dict[str, Any]] = None


class CatalogImportFileCreate(CatalogImportFileBase):
    """Represent Catalog Import File Create and centralize its responsibilities inside this module."""
    user_id: int
    fornecedor_id: Optional[int] = None


class CatalogImportFileResponse(CatalogImportFileBase):
    """Represent Catalog Import File Response and centralize its responsibilities inside this module."""
    id: int
    user_id: int
    fornecedor_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CatalogImportStatus(BaseModel):
    """Status simplificado de importação de catálogo."""

    status: Literal["PROCESSING", "DONE", "PARTIAL", "FAILED"]
    pages_total: int
    pages_processed: int
    result_ready: bool = False


class CatalogImportFilePage(BaseModel):
    """Represent Catalog Import File Page and centralize its responsibilities inside this module."""
    items: List[CatalogImportFileResponse]
    total_items: int
    page: int
    limit: int


class FornecedorImportJobBase(BaseModel):
    """Represent Fornecedor Import Job Base and centralize its responsibilities inside this module."""
    status: str
    result_summary: Optional[Dict[str, Any]] = None


class FornecedorImportJobResponse(FornecedorImportJobBase):
    """Represent Fornecedor Import Job Response and centralize its responsibilities inside this module."""
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
    """Represent Password Reset Schema and centralize its responsibilities inside this module."""
    new_password: str = Field(..., min_length=8)
    token: str


# --- Admin Analytics Schemas ---
class TotalCounts(BaseModel):
    """Represent Total Counts and centralize its responsibilities inside this module."""
    total_usuarios: int
    total_produtos: int
    total_fornecedores: int
    total_geracoes_ia_mes: int
    total_enriquecimentos_mes: int


class UsoIAPorPlano(BaseModel):
    """Represent Uso IAPor Plano and centralize its responsibilities inside this module."""
    plano_id: Optional[int] = None
    nome_plano: str
    total_geracoes_ia_no_mes: int


class UsoIAPorTipo(BaseModel):
    """Represent Uso IAPor Tipo and centralize its responsibilities inside this module."""
    tipo_acao: str
    total_no_mes: int


class UserActivity(BaseModel):
    """Represent User Activity and centralize its responsibilities inside this module."""
    user_id: int
    email: EmailStr
    nome_completo: Optional[str] = None
    created_at: datetime
    total_produtos: Optional[int] = None
    total_geracoes_ia_mes_corrente: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class ProductStatusCount(BaseModel):
    """Represent Product Status Count and centralize its responsibilities inside this module."""
    status: StatusEnriquecimentoEnum
    total: int


class RecentActivity(BaseModel):
    """Represent Recent Activity and centralize its responsibilities inside this module."""
    id: int
    user_id: int
    user_email: Optional[EmailStr] = None
    tipo_acao: TipoAcaoEnum
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardShortcut(BaseModel):
    """Represent one shortcut card in the authenticated user dashboard."""

    label: str
    description: Optional[str] = None
    route: str


class DashboardMeResponse(BaseModel):
    """Represent the non-admin dashboard payload for the authenticated user."""

    plano_nome: str
    product_experience_mode: Literal["basic", "complete"]
    limites: Dict[str, int]
    uso_mes_atual: Dict[str, int]
    totais: Dict[str, int]
    status_produtos: List[ProductStatusCount]
    atividade_recente: List[RegistroHistoricoResponse]
    atalhos: List[DashboardShortcut]


class ExternalCredentialConfigBase(BaseModel):
    """Represent the editable payload for an external credential entry."""

    provider: ExternalCredentialProviderEnum
    secret_value: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: bool = True


class ExternalCredentialConfigUpsert(ExternalCredentialConfigBase):
    """Represent an upsert request for company or personal credential config."""

    scope_type: ExternalCredentialScopeEnum


class ExternalCredentialConfigResponse(ExternalCredentialConfigBase):
    """Represent a credential config returned by the API without exposing raw subject internals."""

    id: int
    scope_type: ExternalCredentialScopeEnum
    source_label: str
    secret_masked: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EffectiveCredentialSource(BaseModel):
    """Represent the effective credential source for one provider."""

    provider: ExternalCredentialProviderEnum
    source: Literal["system", "company", "user", "none"]
    source_label: str
    configured: bool
    description: Optional[str] = None
    company_identifier: Optional[str] = None
    has_secret: bool = False
    config_json: Optional[Dict[str, Any]] = None


class CredentialsOverviewResponse(BaseModel):
    """Represent all credential settings visible to the authenticated user."""

    company_identifier: Optional[str] = None
    company_credentials: List[ExternalCredentialConfigResponse] = []
    user_credentials: List[ExternalCredentialConfigResponse] = []
    effective_sources: List[EffectiveCredentialSource] = []


class BasicGenerationTemplateConfigBase(BaseModel):
    """Represent the editable basic-mode templates for one scope."""

    title_template: Optional[str] = Field(None, max_length=2000)
    description_template: Optional[str] = Field(None, max_length=2000)
    is_active: bool = True


class BasicGenerationTemplateConfigUpsert(BasicGenerationTemplateConfigBase):
    """Represent one upsert request for basic-mode templates."""

    scope_type: ExternalCredentialScopeEnum


class BasicGenerationTemplateConfigResponse(BasicGenerationTemplateConfigBase):
    """Represent a persisted basic-mode template config."""

    id: int
    scope_type: ExternalCredentialScopeEnum
    source_label: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EffectiveBasicGenerationTemplate(BaseModel):
    """Represent the effective basic-mode template source and content."""

    source: Literal["system", "company", "user"]
    source_label: str
    title_template: str
    description_template: str
    is_custom: bool


class BasicGenerationTemplateDefaults(BaseModel):
    """Represent the built-in system defaults for basic-mode templates."""

    title_template: str
    description_template: str


class BasicGenerationTemplateOverviewResponse(BaseModel):
    """Represent all basic-mode template settings visible to the authenticated user."""

    company_identifier: Optional[str] = None
    company_config: Optional[BasicGenerationTemplateConfigResponse] = None
    user_config: Optional[BasicGenerationTemplateConfigResponse] = None
    effective_config: EffectiveBasicGenerationTemplate
    system_defaults: BasicGenerationTemplateDefaults


class AIPolicyConfigBase(BaseModel):
    """Represent one editable AI policy layer."""

    generation_default_mode: AIPolicyModeEnum = AIPolicyModeEnum.BASIC
    enrichment_default_mode: AIPolicyModeEnum = AIPolicyModeEnum.BASIC
    allow_user_override: bool = True
    allow_openai: bool = True
    allow_gemini: bool = True
    allow_attribute_ai: bool = True
    allow_web_llm: bool = True
    allow_provider_fallback: bool = True
    allow_global_learning: bool = True
    max_recovery_attempts: int = Field(1, ge=0, le=10)
    default_provider_preference: Optional[ExternalCredentialProviderEnum] = None
    is_active: bool = True


class AIPolicyConfigUpsert(AIPolicyConfigBase):
    """Represent an upsert request for one AI policy scope."""

    scope_type: AIPolicyScopeEnum
    plan_id: Optional[int] = None


class AIPolicyConfigResponse(AIPolicyConfigBase):
    """Represent one persisted or derived AI policy layer."""

    id: Optional[int] = None
    scope_type: AIPolicyScopeEnum
    source_label: str
    company_identifier: Optional[str] = None
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EffectiveAIPolicyConfig(AIPolicyConfigBase):
    """Represent the resolved effective AI policy for the current user."""

    source: Literal["system", "plan", "company", "user"]
    source_label: str


class AIPolicyOverviewResponse(BaseModel):
    """Represent all AI policy layers visible to the authenticated user."""

    company_identifier: Optional[str] = None
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    system_config: AIPolicyConfigResponse
    plan_config: Optional[AIPolicyConfigResponse] = None
    company_config: Optional[AIPolicyConfigResponse] = None
    user_config: Optional[AIPolicyConfigResponse] = None
    effective_config: EffectiveAIPolicyConfig

# ----- SCHEMAS PARA GERACAO DE CONTEUDO POR CANAL -----
class CanalPublicacaoEnum(str, Enum):
    """Represent the supported publication channels for multi-channel content generation."""

    MERCADO_LIVRE = "mercado_livre"
    GOOGLE_SHOPPING = "google_shopping"
    B2B = "b2b"
    ECOMMERCE = "ecommerce"


class CanalConteudo(BaseModel):
    """Represent content stored for a single publication channel."""

    titulo: Optional[str] = None
    descricao: Optional[str] = None
    gerado_em: Optional[str] = None


class ConteudoCanaisResponse(BaseModel):
    """Represent the API response for channel-specific content generation."""

    produto_id: int
    canal: str
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    gerado_em: Optional[str] = None


# ----- NOVOS SCHEMAS PARA SUGESTAO DE ATRIBUTOS GEMINI -----
class SugestaoAtributoItem(BaseModel):
    """Represent Sugestao Atributo Item and centralize its responsibilities inside this module."""
    chave_atributo: str = Field(
        ...,
        description="A chave do atributo para o qual o valor é sugerido (ex: 'cor', 'material').",
    )
    valor_sugerido: str = Field(
        ..., description="O valor sugerido pela IA para o atributo."
    )


class SugestoesAtributosResponse(BaseModel):
    """Represent Sugestoes Atributos Response and centralize its responsibilities inside this module."""
    sugestoes_atributos: List[SugestaoAtributoItem] = Field(
        ..., description="Lista de sugestões de atributos e seus valores."
    )
    produto_id: int = Field(
        ..., description="ID do produto para o qual as sugestões foram geradas."
    )
    modelo_ia_utilizado: Optional[str] = Field(
        None, description="Modelo de IA utilizado para a sugestão."
    )


# --- Schemas para busca unificada ---
class SearchItem(BaseModel):
    """Represent Search Item and centralize its responsibilities inside this module."""
    id: int
    type: str
    name: str


class SearchResults(BaseModel):
    """Represent Search Results and centralize its responsibilities inside this module."""
    results: List[SearchItem]


# --- Utility Schemas ---
class Msg(BaseModel):
    """Represent Msg and centralize its responsibilities inside this module."""
    msg: str


class FileProcessResponse(BaseModel):
    """Represent File Process Response and centralize its responsibilities inside this module."""
    filename: str
    original_filename: Optional[str] = None
    url: str
    message: str = "File uploaded successfully"
    mimetype: Optional[str] = None
    size_bytes: Optional[int] = None


class SocialLoginConfig(BaseModel):
    """Indica quais provedores de login social estão configurados."""

    google_enabled: bool
    facebook_enabled: bool
    product_experience_default: Literal["basic", "complete"] = "basic"
    allow_admin_experience_preview: bool = True


class RegionExtractionRequest(BaseModel):
    """Represent Region Extraction Request and centralize its responsibilities inside this module."""
    import_file_id: int
    page_number: int
    region: List[float]


class CatalogRegionPreviewRequest(BaseModel):
    """Represent Catalog Region Preview Request and centralize its responsibilities inside this module."""
    file_id: str
    page_number: int
    region: Optional[List[float]] = None


class PdfRegionBulkRequest(BaseModel):
    """Represent Pdf Region Bulk Request and centralize its responsibilities inside this module."""
    file_id: int
    region: List[float]
    pages: Optional[List[int]] = None
    all_pages: Optional[bool] = False


class CatalogPreview(BaseModel):
    """Represent Catalog Preview and centralize its responsibilities inside this module."""
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
CatalogImportResultPending.model_rebuild()
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
BasicGenerationTemplateConfigResponse.model_rebuild()
EffectiveBasicGenerationTemplate.model_rebuild()
BasicGenerationTemplateDefaults.model_rebuild()
BasicGenerationTemplateOverviewResponse.model_rebuild()
AIPolicyConfigResponse.model_rebuild()
EffectiveAIPolicyConfig.model_rebuild()
AIPolicyOverviewResponse.model_rebuild()
ConteudoCanaisResponse.model_rebuild()
CanalConteudo.model_rebuild()

