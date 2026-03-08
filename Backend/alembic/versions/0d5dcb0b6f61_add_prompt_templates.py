"""Add versioned prompt templates.

Revision ID: 0d5dcb0b6f61
Revises: 6d0f5e9d2a21
Create Date: 2026-03-08 17:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0d5dcb0b6f61"
down_revision: Union[str, None] = "6d0f5e9d2a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


prompt_templates_table = sa.table(
    "prompt_templates",
    sa.column("nome", sa.String(length=150)),
    sa.column("conteudo", sa.Text()),
    sa.column("versao", sa.Integer()),
)


PROMPT_SEEDS = [
    {
        "nome": "ia.openai.title.system",
        "conteudo": "Voce e um especialista em copywriting para e-commerce. Gere {num_titulos} opcoes de titulos curtos, atraentes e otimizados para SEO para o produto a seguir. Use apenas fatos explicitamente presentes no contexto. Nao invente historico de empresa, ano de fundacao, tempo de mercado ou dados institucionais.",
        "versao": 1,
    },
    {
        "nome": "ia.openai.title.user",
        "conteudo": "Produto: {nome_base}. Descricao: {descricao}. Marca: {marca}.",
        "versao": 1,
    },
    {
        "nome": "ia.openai.description.system",
        "conteudo": "Voce e um copywriter especialista em e-commerce. Crie uma descricao persuasiva com aproximadamente {tamanho_palavras} palavras para o item a seguir. Use somente fatos presentes no contexto. Nao invente historico de empresa, ano de fundacao, tempo de mercado, premios ou credenciais.",
        "versao": 1,
    },
    {
        "nome": "ia.openai.description.user",
        "conteudo": "Produto: {nome_base}. Informacoes adicionais: {descricao}. Marca: {marca}. Modelo: {modelo}.",
        "versao": 1,
    },
    {
        "nome": "ia.gemini.title.user",
        "conteudo": "Crie {num_titulos} sugestoes de titulos curtos e atrativos para o seguinte produto:\nUse apenas informacoes do contexto e nao invente historico de empresa ou ano de fundacao.\nNome: {nome_base}\nDescricao: {descricao}\nMarca: {marca}",
        "versao": 1,
    },
    {
        "nome": "ia.gemini.description.user",
        "conteudo": "Escreva uma descricao de aproximadamente {tamanho_palavras} palavras para o seguinte produto:\nUse apenas fatos do contexto e nao invente historico de empresa ou ano de fundacao.\nNome: {nome_base}\nInformacoes adicionais: {descricao}\nMarca: {marca}\nModelo: {modelo}",
        "versao": 1,
    },
    {
        "nome": "ia.gemini.attribute_suggestion.user",
        "conteudo": "Analise as seguintes informacoes sobre um produto:\n---\n{contexto}\n---\n\nCom base nesta analise, sugira valores apropriados para os seguintes atributos definidos (use as chaves exatamente como listadas):\n{lista_chaves_str}\n\nSeu objetivo e preencher esses atributos com informacoes relevantes e concisas inferidas do contexto fornecido.\nSua resposta DEVE ser um objeto JSON contendo uma unica chave 'sugestoes_atributos'.\nO valor de 'sugestoes_atributos' deve ser uma lista de objetos.\nCada objeto na lista deve ter duas chaves: 'chave_atributo' (que deve ser uma das chaves da lista que forneci: {lista_chaves_inline}) e 'valor_sugerido' (a sua sugestao de valor para esse atributo).\nSe voce nao puder sugerir um valor para um atributo especifico com base nas informacoes, pode omiti-lo da lista ou fornecer um valor como 'Nao encontrado'.\nNao inclua atributos na sua resposta que nao foram listados explicitamente.",
        "versao": 1,
    },
    {
        "nome": "validator.crew.role",
        "conteudo": "Auditor de Qualidade de Dados de E-commerce",
        "versao": 1,
    },
    {
        "nome": "validator.crew.goal",
        "conteudo": "Sua missao e receber um dicionario de dados de produto (JSON) extraido de forma bruta e transforma-lo em um JSON limpo, padronizado e pronto para ser salvo em um banco de dados de e-commerce. Voce e o guardiao da qualidade dos dados.",
        "versao": 1,
    },
    {
        "nome": "validator.crew.backstory",
        "conteudo": "Voce e um especialista em dados de e-commerce com um olhar treinado para identificar e corrigir inconsistencias. Voce entende a importancia de SKUs, EANs, nomes de produtos, precos e descricoes para o funcionamento de uma loja online. Sua experiencia foi forjada analisando milhares de catalogos de produtos e corrigindo erros comuns de OCR, digitacao e formatacao. Voce e metodico, preciso e implacavel na busca pela padronizacao.",
        "versao": 1,
    },
    {
        "nome": "validator.crew.expected_output",
        "conteudo": "Um objeto JSON contendo os dados do produto limpos e padronizados.",
        "versao": 1,
    },
    {
        "nome": "validator.crew.description",
        "conteudo": "Analise o seguinte dicionario de dados brutos de um produto:\n---\n{raw_data}\n---\n\nExecute as seguintes acoes de limpeza e padronizacao:\n\n1. **SKU e EAN**:\n- Remova espacos em branco extras, no inicio, no fim e no meio.\n- Corrija erros comuns de OCR: troque a letra 'O' por '0' (zero) e a letra 'I' ou 'l' por '1' (um), apenas quando fizer sentido no contexto de codigo de barras ou SKU.\n- Se o campo estiver vazio ou for nulo, mantenha `null` ou `None`.\n\n2. **Nome do Produto (nome_base)**:\n- Corrija a capitalizacao para 'Title Case'.\n- Remova termos promocionais como 'PROMOCAO' e 'OFERTA'.\n- Corrija erros obvios de digitacao, quando possivel.\n\n3. **Preco (preco_original)**:\n- O valor deve ser numerico. Remova simbolos de moeda.\n- Converta virgula decimal para ponto.\n- Se nao for preco valido, retorne `null`.\n\n4. **Descricao (descricao_original)**:\n- Corrija gramatica e ortografia.\n- Remova quebras excessivas e normalize espacos.\n- Mantenha apenas texto informativo e relevante.\n\n5. **Marca (marca)**:\n- Padronize capitalizacao.\n\nIMPORTANTE:\n- O output final deve conter APENAS o objeto JSON corrigido.\n- Nao inclua explicacoes.\n- Campos invalidos devem ser `null`.\n- Mantenha a estrutura de chaves original.",
        "versao": 1,
    },
]


class _MigrationEntries:
    @staticmethod
    def upgrade() -> None:
        op.create_table(
            "prompt_templates",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("nome", sa.String(length=150), nullable=False),
            sa.Column("conteudo", sa.Text(), nullable=False),
            sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("nome", "versao", name="uq_prompt_templates_nome_versao"),
        )
        op.create_index(op.f("ix_prompt_templates_id"), "prompt_templates", ["id"], unique=False)
        op.create_index(op.f("ix_prompt_templates_nome"), "prompt_templates", ["nome"], unique=False)
        op.bulk_insert(prompt_templates_table, PROMPT_SEEDS)

    @staticmethod
    def downgrade() -> None:
        op.drop_index(op.f("ix_prompt_templates_nome"), table_name="prompt_templates")
        op.drop_index(op.f("ix_prompt_templates_id"), table_name="prompt_templates")
        op.drop_table("prompt_templates")


upgrade = _MigrationEntries.upgrade
downgrade = _MigrationEntries.downgrade
