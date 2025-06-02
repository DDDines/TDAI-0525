# Backend/models.py
import enum
from typing import Optional, List, Dict, Any # <--- IMPORTAÇÃO ADICIONADA
from datetime import datetime # Importar datetime para Mapped[datetime]
from sqlalchemy import (Column, Integer, String, Boolean, ForeignKey, DateTime, 
                        Float, Text, UniqueConstraint, Enum as SQLAlchemyEnum)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from database import Base # Importa Base de database.py no mesmo nível


# Enum para status de enriquecimento web
class StatusEnriquecimentoEnum(str, enum.Enum):
    PENDENTE = "pendente"
    EM_PROGRESSO = "em_progresso"
    CONCLUIDO = "concluido"
    FALHA = "falha"
    NAO_INICIADO = "nao_iniciado"

# Enum para status de geração por IA (títulos, descrições, etc.)
class StatusGeracaoIAEnum(str, enum.Enum):
    PENDENTE = "pendente"
    EM_PROGRESSO = "em_progresso"
    CONCLUIDO = "concluido"
    FALHA = "falha"
    NAO_INICIADO = "nao_iniciado"
    NAO_APLICAVEL = "nao_aplicavel" 

# Enum para tipos de campos de atributos de template
class AttributeFieldTypeEnum(str, enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"
    DATE = "date"
    TEXTAREA = "textarea"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String, nullable=True) 
    nome_completo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    provider: Mapped[Optional[str]] = mapped_column(String, nullable=True) 
    provider_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True) 
    
    plano_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("planos.id"), nullable=True)
    plano: Mapped[Optional["Plano"]] = relationship("Plano", back_populates="users")
    
    data_expiracao_plano: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True) # Alterado para datetime minúsculo

    limite_produtos: Mapped[Optional[int]] = mapped_column(Integer, default=0) 
    limite_enriquecimento_web: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    limite_geracao_ia: Mapped[Optional[int]] = mapped_column(Integer, default=0) 

    chave_openai_pessoal: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    chave_google_gemini_pessoal: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Adicionando 'idioma_preferido' que está no schema UserCreate e UserUpdate
    idioma_preferido: Mapped[Optional[str]] = mapped_column(String(10), nullable=True) # Ex: "pt-BR", "en-US"
    # Adicionando 'role_id' que está no schema UserCreate (embora a tabela Role não esteja sendo usada ativamente)
    role_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("roles.id"), nullable=True)
    role: Mapped[Optional["Role"]] = relationship("Role") # Removido back_populates="users" se Role não tem users

    # Adicionando 'updated_at'
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


    produtos: Mapped[List["Produto"]] = relationship("Produto", back_populates="owner", cascade="all, delete-orphan")
    fornecedores: Mapped[List["Fornecedor"]] = relationship("Fornecedor", back_populates="owner", cascade="all, delete-orphan")
    registros_uso_ia: Mapped[List["RegistroUsoIA"]] = relationship("RegistroUsoIA", back_populates="user", cascade="all, delete-orphan")
    product_types: Mapped[List["ProductType"]] = relationship("ProductType", back_populates="owner", cascade="all, delete-orphan")
    
    reset_password_token: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    reset_password_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True) # Alterado para datetime minúsculo


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String, index=True, nullable=False)
    contato: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Adicionando campos do schema FornecedorCreate/Update
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    telefone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    endereco: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    site_url: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Era HttpUrl no schema, string no model
    link_busca_padrao: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Era HttpUrl no schema
    
    # Adicionando timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


    owner: Mapped["User"] = relationship("User", back_populates="fornecedores")
    produtos: Mapped[List["Produto"]] = relationship("Produto", back_populates="fornecedor")
    
    __table_args__ = (UniqueConstraint('user_id', 'nome', name='_user_fornecedor_nome_uc'),)


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Renomeado de nome_original para nome_base para corresponder ao schema ProdutoBase
    nome_base: Mapped[str] = mapped_column(String, index=True, nullable=False) # Era nome_original
    nome_chat_api: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True) 
    descricao_original: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    descricao_chat_api: Mapped[Optional[str]] = mapped_column(Text, nullable=True) 
    sku: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True) 
    ean: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True) 
    ncm: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True) 
    
    # Adicionando campos do schema ProdutoBase que estavam faltando ou divergentes
    marca: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    modelo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    categoria_original: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Era 'categoria'
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON string ou CSV
    link_referencia_fornecedor: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Era HttpUrl no schema
    dados_brutos: Mapped[Optional[Dict[str, Any]]] = mapped_column(Text, nullable=True) # Alterado para Dict[str, Any], armazenado como JSON/Text

    preco_custo: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preco_venda: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    margem_lucro: Mapped[Optional[float]] = mapped_column(Float, nullable=True) 
    estoque_disponivel: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    peso_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    altura_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    largura_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profundidade_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False) # Alterado para datetime minúsculo
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False) # Alterado para datetime minúsculo
    
    imagem_principal_url: Mapped[Optional[str]] = mapped_column(String, nullable=True) 

    status_enriquecimento_web: Mapped[StatusEnriquecimentoEnum] = mapped_column(SQLAlchemyEnum(StatusEnriquecimentoEnum), default=StatusEnriquecimentoEnum.NAO_INICIADO, nullable=False)
    status_titulo_ia: Mapped[StatusGeracaoIAEnum] = mapped_column(SQLAlchemyEnum(StatusGeracaoIAEnum), default=StatusGeracaoIAEnum.NAO_INICIADO, nullable=False)
    status_descricao_ia: Mapped[StatusGeracaoIAEnum] = mapped_column(SQLAlchemyEnum(StatusGeracaoIAEnum), default=StatusGeracaoIAEnum.NAO_INICIADO, nullable=False)
    
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    owner: Mapped["User"] = relationship("User", back_populates="produtos")
    
    fornecedor_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    fornecedor: Mapped[Optional["Fornecedor"]] = relationship("Fornecedor", back_populates="produtos")

    product_type_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("product_types.id"), nullable=True)
    product_type: Mapped[Optional["ProductType"]] = relationship("ProductType") 

    dynamic_attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(Text, nullable=True) # Alterado para Dict[str, Any], armazenado como JSON/Text


