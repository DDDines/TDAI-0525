# Backend/models.py
import enum
from sqlalchemy import (Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Date, Enum as SQLAlchemyEnum, func) # ADICIONADO func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base # MANTIDO (se não estiver usando Mapped)
# from sqlalchemy.orm import Mapped, mapped_column # Se fosse usar a sintaxe mais nova do SQLAlchemy 2.0+
from datetime import datetime, timezone

from core.config import settings

Base = declarative_base()

# --- ENUMS ---
class StatusEnriquecimentoEnum(enum.Enum):
    NAO_INICIADO = "NAO_INICIADO"
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO = "CONCLUIDO"
    FALHA = "FALHA"

class StatusGeracaoIAEnum(enum.Enum):
    NAO_INICIADO = "NAO_INICIADO"
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO = "CONCLUIDO"
    FALHA = "FALHA"
    NAO_APLICAVEL = "NAO_APLICAVEL"

class AttributeFieldTypeEnum(enum.Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    SELECT = "SELECT"
    MULTI_SELECT = "MULTI_SELECT"
    TEXTAREA = "TEXTAREA"

class TipoAcaoIAEnum(enum.Enum):
    GERACAO_TITULO_CURTO = "geracao_titulo_curto"
    GERACAO_TITULO_LONGO = "geracao_titulo_longo"
    GERACAO_DESCRICAO_CURTA = "geracao_descricao_curta"
    GERACAO_DESCRICAO_LONGA = "geracao_descricao_longa"
    GERACAO_PALAVRAS_CHAVE = "geracao_palavras_chave"
    ANALISE_SENTIMENTO = "analise_sentimento"
    ENRIQUECIMENTO_WEB_PRODUTO = "enriquecimento_web_produto"
    OUTRA_ACAO_IA = "outra_acao_ia"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    nome_completo = Column(String, index=True)
    idioma_preferido = Column(String, default="pt-BR")
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    plano_id = Column(Integer, ForeignKey("planos.id"), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)

    limite_produtos = Column(Integer, default=settings.DEFAULT_LIMIT_PRODUTOS_SEM_PLANO)
    limite_enriquecimento_web = Column(Integer, default=settings.DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO)
    limite_geracao_ia = Column(Integer, default=settings.DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO)
    data_expiracao_plano = Column(DateTime(timezone=True), nullable=True)

    chave_openai_pessoal = Column(String, nullable=True)
    chave_google_gemini_pessoal = Column(String, nullable=True)

    provider = Column(String, nullable=True)
    provider_user_id = Column(String, nullable=True, unique=True, index=True)

    reset_password_token = Column(String, nullable=True, unique=True, index=True)
    reset_password_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # --- TIMESTAMPS ALTERADOS ---
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True) # nullable=True se pode não ser atualizado na criação ou se for opcional

    plano = relationship("Plano", back_populates="usuarios")
    role = relationship("Role", back_populates="usuarios")
    produtos = relationship("Produto", back_populates="owner", cascade="all, delete-orphan")
    fornecedores = relationship("Fornecedor", back_populates="owner", cascade="all, delete-orphan")
    product_types = relationship("ProductType", back_populates="owner", cascade="all, delete-orphan")
    registros_uso_ia = relationship("RegistroUsoIA", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    usuarios = relationship("User", back_populates="role")


class Plano(Base):
    __tablename__ = "planos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    descricao = Column(String, nullable=True)
    preco_mensal = Column(Float, default=0.0)
    limite_produtos = Column(Integer, default=10)
    limite_enriquecimento_web = Column(Integer, default=20)
    limite_geracao_ia = Column(Integer, default=50)
    permite_api_externa = Column(Boolean, default=False)
    suporte_prioritario = Column(Boolean, default=False)
    
    usuarios = relationship("User", back_populates="plano")


class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nome = Column(String, index=True, nullable=False)
    contato_principal = Column(String, nullable=True)
    email_contato = Column(String, nullable=True)
    telefone_contato = Column(String, nullable=True)
    site_url = Column(String, nullable=True)
    link_busca_padrao = Column(String, nullable=True)

    # --- TIMESTAMPS ALTERADOS ---
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    owner = relationship("User", back_populates="fornecedores")
    produtos = relationship("Produto", back_populates="fornecedor")


class Produto(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=True)

    nome_base = Column(String, index=True, nullable=False)
    nome_chat_api = Column(String, nullable=True, index=True)
    descricao_original = Column(Text, nullable=True)
    descricao_curta_orig = Column(String, nullable=True)
    descricao_chat_api = Column(Text, nullable=True)
    descricao_curta_chat_api = Column(String, nullable=True)
    
    sku = Column(String, index=True, nullable=True)
    ean = Column(String, index=True, nullable=True)
    ncm = Column(String, index=True, nullable=True)
    marca = Column(String, index=True, nullable=True)
    modelo = Column(String, index=True, nullable=True)
    categoria_original = Column(String, index=True, nullable=True)
    categoria_mapeada = Column(String, index=True, nullable=True)

    preco_custo = Column(Float, nullable=True)
    preco_venda = Column(Float, nullable=True)
    preco_promocional = Column(Float, nullable=True)
    estoque_disponivel = Column(Integer, nullable=True)

    peso_kg = Column(Float, nullable=True)
    altura_cm = Column(Float, nullable=True)
    largura_cm = Column(Float, nullable=True)
    profundidade_cm = Column(Float, nullable=True)

    imagem_principal_url = Column(String, nullable=True)
    imagens_secundarias_urls = Column(JSON, nullable=True)

    dynamic_attributes = Column(JSON, nullable=True)
    dados_brutos = Column(JSON, nullable=True)

    status_enriquecimento_web = Column(SQLAlchemyEnum(StatusEnriquecimentoEnum), default=StatusEnriquecimentoEnum.NAO_INICIADO)
    status_titulo_ia = Column(SQLAlchemyEnum(StatusGeracaoIAEnum), default=StatusGeracaoIAEnum.NAO_INICIADO)
    status_descricao_ia = Column(SQLAlchemyEnum(StatusGeracaoIAEnum), default=StatusGeracaoIAEnum.NAO_INICIADO)
    
    ativo_marketplace = Column(Boolean, default=False)
    data_publicacao_marketplace = Column(DateTime(timezone=True), nullable=True)
    
    # Mantendo seus nomes originais data_criacao e data_atualizacao se preferir
    # data_criacao = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # data_atualizacao = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)
    # Ou usando created_at/updated_at para padronizar:
    created_at = Column(DateTime(timezone=True), name="data_criacao", server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), name="data_atualizacao", server_default=func.now(), onupdate=func.now(), nullable=True)


    owner = relationship("User", back_populates="produtos")
    fornecedor = relationship("Fornecedor", back_populates="produtos")
    product_type = relationship("ProductType", back_populates="produtos")
    registros_uso_ia = relationship("RegistroUsoIA", back_populates="produto", cascade="all, delete-orphan")


