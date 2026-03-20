/**
 * Module historico page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import {
  LuBot,
  LuChevronDown,
  LuChevronUp,
  LuCircleAlert,
  LuFilter,
  LuHistory,
  LuLayers3,
  LuSparkles,
} from 'react-icons/lu';
import PaginationControls from '../components/common/PaginationControls';
import { useAuth } from '../contexts/AuthContext';
import historicoService from '../services/historicoService';
import usoIAService from '../services/usoIAService';
import logger from '../utils/logger';
import './HistoricoPage.css';

const IA_ACTION_LABELS = {
  analise_sentimento_reviews: 'Analise de sentimento',
  criacao_descricao_produto: 'Descricao de produto',
  criacao_produto: 'Criacao de produto',
  criacao_titulo_produto: 'Titulos de produto',
  enriquecimento_web: 'Enriquecimento web',
  enriquecimento_web_produto: 'Enriquecimento web',
  geracao_descricao_ia: 'Geracao de descricao IA',
  geracao_tags_produto: 'Geracao de tags',
  geracao_titulo_ia: 'Geracao de titulo IA',
  otimizacao_seo_conteudo: 'Otimizacao SEO',
  sugestao_atributos_gemini: 'Sugestao de atributos',
  sumarizacao_caracteristicas: 'Sumarizacao de caracteristicas',
  traducao_conteudo_produto: 'Traducao de conteudo',
};

const IA_STATUS_META = {
  ERRO: { label: 'Erro', tone: 'danger' },
  FALHA: { label: 'Falha', tone: 'danger' },
  SUCESSO: { label: 'Sucesso', tone: 'success' },
};

const SYSTEM_ACTION_LABELS = {
  ATUALIZACAO: 'Atualizacao',
  CRIACAO: 'Criacao',
  DELECAO: 'Exclusao',
};

const ENTITY_LABELS = {
  fornecedor: 'Fornecedor',
  fornecedores: 'Fornecedores',
  product_type: 'Tipo de produto',
  produto: 'Produto',
  tipos_de_produto: 'Tipos de produto',
  user: 'Usuario',
  usuario: 'Usuario',
};

const SYSTEM_ACTION_OPTIONS = [
  { value: '', label: 'Todas as acoes' },
  { value: 'CRIACAO', label: 'Criacao' },
  { value: 'ATUALIZACAO', label: 'Atualizacao' },
  { value: 'DELECAO', label: 'Exclusao' },
];

function normalizeText(value = '') {
  return String(value || '')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .trim();
}

function formatDateTime(value) {
  if (!value) return 'N/A';
  try {
    return format(parseISO(value), 'dd/MM/yyyy HH:mm:ss', { locale: ptBR });
  } catch {
    return 'N/A';
  }
}

function formatDateShort(value) {
  if (!value) return 'Sem data';
  try {
    return format(parseISO(value), 'dd/MM/yyyy', { locale: ptBR });
  } catch {
    return 'Sem data';
  }
}

function formatIAAction(value = '') {
  const normalized = normalizeText(value);
  if (IA_ACTION_LABELS[normalized]) return IA_ACTION_LABELS[normalized];
  const raw = String(value || '').trim();
  if (!raw) return 'Nao informado';
  return raw
    .replace(/_/g, ' ')
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

function formatSystemAction(value = '') {
  return SYSTEM_ACTION_LABELS[String(value || '').trim().toUpperCase()] || 'Nao informado';
}

function formatEntity(value = '') {
  return ENTITY_LABELS[normalizeText(value)] || String(value || '').trim() || 'Nao informado';
}

function getIAStatusMeta(record) {
  const key = String(record?.status || '').trim().toUpperCase();
  if (IA_STATUS_META[key]) return IA_STATUS_META[key];
  if (record?.detalhes_erro) return IA_STATUS_META.FALHA;
  return { label: 'Sem status', tone: 'muted' };
}

function getTokenTotal(record) {
  const promptTokens = Number(record?.tokens_prompt || 0);
  const responseTokens = Number(record?.tokens_resposta || 0);
  const total = promptTokens + responseTokens;
  return total > 0 ? total : null;
}

function buildIASummary(record) {
  if (record?.detalhes_erro) return record.detalhes_erro;
  if (record?.resposta_ia) return record.resposta_ia;
  if (record?.prompt_utilizado) return record.prompt_utilizado;
  return 'Sem detalhes adicionais para este registro.';
}

function buildSystemSummary(record) {
  const details = record?.detalhes_json;
  if (details && typeof details === 'object') {
    if (details.nome_base) return `Produto relacionado: ${details.nome_base}`;
    if (details.nome) return `Nome relacionado: ${details.nome}`;
    const entries = Object.entries(details).slice(0, 2);
    if (entries.length > 0) {
      return entries.map(([key, value]) => `${key}: ${String(value)}`).join(' | ');
    }
  }
  return `${formatSystemAction(record?.acao)} em ${formatEntity(record?.entidade)}`;
}

function buildEntityOptions(items) {
  const values = Array.from(
    new Set((Array.isArray(items) ? items : []).map((item) => String(item?.entidade || '').trim()).filter(Boolean))
  ).sort((first, second) => first.localeCompare(second));

  return [{ value: '', label: 'Todas as entidades' }].concat(
    values.map((value) => ({ value, label: formatEntity(value) }))
  );
}

function matchesIASearch(record, query) {
  const normalizedQuery = normalizeText(query);
  if (!normalizedQuery) return true;

  return [
    record?.id,
    record?.produto_id,
    record?.tipo_acao,
    record?.provedor_ia,
    record?.modelo_ia,
    record?.resposta_ia,
    record?.prompt_utilizado,
    record?.detalhes_erro,
    record?.status,
  ]
    .map((value) => normalizeText(value))
    .some((value) => value.includes(normalizedQuery));
}

function matchesSystemSearch(record, query) {
  const normalizedQuery = normalizeText(query);
  if (!normalizedQuery) return true;

  return [
    record?.id,
    record?.entity_id,
    record?.entidade,
    record?.acao,
    record?.user_id,
    buildSystemSummary(record),
    JSON.stringify(record?.detalhes_json || {}),
  ]
    .map((value) => normalizeText(value))
    .some((value) => value.includes(normalizedQuery));
}

function HistoricoPage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [activeTab, setActiveTab] = useState('ia');
  const [historicoIA, setHistoricoIA] = useState([]);
  const [iaTotalItems, setIaTotalItems] = useState(0);
  const [iaCurrentPage, setIaCurrentPage] = useState(0);
  const [iaItemsPerPage, setIaItemsPerPage] = useState(10);
  const [iaLoading, setIaLoading] = useState(false);
  const [iaError, setIaError] = useState('');
  const [iaExpandedId, setIaExpandedId] = useState(null);
  const [iaFilters, setIaFilters] = useState({
    dataFim: '',
    dataInicio: '',
    query: '',
    tipoGeracao: '',
  });
  const [historicoSistema, setHistoricoSistema] = useState([]);
  const [systemTotalItems, setSystemTotalItems] = useState(0);
  const [systemCurrentPage, setSystemCurrentPage] = useState(0);
  const [systemItemsPerPage, setSystemItemsPerPage] = useState(10);
  const [systemLoading, setSystemLoading] = useState(false);
  const [systemError, setSystemError] = useState('');
  const [systemExpandedId, setSystemExpandedId] = useState(null);
  const [systemFilters, setSystemFilters] = useState({
    acao: '',
    entidade: '',
    query: '',
  });
  const [tiposAcaoIA, setTiposAcaoIA] = useState([]);

  const fetchHistoricoIA = useCallback(async () => {
    if (isAuthLoading) {
      logger.log('HistoricoPage: auth esta carregando, aguardando...');
      return;
    }

    if (!user) {
      logger.log('HistoricoPage: usuario nao autenticado, nao buscando historico.');
      setHistoricoIA([]);
      setIaTotalItems(0);
      setIaLoading(false);
      return;
    }

    setIaLoading(true);
    setIaError('');
    try {
      const params = {
        data_fim: iaFilters.dataFim ? `${iaFilters.dataFim}T23:59:59` : undefined,
        data_inicio: iaFilters.dataInicio ? `${iaFilters.dataInicio}T00:00:00` : undefined,
        limit: iaItemsPerPage,
        skip: iaCurrentPage * iaItemsPerPage,
        tipo_geracao: iaFilters.tipoGeracao || undefined,
      };

      const responseData = await usoIAService.getMeuHistoricoUsoIA(params);
      if (responseData && Array.isArray(responseData.items) && typeof responseData.total_items === 'number') {
        setHistoricoIA(responseData.items);
        setIaTotalItems(responseData.total_items);
      } else {
        console.warn('HistoricoPage: formato de dados inesperado recebido para historico IA:', responseData);
        setHistoricoIA([]);
        setIaTotalItems(0);
      }
    } catch (err) {
      const errorMsg =
        err?.response?.data?.detail ||
        err?.detail ||
        err?.message ||
        'Falha ao buscar historico de uso de IA.';
      console.error('HistoricoPage: erro ao buscar historico de IA:', err);
      setIaError(errorMsg);
      setHistoricoIA([]);
      setIaTotalItems(0);
    } finally {
      setIaLoading(false);
    }
  }, [iaCurrentPage, iaFilters.dataFim, iaFilters.dataInicio, iaFilters.tipoGeracao, iaItemsPerPage, isAuthLoading, user]);

  const fetchHistoricoSistema = useCallback(async () => {
    if (isAuthLoading || !user) {
      return;
    }

    setSystemLoading(true);
    setSystemError('');
    try {
      const data = await historicoService.getHistorico({
        acao: systemFilters.acao || undefined,
        entidade: systemFilters.entidade || undefined,
        limit: systemItemsPerPage,
        skip: systemCurrentPage * systemItemsPerPage,
      });
      if (data && Array.isArray(data.items) && typeof data.total_items === 'number') {
        setHistoricoSistema(data.items);
        setSystemTotalItems(data.total_items);
      } else {
        console.warn('HistoricoPage: formato de dados inesperado recebido para historico do sistema:', data);
        setHistoricoSistema([]);
        setSystemTotalItems(0);
      }
    } catch (err) {
      const errorMsg =
        err?.response?.data?.detail ||
        err?.detail ||
        err?.message ||
        'Falha ao buscar historico do sistema.';
      console.error('HistoricoPage: erro ao buscar historico do sistema:', err);
      setSystemError(errorMsg);
      setHistoricoSistema([]);
      setSystemTotalItems(0);
    } finally {
      setSystemLoading(false);
    }
  }, [isAuthLoading, systemCurrentPage, systemFilters.acao, systemFilters.entidade, systemItemsPerPage, user]);

  useEffect(() => {
    void fetchHistoricoIA();
  }, [fetchHistoricoIA]);

  useEffect(() => {
    void fetchHistoricoSistema();
  }, [fetchHistoricoSistema]);

  useEffect(() => {
    if (isAuthLoading || !user) {
      return;
    }

    const loadTiposAcaoIA = async () => {
      try {
        const data = await usoIAService.getTiposHistorico();
        setTiposAcaoIA(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('HistoricoPage: erro ao carregar tipos de acao de IA:', err);
      }
    };
    void loadTiposAcaoIA();
  }, [isAuthLoading, user]);

  const iaVisibleItems = useMemo(
    () => historicoIA.filter((record) => matchesIASearch(record, iaFilters.query)),
    [historicoIA, iaFilters.query]
  );

  const systemVisibleItems = useMemo(
    () => historicoSistema.filter((record) => matchesSystemSearch(record, systemFilters.query)),
    [historicoSistema, systemFilters.query]
  );

  const entityOptions = useMemo(() => buildEntityOptions(historicoSistema), [historicoSistema]);

  const summaryCards = useMemo(() => {
    const iaFailures = historicoIA.filter((record) => getIAStatusMeta(record).tone === 'danger').length;
    const totalTokensOnPage = historicoIA.reduce((sum, record) => sum + Number(getTokenTotal(record) || 0), 0);
    const latestActivity = [historicoIA[0]?.created_at, historicoSistema[0]?.created_at]
      .filter(Boolean)
      .sort()
      .reverse()[0];

    return [
      {
        helper: 'Total com filtros aplicados no backend',
        icon: <LuSparkles />,
        label: 'Registros IA',
        value: iaTotalItems,
      },
      {
        helper: 'Falhas detectadas nesta pagina',
        icon: <LuCircleAlert />,
        label: 'Falhas IA',
        tone: iaFailures > 0 ? 'danger' : 'success',
        value: iaFailures,
      },
      {
        helper: 'Soma de prompt e resposta na pagina atual',
        icon: <LuBot />,
        label: 'Tokens na pagina',
        value: totalTokensOnPage,
      },
      {
        helper: latestActivity ? `Ultima atividade em ${formatDateShort(latestActivity)}` : 'Sem atividade registrada',
        icon: <LuHistory />,
        label: 'Eventos do sistema',
        value: systemTotalItems,
      },
    ];
  }, [historicoIA, historicoSistema, iaTotalItems, systemTotalItems]);

  const iaTotalPages = Math.ceil(iaTotalItems / iaItemsPerPage);
  const systemTotalPages = Math.ceil(systemTotalItems / systemItemsPerPage);

  const handleIAFilterChange = (key, value) => {
    setIaFilters((prev) => ({ ...prev, [key]: value }));
    if (key !== 'query') {
      setIaCurrentPage(0);
    }
  };

  const handleSystemFilterChange = (key, value) => {
    setSystemFilters((prev) => ({ ...prev, [key]: value }));
    if (key !== 'query') {
      setSystemCurrentPage(0);
    }
  };

  if (isAuthLoading) {
    return (
      <div className="app-page-shell historico-page-shell">
        <div className="historico-state-card">Carregando historico...</div>
      </div>
    );
  }

  return (
    <div className="app-page-shell historico-page-shell">
      <section className="historico-overview-grid">
        {summaryCards.map((card) => (
          <article
            key={card.label}
            className={`historico-summary-card${card.tone ? ` historico-summary-card--${card.tone}` : ''}`}
          >
            <div className="historico-summary-icon">{card.icon}</div>
            <div className="historico-summary-content">
              <span className="historico-summary-label">{card.label}</span>
              <strong className="historico-summary-value">{card.value}</strong>
              <p className="historico-summary-helper">{card.helper}</p>
            </div>
          </article>
        ))}
      </section>

      <section className="historico-panel">
        <div className="historico-panel-header">
          <div>
            <h2>Central de historico</h2>
            <p>Acompanhe o que foi executado com IA e os eventos do sistema sem sair da operacao.</p>
          </div>
          <div className="historico-tabs" role="tablist" aria-label="Tipos de historico">
            <button
              type="button"
              className={`historico-tab${activeTab === 'ia' ? ' active' : ''}`}
              role="tab"
              aria-selected={activeTab === 'ia'}
              onClick={() => setActiveTab('ia')}
            >
              <LuBot />
              Uso de IA
            </button>
            <button
              type="button"
              className={`historico-tab${activeTab === 'sistema' ? ' active' : ''}`}
              role="tab"
              aria-selected={activeTab === 'sistema'}
              onClick={() => setActiveTab('sistema')}
            >
              <LuLayers3 />
              Eventos do sistema
            </button>
          </div>
        </div>

        {activeTab === 'ia' ? (
          <>
            <div className="historico-filter-grid">
              <label className="historico-filter-field">
                <span>Tipo de acao de IA</span>
                <select
                  aria-label="Tipo de acao de IA"
                  value={iaFilters.tipoGeracao}
                  onChange={(event) => handleIAFilterChange('tipoGeracao', event.target.value)}
                  disabled={iaLoading}
                >
                  <option value="">Todas as acoes</option>
                  {tiposAcaoIA.map((tipo) => (
                    <option key={tipo} value={tipo}>
                      {formatIAAction(tipo)}
                    </option>
                  ))}
                </select>
              </label>

              <label className="historico-filter-field">
                <span>De</span>
                <input
                  aria-label="Data inicial de uso de IA"
                  type="date"
                  value={iaFilters.dataInicio}
                  onChange={(event) => handleIAFilterChange('dataInicio', event.target.value)}
                />
              </label>

              <label className="historico-filter-field">
                <span>Ate</span>
                <input
                  aria-label="Data final de uso de IA"
                  type="date"
                  value={iaFilters.dataFim}
                  onChange={(event) => handleIAFilterChange('dataFim', event.target.value)}
                />
              </label>

              <label className="historico-filter-field historico-filter-field--search">
                <span>Busca textual</span>
                <div className="historico-filter-search">
                  <LuFilter />
                  <input
                    aria-label="Busca textual no historico de IA"
                    placeholder="Produto, modelo, resposta ou erro"
                    type="search"
                    value={iaFilters.query}
                    onChange={(event) => handleIAFilterChange('query', event.target.value)}
                  />
                </div>
              </label>
            </div>

            <p className="historico-filter-note">
              O filtro textual desta tela atua sobre os registros ja carregados na pagina atual.
            </p>

            {iaLoading ? (
              <div className="historico-state-card">Carregando registros de uso de IA...</div>
            ) : iaError ? (
              <div className="historico-state-card historico-state-card--error">{iaError}</div>
            ) : iaVisibleItems.length === 0 ? (
              <div className="historico-state-card">Nenhum registro de uso de IA encontrado com os filtros atuais.</div>
            ) : (
              <div className="table-responsive">
                <table className="historico-table">
                  <thead>
                    <tr>
                      <th>Quando</th>
                      <th>Produto</th>
                      <th>Acao</th>
                      <th>Status</th>
                      <th>Modelo</th>
                      <th>Resumo</th>
                      <th>Detalhes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {iaVisibleItems.map((record) => {
                      const isExpanded = iaExpandedId === record.id;
                      const statusMeta = getIAStatusMeta(record);
                      const tokenTotal = getTokenTotal(record);

                      return (
                        <React.Fragment key={record.id}>
                          <tr>
                            <td>{formatDateTime(record.created_at)}</td>
                            <td>
                              <div className="historico-cell-stack">
                                <strong>{record.produto_id || 'N/A'}</strong>
                                <span>Registro #{record.id}</span>
                              </div>
                            </td>
                            <td>{formatIAAction(record.tipo_acao)}</td>
                            <td>
                              <span className={`historico-chip historico-chip--${statusMeta.tone}`}>
                                {statusMeta.label}
                              </span>
                            </td>
                            <td>
                              <div className="historico-cell-stack">
                                <strong>{record.modelo_ia || 'N/A'}</strong>
                                <span>{record.provedor_ia || 'Provedor nao informado'}</span>
                                <span>{tokenTotal ? `${tokenTotal} tokens` : 'Sem tokens'}</span>
                              </div>
                            </td>
                            <td>
                              <div className="historico-summary-text" title={buildIASummary(record)}>
                                {buildIASummary(record)}
                              </div>
                            </td>
                            <td>
                              <button
                                type="button"
                                className="historico-detail-toggle"
                                onClick={() => setIaExpandedId(isExpanded ? null : record.id)}
                              >
                                {isExpanded ? <LuChevronUp /> : <LuChevronDown />}
                                {isExpanded ? 'Ocultar' : 'Ver'}
                              </button>
                            </td>
                          </tr>
                          {isExpanded ? (
                            <tr className="historico-detail-row">
                              <td colSpan={7}>
                                <div className="historico-detail-panel">
                                  <div className="historico-detail-grid">
                                    <div>
                                      <span className="historico-detail-label">Provedor</span>
                                      <strong>{record.provedor_ia || 'Nao informado'}</strong>
                                    </div>
                                    <div>
                                      <span className="historico-detail-label">Modelo</span>
                                      <strong>{record.modelo_ia || 'Nao informado'}</strong>
                                    </div>
                                    <div>
                                      <span className="historico-detail-label">Creditos</span>
                                      <strong>{record.creditos_consumidos ?? 0}</strong>
                                    </div>
                                    <div>
                                      <span className="historico-detail-label">Custo estimado</span>
                                      <strong>
                                        {record.custo_estimado_usd != null
                                          ? `US$ ${Number(record.custo_estimado_usd).toFixed(4)}`
                                          : 'Nao informado'}
                                      </strong>
                                    </div>
                                  </div>
                                  {record.prompt_utilizado ? (
                                    <div className="historico-detail-block">
                                      <span className="historico-detail-label">Prompt utilizado</span>
                                      <pre>{record.prompt_utilizado}</pre>
                                    </div>
                                  ) : null}
                                  {record.resposta_ia ? (
                                    <div className="historico-detail-block">
                                      <span className="historico-detail-label">Resposta retornada</span>
                                      <pre>{record.resposta_ia}</pre>
                                    </div>
                                  ) : null}
                                  {record.detalhes_erro ? (
                                    <div className="historico-detail-block historico-detail-block--error">
                                      <span className="historico-detail-label">Erro registrado</span>
                                      <pre>{record.detalhes_erro}</pre>
                                    </div>
                                  ) : null}
                                </div>
                              </td>
                            </tr>
                          ) : null}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <PaginationControls
              currentPage={iaCurrentPage}
              totalPages={iaTotalPages}
              onPageChange={setIaCurrentPage}
              isLoading={iaLoading}
              itemsPerPage={iaItemsPerPage}
              onItemsPerPageChange={(value) => {
                setIaItemsPerPage(Number(value));
                setIaCurrentPage(0);
              }}
              totalItems={iaTotalItems}
            />
          </>
        ) : (
          <>
            <div className="historico-filter-grid">
              <label className="historico-filter-field">
                <span>Entidade</span>
                <select
                  aria-label="Entidade do historico do sistema"
                  value={systemFilters.entidade}
                  onChange={(event) => handleSystemFilterChange('entidade', event.target.value)}
                  disabled={systemLoading}
                >
                  {entityOptions.map((option) => (
                    <option key={option.value || 'all'} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="historico-filter-field">
                <span>Acao do sistema</span>
                <select
                  aria-label="Acao do historico do sistema"
                  value={systemFilters.acao}
                  onChange={(event) => handleSystemFilterChange('acao', event.target.value)}
                  disabled={systemLoading}
                >
                  {SYSTEM_ACTION_OPTIONS.map((option) => (
                    <option key={option.value || 'all'} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="historico-filter-field historico-filter-field--search historico-filter-field--wide">
                <span>Busca textual</span>
                <div className="historico-filter-search">
                  <LuFilter />
                  <input
                    aria-label="Busca textual no historico do sistema"
                    placeholder="Entidade, ID, acao ou detalhe"
                    type="search"
                    value={systemFilters.query}
                    onChange={(event) => handleSystemFilterChange('query', event.target.value)}
                  />
                </div>
              </label>
            </div>

            <p className="historico-filter-note">
              Entidade e acao filtram direto na API. A busca textual desta tela atua sobre os itens carregados.
            </p>

            {systemLoading ? (
              <div className="historico-state-card">Carregando eventos do sistema...</div>
            ) : systemError ? (
              <div className="historico-state-card historico-state-card--error">{systemError}</div>
            ) : systemVisibleItems.length === 0 ? (
              <div className="historico-state-card">Nenhum evento do sistema encontrado com os filtros atuais.</div>
            ) : (
              <div className="table-responsive">
                <table className="historico-table">
                  <thead>
                    <tr>
                      <th>Quando</th>
                      <th>Entidade</th>
                      <th>Acao</th>
                      <th>Registro</th>
                      <th>Resumo</th>
                      <th>Detalhes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {systemVisibleItems.map((record) => {
                      const isExpanded = systemExpandedId === record.id;
                      return (
                        <React.Fragment key={record.id}>
                          <tr>
                            <td>{formatDateTime(record.created_at)}</td>
                            <td>{formatEntity(record.entidade)}</td>
                            <td>
                              <span className="historico-chip historico-chip--muted">
                                {formatSystemAction(record.acao)}
                              </span>
                            </td>
                            <td>
                              <div className="historico-cell-stack">
                                <strong>{record.entity_id || 'N/A'}</strong>
                                <span>Historico #{record.id}</span>
                              </div>
                            </td>
                            <td>
                              <div className="historico-summary-text" title={buildSystemSummary(record)}>
                                {buildSystemSummary(record)}
                              </div>
                            </td>
                            <td>
                              <button
                                type="button"
                                className="historico-detail-toggle"
                                onClick={() => setSystemExpandedId(isExpanded ? null : record.id)}
                              >
                                {isExpanded ? <LuChevronUp /> : <LuChevronDown />}
                                {isExpanded ? 'Ocultar' : 'Ver'}
                              </button>
                            </td>
                          </tr>
                          {isExpanded ? (
                            <tr className="historico-detail-row">
                              <td colSpan={6}>
                                <div className="historico-detail-panel">
                                  <div className="historico-detail-grid">
                                    <div>
                                      <span className="historico-detail-label">Usuario</span>
                                      <strong>{record.user_id || 'Nao informado'}</strong>
                                    </div>
                                    <div>
                                      <span className="historico-detail-label">Entidade</span>
                                      <strong>{formatEntity(record.entidade)}</strong>
                                    </div>
                                    <div>
                                      <span className="historico-detail-label">Acao</span>
                                      <strong>{formatSystemAction(record.acao)}</strong>
                                    </div>
                                    <div>
                                      <span className="historico-detail-label">Horario</span>
                                      <strong>{formatDateTime(record.created_at)}</strong>
                                    </div>
                                  </div>
                                  <div className="historico-detail-block">
                                    <span className="historico-detail-label">Detalhes registrados</span>
                                    <pre>
                                      {record?.detalhes_json
                                        ? JSON.stringify(record.detalhes_json, null, 2)
                                        : 'Nenhum detalhe adicional foi salvo para este evento.'}
                                    </pre>
                                  </div>
                                </div>
                              </td>
                            </tr>
                          ) : null}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <PaginationControls
              currentPage={systemCurrentPage}
              totalPages={systemTotalPages}
              onPageChange={setSystemCurrentPage}
              isLoading={systemLoading}
              itemsPerPage={systemItemsPerPage}
              onItemsPerPageChange={(value) => {
                setSystemItemsPerPage(Number(value));
                setSystemCurrentPage(0);
              }}
              totalItems={systemTotalItems}
            />
          </>
        )}
      </section>
    </div>
  );
}

export default HistoricoPage;
