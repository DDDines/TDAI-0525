# Backend/models.py

from sqlalchemy import (Column, Integer, String, Boolean, DateTime, ForeignKey, Text,
                        Float, Enum as SQLAlchemyEnum, JSON, Index, UniqueConstraint, func)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.mutable import MutableDict, MutableList # Para tipos JSON mutáveis
from Backend.database import Base # Assume que database.py define Base = declarative_base()
from datetime import datetime, timezone # Corrigido para importar timezone
import enum

# Definição dos Enums Python
class StatusEnriquecimentoEnum(str, enum.Enum):
    NAO_INICIADO = "NAO_INICIADO"
    PENDENTE = "PENDENTE" # Adicionado, se necessário para indicar que está na fila
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    CONCLUIDO_COM_DADOS_PARCIAIS = "CONCLUIDO_COM_DADOS_PARCIAIS"
    CONCLUIDO = "CONCLUIDO"
    FALHOU = "FALHOU"
    FALHA_API_EXTERNA = "FALHA_API_EXTERNA"
    FALHA_CONFIGURACAO_API_EXTERNA = "FALHA_CONFIGURACAO_API_EXTERNA"
    FALHA = "FALHA"
    NENHUMA_FONTE_ENCONTRADA = "NENHUMA_FONTE_ENCONTRADA"
    NAO_APLICAVEL = "NAO_APLICAVEL" # Para produtos onde enriquecimento web não se aplica


  
    

class StatusGeracaoIAEnum(str, enum.Enum):
    NAO_INICIADO = "NAO_INICIADO"
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO = "CONCLUIDO"
    FALHA = "FALHA"
    NAO_APLICAVEL = "NAO_APLICAVEL" # Se IA não for usada para este campo/produto

class TipoAcaoEnum(str, enum.Enum):
    CRIACAO_TITULO_PRODUTO = "criacao_titulo_produto"
    CRIACAO_DESCRICAO_PRODUTO = "criacao_descricao_produto"
    ENRIQUECIMENTO_WEB_PRODUTO = "enriquecimento_web_produto" # Ação de buscar dados na web com ou sem IA
    OTIMIZACAO_SEO_CONTEUDO = "otimizacao_seo_conteudo"
    GERACAO_TAGS_PRODUTO = "geracao_tags_produto"
    ANALISE_SENTIMENTO_REVIEWS = "analise_sentimento_reviews"
    TRADUCAO_CONTEUDO_PRODUTO = "traducao_conteudo_produto"
    SUMARIZACAO_CARACTERISTICAS = "sumarizacao_caracteristicas"
    SUGESTAO_ATRIBUTOS_GEMINI = "sugestao_atributos_gemini" # <-- NOVO VALOR ADICIONADO
    CRIACAO_PRODUTO = "criacao_produto"
    OUTRO = "outro"

class TipoAcaoSistemaEnum(str, enum.Enum):
    CRIACAO = "CRIACAO"
    ATUALIZACAO = "ATUALIZACAO"
    DELECAO = "DELECAO"

