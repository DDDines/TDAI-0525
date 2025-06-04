# Backend/models.py
import enum
from sqlalchemy import (Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, Date, Enum as SQLAlchemyEnum, func)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

from core.config import settings

Base = declarative_base()

# --- Timestamp Mixin ---
# ASSUMINDO que esta é a definição do seu TimestampMixin
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

# --- ENUMS ---
class StatusEnriquecimentoEnum(enum.Enum):
    NAO_INICIADO = "NAO_INICIADO"
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO = "CONCLUIDO"
    FALHA = "FALHA"
    # Adicionados status mais detalhados para enriquecimento
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    CONCLUIDO_COM_DADOS_PARCIAIS = "CONCLUIDO_COM_DADOS_PARCIAIS"
    NENHUMA_FONTE_ENCONTRADA = "NENHUMA_FONTE_ENCONTRADA"
    FALHA_CONFIGURACAO_API_EXTERNA = "FALHA_CONFIGURACAO_API_EXTERNA" # Ex: Google CSE API key faltando
    FALHA_API_EXTERNA = "FALHA_API_EXTERNA" # Ex: API externa retornou erro ou rate limit

class StatusGeracaoIAEnum(enum.Enum):
    NAO_INICIADO = "NAO_INICIADO"
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO = "CONCLUIDO"
    FALHA = "FALHA"
    NAO_APLICAVEL = "NAO_APLICAVEL"
    # Adicionados status mais detalhados para geração IA
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    LIMITE_ATINGIDO = "LIMITE_ATINGIDO"
    FALHA_CONFIGURACAO_IA = "FALHA_CONFIGURACAO_IA" # Ex: OpenAI key faltando
    FALHA_GERACAO_CONTEUDO = "FALHA_GERACAO_CONTEUDO" # Erro na geração sem ser limite ou config

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
    # Tipos de ação mais detalhados para logging
    ENRIQUECIMENTO_BUSCA_GOOGLE = "enriquecimento_busca_google"
    ENRIQUECIMENTO_SCRAPING = "enriquecimento_scraping"
    ENRIQUECIMENTO_EXTRACAO_LLM = "enriquecimento_extracao_llm"
    GERACAO_TITULO_IA = "geracao_titulo_ia"
    GERACAO_DESCRICAO_IA = "geracao_descricao_ia"
    VALIDACAO_CONTEUDO_IA = "validacao_conteudo_ia"
    OUTRA_ACAO_IA = "outra_acao_ia"


class User(TimestampMixin, Base): # Herda de TimestampMixin
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True} # ADICIONADO
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
    
    plano = relationship("Plano", back_populates="usuarios")
    role = relationship("Role", back_populates="usuarios")
    produtos = relationship("Produto", back_populates="owner", cascade="all, delete-orphan")
    fornecedores = relationship("Fornecedor", back_populates="owner", cascade="all, delete-orphan")
    product_types = relationship("ProductType", back_populates="owner", cascade="all, delete-orphan")
    registros_uso_ia = relationship("RegistroUsoIA", back_populates="user", cascade="all, delete-orphan")


class Role(TimestampMixin, Base): # Herda de TimestampMixin (conforme seu traceback)
    __tablename__ = "roles"
    __table_args__ = {'extend_existing': True} # ADICIONADO
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    usuarios = relationship("User", back_populates="role")


class Plano(TimestampMixin, Base): # Herda de TimestampMixin
    __tablename__ = "planos"
    __table_args__ = {'extend_existing': True} # ADICIONADO
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    descricao = Column(String, nullable=True)
    preco_mensal = Column(Float, default=0.0)
    # Renomeando para max_titulos_mes e max_descricoes_mes para clareza
    max_titulos_mes = Column(Integer, default=50) # Novo nome
    max_descricoes_mes = Column(Integer, default=50) # Novo nome
    limite_produtos = Column(Integer, default=10)
    limite_enriquecimento_web = Column(Integer, default=20)
    limite_geracao_ia = Column(Integer, default=50) # Mantido para compatibilidade, mas os dois acima são mais específicos
    permite_api_externa = Column(Boolean, default=False)
    suporte_prioritario = Column(Boolean, default=False)
    
    usuarios = relationship("User", back_populates="plano")


