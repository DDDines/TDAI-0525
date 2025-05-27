# tdai_project/Backend/models.py
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum as SQLAlchemyEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum 

from database import Base 

class StatusEnriquecimentoEnum(enum.Enum):
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    FALHOU = "FALHOU"
    NENHUMA_FONTE_ENCONTRADA = "NENHUMA_FONTE_ENCONTRADA"
    CONCLUIDO_COM_DADOS_PARCIAIS = "CONCLUIDO_COM_DADOS_PARCIAIS"
    FALHA_CONFIGURACAO_API_EXTERNA = "FALHA_CONFIGURACAO_API_EXTERNA"
    FALHA_API_EXTERNA = "FALHA_API_EXTERNA"

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)

    users = relationship("User", back_populates="role")

class Plano(Base):
    __tablename__ = "planos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    max_descricoes_mes = Column(Integer, default=0)
    max_titulos_mes = Column(Integer, default=0)

    users = relationship("User", back_populates="plano")

class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    site_url = Column(String, nullable=True)
    catalogo_pdf_path = Column(String, nullable=True)
    link_busca_padrao = Column(String, nullable=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="fornecedores_cadastrados")
    produtos = relationship("Produto", back_populates="fornecedor")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome_base = Column(String, index=True, nullable=False)
    marca = Column(String, index=True, nullable=True)
    categoria_original = Column(String, nullable=True)
    dados_brutos = Column(JSON, nullable=True)
    
    descricao_principal_gerada = Column(Text, nullable=True)
    titulos_sugeridos = Column(JSON, nullable=True)

    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status_enriquecimento_web = Column(
        SQLAlchemyEnum(
            StatusEnriquecimentoEnum 
            # native_enum=True é o default para PostgreSQL e tentará usar os NOMES dos membros.
            # Se o tipo ENUM no DB foi criado com os valores em maiúsculas (PENDENTE, EM_PROGRESSO),
            # e agora os .value do Python Enum também são essas strings maiúsculas, deve alinhar.
        ),
        default=StatusEnriquecimentoEnum.PENDENTE, # Atribui o membro do enum
        nullable=False
    )
    log_enriquecimento_web = Column(JSON, nullable=True)

    fornecedor = relationship("Fornecedor", back_populates="produtos")
    owner = relationship("User", back_populates="produtos_cadastrados")
    historico_uso_ia = relationship("UsoIA", back_populates="produto")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class UsoIA(Base):
    __tablename__ = "uso_ia"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    tipo_geracao = Column(String, nullable=False)
    modelo_ia_usado = Column(String, nullable=False)
    prompt_utilizado = Column(Text, nullable=True)
    resultado_gerado = Column(Text, nullable=True)
    custo_aproximado_tokens = Column(Integer, nullable=True)

    user = relationship("User", back_populates="historico_uso_ia")
    produto = relationship("Produto", back_populates="historico_uso_ia")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    idioma_preferido = Column(String, default="pt")
    chave_openai_pessoal = Column(String, nullable=True)
    
    plano_id = Column(Integer, ForeignKey("planos.id"), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)

    plano = relationship("Plano", back_populates="users")
    role = relationship("Role", back_populates="users")
    
    fornecedores_cadastrados = relationship("Fornecedor", back_populates="owner")
    produtos_cadastrados = relationship("Produto", back_populates="owner")
    historico_uso_ia = relationship("UsoIA", back_populates="user")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())