class AttributeFieldTypeEnum(str, enum.Enum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"      # Dropdown com uma única seleção
    MULTISELECT = "multiselect" # Lista de checkboxes ou similar para múltiplas seleções
    DATE = "date"
    TEXTAREA = "textarea"   # Para textos mais longos
    # Adicionar outros tipos conforme necessário (ex: color_picker, rich_text)


# Modelo de Usuário
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True) # Nullable para OAuth users sem senha local
    nome_completo = Column(String, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Campos para OAuth
    provider = Column(String, nullable=True) # ex: "google", "facebook"
    provider_user_id = Column(String, nullable=True) # ID do usuário no provedor OAuth

    # Campos de personalização e plano
    idioma_preferido = Column(String, default="pt_BR")
    plano_id = Column(Integer, ForeignKey("planos.id"), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True) # Assumindo que o default role será "user"

    # Chaves de API pessoais
    chave_openai_pessoal = Column(String, nullable=True)
    chave_google_gemini_pessoal = Column(String, nullable=True) # Para Gemini

    # Limites (podem ser herdados do plano ou personalizados)
    limite_produtos = Column(Integer, default=10)
    limite_enriquecimento_web = Column(Integer, default=50) # por mês ou total
    limite_geracao_ia = Column(Integer, default=100) # por mês ou total
    data_expiracao_plano = Column(DateTime(timezone=True), nullable=True)

    # Token para reset de senha
    reset_password_token = Column(String, nullable=True, index=True)
    reset_password_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    plano = relationship("Plano", back_populates="usuarios")
    role = relationship("Role", back_populates="usuarios")
    produtos = relationship("Produto", back_populates="owner", cascade="all, delete-orphan")
    fornecedores = relationship("Fornecedor", back_populates="owner", cascade="all, delete-orphan")
    product_types_criados = relationship("ProductType", back_populates="owner", cascade="all, delete-orphan") # Tipos criados pelo usuário
    registros_uso_ia_feitos = relationship("RegistroUsoIA", back_populates="usuario", cascade="all, delete-orphan")
    historicos = relationship("RegistroHistorico", back_populates="usuario", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user_id'),)


# Modelo de Role (Função/Papel do usuário)
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # Ex: "admin", "user", "gerente"
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuarios = relationship("User", back_populates="role")


# Modelo de Plano de Assinatura
class Plano(Base):
    __tablename__ = "planos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    descricao = Column(Text, nullable=True)
    preco_mensal = Column(Float, nullable=False, default=0.0)
    # Limites associados ao plano
    limite_produtos = Column(Integer, default=10)
    limite_enriquecimento_web = Column(Integer, default=50)
    limite_geracao_ia = Column(Integer, default=100)
    # Outras características do plano
    permite_api_externa = Column(Boolean, default=False) # Se o plano permite acesso via API
    suporte_prioritario = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuarios = relationship("User", back_populates="plano")


# Modelo de Fornecedor
class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True, nullable=False)
    email_contato = Column(String, nullable=True)
    telefone_contato = Column(String, nullable=True)
    endereco = Column(Text, nullable=True)
    site_url = Column(String, nullable=True) # Alterado de Text para String, se apropriado
    termos_contratuais = Column(Text, nullable=True)
    contato_principal = Column(String, nullable=True)
    observacoes = Column(Text, nullable=True)
    link_busca_padrao = Column(String, nullable=True) # Link base para buscar produtos deste fornecedor
    default_column_mapping = Column(MutableDict.as_mutable(JSON), nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Dono do registro do fornecedor
    owner = relationship("User", back_populates="fornecedores")
    produtos = relationship("Produto", back_populates="fornecedor") # Produtos associados a este fornecedor

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# Modelo de Tipo de Produto (ProductType)
class ProductType(Base):
    __tablename__ = "product_types"

    id = Column(Integer, primary_key=True, index=True)
    key_name = Column(String, nullable=False, comment="Chave única para identificar o tipo, ex: 'smartphones'") # Não necessariamente unique globalmente se user_id estiver presente
    friendly_name = Column(String, nullable=False, comment="Nome amigável, ex: 'Smartphones'")
    description = Column(Text, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="Se NULL, é um tipo global/padrão. Senão, pertence a um usuário.")
    owner = relationship("User", back_populates="product_types_criados")

    # Relacionamento com AttributeTemplate
    attribute_templates = relationship("AttributeTemplate", back_populates="product_type", cascade="all, delete-orphan")
    produtos_associados = relationship("Produto", back_populates="product_type")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'key_name', name='_user_key_name_uc'),
        Index('ix_product_types_user_id_key_name', 'user_id', 'key_name'),
    )


# Índice parcial para garantir key_name único quando user_id é NULL
Index(
    'ix_product_types_global_key_name_unique',
    ProductType.key_name,
    unique=True,
    postgresql_where=(ProductType.user_id.is_(None))
)


# Modelo de Template de Atributo (AttributeTemplate)
class AttributeTemplate(Base):
    __tablename__ = "attribute_templates"

    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)

    attribute_key = Column(String, nullable=False, comment="Chave do atributo, ex: 'cor', 'memoria_ram'")
    label = Column(String, nullable=False, comment="Nome de exibição do atributo, ex: 'Cor', 'Memória RAM'")
    field_type = Column(SQLAlchemyEnum(AttributeFieldTypeEnum), nullable=False, default=AttributeFieldTypeEnum.TEXT)
    description = Column(Text, nullable=True, comment="Ajuda sobre o atributo")
    default_value = Column(String, nullable=True) # Valor padrão como string, conversão no frontend/lógica
    options = Column(JSON, nullable=True, comment="Lista de opções para select/multiselect, armazenada como JSON: ['Op1', 'Op2']") # Armazenar como JSON array
    is_required = Column(Boolean, default=False)
    is_filterable = Column(Boolean, default=False) # Se pode ser usado para filtros na loja
    display_order = Column(Integer, default=0) # Para ordenação na UI

    product_type = relationship("ProductType", back_populates="attribute_templates")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('product_type_id', 'attribute_key', name='_product_type_attribute_key_uc'),
    )


