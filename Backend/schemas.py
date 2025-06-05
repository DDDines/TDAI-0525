# Backend/schemas.py

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, EmailStr, HttpUrl, Field, field_validator, model_validator
from datetime import datetime
import json # Para validação de JSON string

# É crucial que a importação de 'models' funcione corretamente.
# Se 'models' estiver no mesmo diretório ou em um caminho Python reconhecido,
# a importação direta pode funcionar. Caso contrário, pode ser necessário um ajuste
# relativo ou absoluto dependendo de como o projeto é executado.
# Assumindo que 'models.py' está no mesmo diretório (Backend) e é acessível:
from models import StatusEnriquecimentoEnum, StatusGeracaoIAEnum, TipoAcaoIAEnum, AttributeFieldTypeEnum

# Schemas de Autenticação e Usuário
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None # Adicionado para identificar o usuário pelo ID

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

class UserCreateOAuth(UserBase): # Para criação via OAuth
    provider: Optional[str] = None
    provider_user_id: Optional[str] = None
    # Não requer password na criação OAuth

class UserUpdate(BaseModel): # O que o próprio usuário pode atualizar
    email: Optional[EmailStr] = None
    nome_completo: Optional[str] = None
    password: Optional[str] = None # Para alteração de senha
    idioma_preferido: Optional[str] = None
    chave_openai_pessoal: Optional[str] = None
    chave_google_gemini_pessoal: Optional[str] = None

class UserUpdateByAdmin(UserUpdate): # O que um admin pode atualizar em qualquer usuário
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    plano_id: Optional[int] = None
    role_id: Optional[int] = None
    limite_produtos: Optional[int] = None
    limite_enriquecimento_web: Optional[int] = None
    limite_geracao_ia: Optional[int] = None
    data_expiracao_plano: Optional[datetime] = None

class UserUpdateOAuth(BaseModel): # Dados que podem ser atualizados via OAuth (ex: nome, se mudar no provedor)
    nome_completo: Optional[str] = None
    # Outros campos que o OAuth possa fornecer e queiramos atualizar

class UserResponse(UserBase): # O que é retornado pela API
    id: int
    created_at: datetime
    updated_at: datetime
    limite_produtos: Optional[int] = None
    limite_enriquecimento_web: Optional[int] = None
    limite_geracao_ia: Optional[int] = None
    data_expiracao_plano: Optional[datetime] = None
    # Adicionar informações do plano e role se desejado na resposta
    # plano: Optional[PlanoResponse] = None # Evitar dependência circular aqui, resolver no router
    # role: Optional[RoleResponse] = None  # Evitar dependência circular

    class Config:
        from_attributes = True

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
    name: Optional[str] = Field(None, min_length=3, max_length=50) # Tornar opcional na atualização

