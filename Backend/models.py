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

# NOVO ENUM PARA STATUS DE GERAÇÃO DE CONTEÚDO POR IA
class StatusGeracaoIAEnum(enum.Enum):
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    FALHOU = "FALHOU"
    NAO_SOLICITADO = "NAO_SOLICITADO" # Adicionado para um estado inicial mais claro
    FALHA_CONFIGURACAO_IA = "FALHA_CONFIGURACAO_IA" # Para quando a API key está em falta, etc.
    LIMITE_ATINGIDO = "LIMITE_ATINGIDO" # Para quando o plano do usuário não permite mais gerações

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
    
    # NOVO RELACIONAMENTO ADICIONADO AQUI
    product_types_created = relationship("ProductType", back_populates="owner")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class ProductType(Base):
    __tablename__ = "product_types"

    id = Column(Integer, primary_key=True, index=True)
    key_name = Column(String, unique=True, index=True, nullable=False, comment="Nome chave único para o tipo, ex: 'eletronicos', 'vestuario'")
    friendly_name = Column(String, nullable=False, comment="Nome amigável para exibição, ex: 'Eletrônicos', 'Vestuário'")
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="Se nulo, é um tipo global/padrão")

    owner = relationship("User", back_populates="product_types_created")
    attribute_templates = relationship("AttributeTemplate", back_populates="product_type", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def __repr__(self):
        return f"<ProductType(id={self.id}, key_name='{self.key_name}', friendly_name='{self.friendly_name}')>"

class AttributeTemplate(Base):
    __tablename__ = "attribute_templates"

    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
    
    attribute_key = Column(String, nullable=False, comment="Chave interna para o atributo, ex: 'cor_principal', 'voltagem_equipamento'")
    label = Column(String, nullable=False, comment="Rótulo do atributo para exibição em formulários, ex: 'Cor Principal', 'Voltagem'")
    field_type = Column(String, nullable=False, comment="Tipo de campo para o formulário, ex: 'text', 'select', 'number', 'checkbox'") 
    options = Column(JSON, nullable=True, comment="Opções para campos do tipo 'select' ou 'radio', armazenadas como JSON. Ex: ['vermelho', 'azul'] ou [{'value': '110v', 'label': '110V'}]")
    is_required = Column(Boolean, default=False, nullable=False)
    tooltip_text = Column(String, nullable=True, comment="Texto de ajuda/dica para o campo.")
    default_value = Column(String, nullable=True, comment="Valor padrão para o atributo.")
    display_order = Column(Integer, default=0, nullable=False, comment="Ordem de exibição do atributo no formulário.")

    product_type = relationship("ProductType", back_populates="attribute_templates")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def __repr__(self):
        return f"<AttributeTemplate(id={self.id}, attribute_key='{self.attribute_key}', label='{self.label}')>"

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
    dados_brutos = Column(JSON, nullable=True) # Deve incluir product_type_key_referencia e atributos_dinamicos
    
    descricao_principal_gerada = Column(Text, nullable=True)
    titulos_sugeridos = Column(JSON, nullable=True) 

    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status_enriquecimento_web = Column(
        SQLAlchemyEnum(StatusEnriquecimentoEnum),
        default=StatusEnriquecimentoEnum.PENDENTE, 
        nullable=False
    )
    log_enriquecimento_web = Column(JSON, nullable=True)

    status_titulo_ia = Column(
        SQLAlchemyEnum(StatusGeracaoIAEnum),
        default=StatusGeracaoIAEnum.NAO_SOLICITADO, 
        nullable=False
    )
    status_descricao_ia = Column(
        SQLAlchemyEnum(StatusGeracaoIAEnum),
        default=StatusGeracaoIAEnum.NAO_SOLICITADO, 
        nullable=False
    )

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
    tipo_geracao = Column(String, nullable=False) # Ex: "titulo", "descricao", "atributos"
    modelo_ia_usado = Column(String, nullable=False)
    prompt_utilizado = Column(Text, nullable=True)
    resultado_gerado = Column(Text, nullable=True)
    custo_aproximado_tokens = Column(Integer, nullable=True)

    user = relationship("User", back_populates="historico_uso_ia")
    produto = relationship("Produto", back_populates="historico_uso_ia")