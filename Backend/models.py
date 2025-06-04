from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy_json import mutable_json_type
from Backend.database import Base
import enum
from typing import Optional

# Enums de Status
class StatusEnriquecimentoEnum(str, enum.Enum):
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    CONCLUIDO_FALHA = "CONCLUIDO_FALHA"
    IGNORADO = "IGNORADO"

class StatusGeracaoIAEnum(str, enum.Enum):
    PENDENTE = "PENDENTE"
    EM_PROCESSAMENTO = "EM_PROCESSAMENTO"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    CONCLUIDO_FALHA = "CONCLUIDO_FALHA"
    REVISAR_MANUALMENTE = "REVISAR_MANUALMENTE"
    NAO_APLICAVEL = "NAO_APLICAVEL"

class AttributeFieldTypeEnum(str, enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"
    DATE = "date"
    BOOLEAN = "boolean"
    # Adicionar outros tipos se necessário, como MULTISELECT

class TipoAcaoIAEnum(str, enum.Enum):
    GERACAO_TITULO = "geracao_titulo"
    GERACAO_DESCRICAO = "geracao_descricao"
    SUGESTAO_ATRIBUTOS = "sugestao_atributos"
    ENRIQUECIMENTO_WEB = "enriquecimento_web"
    ANALISE_DADOS = "analise_dados"

# Mixin para campos de timestamp
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(255))

    users = relationship("User", back_populates="role")

class Plano(TimestampMixin, Base):
    __tablename__ = "planos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, index=True, nullable=False)
    descricao = Column(String(500))
    preco_mensal = Column(Float, nullable=False, default=0.0)
    limite_produtos = Column(Integer, nullable=False, default=0)
    limite_enriquecimento_web = Column(Integer, nullable=False, default=0)
    limite_geracao_ia = Column(Integer, nullable=False, default=0)
    permite_api_externa = Column(Boolean, nullable=False, default=False)
    suporte_prioritario = Column(Boolean, nullable=False, default=False)
    # Adicionar data de expiração se for um plano com validade
    data_expiracao_plano = Column(DateTime(timezone=True))


    users = relationship("User", back_populates="plano")

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    nome_completo = Column(String(100))
    idioma_preferido = Column(String(10), default="pt-BR")
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    provider = Column(String(50), nullable=True) # Ex: "google", "facebook"
    provider_user_id = Column(String(255), nullable=True, unique=True) # ID do usuário no provedor OAuth
    
    # Chaves de API pessoais
    chave_openai_pessoal = Column(String(255), nullable=True)
    chave_google_gemini_pessoal = Column(String(255), nullable=True)

    # Limites personalizados (se o plano permitir sobrescrever ou para admins)
    limite_produtos = Column(Integer, nullable=True)
    limite_enriquecimento_web = Column(Integer, nullable=True)
    limite_geracao_ia = Column(Integer, nullable=True)

    # Relacionamentos
    role_id = Column(Integer, ForeignKey("roles.id"), default=lambda: 2) # Default para 'user' role
    role = relationship("Role", back_populates="users")

    plano_id = Column(Integer, ForeignKey("planos.id"), nullable=True)
    plano = relationship("Plano", back_populates="users")

    fornecedores = relationship("Fornecedor", back_populates="owner", cascade="all, delete-orphan")
    produtos = relationship("Produto", back_populates="owner", cascade="all, delete-orphan")
    product_types = relationship("ProductType", back_populates="owner", cascade="all, delete-orphan")
    registros_uso_ia = relationship("RegistroUsoIA", back_populates="user", cascade="all, delete-orphan")


class Fornecedor(TimestampMixin, Base):
    __tablename__ = "fornecedores"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), index=True, nullable=False)
    contato_principal = Column(String(100))
    email_contato = Column(String(255))
    telefone_contato = Column(String(20))
    site_url = Column(String(255))
    link_busca_padrao = Column(String(255))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="fornecedores")

    produtos = relationship("Produto", back_populates="fornecedor", cascade="all, delete-orphan")


class ProductType(TimestampMixin, Base):
    __tablename__ = "product_types"
    id = Column(Integer, primary_key=True, index=True)
    key_name = Column(String(100), unique=True, index=True, nullable=False) # Ex: eletronico, roupa
    friendly_name = Column(String(150), nullable=False) # Ex: Eletrônico, Vestuário
    description = Column(String(500))

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # None for global types
    owner = relationship("User", back_populates="product_types")

    attribute_templates = relationship("AttributeTemplate", back_populates="product_type", cascade="all, delete-orphan")
    products = relationship("Produto", back_populates="product_type")


