"""Repositorio para prompts versionados usados pelos fluxos de IA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from sqlalchemy.orm import Session

from Backend.database import SessionLocal
from Backend.models import PromptTemplate


class PromptTemplateName:
    """Nominal identifiers for prompt templates persisted in the database."""

    IA_OPENAI_TITLE_SYSTEM = "ia.openai.title.system"
    IA_OPENAI_TITLE_USER = "ia.openai.title.user"
    IA_OPENAI_DESCRIPTION_SYSTEM = "ia.openai.description.system"
    IA_OPENAI_DESCRIPTION_USER = "ia.openai.description.user"
    IA_GEMINI_TITLE_USER = "ia.gemini.title.user"
    IA_GEMINI_DESCRIPTION_USER = "ia.gemini.description.user"
    IA_GEMINI_ATTRIBUTE_SUGGESTION_USER = "ia.gemini.attribute_suggestion.user"
    VALIDATOR_CREW_ROLE = "validator.crew.role"
    VALIDATOR_CREW_GOAL = "validator.crew.goal"
    VALIDATOR_CREW_BACKSTORY = "validator.crew.backstory"
    VALIDATOR_CREW_EXPECTED_OUTPUT = "validator.crew.expected_output"
    VALIDATOR_CREW_DESCRIPTION = "validator.crew.description"


DEFAULT_PROMPT_TEMPLATES: Dict[str, str] = {
    PromptTemplateName.IA_OPENAI_TITLE_SYSTEM: (
        "Voce e um especialista em copywriting para e-commerce. Gere exatamente {num_titulos} "
        "titulo(s) curtos, atraentes e otimizados para SEO para o produto a seguir. "
        "Preserve o idioma original do nome do produto. "
        "Nao traduza nomes proprios, colecoes, linhas, series ou palavras em ingles que ja identifiquem o item. "
        "Se o nome original ja estiver bom, mantenha-o praticamente igual. "
        "A primeira linha deve ser a melhor versao minimamente limpa do nome original, preservando seus tokens centrais. "
        "As demais linhas podem variar ordem ou complemento neutro, mas sem perder a identidade principal do nome original. "
        "Use apenas fatos explicitamente presentes no contexto. "
        "Nunca use chamada para acao, tom promocional, promessas, verbos de venda ou frases como 'exiba', "
        "'descubra', 'transforme', 'ideal para', 'perfeito para', 'aproveite' ou 'seus'. "
        "Se nao houver muitas variacoes seguras, prefira pequenas variacoes neutras do proprio nome original em vez de inventar. "
        "Nao invente historico de empresa, ano de fundacao, tempo de mercado ou dados institucionais. "
        "Formato obrigatorio da resposta: devolva somente os titulos finais, com uma linha por titulo. "
        "Nao use markdown, numeracao, bullets, asteriscos, aspas, explicacoes, comentarios, observacoes ou texto introdutorio. "
        "Se for apenas 1 titulo, responda com uma unica linha."
    ),
    PromptTemplateName.IA_OPENAI_TITLE_USER: (
        "Nome original do produto: {nome_base}. Descricao: {descricao}. Marca: {marca}. "
        "Mantenha nomes proprios e palavras-chave originais do nome sempre que possivel. "
        "Se o nome original estiver em ingles e ja identificar bem o item, mantenha-o em ingles; nao traduza parcialmente. "
        "Responda somente com o(s) titulo(s) final(is)."
    ),
    PromptTemplateName.IA_OPENAI_DESCRIPTION_SYSTEM: (
        "Voce e um copywriter especialista em e-commerce. Crie uma descricao persuasiva "
        "com aproximadamente {tamanho_palavras} palavras para o item a seguir. "
        "Use somente fatos presentes no contexto. "
        "Use tom claro, util e comercialmente convincente, mas sem fantasia, exageros ou promessas nao verificadas. "
        "Nao use chamada para acao ou frases promocionais como 'adquira', 'compre', 'invista', "
        "'aproveite', 'descubra', 'impulsione suas vendas' ou equivalentes. "
        "Nao traduza nomes proprios, colecoes, series ou linhas do produto quando o nome original ja identificar bem o item. "
        "Nao invente historico de empresa, ano de fundacao, tempo de mercado, premios ou credenciais. "
        "Formato obrigatorio da resposta: devolva somente um paragrafo final, sem titulo, sem markdown, "
        "sem bullets, sem listas, sem introducao e sem observacoes."
    ),
    PromptTemplateName.IA_OPENAI_DESCRIPTION_USER: (
        "Nome original do produto: {nome_base}. Informacoes adicionais: {descricao}. Marca: {marca}. Modelo: {modelo}. "
        "Priorize descricao factual do item e preserve nomes proprios no idioma original. "
        "Responda somente com a descricao final."
    ),
    PromptTemplateName.IA_GEMINI_TITLE_USER: (
        "Crie {num_titulos} sugestoes de titulos curtos e atrativos para o seguinte produto:\n"
        "Use apenas informacoes do contexto e nao invente historico de empresa ou ano de fundacao.\n"
        "Preserve o idioma original do nome e nao traduza nomes proprios, colecoes, linhas ou series.\n"
        "A primeira linha deve ser a melhor versao minimamente limpa do nome original.\n"
        "Nao use CTA, promessas, verbos promocionais, frases como 'exiba', 'descubra', 'ideal para' ou 'perfeito para'.\n"
        "Se faltarem variacoes seguras, prefira pequenas variacoes neutras do proprio nome.\n"
        "Nome original: {nome_base}\n"
        "Descricao: {descricao}\n"
        "Marca: {marca}"
    ),
    PromptTemplateName.IA_GEMINI_DESCRIPTION_USER: (
        "Escreva uma descricao de aproximadamente {tamanho_palavras} palavras para o seguinte produto:\n"
        "Use apenas fatos do contexto e nao invente historico de empresa ou ano de fundacao.\n"
        "Use tom claro e util, sem fantasia nem exagero comercial.\n"
        "Nao use chamada para acao ou frases promocionais como 'adquira', 'compre', 'invista' ou 'descubra'.\n"
        "Preserve nomes proprios no idioma original.\n"
        "Nome original: {nome_base}\n"
        "Informacoes adicionais: {descricao}\n"
        "Marca: {marca}\n"
        "Modelo: {modelo}"
    ),
    PromptTemplateName.IA_GEMINI_ATTRIBUTE_SUGGESTION_USER: (
        "Analise as seguintes informacoes sobre um produto:\n---\n{contexto}\n---\n\n"
        "Com base nesta analise, sugira valores apropriados para os seguintes atributos definidos "
        "(use as chaves exatamente como listadas):\n{lista_chaves_str}\n\n"
        "Seu objetivo e preencher esses atributos com informacoes relevantes e concisas inferidas do contexto fornecido.\n"
        "Sua resposta DEVE ser um objeto JSON contendo uma unica chave 'sugestoes_atributos'.\n"
        "O valor de 'sugestoes_atributos' deve ser uma lista de objetos.\n"
        "Cada objeto na lista deve ter duas chaves: 'chave_atributo' (que deve ser uma das chaves da lista que forneci: {lista_chaves_inline}) e 'valor_sugerido' (a sua sugestao de valor para esse atributo).\n"
        "Se voce nao puder sugerir um valor para um atributo especifico com base nas informacoes, pode omiti-lo da lista ou fornecer um valor como 'Nao encontrado'.\n"
        "Nao inclua atributos na sua resposta que nao foram listados explicitamente."
    ),
    PromptTemplateName.VALIDATOR_CREW_ROLE: "Auditor de Qualidade de Dados de E-commerce",
    PromptTemplateName.VALIDATOR_CREW_GOAL: (
        "Sua missao e receber um dicionario de dados de produto (JSON) extraido de forma bruta "
        "e transforma-lo em um JSON limpo, padronizado e pronto para ser salvo em um banco de dados "
        "de e-commerce. Voce e o guardiao da qualidade dos dados."
    ),
    PromptTemplateName.VALIDATOR_CREW_BACKSTORY: (
        "Voce e um especialista em dados de e-commerce com um olhar treinado para identificar "
        "e corrigir inconsistencias. Voce entende a importancia de SKUs, EANs, nomes de produtos, "
        "precos e descricoes para o funcionamento de uma loja online. Sua experiencia foi forjada "
        "analisando milhares de catalogos de produtos e corrigindo erros comuns de OCR, digitacao e "
        "formatacao. Voce e metodico, preciso e implacavel na busca pela padronizacao."
    ),
    PromptTemplateName.VALIDATOR_CREW_EXPECTED_OUTPUT: "Um objeto JSON contendo os dados do produto limpos e padronizados.",
    PromptTemplateName.VALIDATOR_CREW_DESCRIPTION: (
        "Analise o seguinte dicionario de dados brutos de um produto:\n"
        "---\n"
        "{raw_data}\n"
        "---\n\n"
        "Execute as seguintes acoes de limpeza e padronizacao:\n\n"
        "1. **SKU e EAN**:\n"
        "- Remova espacos em branco extras, no inicio, no fim e no meio.\n"
        "- Corrija erros comuns de OCR: troque a letra 'O' por '0' (zero) e a letra 'I' ou 'l' por '1' (um), apenas quando fizer sentido no contexto de codigo de barras ou SKU.\n"
        "- Se o campo estiver vazio ou for nulo, mantenha `null` ou `None`.\n\n"
        "2. **Nome do Produto (nome_base)**:\n"
        "- Corrija a capitalizacao para 'Title Case'.\n"
        "- Remova termos promocionais como 'PROMOCAO' e 'OFERTA'.\n"
        "- Corrija erros obvios de digitacao, quando possivel.\n\n"
        "3. **Preco (preco_original)**:\n"
        "- O valor deve ser numerico. Remova simbolos de moeda.\n"
        "- Converta virgula decimal para ponto.\n"
        "- Se nao for preco valido, retorne `null`.\n\n"
        "4. **Descricao (descricao_original)**:\n"
        "- Corrija gramatica e ortografia.\n"
        "- Remova quebras excessivas e normalize espacos.\n"
        "- Mantenha apenas texto informativo e relevante.\n\n"
        "5. **Marca (marca)**:\n"
        "- Padronize capitalizacao.\n\n"
        "IMPORTANTE:\n"
        "- O output final deve conter APENAS o objeto JSON corrigido.\n"
        "- Nao inclua explicacoes.\n"
        "- Campos invalidos devem ser `null`.\n"
        "- Mantenha a estrutura de chaves original."
    ),
}


class _SafePromptFormatDict(dict):
    """Prevent KeyError when rendering templates with partial context."""

    def __missing__(self, key: str) -> str:
        """Return an empty string for missing prompt placeholders."""
        return ""


@dataclass(frozen=True)
class PromptLookupResult:
    """Return prompt lookup metadata without leaking ORM entities to callers."""

    nome: str
    conteudo: str
    versao: int
    source: str


class PromptTemplateRepository:
    """Repository OO para leitura e seed de prompts versionados."""

    def __init__(self, db: Session) -> None:
        """Initialize injected dependencies and runtime configuration for Prompt Template Repository."""
        self._db = db

    def get_latest_template(self, *, nome: str) -> Optional[PromptTemplate]:
        """Return the highest prompt version for the requested logical name."""
        return (
            self._db.query(PromptTemplate)
            .filter(PromptTemplate.nome == nome)
            .order_by(PromptTemplate.versao.desc(), PromptTemplate.id.desc())
            .first()
        )

    def get_prompt(self, *, nome: str) -> PromptLookupResult:
        """Return the latest persisted prompt or the fallback default when none exists."""
        template = self.get_latest_template(nome=nome)
        if template is not None:
            return PromptLookupResult(
                nome=template.nome,
                conteudo=template.conteudo,
                versao=int(template.versao or 1),
                source="database",
            )

        return PromptLookupResult(
            nome=nome,
            conteudo=DEFAULT_PROMPT_TEMPLATES[nome],
            versao=0,
            source="default",
        )

    def render_prompt(self, *, nome: str, context: Optional[Mapping[str, Any]] = None) -> PromptLookupResult:
        """Render a prompt template with a partial-safe string context."""
        prompt = self.get_prompt(nome=nome)
        rendered = prompt.conteudo.format_map(_SafePromptFormatDict(**dict(context or {})))
        return PromptLookupResult(
            nome=prompt.nome,
            conteudo=rendered,
            versao=prompt.versao,
            source=prompt.source,
        )

    def sync_default_templates(self) -> Dict[str, int]:
        """Insert new prompt versions when bundled defaults diverge from persisted ones."""
        created_versions: Dict[str, int] = {}
        for nome, conteudo in DEFAULT_PROMPT_TEMPLATES.items():
            latest = self.get_latest_template(nome=nome)
            if latest is not None and str(latest.conteudo or "") == conteudo:
                continue

            next_version = 1 if latest is None else int(latest.versao or 0) + 1
            template = PromptTemplate(nome=nome, conteudo=conteudo, versao=next_version)
            self._db.add(template)
            self._db.flush()
            created_versions[nome] = next_version

        if created_versions:
            self._db.commit()
        return created_versions


class PromptTemplateResolver:
    """Resolve prompts via database first and fallback defaults when needed."""

    def __init__(self, *, session_factory=SessionLocal, repository_cls=PromptTemplateRepository) -> None:
        """Initialize injected dependencies and runtime configuration for Prompt Template Resolver."""
        self._session_factory = session_factory
        self._repository_cls = repository_cls

    def get_prompt(self, *, nome: str, context: Optional[Mapping[str, Any]] = None) -> PromptLookupResult:
        """Load and optionally render a prompt in an isolated read session."""
        session = self._session_factory()
        try:
            return self._repository_cls(session).render_prompt(nome=nome, context=context)
        except Exception:
            content = DEFAULT_PROMPT_TEMPLATES[nome].format_map(
                _SafePromptFormatDict(**dict(context or {}))
            )
            return PromptLookupResult(nome=nome, conteudo=content, versao=0, source="default")
        finally:
            session.close()
