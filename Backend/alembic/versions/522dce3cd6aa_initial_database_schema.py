"""Initial database schema

Revision ID: 522dce3cd6aa
Revises: 
Create Date: 2025-06-05 14:05:37.626197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '522dce3cd6aa'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('planos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=True),
    sa.Column('preco_mensal', sa.Float(), nullable=False),
    sa.Column('limite_produtos', sa.Integer(), nullable=True),
    sa.Column('limite_enriquecimento_web', sa.Integer(), nullable=True),
    sa.Column('limite_geracao_ia', sa.Integer(), nullable=True),
    sa.Column('permite_api_externa', sa.Boolean(), nullable=True),
    sa.Column('suporte_prioritario', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_planos_id'), 'planos', ['id'], unique=False)
    op.create_index(op.f('ix_planos_nome'), 'planos', ['nome'], unique=True)
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)
    op.create_index(op.f('ix_roles_name'), 'roles', ['name'], unique=True)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=True),
    sa.Column('nome_completo', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('is_superuser', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('provider', sa.String(), nullable=True),
    sa.Column('provider_user_id', sa.String(), nullable=True),
    sa.Column('idioma_preferido', sa.String(), nullable=True),
    sa.Column('plano_id', sa.Integer(), nullable=True),
    sa.Column('role_id', sa.Integer(), nullable=True),
    sa.Column('chave_openai_pessoal', sa.String(), nullable=True),
    sa.Column('chave_google_gemini_pessoal', sa.String(), nullable=True),
    sa.Column('limite_produtos', sa.Integer(), nullable=True),
    sa.Column('limite_enriquecimento_web', sa.Integer(), nullable=True),
    sa.Column('limite_geracao_ia', sa.Integer(), nullable=True),
    sa.Column('data_expiracao_plano', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reset_password_token', sa.String(), nullable=True),
    sa.Column('reset_password_token_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['plano_id'], ['planos.id'], ),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user_id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_nome_completo'), 'users', ['nome_completo'], unique=False)
    op.create_index(op.f('ix_users_reset_password_token'), 'users', ['reset_password_token'], unique=False)
    op.create_table('fornecedores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(), nullable=False),
    sa.Column('email_contato', sa.String(), nullable=True),
    sa.Column('telefone_contato', sa.String(), nullable=True),
    sa.Column('endereco', sa.Text(), nullable=True),
    sa.Column('site_url', sa.String(), nullable=True),
    sa.Column('termos_contratuais', sa.Text(), nullable=True),
    sa.Column('contato_principal', sa.String(), nullable=True),
    sa.Column('observacoes', sa.Text(), nullable=True),
    sa.Column('link_busca_padrao', sa.String(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fornecedores_id'), 'fornecedores', ['id'], unique=False)
    op.create_index(op.f('ix_fornecedores_nome'), 'fornecedores', ['nome'], unique=False)
    op.create_table('product_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key_name', sa.String(), nullable=False, comment="Chave única para identificar o tipo, ex: 'smartphones'"),
    sa.Column('friendly_name', sa.String(), nullable=False, comment="Nome amigável, ex: 'Smartphones'"),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True, comment='Se NULL, é um tipo global/padrão. Senão, pertence a um usuário.'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'key_name', name='_user_key_name_uc')
    )
    op.create_index('ix_product_types_global_key_name_unique', 'product_types', ['key_name'], unique=True, postgresql_where=sa.text('user_id IS NULL'))
    op.create_index(op.f('ix_product_types_id'), 'product_types', ['id'], unique=False)
    op.create_index('ix_product_types_user_id_key_name', 'product_types', ['user_id', 'key_name'], unique=False)
    op.create_table('attribute_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_type_id', sa.Integer(), nullable=False),
    sa.Column('attribute_key', sa.String(), nullable=False, comment="Chave do atributo, ex: 'cor', 'memoria_ram'"),
    sa.Column('label', sa.String(), nullable=False, comment="Nome de exibição do atributo, ex: 'Cor', 'Memória RAM'"),
    sa.Column('field_type', sa.Enum('TEXT', 'NUMBER', 'BOOLEAN', 'SELECT', 'MULTISELECT', 'DATE', 'TEXTAREA', name='attributefieldtypeenum'), nullable=False),
    sa.Column('description', sa.Text(), nullable=True, comment='Ajuda sobre o atributo'),
    sa.Column('default_value', sa.String(), nullable=True),
    sa.Column('options', sa.JSON(), nullable=True, comment="Lista de opções para select/multiselect, armazenada como JSON: ['Op1', 'Op2']"),
    sa.Column('is_required', sa.Boolean(), nullable=True),
    sa.Column('is_filterable', sa.Boolean(), nullable=True),
    sa.Column('display_order', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['product_type_id'], ['product_types.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('product_type_id', 'attribute_key', name='_product_type_attribute_key_uc')
    )
    op.create_index(op.f('ix_attribute_templates_id'), 'attribute_templates', ['id'], unique=False)
    op.create_table('produtos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('nome_base', sa.String(length=255), nullable=False, comment='Nome principal/original do produto'),
    sa.Column('nome_chat_api', sa.String(length=255), nullable=True, comment='Nome otimizado/gerado pela IA'),
    sa.Column('descricao_original', sa.Text(), nullable=True),
    sa.Column('descricao_chat_api', sa.Text(), nullable=True),
    sa.Column('sku', sa.String(length=100), nullable=True),
    sa.Column('ean', sa.String(length=13), nullable=True),
    sa.Column('ncm', sa.String(length=8), nullable=True),
    sa.Column('marca', sa.String(length=100), nullable=True),
    sa.Column('modelo', sa.String(length=100), nullable=True),
    sa.Column('preco_custo', sa.Float(), nullable=True),
    sa.Column('preco_venda', sa.Float(), nullable=True),
    sa.Column('margem_lucro', sa.Float(), nullable=True),
    sa.Column('estoque_disponivel', sa.Integer(), nullable=True),
    sa.Column('peso_gramas', sa.Integer(), nullable=True, comment='Peso em gramas'),
    sa.Column('dimensoes_cm', sa.String(length=50), nullable=True, comment='Formato AxLxP, ex: 10x15x20'),
    sa.Column('fornecedor_id', sa.Integer(), nullable=True),
    sa.Column('product_type_id', sa.Integer(), nullable=True),
    sa.Column('categoria_original', sa.String(length=150), nullable=True),
    sa.Column('categoria_mapeada', sa.String(length=150), nullable=True),
    sa.Column('tags_palavras_chave', sa.JSON(), nullable=True),
    sa.Column('imagem_principal_url', sa.String(), nullable=True),
    sa.Column('imagens_secundarias_urls', sa.JSON(), nullable=True),
    sa.Column('video_url', sa.String(), nullable=True),
    sa.Column('status_enriquecimento_web', sa.Enum('NAO_INICIADO', 'PENDENTE', 'EM_PROGRESSO', 'CONCLUIDO', 'FALHA', 'NAO_APLICAVEL', name='statusenriquecimentoenum'), nullable=True),
    sa.Column('status_titulo_ia', sa.Enum('NAO_INICIADO', 'PENDENTE', 'EM_PROGRESSO', 'CONCLUIDO', 'FALHA', 'NAO_APLICAVEL', name='statusgeracaoiaenum'), nullable=True),
    sa.Column('status_descricao_ia', sa.Enum('NAO_INICIADO', 'PENDENTE', 'EM_PROGRESSO', 'CONCLUIDO', 'FALHA', 'NAO_APLICAVEL', name='statusgeracaoiaenum'), nullable=True),
    sa.Column('dados_brutos_web', sa.JSON(), nullable=True, comment='JSON com dados extraídos da web (textos, metadados)'),
    sa.Column('dynamic_attributes', sa.JSON(), nullable=True, comment='Atributos dinâmicos preenchidos baseados no ProductType (JSON)'),
    sa.Column('log_processamento', sa.JSON(), nullable=True, comment='Lista de mensagens/eventos de log para este produto'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['fornecedor_id'], ['fornecedores.id'], ),
    sa.ForeignKeyConstraint(['product_type_id'], ['product_types.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_produtos_ean'), 'produtos', ['ean'], unique=False)
    op.create_index(op.f('ix_produtos_id'), 'produtos', ['id'], unique=False)
    op.create_index(op.f('ix_produtos_sku'), 'produtos', ['sku'], unique=False)
    op.create_index('ix_produtos_user_id_ean', 'produtos', ['user_id', 'ean'], unique=False)
    op.create_index('ix_produtos_user_id_nome_base', 'produtos', ['user_id', 'nome_base'], unique=False)
    op.create_index('ix_produtos_user_id_sku', 'produtos', ['user_id', 'sku'], unique=False)
    op.create_table('registros_uso_ia',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('produto_id', sa.Integer(), nullable=True),
    sa.Column('tipo_acao', sa.Enum('CRIACAO_TITULO_PRODUTO', 'CRIACAO_DESCRICAO_PRODUTO', 'ENRIQUECIMENTO_WEB_PRODUTO', 'OTIMIZACAO_SEO_CONTEUDO', 'GERACAO_TAGS_PRODUTO', 'ANALISE_SENTIMENTO_REVIEWS', 'TRADUCAO_CONTEUDO_PRODUTO', 'SUMARIZACAO_CARACTERISTICAS', 'SUGESTAO_ATRIBUTOS_GEMINI', 'OUTRO', name='tipoacaoiaenum'), nullable=False),
    sa.Column('provedor_ia', sa.String(), nullable=True),
    sa.Column('modelo_ia', sa.String(), nullable=True),
    sa.Column('prompt_utilizado', sa.Text(), nullable=True),
    sa.Column('resposta_ia', sa.Text(), nullable=True),
    sa.Column('tokens_prompt', sa.Integer(), nullable=True),
    sa.Column('tokens_resposta', sa.Integer(), nullable=True),
    sa.Column('custo_estimado_usd', sa.Float(), nullable=True),
    sa.Column('creditos_consumidos', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('detalhes_erro', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_registros_uso_ia_id'), 'registros_uso_ia', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_registros_uso_ia_id'), table_name='registros_uso_ia')
    op.drop_table('registros_uso_ia')
    op.drop_index('ix_produtos_user_id_sku', table_name='produtos')
    op.drop_index('ix_produtos_user_id_nome_base', table_name='produtos')
    op.drop_index('ix_produtos_user_id_ean', table_name='produtos')
    op.drop_index(op.f('ix_produtos_sku'), table_name='produtos')
    op.drop_index(op.f('ix_produtos_id'), table_name='produtos')
    op.drop_index(op.f('ix_produtos_ean'), table_name='produtos')
    op.drop_table('produtos')
    op.drop_index(op.f('ix_attribute_templates_id'), table_name='attribute_templates')
    op.drop_table('attribute_templates')
    op.drop_index('ix_product_types_user_id_key_name', table_name='product_types')
    op.drop_index(op.f('ix_product_types_id'), table_name='product_types')
    op.drop_index('ix_product_types_global_key_name_unique', table_name='product_types', postgresql_where=sa.text('user_id IS NULL'))
    op.drop_table('product_types')
    op.drop_index(op.f('ix_fornecedores_nome'), table_name='fornecedores')
    op.drop_index(op.f('ix_fornecedores_id'), table_name='fornecedores')
    op.drop_table('fornecedores')
    op.drop_index(op.f('ix_users_reset_password_token'), table_name='users')
    op.drop_index(op.f('ix_users_nome_completo'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_roles_name'), table_name='roles')
    op.drop_index(op.f('ix_roles_id'), table_name='roles')
    op.drop_table('roles')
    op.drop_index(op.f('ix_planos_nome'), table_name='planos')
    op.drop_index(op.f('ix_planos_id'), table_name='planos')
    op.drop_table('planos')
    # ### end Alembic commands ###