class AttributeTemplate(TimestampMixin, Base):
    __tablename__ = "attribute_templates"
    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
    attribute_key = Column(String(100), index=True, nullable=False) # Ex: voltagem, tamanho, cor
    label = Column(String(150), nullable=False)
    field_type = Column(SQLEnum(AttributeFieldTypeEnum), nullable=False)
    options = Column(JSON, nullable=True) # Para select/multiselect, armazenado como JSON array
    is_required = Column(Boolean, default=False)
    is_filtrable = Column(Boolean, default=False)
    tooltip_text = Column(String(255))
    default_value = Column(String(255))
    display_order = Column(Integer, default=0)

    product_type = relationship("ProductType", back_populates="attribute_templates")


class Produto(TimestampMixin, Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome_base = Column(String(255), index=True, nullable=False)
    nome_chat_api = Column(String(255))
    descricao_original = Column(Text)
    descricao_curta_orig = Column(String(500))
    descricao_chat_api = Column(Text)
    descricao_curta_chat_api = Column(String(500))

    sku = Column(String(100), unique=True, index=True)
    ean = Column(String(100))
    ncm = Column(String(20))

    marca = Column(String(100))
    modelo = Column(String(100))
    categoria_original = Column(String(150))
    categoria_mapeada = Column(String(150))

    preco_custo = Column(Float)
    preco_venda = Column(Float)
    preco_promocional = Column(Float)
    estoque_disponivel = Column(Integer)

    peso_kg = Column(Float)
    altura_cm = Column(Float)
    largura_cm = Column(Float)
    profundidade_cm = Column(Float)

    # --- CAMPOS DE MÍDIA E LOG ATUALIZADOS/ADICIONADOS AQUI ---
    # `imagens_produto` e `videos_produto` serão JSON que armazenam listas de dicts
    # A recomendação é usar mutable_json_type para garantir que alterações no Python sejam detectadas pelo SQLAlchemy
    imagens_produto = Column(mutable_json_type(dbtype=JSON(), nested=True), default=[])
    videos_produto = Column(mutable_json_type(dbtype=JSON(), nested=True), default=[])
    log_enriquecimento_web = Column(mutable_json_type(dbtype=JSON(), nested=True), default=lambda: {"historico_mensagens": []}) # Inicializa com estrutura de log
    # --- FIM DOS CAMPOS DE MÍDIA E LOG ---

    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    fornecedor = relationship("Fornecedor", back_populates="produtos")

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="produtos")

    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=True)
    product_type = relationship("ProductType", back_populates="products")

    # Atributos dinâmicos e dados brutos originais
    dynamic_attributes = Column(mutable_json_type(dbtype=JSON(), nested=True), default={})
    dados_brutos = Column(mutable_json_type(dbtype=JSON(), nested=True), default={})

    ativo_marketplace = Column(Boolean, default=False)
    data_publicacao_marketplace = Column(DateTime(timezone=True))

    status_enriquecimento_web = Column(SQLEnum(StatusEnriquecimentoEnum), nullable=False, default=StatusEnriquecimentoEnum.PENDENTE)
    status_titulo_ia = Column(SQLEnum(StatusGeracaoIAEnum), nullable=False, default=StatusGeracaoIAEnum.PENDENTE)
    status_descricao_ia = Column(SQLEnum(StatusGeracaoIAEnum), nullable=False, default=StatusGeracaoIAEnum.PENDENTE)


class RegistroUsoIA(TimestampMixin, Base):
    __tablename__ = "registros_uso_ia"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tipo_acao = Column(SQLEnum(TipoAcaoIAEnum), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=True) # Pode ser nulo se a ação não for sobre um produto específico
    provedor_ia = Column(String(50)) # Ex: "OpenAI", "Google Gemini"
    modelo_usado = Column(String(100)) # Ex: "gpt-4", "gemini-pro"
    prompt_utilizado = Column(Text)
    resposta_ia_raw = Column(Text)
    tokens_entrada = Column(Integer, default=0)
    tokens_saida = Column(Integer, default=0)
    custo_estimado = Column(Float, default=0.0)

    user = relationship("User", back_populates="registros_uso_ia")
    produto = relationship("Produto", backref="registros_ia_associados") # backref para associação de volta no Produto

# Adicionar a chamada para User.model_rebuild() no final se houver referências circulares complexas
# ou se você estiver usando Pydantic 2.x e SQLAlchemy 1.x ou mais recentes com esta configuração
# No entanto, para modelos SQLAlchemy, o back_populates já lida com a maioria das referências