class ProductType(Base):
    __tablename__ = "product_types"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    key_name = Column(String, index=True, nullable=False) # Considere adicionar UniqueConstraint com user_id
    friendly_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # --- TIMESTAMPS ALTERADOS ---
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    owner = relationship("User", back_populates="product_types")
    attribute_templates = relationship("AttributeTemplate", back_populates="product_type", cascade="all, delete-orphan", lazy="selectin")
    produtos = relationship("Produto", back_populates="product_type")


class AttributeTemplate(Base):
    __tablename__ = "attribute_templates"
    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
    
    attribute_key = Column(String, nullable=False)
    label = Column(String, nullable=False)
    field_type = Column(SQLAlchemyEnum(AttributeFieldTypeEnum), nullable=False)
    
    is_required = Column(Boolean, default=False)
    is_filtrable = Column(Boolean, default=False) # Se o atributo pode ser usado em filtros de busca
    display_order = Column(Integer, default=0)
    
    options = Column(JSON, nullable=True) # Para SELECT, MULTI_SELECT
    
    default_value = Column(String, nullable=True)
    tooltip_text = Column(String, nullable=True)
    
    # --- TIMESTAMPS ALTERADOS ---
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    product_type = relationship("ProductType", back_populates="attribute_templates")


class RegistroUsoIA(Base):
    __tablename__ = "registros_uso_ia"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=True)

    tipo_acao = Column(SQLAlchemyEnum(TipoAcaoIAEnum), nullable=False)
    provedor_ia = Column(String, nullable=True)
    modelo_usado = Column(String, nullable=True)
    
    tokens_entrada = Column(Integer, default=0)
    tokens_saida = Column(Integer, default=0)
    custo_estimado = Column(Float, default=0.0)
    
    prompt_utilizado = Column(Text, nullable=True)
    resposta_ia_raw = Column(Text, nullable=True)
    
    # --- TIMESTAMP ÚNICO ---
    # Renomeado de 'timestamp' para 'created_at' para padronização, e usando server_default
    created_at = Column(DateTime(timezone=True), name="timestamp", server_default=func.now(), index=True, nullable=False)

    user = relationship("User", back_populates="registros_uso_ia")
    produto = relationship("Produto", back_populates="registros_uso_ia")