class ProductType(Base):
    __tablename__ = "product_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key_name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False) 
    friendly_name: Mapped[str] = mapped_column(String, nullable=False) 
    
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True) 
    owner: Mapped[Optional["User"]] = relationship("User", back_populates="product_types")

    attribute_templates: Mapped[List["AttributeTemplate"]] = relationship(
        "AttributeTemplate", 
        back_populates="product_type", 
        cascade="all, delete-orphan",
        order_by="AttributeTemplate.display_order" 
    )


class AttributeTemplate(Base):
    __tablename__ = "attribute_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("product_types.id"), nullable=False)
    
    attribute_key: Mapped[str] = mapped_column(String, nullable=False) 
    label: Mapped[str] = mapped_column(String, nullable=False) 
    field_type: Mapped[AttributeFieldTypeEnum] = mapped_column(SQLAlchemyEnum(AttributeFieldTypeEnum), nullable=False)
    
    options: Mapped[Optional[str]] = mapped_column(Text, nullable=True) 
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    tooltip_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0) 

    product_type: Mapped["ProductType"] = relationship("ProductType", back_populates="attribute_templates")

    __table_args__ = (UniqueConstraint('product_type_id', 'attribute_key', name='_product_type_attribute_key_uc'),)


class Plano(Base):
    __tablename__ = "planos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String, unique=True, nullable=False) 
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preco_mensal: Mapped[float] = mapped_column(Float, default=0.0)
    
    limite_produtos: Mapped[int] = mapped_column(Integer, default=10) 
    limite_enriquecimento_web: Mapped[int] = mapped_column(Integer, default=50) 
    limite_geracao_ia: Mapped[int] = mapped_column(Integer, default=100) 
    
    permite_api_externa: Mapped[bool] = mapped_column(Boolean, default=False)
    suporte_prioritario: Mapped[bool] = mapped_column(Boolean, default=False)

    users: Mapped[List["User"]] = relationship("User", back_populates="plano")


class RegistroUsoIA(Base): # Renomeado de UsoIA para RegistroUsoIA para consistência
    __tablename__ = "registros_uso_ia" # Nome da tabela mantido como no schema

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    user: Mapped["User"] = relationship("User", back_populates="registros_uso_ia")
    
    tipo_geracao: Mapped[str] = mapped_column(String, nullable=False) 
    produto_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("produtos.id"), nullable=True) 
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now()) # Alterado para datetime minúsculo
    custo_aproximado: Mapped[Optional[float]] = mapped_column(Float, nullable=True) 
    provedor_ia: Mapped[Optional[str]] = mapped_column(String, nullable=True) 
    modelo_ia: Mapped[Optional[str]] = mapped_column(String, nullable=True) 
    sucesso: Mapped[bool] = mapped_column(Boolean, default=True)
    detalhes_erro: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Adicionado input_text e output_text
    input_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False) 
    description: Mapped[Optional[str]] = mapped_column(String(255))
    # Se Role tiver um relacionamento com User (ex: users: Mapped[List["User"]] = relationship(back_populates="role"))
    # Isso precisaria ser adicionado se a FK em User.role_id fosse usada bidirecionalmente.
    # Por agora, a FK em User é unidirecional do ponto de vista do relacionamento explícito.