class Fornecedor(TimestampMixin, Base): # Herda de TimestampMixin
    __tablename__ = "fornecedores"
    __table_args__ = {'extend_existing': True} # ADICIONADO
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    nome = Column(String, index=True, nullable=False)
    contato_principal = Column(String, nullable=True)
    email_contato = Column(String, nullable=True)
    telefone_contato = Column(String, nullable=True)
    site_url = Column(String, nullable=True)
    link_busca_padrao = Column(String, nullable=True)

    owner = relationship("User", back_populates="fornecedores")
    produtos = relationship("Produto", back_populates="fornecedor")


class Produto(TimestampMixin, Base): # Herda de TimestampMixin
    __tablename__ = "produtos"
    __table_args__ = {'extend_existing': True} # ADICIONADO
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=True)

    nome_base = Column(String, index=True, nullable=False)
    nome_chat_api = Column(String, nullable=True, index=True) # Nome otimizado por IA
    descricao_original = Column(Text, nullable=True) # Descrição original do fornecedor/usuário
    descricao_curta_orig = Column(String, nullable=True) # Descrição curta original
    descricao_principal_gerada = Column(Text, nullable=True) # Descrição longa otimizada por IA
    descricao_curta_gerada = Column(String, nullable=True) # Descrição curta otimizada por IA
    
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
    imagens_secundarias_urls = Column(JSON, nullable=True) # Lista de URLs de imagens

    dynamic_attributes = Column(JSON, nullable=True) # Atributos dinâmicos como JSON
    dados_brutos = Column(JSON, nullable=True) # Dados brutos originais do arquivo/web

    status_enriquecimento_web = Column(SQLAlchemyEnum(StatusEnriquecimentoEnum), default=StatusEnriquecimentoEnum.NAO_INICIADO)
    status_titulo_ia = Column(SQLAlchemyEnum(StatusGeracaoIAEnum), default=StatusGeracaoIAEnum.NAO_INICIADO)
    status_descricao_ia = Column(SQLAlchemyEnum(StatusGeracaoIAEnum), default=StatusGeracaoIAEnum.NAO_INICIADO)
    
    # Campo para armazenar títulos sugeridos por IA
    titulos_sugeridos = Column(JSON, nullable=True) # Lista de strings de títulos

    ativo_marketplace = Column(Boolean, default=False)
    data_publicacao_marketplace = Column(DateTime(timezone=True), nullable=True)
    
    owner = relationship("User", back_populates="produtos")
    fornecedor = relationship("Fornecedor", back_populates="produtos")
    product_type = relationship("ProductType", back_populates="produtos")
    registros_uso_ia = relationship("RegistroUsoIA", back_populates="produto", cascade="all, delete-orphan")


class ProductType(TimestampMixin, Base): # Herda de TimestampMixin
    __tablename__ = "product_types"
    __table_args__ = {'extend_existing': True} # ADICIONADO
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Pode ser global (None) ou do usuário
    
    key_name = Column(String, index=True, nullable=False) 
    friendly_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    owner = relationship("User", back_populates="product_types")
    attribute_templates = relationship("AttributeTemplate", back_populates="product_type", cascade="all, delete-orphan", lazy="selectin")
    produtos = relationship("Produto", back_populates="product_type")


class AttributeTemplate(TimestampMixin, Base): # Herda de TimestampMixin
    __tablename__ = "attribute_templates"
    __table_args__ = {'extend_existing': True} # ADICIONADO
    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
    
    attribute_key = Column(String, nullable=False)
    label = Column(String, nullable=False)
    field_type = Column(SQLAlchemyEnum(AttributeFieldTypeEnum), nullable=False)
    
    is_required = Column(Boolean, default=False)
    is_filtrable = Column(Boolean, default=False) 
    display_order = Column(Integer, default=0)
    
    options = Column(JSON, nullable=True) # Para SELECT, MULTI_SELECT (JSON string ou lista Python)
    
    default_value = Column(String, nullable=True)
    tooltip_text = Column(String, nullable=True)

    product_type = relationship("ProductType", back_populates="attribute_templates")


class RegistroUsoIA(TimestampMixin, Base): # Herda de TimestampMixin
    __tablename__ = "registros_uso_ia"
    __table_args__ = {'extend_existing': True} # ADICIONADO
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
    
    user = relationship("User", back_populates="registros_uso_ia")
    produto = relationship("Produto", back_populates="registros_uso_ia")