# Modelo de Produto
class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # Dono do produto

    # Nomes e Descrições
    nome_base = Column(String(255), nullable=False, comment="Nome principal/original do produto")
    nome_chat_api = Column(String(255), nullable=True, comment="Nome otimizado/gerado pela IA")
    descricao_original = Column(Text, nullable=True)
    descricao_chat_api = Column(Text, nullable=True)

    # Identificadores
    sku = Column(String(100), index=True, nullable=True)
    ean = Column(String(13), index=True, nullable=True) # GTIN-13
    ncm = Column(String(8), nullable=True) # Nomenclatura Comum do Mercosul

    # Detalhes Básicos
    marca = Column(String(100), nullable=True)
    modelo = Column(String(100), nullable=True)

    # Preços
    preco_custo = Column(Float, nullable=True)
    preco_venda = Column(Float, nullable=True)
    margem_lucro = Column(Float, nullable=True) # Pode ser calculado

    # Logística e Estoque
    estoque_disponivel = Column(Integer, nullable=True)
    peso_gramas = Column(Integer, nullable=True, comment="Peso em gramas")
    dimensoes_cm = Column(String(50), nullable=True, comment="Formato AxLxP, ex: 10x15x20")

    # Relacionamentos
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=True) # Associa ao tipo de produto

    # Categorização e SEO
    categoria_original = Column(String(150), nullable=True)
    categoria_mapeada = Column(String(150), nullable=True) # Categoria após algum processamento/padronização
    tags_palavras_chave = Column(MutableList.as_mutable(JSON), nullable=True) # Lista de strings

    # Mídia
    imagem_principal_url = Column(String, nullable=True) # URL da imagem principal
    imagens_secundarias_urls = Column(MutableList.as_mutable(JSON), nullable=True) # Lista de URLs de imagens secundárias
    video_url = Column(String, nullable=True) # URL de um vídeo do produto

    # Status de Processamento
    status_enriquecimento_web = Column(SQLAlchemyEnum(StatusEnriquecimentoEnum), default=StatusEnriquecimentoEnum.NAO_INICIADO)
    status_titulo_ia = Column(SQLAlchemyEnum(StatusGeracaoIAEnum), default=StatusGeracaoIAEnum.NAO_INICIADO)
    status_descricao_ia = Column(SQLAlchemyEnum(StatusGeracaoIAEnum), default=StatusGeracaoIAEnum.NAO_INICIADO)
    # Adicionar mais status conforme necessário (ex: status_imagens_ia, status_seo_ia)

    # Dados Brutos e Atributos
    dados_brutos_web = Column(MutableDict.as_mutable(JSON), nullable=True, comment="JSON com dados extraídos da web (textos, metadados)")
    dynamic_attributes = Column(MutableDict.as_mutable(JSON), nullable=True, comment="Atributos dinâmicos preenchidos baseados no ProductType (JSON)")

    # Histórico de mensagens do processo de enriquecimento web/IA.
    # Estrutura flexível armazenada como JSON (lista ou dict).
    log_enriquecimento_web = Column(JSON, nullable=True, comment="Log de enriquecimento web do produto")

    # Log de Processamento (simplificado, pode ser uma tabela separada para logs detalhados)
    log_processamento = Column(MutableList.as_mutable(JSON), nullable=True, comment="Lista de mensagens/eventos de log para este produto")
    # Ex: [{"timestamp": "2023-10-26T10:00:00Z", "actor": "system/user_X", "action": "Enriquecimento Web Concluído", "details": "..."}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="produtos")
    fornecedor = relationship("Fornecedor", back_populates="produtos")
    product_type = relationship("ProductType", back_populates="produtos_associados")
    registros_uso_ia = relationship("RegistroUsoIA", back_populates="produto", cascade="all, delete-orphan")

    # Índices para otimizar buscas comuns
    __table_args__ = (
        Index('ix_produtos_user_id_nome_base', 'user_id', 'nome_base'),
        Index('ix_produtos_user_id_sku', 'user_id', 'sku', unique=False),
        Index('ix_produtos_user_id_ean', 'user_id', 'ean', unique=False),
        UniqueConstraint('user_id', 'sku', name='uq_produtos_user_sku'),
        UniqueConstraint('user_id', 'ean', name='uq_produtos_user_ean'),
    )


# Modelo para Registro de Uso de IA
class RegistroUsoIA(Base):
    __tablename__ = "registros_uso_ia"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="SET NULL"), nullable=True) # Se o produto for deletado, manter o registro de uso
    
    tipo_acao = Column(SQLAlchemyEnum(TipoAcaoEnum, name="tipoacaoenum"), nullable=False)  # Usar o Enum Python
    provedor_ia = Column(String, nullable=True) # ex: "openai", "gemini"
    modelo_ia = Column(String, nullable=True) # ex: "gpt-3.5-turbo", "gemini-1.5-flash-latest"
    
    prompt_utilizado = Column(Text, nullable=True) # Para auditoria, pode ser longo
    resposta_ia = Column(Text, nullable=True) # Para auditoria, pode ser longo
    
    tokens_prompt = Column(Integer, nullable=True)
    tokens_resposta = Column(Integer, nullable=True)
    custo_estimado_usd = Column(Float, nullable=True) # Se aplicável e rastreável
    creditos_consumidos = Column(Integer, nullable=False, default=1) # Quantidade de "operações" ou créditos específicos da plataforma
    
    status = Column(String, default="SUCESSO") # Ex: SUCESSO, FALHA
    detalhes_erro = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario = relationship("User", back_populates="registros_uso_ia_feitos")
    produto = relationship("Produto", back_populates="registros_uso_ia")


class RegistroHistorico(Base):
    __tablename__ = "registros_historico"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    entidade = Column(String, nullable=False)
    acao = Column(SQLAlchemyEnum(TipoAcaoSistemaEnum), nullable=False)
    entity_id = Column(Integer, nullable=True)
    detalhes_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("User", back_populates="historicos")


class CatalogImportFile(Base):
    __tablename__ = "catalog_import_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=True)
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="UPLOADED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    result_summary = Column(MutableDict.as_mutable(JSON), nullable=True)

    user = relationship("User")
    fornecedor = relationship("Fornecedor")