class RoleResponse(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # users: List[UserResponse] = [] # Cuidado com recursão, talvez apenas IDs ou omitir

    class Config:
        from_attributes = True

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
    # Demais campos também opcionais na atualização, se desejado

class PlanoResponse(PlanoBase):
    id: int
    created_at: datetime
    updated_at: datetime
    # users: List[UserResponse] = [] # Cuidado com recursão

    class Config:
        from_attributes = True


# Adicionar UserResponse ao final para resolver dependência circular se PlanoResponse referenciar UserResponse
UserResponse.model_rebuild()


# Schemas para Fornecedor
class FornecedorBase(BaseModel):
    nome: str = Field(..., max_length=200)
    email_contato: Optional[EmailStr] = None
    telefone_contato: Optional[str] = Field(None, max_length=20)
    endereco: Optional[str] = None
    site_url: Optional[HttpUrl] = None
    termos_contratuais: Optional[str] = None
    contato_principal: Optional[str] = Field(None, max_length=100)
    observacoes: Optional[str] = None
    link_busca_padrao: Optional[HttpUrl] = None # Link base para buscar produtos deste fornecedor

class FornecedorCreate(FornecedorBase):
    pass

class FornecedorUpdate(FornecedorBase):
    # Tornar campos opcionais para atualização parcial
    nome: Optional[str] = Field(None, max_length=200)
    # Adicionar Optional para todos os outros campos se desejar atualização parcial

class FornecedorResponse(FornecedorBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Schemas para AttributeTemplate
class AttributeTemplateBase(BaseModel):
    attribute_key: str = Field(..., description="Chave única do atributo no template (ex: 'cor', 'tamanho_tela').")
    label: str = Field(..., description="Nome amigável do atributo para exibição (ex: 'Cor', 'Tamanho da Tela').")
    field_type: AttributeFieldTypeEnum = Field(AttributeFieldTypeEnum.TEXT, description="Tipo de campo para o atributo (text, number, boolean, select, multiselect, date).")
    description: Optional[str] = Field(None, description="Descrição ou ajuda sobre o atributo.")
    default_value: Optional[str] = Field(None, description="Valor padrão para o atributo (string, pode precisar de conversão).")
    options: Optional[Union[List[str], str]] = Field(None, description="Lista de opções para tipos 'select' ou 'multiselect', pode ser string JSON.")
    is_required: bool = Field(False, description="Indica se o atributo é obrigatório.")
    is_filterable: bool = Field(False, description="Indica se o atributo pode ser usado para filtros.")
    display_order: int = Field(0, description="Ordem de exibição do atributo.")

    @field_validator('options', mode='before')
    @classmethod
    def parse_json_options(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                parsed_value = json.loads(value)
                if not isinstance(parsed_value, list):
                    raise ValueError("String JSON para 'options' deve representar uma lista.")
                return parsed_value # Retorna a lista Python
            except json.JSONDecodeError:
                raise ValueError("String para 'options' não é um JSON válido.")
        return value # Se já for lista ou None, retorna como está

class AttributeTemplateCreate(AttributeTemplateBase):
    pass # product_type_id será atribuído no CRUD

class AttributeTemplateUpdate(AttributeTemplateBase):
    # Todos os campos são opcionais na atualização
    attribute_key: Optional[str] = None
    label: Optional[str] = None
    field_type: Optional[AttributeFieldTypeEnum] = None
    # ... tornar todos os outros campos Optional

class AttributeTemplateResponse(AttributeTemplateBase):
    id: int
    product_type_id: int
    options: Optional[List[str]] = None # Garante que a resposta seja uma lista

    class Config:
        from_attributes = True


# Schemas para ProductType
class ProductTypeBase(BaseModel):
    key_name: str = Field(..., description="Chave única para identificar o tipo de produto (ex: 'smartphones', 'camisetas_manga_longa').")
    friendly_name: str = Field(..., description="Nome amigável do tipo de produto (ex: 'Smartphones', 'Camisetas Manga Longa').")
    description: Optional[str] = Field(None, description="Descrição do tipo de produto.")

class ProductTypeCreate(ProductTypeBase):
    attribute_templates: List[AttributeTemplateCreate] = []

class ProductTypeUpdate(ProductTypeBase):
    key_name: Optional[str] = None
    friendly_name: Optional[str] = None
    # attribute_templates: Opcionalmente, permitir atualizar/adicionar/remover atributos aqui,
    # mas geralmente é melhor ter endpoints separados para gerenciar atributos de um tipo.

class ProductTypeResponse(ProductTypeBase):
    id: int
    user_id: Optional[int] = None # Tipos podem ser globais (user_id=None) ou específicos do usuário
    attribute_templates: List[AttributeTemplateResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Schemas para Produto
class ProdutoBase(BaseModel):
    nome_base: str = Field(..., max_length=255, description="Nome principal ou base do produto.")
    nome_chat_api: Optional[str] = Field(None, max_length=255, description="Nome otimizado ou gerado pela IA.")
    descricao_original: Optional[str] = Field(None, description="Descrição original fornecida ou importada.")
    descricao_chat_api: Optional[str] = Field(None, description="Descrição otimizada ou gerada pela IA.")
    
    sku: Optional[str] = Field(None, max_length=100, index=True, description="SKU (Stock Keeping Unit) do produto.")
    ean: Optional[str] = Field(None, max_length=13, index=True, description="EAN (European Article Number) / GTIN.")
    ncm: Optional[str] = Field(None, max_length=8, description="NCM (Nomenclatura Comum do Mercosul).")
    
    marca: Optional[str] = Field(None, max_length=100)
    modelo: Optional[str] = Field(None, max_length=100)
    
    preco_custo: Optional[float] = Field(None, ge=0)
    preco_venda: Optional[float] = Field(None, ge=0)
    margem_lucro: Optional[float] = Field(None, description="Calculado ou informado.")
    
    estoque_disponivel: Optional[int] = Field(None, ge=0)
    peso_gramas: Optional[int] = Field(None, ge=0)
    dimensoes_cm: Optional[str] = Field(None, max_length=50, description="Ex: 10x15x20 (AxLxP)")
    
    fornecedor_id: Optional[int] = None
    product_type_id: Optional[int] = None # ID do Tipo de Produto associado
    
    categoria_original: Optional[str] = Field(None, max_length=150)
    categoria_mapeada: Optional[str] = Field(None, max_length=150)
    tags_palavras_chave: Optional[List[str]] = Field(None) # Lista de strings
    
    imagem_principal_url: Optional[HttpUrl] = None
    imagens_secundarias_urls: Optional[List[HttpUrl]] = Field(None) # Lista de URLs
    video_url: Optional[HttpUrl] = None
    
    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = StatusEnriquecimentoEnum.NAO_INICIADO
    status_titulo_ia: Optional[StatusGeracaoIAEnum] = StatusGeracaoIAEnum.NAO_INICIADO
    status_descricao_ia: Optional[StatusGeracaoIAEnum] = StatusGeracaoIAEnum.NAO_INICIADO
    
    dados_brutos_web: Optional[Dict[str, Any]] = Field(None, description="JSON com dados extraídos da web (textos, metadados).")
    # dynamic_attributes deveria ser Dict[str, Any] para Pydantic v2
    # Se estiver usando Pydantic v1, Json[Dict[str,Any]] pode ser necessário se esperar uma string JSON
    dynamic_attributes: Optional[Dict[str, Any]] = Field(None, description="Atributos dinâmicos baseados no ProductType (JSON).")

    # Campo para logs ou histórico de processamento do produto
    log_processamento: Optional[List[Dict[str, Any]]] = Field(None, description="Log de eventos de processamento do produto.")


class ProdutoCreate(ProdutoBase):
    # Campos que podem ser diferentes ou adicionais na criação
    pass

class ProdutoUpdate(ProdutoBase):
    # Todos os campos são opcionais na atualização
    nome_base: Optional[str] = Field(None, max_length=255)
    # ... tornar todos os outros campos Optional se não forem obrigatórios na atualização
    # Adicionar aqui campos que só podem ser atualizados e não criados, se houver

class ProdutoResponse(ProdutoBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    # Incluir informações do fornecedor e tipo de produto se desejado na resposta
    fornecedor: Optional[FornecedorResponse] = None
    product_type: Optional[ProductTypeResponse] = None # Resposta completa do ProductType
    
    # No Pydantic V2, `model_config` substitui `Config` para `from_attributes`
    class Config:
        from_attributes = True # Para permitir conversão de modelos SQLAlchemy


# Schema para a requisição de deleção em lote de produtos
class ProdutoBatchDeleteRequest(BaseModel):
    produto_ids: List[int]


# Schemas para RegistroUsoIA
class RegistroUsoIABase(BaseModel):
    user_id: int
    produto_id: Optional[int] = None
    tipo_acao: TipoAcaoIAEnum
    provedor_ia: Optional[str] = None
    modelo_ia: Optional[str] = None
    prompt_utilizado: Optional[str] = None
    resposta_ia: Optional[str] = None # Pode ser grande, considere omitir da resposta padrão
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

    class Config:
        from_attributes = True

class UsoIAPage(BaseModel):
    items: List[RegistroUsoIAResponse]
    total_items: int
    page: int
    limit: int

# Schemas para Analytics do Admin
class AdminAnalyticsOverview(BaseModel):
    total_usuarios: int
    total_produtos_ativos: int # Ajustar conforme a definição de "ativo"
    total_fornecedores: int
    geracoes_ia_mes_corrente: int
    enriquecimentos_web_mes_corrente: int

class UsoIAPorPlanoResponse(BaseModel):
    plano_id: Optional[int] = None
    nome_plano: str
    total_geracoes_ia_no_mes: int

class UsoIAPorUsuarioResponse(BaseModel):
    user_id: int
    email_usuario: EmailStr
    nome_plano: Optional[str] = "Sem Plano"
    total_geracoes_ia_no_mes: int

class UsoIAPorTipoAcaoResponse(BaseModel):
    tipo_acao: str # Usar o valor do enum string
    total_no_mes: int

class UserActivityResponse(BaseModel):
    user_id: int
    email: EmailStr
    nome_completo: Optional[str] = None
    created_at: datetime
    total_produtos_count: int = 0
    total_geracoes_ia_mes_corrente_count: int = 0
    # Adicionar mais métricas se necessário

    class Config:
        from_attributes = True # Para construir a partir de objetos User com atributos adicionados


# ----- NOVOS SCHEMAS PARA SUGESTÃO DE ATRIBUTOS GEMINI -----
class SugestaoAtributoItem(BaseModel):
    chave_atributo: str = Field(..., description="A chave do atributo para o qual o valor é sugerido (ex: 'cor', 'material').")
    valor_sugerido: str = Field(..., description="O valor sugerido pela IA para o atributo.")

class SugestoesAtributosResponse(BaseModel):
    sugestoes_atributos: List[SugestaoAtributoItem] = Field(..., description="Lista de sugestões de atributos e seus valores.")
    produto_id: int = Field(..., description="ID do produto para o qual as sugestões foram geradas.")
    modelo_ia_utilizado: Optional[str] = Field(None, description="Modelo de IA utilizado para a sugestão.")

class ProdutoContextoParaSugestao(BaseModel): # Exemplo, não usado diretamente pelo endpoint atual
    nome_base: Optional[str] = None
    descricao_original: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    sku: Optional[str] = None
    ean: Optional[str] = None
    categoria_original: Optional[str] = None
    dados_brutos_web: Optional[Dict[str, Any]] = None
    atributos_atuais: Optional[Dict[str, Any]] = None

class GeracaoSugestaoAtributoRequest(BaseModel): # Exemplo, não usado diretamente pelo endpoint atual
    produto_id: int
# ----- FIM DOS NOVOS SCHEMAS -----


# Schema para paginação genérica de produtos
class ProdutoPage(BaseModel):
    items: List[ProdutoResponse]
    total_items: int
    page: int # O número da página atual (base 0)
    limit: int # O limite de itens por página

# Assegurar que UserResponse possa ser construído a partir de atributos de modelos SQLAlchemy
UserResponse.model_rebuild()
PlanoResponse.model_rebuild()
RoleResponse.model_rebuild()
FornecedorResponse.model_rebuild()
AttributeTemplateResponse.model_rebuild()
ProductTypeResponse.model_rebuild()
ProdutoResponse.model_rebuild()
RegistroUsoIAResponse.model_rebuild()
UserActivityResponse.model_rebuild()
