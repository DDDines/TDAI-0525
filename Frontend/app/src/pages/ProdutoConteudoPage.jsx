/**
 * Module produto conteudo page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  LuBox,
  LuBuilding2,
  LuChevronLeft,
  LuChevronRight,
  LuCircleCheck,
  LuCircleMinus,
  LuCircleX,
  LuClock3,
  LuCopy,
  LuFileText,
  LuGlobe,
  LuHash,
  LuImage,
  LuLoaderCircle,
  LuPencil,
  LuScanBarcode,
  LuSparkles,
  LuTag,
  LuTrash2,
  LuTriangleAlert,
  LuType,
  LuX,
} from 'react-icons/lu';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import ProductContentWorkspace from '../components/produtos/ProductContentWorkspace.jsx';
import { useAppExperience } from '../contexts/AppExperienceContext.jsx';
import productService from '../services/productService';
import { showErrorToast, showSuccessToast, showWarningToast } from '../utils/notifications';
import { extractErrorMessage } from '../utils/errorDetails.js';
import { queryKeys } from '../lib/queryKeys.js';
import { calculateContentQualityScore, getContentQualityBreakdown, getContentQualityTier } from '../utils/productQualityScore.js';
import './ProdutoConteudoPage.css';

const STATUS_CONFIG = {
  NAO_INICIADO: { className: 'grey', label: 'Não iniciado', title: 'Não iniciado', icon: LuCircleMinus },
  PENDENTE: { className: 'orange', label: 'Pendente', title: 'Pendente', icon: LuClock3 },
  EM_PROGRESSO: { className: 'blue', label: 'Em progresso', title: 'Em progresso', icon: LuLoaderCircle },
  CONCLUIDO: { className: 'green', label: 'Concluído', title: 'Concluído', icon: LuCircleCheck },
  CONCLUIDO_SUCESSO: { className: 'green', label: 'Concluído', title: 'Concluído', icon: LuCircleCheck },
  CONCLUIDO_COM_DADOS_PARCIAIS: {
    className: 'blue',
    label: 'Parcial',
    title: 'Concluído com dados parciais',
    icon: LuTriangleAlert,
  },
  FALHA: { className: 'red', label: 'Falha', title: 'Falha', icon: LuCircleX },
  FALHOU: { className: 'red', label: 'Falha', title: 'Falhou', icon: LuCircleX },
  FALHA_API_EXTERNA: { className: 'red', label: 'Falha API', title: 'Falha de API externa', icon: LuCircleX },
  FALHA_CONFIGURACAO_API_EXTERNA: {
    className: 'red',
    label: 'Configuração',
    title: 'Falha de configuração da API',
    icon: LuTriangleAlert,
  },
  NENHUMA_FONTE_ENCONTRADA: {
    className: 'red',
    label: 'Sem fonte',
    title: 'Nenhuma fonte encontrada',
    icon: LuCircleMinus,
  },
  NAO_APLICAVEL: { className: 'grey', label: 'Não aplicável', title: 'Não aplicável', icon: LuCircleMinus },
};

const PROCESS_STATUS_CONFIG = [
  { key: 'status_enriquecimento_web', label: 'Web', title: 'Enriquecimento web', icon: LuGlobe },
  { key: 'status_titulo_ia', label: 'Títulos', title: 'Geração de títulos', icon: LuType },
  { key: 'status_descricao_ia', label: 'Descrição', title: 'Geração de descrição', icon: LuFileText },
];

const REPROCESS_CONFIRM_STATUSES = new Set([
  'CONCLUIDO',
  'CONCLUIDO_SUCESSO',
  'CONCLUIDO_COM_DADOS_PARCIAIS',
]);
const WEB_ENRICHMENT_TERMINAL_STATUSES = new Set([
  'CONCLUIDO',
  'CONCLUIDO_SUCESSO',
  'CONCLUIDO_COM_DADOS_PARCIAIS',
  'FALHA',
  'FALHOU',
  'FALHA_API_EXTERNA',
  'FALHA_CONFIGURACAO_API_EXTERNA',
  'NENHUMA_FONTE_ENCONTRADA',
  'NAO_APLICAVEL',
]);
const WEB_ENRICHMENT_WARNING_STATUSES = new Set([
  'CONCLUIDO_COM_DADOS_PARCIAIS',
  'FALHA',
  'FALHOU',
  'FALHA_API_EXTERNA',
  'FALHA_CONFIGURACAO_API_EXTERNA',
  'NENHUMA_FONTE_ENCONTRADA',
]);
const GENERATION_TERMINAL_STATUSES = new Set([
  'CONCLUIDO',
  'CONCLUIDO_SUCESSO',
  'FALHA',
  'FALHOU',
  'NAO_APLICAVEL',
]);
const ACTIVE_PROCESS_STATUSES = new Set([
  'PENDENTE',
  'EM_PROGRESSO',
]);
const PROCESS_POLL_INTERVAL_MS = 3000;
const PROCESS_MAX_POLLS = 40;
const POLL_CANCELLED = Symbol('product-process-poll-cancelled');
const POLL_FAILED = Symbol('product-process-poll-failed');

const CANAIS_CONFIG = [
  { id: 'mercado_livre', label: 'Mercado Livre' },
  { id: 'google_shopping', label: 'Google Shopping' },
  { id: 'b2b', label: 'B2B / Distribuidores' },
  { id: 'ecommerce', label: 'E-commerce' },
];

const COMPANY_TIMELINE_HINTS = [
  'iniciou suas atividades',
  'iniciou as atividades',
  'fundada em',
  'fundado em',
  'anos de mercado',
  'no mercado desde',
  'atuando desde',
  'historia da empresa',
];

const COLLECTED_FIELD_PRIORITY = [
  ['modelo', 'Modelo'],
  ['categoria_original', 'Categoria original'],
  ['categoria_mapeada', 'Categoria mapeada'],
  ['ncm', 'NCM'],
  ['peso_gramas', 'Peso (g)'],
  ['dimensoes_cm', 'Dimensões (cm)'],
  ['tags_palavras_chave', 'Palavras-chave'],
];

const HIDDEN_WEB_KEYS = new Set([
  'titulos_sugeridos_gerados',
  'descricao_gerada',
  'descricao_detalhada_seo',
  'feedback_conteudo',
  'feedback_conteudo_historico',
  'html_extraido',
  'html_bruto',
  'texto_bruto',
  'texto_extraido',
  'resumo_aplicacao',
  'historico_mensagens',
  'log_processamento',
]);

const HIDDEN_KEY_PATTERNS = [
  /historico/i,
  /trace/i,
  /stack/i,
  /prompt/i,
  /resposta/i,
  /html/i,
  /raw/i,
  /bruto/i,
  /feedback/i,
  /debug/i,
  /log/i,
  /telemetry/i,
  /^titulo/i,
  /^descricao/i,
  /_seo$/i,
  /imagem/i,
  /image/i,
  /thumbnail/i,
  /url.*fonte/i,
];

const RAW_WEB_ALLOWED_KEY_PATTERNS = [
  /^nome$/i,
  /^marca$/i,
  /^modelo$/i,
  /^material$/i,
  /^cor$/i,
  /^acabamento$/i,
  /^categoria/i,
  /^ncm$/i,
  /^ean$/i,
  /^sku$/i,
  /^codigo/i,
  /^referencia$/i,
  /^aplicacao$/i,
  /^compatibilidade$/i,
  /^capacidade$/i,
  /^comprimento$/i,
  /^largura$/i,
  /^altura$/i,
  /^peso/i,
  /dimens/i,
  /^composicao$/i,
  /^conteudo(?:\s+da)?\s+embalagem$/i,
  /^voltagem$/i,
  /^potencia$/i,
  /^tensao$/i,
  /^corrente$/i,
  /^pressao$/i,
  /^diametro$/i,
  /^espessura$/i,
  /^quantidade$/i,
];

const COLLECTED_VALUE_NOISE_PATTERNS = [
  /https?:\/\//i,
  /url da fonte/i,
  /caminho do catalogo/i,
  /clique para/i,
  /adicionar aos desejos/i,
  /calcule o frete/i,
  /compartilhar/i,
  /transportadoras/i,
  /whatsapp/i,
  /sem juros/i,
];

function normalizeText(value) {
  return String(value || '').trim();
}

function normalizeProcessStatusValue(statusValue) {
  const rawStatus =
    typeof statusValue === 'object' && statusValue !== null && 'value' in statusValue
      ? statusValue.value
      : statusValue;
  return String(rawStatus || '')
    .split('.')
    .pop()
    .toUpperCase();
}

function hasCompanyTimelineClaim(text) {
  const normalized = normalizeText(text).toLowerCase();
  if (COMPANY_TIMELINE_HINTS.some((hint) => normalized.includes(hint))) return true;
  return /(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|iniciou\s+suas?\s+atividades)/i.test(
    normalized,
  );
}

function sanitizeCompanyTimelineText(text) {
  const normalized = normalizeText(text).replace(/\r\n?/g, '\n');
  const filteredLines = normalized.split('\n').reduce((accumulator, rawLine) => {
    const trimmedLine = rawLine.trim();
    if (!trimmedLine) {
      if (accumulator.length > 0 && accumulator[accumulator.length - 1] !== '') {
        accumulator.push('');
      }
      return accumulator;
    }

    const filteredLine = trimmedLine
      .split(/(?<=[.!?])\s+/)
      .map((chunk) => normalizeText(chunk))
      .filter((chunk) => chunk && !hasCompanyTimelineClaim(chunk))
      .join(' ');

    if (filteredLine) {
      accumulator.push(filteredLine);
    }
    return accumulator;
  }, []);

  const sanitized = filteredLines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
  return sanitized || normalized;
}

function extractGeneratedTitles(produto) {
  const directTitles = Array.isArray(produto?.titulos_sugeridos) ? produto.titulos_sugeridos : [];
  const rawTitles = Array.isArray(produto?.dados_brutos_web?.titulos_sugeridos_gerados)
    ? produto.dados_brutos_web.titulos_sugeridos_gerados
    : [];
  const primarySource = directTitles.filter((item) => normalizeText(item)).length > 0
    ? directTitles
    : rawTitles;
  const merged = primarySource.map((item) => normalizeText(item)).filter(Boolean);
  const seen = new Set();
  const unique = [];

  for (const item of merged) {
    const folded = item.toLowerCase();
    if (seen.has(folded)) continue;
    seen.add(folded);
    unique.push(item);
  }

  return unique.slice(0, 5);
}

function extractMainDescription(produto) {
  const candidates = [
    normalizeText(produto?.descricao_chat_api),
    normalizeText(produto?.dados_brutos_web?.descricao_gerada),
    normalizeText(produto?.descricao_original),
    normalizeText(produto?.dados_brutos_web?.descricao_detalhada_seo),
  ].filter(Boolean);

  for (const candidate of candidates) {
    return sanitizeCompanyTimelineText(candidate);
  }

  return '';
}

function extractOrderedProductIdsFromState(stateValue) {
  if (!stateValue || !Array.isArray(stateValue.productIds)) {
    return [];
  }
  const parsed = stateValue.productIds
    .map((id) => Number(id))
    .filter((id) => Number.isInteger(id) && id > 0);
  return Array.from(new Set(parsed));
}

function extractListQueryFromState(stateValue) {
  if (!stateValue || typeof stateValue.productQuery !== 'object' || stateValue.productQuery === null) {
    return { sort_by: 'id', sort_order: 'asc' };
  }
  const allowedKeys = new Set([
    'sort_by',
    'sort_order',
    'search',
    'status_enriquecimento_web',
    'status_titulo_ia',
    'status_descricao_ia',
    'fornecedor_id',
    'product_type_id',
  ]);
  const sanitized = {};
  Object.entries(stateValue.productQuery).forEach(([key, value]) => {
    if (!allowedKeys.has(key)) return;
    if (value === undefined || value === null || value === '') return;
    sanitized[key] = value;
  });
  if (!sanitized.sort_by) sanitized.sort_by = 'id';
  if (!sanitized.sort_order) sanitized.sort_order = 'asc';
  return sanitized;
}

function buildReturnTarget(locationState) {
  const rawValue = typeof locationState?.returnTo === 'string' ? locationState.returnTo.trim() : '';
  return rawValue.startsWith('/produtos') ? rawValue : '/produtos';
}

function hasExplicitReturnTarget(locationState) {
  const rawValue = typeof locationState?.returnTo === 'string' ? locationState.returnTo.trim() : '';
  return rawValue.startsWith('/produtos');
}

function buildEditTarget(returnTo, productId) {
  if (!productId) {
    return returnTo || '/produtos';
  }
  const [pathname, search = ''] = String(returnTo || '/produtos').split('?');
  const params = new URLSearchParams(search);
  params.set('id', String(productId));
  const nextSearch = params.toString();
  return nextSearch ? `${pathname}?${nextSearch}` : pathname;
}

async function fetchOrderedProductIds(queryParams) {
  try {
    const response = await productService.getProdutosIds(queryParams);
    const ids = Array.isArray(response?.ids)
      ? response.ids
          .map((item) => Number(item))
          .filter((id) => Number.isInteger(id) && id > 0)
      : [];
    if (ids.length > 0) {
      return Array.from(new Set(ids));
    }
  } catch {
    // Fallback to paginated list loading when the ID endpoint is unavailable.
  }

  const allIds = [];
  const pageLimit = 200;
  let skip = 0;
  let attempts = 0;

  while (attempts < 2000) {
    attempts += 1;
    const response = await productService.getProdutos({
      ...queryParams,
      skip,
      limit: pageLimit,
    });
    const items = Array.isArray(response?.items) ? response.items : [];
    const pageIds = items
      .map((item) => Number(item?.id))
      .filter((id) => Number.isInteger(id) && id > 0);
    allIds.push(...pageIds);

    if (items.length === 0) break;

    skip += items.length;
    const totalItems = Number(response?.total_items);
    if (Number.isFinite(totalItems) && totalItems >= 0 && skip >= totalItems) break;
    if (items.length < pageLimit) break;
  }

  return Array.from(new Set(allIds));
}

function normalizeStatusValue(status) {
  const rawStatus =
    typeof status === 'object' && status !== null && 'value' in status ? status.value : status;
  return String(rawStatus ?? '').split('.').pop().toUpperCase();
}

function getStatusConfig(status) {
  const normalizedStatus = normalizeStatusValue(status);
  const cfg = STATUS_CONFIG[normalizedStatus] || {
    className: 'grey',
    label: 'Desconhecido',
    title: 'Desconhecido',
    icon: LuTriangleAlert,
  };
  return { normalizedStatus, cfg };
}

function humanizeKey(key) {
  const normalized = normalizeText(key)
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!normalized) return '';
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function normalizeValueForDisplay(value) {
  if (value === undefined || value === null) return '';
  if (Array.isArray(value)) {
    const compactValues = value
      .map((entry) => normalizeText(entry))
      .filter(Boolean)
      .slice(0, 4);
    return compactValues.length > 0 ? compactValues.join(' • ') : '';
  }
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não';
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : '';
  return normalizeText(value);
}

function countWords(value) {
  return normalizeText(value)
    .split(/\s+/)
    .filter(Boolean).length;
}

function isValueDisplayable(value) {
  if (value === undefined || value === null) return false;
  if (Array.isArray(value)) {
    return value.length > 0 && value.length <= 4 && value.every((entry) => ['string', 'number', 'boolean'].includes(typeof entry));
  }
  return ['string', 'number', 'boolean'].includes(typeof value);
}

function containsCollectedValueNoise(value) {
  const normalized = normalizeText(value);
  if (!normalized) return false;
  return COLLECTED_VALUE_NOISE_PATTERNS.some((pattern) => pattern.test(normalized));
}

function isMeaningfulCollectedValue(value) {
  const normalized = normalizeText(value);
  if (!normalized) return false;
  if (/^[\d./-]{1,5}$/.test(normalized)) return false;
  return true;
}

function isConciseCollectedValue(value, { maxChars = 140, maxWords = 18 } = {}) {
  const normalized = normalizeText(value);
  if (!normalized) return false;
  if (normalized.length > maxChars) return false;
  if (countWords(normalized) > maxWords) return false;
  if (containsCollectedValueNoise(normalized)) return false;
  if (!isMeaningfulCollectedValue(normalized)) return false;
  return true;
}

function isAllowedRawWebCollectedKey(key) {
  const normalizedKey = normalizeText(key);
  if (!normalizedKey) return false;
  return RAW_WEB_ALLOWED_KEY_PATTERNS.some((pattern) => pattern.test(normalizedKey));
}

function shouldHideCollectedKey(key, normalizedValue, knownTitles, descriptionText) {
  const normalizedKey = normalizeText(key).toLowerCase();
  if (!normalizedKey) return true;
  if (HIDDEN_WEB_KEYS.has(normalizedKey)) return true;
  if (HIDDEN_KEY_PATTERNS.some((pattern) => pattern.test(normalizedKey))) return true;
  if (!normalizedValue) return true;
  if (normalizedValue.length > 220) return true;
  if (containsCollectedValueNoise(normalizedValue)) return true;
  if (!isMeaningfulCollectedValue(normalizedValue)) return true;
  if (knownTitles.has(normalizedValue.toLowerCase())) return true;
  if (descriptionText && descriptionText.toLowerCase().includes(normalizedValue.toLowerCase())) return true;
  return false;
}

function pushCollectedEntry(entries, seen, label, value) {
  const normalizedLabel = normalizeText(label);
  const normalizedValue = normalizeText(value);
  if (!normalizedLabel || !normalizedValue) return;
  const dedupeKey = `${normalizedLabel.toLowerCase()}::${normalizedValue.toLowerCase()}`;
  if (seen.has(dedupeKey)) return;
  seen.add(dedupeKey);
  entries.push({ label: normalizedLabel, value: normalizedValue });
}

function buildGeneralInfoItems(produto) {
  const supplierName = normalizeText(produto?.fornecedor?.nome || produto?.fornecedor_nome);
  const productTypeName = normalizeText(
    produto?.product_type?.friendly_name || produto?.tipo_produto?.friendly_name || produto?.product_type_name,
  );
  return [
    { label: 'ID', value: normalizeText(produto?.id), icon: LuHash },
    { label: 'Marca', value: normalizeText(produto?.marca), icon: LuTag },
    { label: 'SKU', value: normalizeText(produto?.sku), icon: LuBox },
    { label: 'EAN', value: normalizeText(produto?.ean), icon: LuScanBarcode },
    { label: 'Fornecedor', value: supplierName, icon: LuBuilding2 },
    { label: 'Tipo', value: productTypeName, icon: LuType },
  ].filter((item) => item.value);
}

function buildCollectedInfoEntries(produto) {
  const entries = [];
  const seen = new Set();
  const titles = new Set(extractGeneratedTitles(produto).map((item) => item.toLowerCase()));
  const description = extractMainDescription(produto);
  const dynamicAttributes = produto?.dynamic_attributes && typeof produto.dynamic_attributes === 'object'
    ? produto.dynamic_attributes
    : {};
  const rawWebData = produto?.dados_brutos_web && typeof produto.dados_brutos_web === 'object'
    ? produto.dados_brutos_web
    : {};
  const attributeTemplates = Array.isArray(produto?.product_type?.attribute_templates)
    ? produto.product_type.attribute_templates
    : [];
  const attributeLabels = new Map(
    attributeTemplates
      .filter((template) => normalizeText(template?.attribute_key))
      .map((template) => [template.attribute_key, normalizeText(template.label) || humanizeKey(template.attribute_key)]),
  );

  Object.entries(dynamicAttributes).forEach(([key, value]) => {
    if (!isValueDisplayable(value)) return;
    if (!attributeLabels.has(key) && !isAllowedRawWebCollectedKey(key)) return;
    const normalizedValue = normalizeValueForDisplay(value);
    if (shouldHideCollectedKey(key, normalizedValue, titles, description)) return;
    pushCollectedEntry(entries, seen, attributeLabels.get(key) || humanizeKey(key), normalizedValue);
  });

  COLLECTED_FIELD_PRIORITY.forEach(([key, label]) => {
    const normalizedValue = normalizeValueForDisplay(produto?.[key]);
    if (!normalizedValue) return;
    if (shouldHideCollectedKey(key, normalizedValue, titles, description)) return;
    pushCollectedEntry(entries, seen, label, normalizedValue);
  });

  const specsDict = rawWebData.especificacoes_tecnicas_dict && typeof rawWebData.especificacoes_tecnicas_dict === 'object'
    ? rawWebData.especificacoes_tecnicas_dict
    : null;
  if (specsDict) {
    Object.entries(specsDict).forEach(([key, value]) => {
      if (!isValueDisplayable(value)) return;
      const normalizedValue = normalizeValueForDisplay(value);
      if (shouldHideCollectedKey(key, normalizedValue, titles, description)) return;
      if (!isConciseCollectedValue(normalizedValue, { maxChars: 120, maxWords: 16 })) return;
      pushCollectedEntry(entries, seen, humanizeKey(key), normalizedValue);
    });
  }

  Object.entries(rawWebData).forEach(([key, value]) => {
    if (key === 'especificacoes_tecnicas_dict') return;
    if (!isValueDisplayable(value)) return;
    if (!isAllowedRawWebCollectedKey(key)) return;
    const normalizedValue = normalizeValueForDisplay(value);
    if (shouldHideCollectedKey(key, normalizedValue, titles, description)) return;
    if (!isConciseCollectedValue(normalizedValue, { maxChars: 110, maxWords: 12 })) return;
    pushCollectedEntry(entries, seen, humanizeKey(key), normalizedValue);
  });

  return entries;
}

function ProcessStatusCard({ produto, processInfo }) {
  const { normalizedStatus, cfg } = getStatusConfig(produto?.[processInfo.key]);
  const StatusIcon = cfg.icon;
  const ProcessIcon = processInfo.icon;

  return (
    <article
      className={`produto-conteudo-status-card produto-conteudo-status-card--${cfg.className}`}
      title={`${processInfo.title}: ${cfg.title}`}
      aria-label={`${processInfo.title}: ${cfg.title}`}
    >
      <span className="produto-conteudo-status-icon-wrap">
        <ProcessIcon className="produto-conteudo-status-process-icon" aria-hidden="true" />
      </span>
      <div className="produto-conteudo-status-copy">
        <span className="produto-conteudo-status-label">{processInfo.label}</span>
        <strong className="produto-conteudo-status-value">
          <StatusIcon
            className={`produto-conteudo-status-state-icon ${ACTIVE_PROCESS_STATUSES.has(normalizedStatus) ? 'is-spinning' : ''}`}
            aria-hidden="true"
          />
          {cfg.label}
        </strong>
      </div>
    </article>
  );
}

function ProdutoConteudoPage() {
  const { produtoId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { effectiveMode } = useAppExperience();
  const [savingFeedback, setSavingFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [feedbackComment, setFeedbackComment] = useState('');
  const [pendingAction, setPendingAction] = useState('');
  const [channelLoading, setChannelLoading] = useState({});
  const processPollRunsRef = useRef({
    status_enriquecimento_web: 0,
    status_titulo_ia: 0,
    status_descricao_ia: 0,
  });
  const showAiFeatures = effectiveMode === 'complete';

  const idsFromState = useMemo(() => extractOrderedProductIdsFromState(location.state), [location.state]);
  const listQueryFromState = useMemo(() => extractListQueryFromState(location.state), [location.state]);
  const returnTo = useMemo(() => buildReturnTarget(location.state), [location.state]);
  const hasExplicitReturnTo = useMemo(() => hasExplicitReturnTarget(location.state), [location.state]);

  const produtoQuery = useQuery({
    queryKey: queryKeys.produto(produtoId),
    queryFn: () => productService.getProdutoById(produtoId),
  });

  const orderedIdsQuery = useQuery({
    queryKey: queryKeys.orderedProductIds(listQueryFromState),
    queryFn: () => fetchOrderedProductIds(listQueryFromState),
    placeholderData: idsFromState,
  });

  useEffect(() => {
    if (produtoQuery.error) {
      showErrorToast(extractErrorMessage(produtoQuery.error, 'Falha ao carregar conteúdo do produto.'));
    }
  }, [produtoQuery.error]);

  useEffect(
    () => () => {
      processPollRunsRef.current.status_enriquecimento_web += 1;
      processPollRunsRef.current.status_titulo_ia += 1;
      processPollRunsRef.current.status_descricao_ia += 1;
    },
    [],
  );

  const produto = produtoQuery.data;
  const titles = useMemo(() => extractGeneratedTitles(produto), [produto]);
  const description = useMemo(() => extractMainDescription(produto), [produto]);
  const generalInfoItems = useMemo(() => buildGeneralInfoItems(produto), [produto]);
  const collectedInfoEntries = useMemo(() => buildCollectedInfoEntries(produto), [produto]);

  useEffect(() => {
    const savedFeedback = produto?.dados_brutos_web?.feedback_conteudo;
    if (savedFeedback?.valor) {
      setFeedback(savedFeedback.valor);
      setFeedbackComment(savedFeedback.comentario || '');
      return;
    }
    setFeedback('');
    setFeedbackComment('');
  }, [produto]);

  const orderedProductIds = useMemo(() => {
    const merged = Array.isArray(orderedIdsQuery.data) ? [...orderedIdsQuery.data] : [];
    idsFromState.forEach((id) => {
      if (!merged.includes(id)) merged.push(id);
    });
    const productIdFromData = Number(produto?.id);
    if (Number.isInteger(productIdFromData) && productIdFromData > 0 && !merged.includes(productIdFromData)) {
      merged.push(productIdFromData);
    }
    return merged;
  }, [idsFromState, orderedIdsQuery.data, produto?.id]);

  const refreshProduto = useCallback(async () => {
    if (!produto?.id) return null;
    const updated = await productService.getProdutoById(produto.id);
    queryClient.setQueryData(queryKeys.produto(produto.id), updated);
    return updated;
  }, [produto?.id, queryClient]);

  const patchProdutoStatus = useCallback((field, value) => {
    if (!produto?.id) return;
    queryClient.setQueryData(queryKeys.produto(produto.id), (current) =>
      current ? { ...current, [field]: value } : current
    );
  }, [produto?.id, queryClient]);

  const pollProdutoUntilTerminal = useCallback(async (statusField, runId, errorMessage) => {
    const terminalStatuses =
      statusField === 'status_enriquecimento_web'
        ? WEB_ENRICHMENT_TERMINAL_STATUSES
        : GENERATION_TERMINAL_STATUSES;

    for (let attempt = 0; attempt < PROCESS_MAX_POLLS; attempt += 1) {
      if (processPollRunsRef.current[statusField] !== runId) {
        return POLL_CANCELLED;
      }

      try {
        const updated = await refreshProduto();
        if (processPollRunsRef.current[statusField] !== runId) {
          return POLL_CANCELLED;
        }
        const currentStatus = normalizeProcessStatusValue(updated?.[statusField]);
        if (terminalStatuses.has(currentStatus)) {
          return updated;
        }
      } catch (error) {
        if (processPollRunsRef.current[statusField] !== runId) {
          return POLL_CANCELLED;
        }
        showErrorToast(extractErrorMessage(error, errorMessage));
        return POLL_FAILED;
      }

      await new Promise((resolve) => setTimeout(resolve, PROCESS_POLL_INTERVAL_MS));
    }

    return null;
  }, [refreshProduto]);

  const runGeneration = useCallback(
    async (target, mode) => {
      if (!produto?.id) return;

      const actionKey = `${target}-${mode}`;
      const statusField = target === 'titles' ? 'status_titulo_ia' : 'status_descricao_ia';
      const currentStatus = normalizeProcessStatusValue(produto?.[statusField]);
      if (ACTIVE_PROCESS_STATUSES.has(currentStatus)) {
        return;
      }

      const pollRunId = processPollRunsRef.current[statusField] + 1;
      processPollRunsRef.current[statusField] = pollRunId;
      setPendingAction(actionKey);
      patchProdutoStatus(statusField, 'PENDENTE');
      try {
        if (target === 'titles') {
          if (mode === 'ai') {
            await productService.gerarTitulosProduto(produto.id);
          } else {
            await productService.gerarTitulosProdutoModoBasico(produto.id);
          }
        } else if (mode === 'ai') {
          await productService.gerarDescricaoProduto(produto.id);
        } else {
          await productService.gerarDescricaoProdutoModoBasico(produto.id);
        }
        patchProdutoStatus(statusField, 'EM_PROGRESSO');
        const updated = await pollProdutoUntilTerminal(
          statusField,
          pollRunId,
          target === 'titles'
            ? 'Não foi possível atualizar os títulos gerados.'
            : 'Não foi possível atualizar a descrição gerada.'
        );
        if (updated === POLL_CANCELLED || updated === POLL_FAILED) {
          return;
        }
        if (!updated) {
          showErrorToast(
            target === 'titles'
              ? 'A geração de títulos continua em segundo plano. Atualize o produto em instantes.'
              : 'A geração da descrição continua em segundo plano. Atualize o produto em instantes.'
          );
        }
      } catch (error) {
        patchProdutoStatus(statusField, 'FALHA');
        showErrorToast(extractErrorMessage(
          error,
          target === 'titles' ? 'Erro ao gerar títulos.' : 'Erro ao gerar descrição.',
        ));
      } finally {
        setPendingAction((current) => (current === actionKey ? '' : current));
      }
    },
    [patchProdutoStatus, pollProdutoUntilTerminal, produto?.id, produto?.status_descricao_ia, produto?.status_titulo_ia],
  );

  const runWebEnrichment = useCallback(async () => {
    if (!produto?.id) return;

    const currentStatus = normalizeProcessStatusValue(produto?.status_enriquecimento_web);
    if (ACTIVE_PROCESS_STATUSES.has(currentStatus)) {
      return;
    }

    if (REPROCESS_CONFIRM_STATUSES.has(currentStatus)) {
      const confirmed = window.confirm(
        `A etapa de enriquecimento web para "${produto.nome_base}" ja foi concluida. Deseja executar novamente?`
      );
      if (!confirmed) {
        return;
      }
    }

    setPendingAction('web');
    const pollRunId = processPollRunsRef.current.status_enriquecimento_web + 1;
    processPollRunsRef.current.status_enriquecimento_web = pollRunId;
    patchProdutoStatus('status_enriquecimento_web', 'PENDENTE');
    try {
      await productService.iniciarEnriquecimentoWebProduto(produto.id);
      patchProdutoStatus('status_enriquecimento_web', 'EM_PROGRESSO');
      const updated = await pollProdutoUntilTerminal(
        'status_enriquecimento_web',
        pollRunId,
        'Não foi possível atualizar o enriquecimento web.'
      );
      if (updated === POLL_CANCELLED || updated === POLL_FAILED) {
        return;
      }
      if (!updated) {
        showErrorToast('O enriquecimento web continua em segundo plano. Atualize o produto em instantes.');
        return;
      }

      const finalStatus = normalizeProcessStatusValue(updated.status_enriquecimento_web);
      if (WEB_ENRICHMENT_WARNING_STATUSES.has(finalStatus)) {
        showWarningToast(
          `Enriquecimento web finalizado com pendências (${finalStatus}). Revise os dados coletados.`
        );
      } else {
        showSuccessToast('Enriquecimento web finalizado com sucesso.');
      }
    } catch (error) {
      patchProdutoStatus('status_enriquecimento_web', 'FALHA');
      showErrorToast(extractErrorMessage(error, 'Falha ao iniciar o enriquecimento web.'));
    } finally {
      setPendingAction((current) => (current === 'web' ? '' : current));
    }
  }, [
    patchProdutoStatus,
    produto?.id,
    produto?.nome_base,
    produto?.status_enriquecimento_web,
    pollProdutoUntilTerminal,
  ]);

  const handleFeedback = async (valor) => {
    if (!produto?.id) return;
    setSavingFeedback(true);
    try {
      const updated = await productService.registrarFeedbackConteudoGerado(produto.id, {
        valor,
        comentario: feedbackComment,
      });
      queryClient.setQueryData(queryKeys.produto(produto.id), updated);
      setFeedback(valor);
      showSuccessToast('Feedback salvo com sucesso.');
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao salvar feedback.'));
    } finally {
      setSavingFeedback(false);
    }
  };

  const handleGerarCanal = useCallback(async (canal) => {
    if (!produto?.id) return;
    setChannelLoading((prev) => ({ ...prev, [canal]: true }));
    try {
      await productService.gerarConteudoCanal(produto.id, canal);
      await refreshProduto();
      showSuccessToast('Conteúdo do canal gerado com sucesso.');
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Erro ao gerar conteúdo do canal.'));
    } finally {
      setChannelLoading((prev) => ({ ...prev, [canal]: false }));
    }
  }, [produto?.id, refreshProduto]);

  const hasMainContent = titles.length > 0 || Boolean(description);
  const currentProductId = Number(produto?.id ?? produtoId ?? 0);
  const currentProductIndex = orderedProductIds.findIndex((id) => id === currentProductId);
  const previousProductId = currentProductIndex > 0 ? orderedProductIds[currentProductIndex - 1] : null;
  const nextProductId =
    currentProductIndex >= 0 && currentProductIndex < orderedProductIds.length - 1
      ? orderedProductIds[currentProductIndex + 1]
      : null;

  const navigateToProduct = (targetProductId) => {
    const nextState = {
      productIds: orderedProductIds,
      productQuery: listQueryFromState,
    };
    if (hasExplicitReturnTo) nextState.returnTo = returnTo;
    navigate(`/produtos/${targetProductId}/conteudo`, { state: nextState });
  };

  const handleClose = () => navigate(returnTo);
  const handleEdit = () => {
    if (!produto?.id) return;
    navigate(buildEditTarget(returnTo, produto.id));
  };

  const handleDeleteProduct = useCallback(async () => {
    if (!produto?.id || pendingAction === 'delete') {
      return;
    }

    const confirmed = window.confirm(
      `Tem certeza que deseja ocultar "${produto.nome_base}"?\n\nEle será ocultado da lista, mas continuará salvo no banco de dados.`
    );
    if (!confirmed) {
      return;
    }

    const remainingProductIds = orderedProductIds.filter((id) => id !== currentProductId);
    const nextVisibleProductId = nextProductId ?? previousProductId ?? remainingProductIds[0] ?? null;

    setPendingAction('delete');
    try {
      await productService.deleteProduto(produto.id);
      queryClient.removeQueries({ queryKey: queryKeys.produto(produto.id), exact: true });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['produtos'] }),
        queryClient.invalidateQueries({ queryKey: ['produto-navigation'] }),
      ]);
      showSuccessToast('Produto ocultado com sucesso.');

      if (nextVisibleProductId) {
        const nextState = {
          productIds: remainingProductIds,
          productQuery: listQueryFromState,
        };
        if (hasExplicitReturnTo) {
          nextState.returnTo = returnTo;
        }
        navigate(`/produtos/${nextVisibleProductId}/conteudo`, {
          state: nextState,
          replace: true,
        });
        return;
      }

      navigate(returnTo, { replace: true });
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao ocultar produto.'));
    } finally {
      setPendingAction((current) => (current === 'delete' ? '' : current));
    }
  }, [
    currentProductId,
    hasExplicitReturnTo,
    listQueryFromState,
    navigate,
    nextProductId,
    orderedProductIds,
    pendingAction,
    previousProductId,
    produto?.id,
    produto?.nome_base,
    queryClient,
    returnTo,
  ]);

  const supplierName = normalizeText(produto?.fornecedor?.nome || produto?.fornecedor_nome);
  const productTypeName = normalizeText(
    produto?.product_type?.friendly_name || produto?.tipo_produto?.friendly_name || produto?.product_type_name,
  );
  const contextParts = [
    normalizeText(produto?.marca) ? `Marca: ${produto.marca}` : '',
    normalizeText(produto?.sku) ? `SKU: ${produto.sku}` : '',
    supplierName ? `Fornecedor: ${supplierName}` : '',
    productTypeName ? `Tipo: ${productTypeName}` : '',
  ].filter(Boolean);
  const webEnrichmentRunning = ACTIVE_PROCESS_STATUSES.has(
    normalizeProcessStatusValue(produto?.status_enriquecimento_web)
  );
  const titleGenerationRunning = ACTIVE_PROCESS_STATUSES.has(
    normalizeProcessStatusValue(produto?.status_titulo_ia)
  );
  const descriptionGenerationRunning = ACTIVE_PROCESS_STATUSES.has(
    normalizeProcessStatusValue(produto?.status_descricao_ia)
  );

  return (
    <div className="app-page-shell produto-conteudo-shell">
      <header className="produto-conteudo-topbar">
        <div className="produto-conteudo-heading-group">
          <h1 className="produto-conteudo-title">{normalizeText(produto?.nome_base) || 'Produto sem nome'}</h1>
          <p className="app-muted-note produto-conteudo-context">
            {contextParts.length > 0 ? contextParts.join(' • ') : `Produto #${produto?.id || produtoId}`}
          </p>
        </div>
        <button
          type="button"
          className="produto-conteudo-close-button"
          aria-label="Fechar conteúdo do produto"
          title="Fechar"
          onClick={handleClose}
        >
          <LuX className="produto-conteudo-close-icon" aria-hidden="true" />
        </button>
      </header>

      <div className="produto-conteudo-floating-nav" aria-label="Navegação entre produtos">
        <button
          type="button"
          className="produto-conteudo-floating-btn left"
          disabled={!previousProductId}
          aria-label="Produto anterior"
          onClick={() => navigateToProduct(previousProductId)}
        >
          <LuChevronLeft className="produto-conteudo-nav-icon" aria-hidden="true" />
        </button>
        <button
          type="button"
          className="produto-conteudo-floating-btn right"
          disabled={!nextProductId}
          aria-label="Próximo produto"
          onClick={() => navigateToProduct(nextProductId)}
        >
          <LuChevronRight className="produto-conteudo-nav-icon" aria-hidden="true" />
        </button>
      </div>

      <section className="app-toolbar-card produto-conteudo-overview-card">
        <div className="produto-conteudo-overview-layout">
          <div className="produto-conteudo-overview-media">
            {normalizeText(produto?.imagem_principal_url) ? (
              <img src={produto.imagem_principal_url} alt={normalizeText(produto?.nome_base) || 'Produto'} />
            ) : (
              <div className="produto-conteudo-media-placeholder">
                <LuImage aria-hidden="true" />
              </div>
            )}
          </div>

          <div className="produto-conteudo-overview-content">
            <div className="produto-conteudo-overview-copy">
              <div className="produto-conteudo-general-grid">
                {generalInfoItems.length > 0 ? (
                  generalInfoItems.map((item) => {
                    const ItemIcon = item.icon;
                    return (
                      <article key={item.label} className="produto-conteudo-general-item">
                        <span className="produto-conteudo-general-item-label">
                          <ItemIcon aria-hidden="true" />
                          {item.label}
                        </span>
                        <strong>{item.value}</strong>
                      </article>
                    );
                  })
                ) : (
                  <article className="produto-conteudo-general-item produto-conteudo-general-item--empty">
                    <span className="produto-conteudo-general-item-label">
                      <LuBox aria-hidden="true" />
                      Produto
                    </span>
                    <strong>Sem informações complementares.</strong>
                  </article>
                )}
              </div>
            </div>

            <div className="produto-conteudo-overview-footer">
              <div className="produto-conteudo-status-grid">
                {PROCESS_STATUS_CONFIG.map((processInfo) => (
                  <ProcessStatusCard key={processInfo.key} produto={produto} processInfo={processInfo} />
                ))}
              </div>

              {(() => {
                const cqs = calculateContentQualityScore(produto);
                const { label, tier } = getContentQualityTier(cqs);
                const breakdown = getContentQualityBreakdown(produto);
                return (
                  <div className="pcc-quality-bar-wrap">
                    <div className="pcc-quality-bar-header">
                      <span className="pcc-quality-bar-label">Qualidade do conteúdo</span>
                      <span className={`pcc-quality-bar-score pcc-quality-bar-score--${tier}`}>
                        {cqs}/100 — {label}
                      </span>
                    </div>
                    <div className="pcc-quality-bar-track" title={`${cqs}% completo`}>
                      <div className={`pcc-quality-bar-fill pcc-quality-bar-fill--${tier}`} style={{ width: `${cqs}%` }} />
                    </div>
                    <div className="pcc-quality-breakdown">
                      {breakdown.map((item) => (
                        <span
                          key={item.label}
                          className={`pcc-quality-item ${item.done ? 'pcc-quality-item--done' : 'pcc-quality-item--missing'}`}
                          title={item.done ? `${item.label}: +${item.points} pts` : `${item.label}: faltando (${item.points} pts)`}>
                          {item.label}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })()}

              <div className="produto-conteudo-actions-row">
                {/* Left: action shortcuts */}
                <div className="produto-conteudo-shortcuts" aria-label="Atalhos de geração">
                  <button
                    type="button"
                    className="produto-conteudo-shortcut-btn"
                    aria-label="Executar enriquecimento web"
                    title="Executar enriquecimento web"
                    disabled={!produto?.id || pendingAction === 'web' || webEnrichmentRunning}
                    onClick={runWebEnrichment}
                  >
                    <span className="produto-conteudo-shortcut-indicator blue">
                      <LuGlobe aria-hidden="true" />
                    </span>
                  </button>
                  <button
                    type="button"
                    className="produto-conteudo-shortcut-btn"
                    aria-label="Gerar títulos no básico"
                    title="Gerar títulos no básico"
                    disabled={!produto?.id || pendingAction === 'titles-basic' || titleGenerationRunning}
                    onClick={() => runGeneration('titles', 'basic')}
                  >
                    <span className="produto-conteudo-shortcut-indicator grey">
                      <LuType aria-hidden="true" />
                    </span>
                  </button>
                  {showAiFeatures ? (
                    <button
                      type="button"
                      className="produto-conteudo-shortcut-btn produto-conteudo-shortcut-btn--ai"
                      aria-label="Gerar títulos com IA"
                      title="Gerar títulos com IA"
                      disabled={!produto?.id || pendingAction === 'titles-ai' || titleGenerationRunning}
                      onClick={() => runGeneration('titles', 'ai')}
                    >
                      <span className="produto-conteudo-shortcut-indicator blue is-ai">
                        <LuType aria-hidden="true" />
                        <span className="produto-conteudo-shortcut-badge">
                          <LuSparkles aria-hidden="true" />
                        </span>
                      </span>
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="produto-conteudo-shortcut-btn"
                    aria-label="Gerar descrição no básico"
                    title="Gerar descrição no básico"
                    disabled={!produto?.id || pendingAction === 'description-basic' || descriptionGenerationRunning}
                    onClick={() => runGeneration('description', 'basic')}
                  >
                    <span className="produto-conteudo-shortcut-indicator green">
                      <LuFileText aria-hidden="true" />
                    </span>
                  </button>
                  {showAiFeatures ? (
                    <button
                      type="button"
                      className="produto-conteudo-shortcut-btn produto-conteudo-shortcut-btn--ai"
                      aria-label="Gerar descrição com IA"
                      title="Gerar descrição com IA"
                      disabled={!produto?.id || pendingAction === 'description-ai' || descriptionGenerationRunning}
                      onClick={() => runGeneration('description', 'ai')}
                    >
                      <span className="produto-conteudo-shortcut-indicator green is-ai">
                        <LuFileText aria-hidden="true" />
                        <span className="produto-conteudo-shortcut-badge">
                          <LuSparkles aria-hidden="true" />
                        </span>
                      </span>
                    </button>
                  ) : null}
                </div>

                {/* Right: edit + delete, each in its own pill */}
                <div className="produto-conteudo-shortcuts-right">
                  <div className="produto-conteudo-shortcuts">
                    <button
                      type="button"
                      className="produto-conteudo-shortcut-btn"
                      aria-label="Abrir edição"
                      title="Abrir edição"
                      disabled={!produto?.id}
                      onClick={handleEdit}
                    >
                      <span className="produto-conteudo-shortcut-indicator slate">
                        <LuPencil aria-hidden="true" />
                      </span>
                    </button>
                  </div>
                  <div className="produto-conteudo-shortcuts">
                    <button
                      type="button"
                      className="produto-conteudo-shortcut-btn"
                      aria-label="Ocultar produto"
                      title="Ocultar produto"
                      disabled={!produto?.id || pendingAction === 'delete'}
                      onClick={handleDeleteProduct}
                    >
                      <span className="produto-conteudo-shortcut-indicator red">
                        <LuTrash2 aria-hidden="true" />
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="app-toolbar-card produto-conteudo-main-card">
        <ProductContentWorkspace
          titles={titles}
          description={description}
          titleHeading="5 títulos sugeridos"
          descriptionHeading="Descrição principal"
          emptyTitleMessage="Título ainda não gerado para esta posição."
          emptyDescriptionMessage="Descrição ainda não gerada."
        />
      </section>

      {showAiFeatures && (
        <section className="app-toolbar-card pcc-canais-card">
          <div className="produto-conteudo-section-header">
            <div>
              <h2>Canais de publicação</h2>
              <p className="app-muted-note">
                Conteúdo adaptado para cada plataforma de venda.
              </p>
            </div>
          </div>
          <div className="pcc-canais-grid">
            {CANAIS_CONFIG.map((canal) => {
              const canalData = produto?.conteudo_canais?.[canal.id] || {};
              const isLoading = channelLoading[canal.id];
              return (
                <article key={canal.id} className="pcc-canal-card">
                  <div className="pcc-canal-card-header">
                    <span className="pcc-canal-label">{canal.label}</span>
                    <button
                      type="button"
                      className="btn-secondary btn-sm pcc-canal-gerar-btn"
                      disabled={!produto?.id || isLoading}
                      onClick={() => handleGerarCanal(canal.id)}
                    >
                      {isLoading
                        ? <LuLoaderCircle className="pcc-canal-spin" aria-hidden="true" />
                        : <LuSparkles aria-hidden="true" />
                      }
                      Gerar
                    </button>
                  </div>
                  <div className="pcc-canal-field">
                    <span className="pcc-canal-field-label">Título</span>
                    {canalData.titulo ? (
                      <div className="pcc-canal-field-value-row">
                        <p className="pcc-canal-field-text">{canalData.titulo}</p>
                        <button
                          type="button"
                          className="pcc-canal-copy-btn"
                          aria-label="Copiar título"
                          title="Copiar título"
                          onClick={() => {
                            navigator.clipboard.writeText(canalData.titulo);
                            showSuccessToast('Título copiado!');
                          }}
                        >
                          <LuCopy aria-hidden="true" />
                        </button>
                      </div>
                    ) : (
                      <p className="pcc-canal-empty">Não gerado ainda.</p>
                    )}
                  </div>
                  <div className="pcc-canal-field">
                    <span className="pcc-canal-field-label">Descrição</span>
                    {canalData.descricao ? (
                      <div className="pcc-canal-field-value-row">
                        <p className="pcc-canal-field-text">{canalData.descricao}</p>
                        <button
                          type="button"
                          className="pcc-canal-copy-btn"
                          aria-label="Copiar descrição"
                          title="Copiar descrição"
                          onClick={() => {
                            navigator.clipboard.writeText(canalData.descricao);
                            showSuccessToast('Descrição copiada!');
                          }}
                        >
                          <LuCopy aria-hidden="true" />
                        </button>
                      </div>
                    ) : (
                      <p className="pcc-canal-empty">Não gerada ainda.</p>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      <section className="app-toolbar-card produto-conteudo-collected-card">
        <div className="produto-conteudo-section-header">
          <div>
            <h2>Informações coletadas</h2>
            <p className="app-muted-note">
              Dados relevantes para identificar e revisar o produto antes de publicar o conteúdo.
            </p>
          </div>
        </div>

        {collectedInfoEntries.length > 0 ? (
          <div className="produto-conteudo-collected-grid">
            {collectedInfoEntries.map((entry) => (
              <article key={`${entry.label}-${entry.value}`} className="produto-conteudo-collected-item">
                <span>{entry.label}</span>
                <strong>{entry.value}</strong>
              </article>
            ))}
          </div>
        ) : (
          <div className="produto-conteudo-empty-card">
            <p>Nenhuma informação adicional coletada para este produto.</p>
          </div>
        )}
      </section>

      <section className="app-toolbar-card produto-conteudo-feedback-card">
        <div className="produto-conteudo-section-header">
          <div>
            <h2>Feedback rápido</h2>
            <p className="app-muted-note">
              Marque se o material já está bom ou se ainda precisa de ajuste.
            </p>
          </div>
        </div>
        <div className="produto-conteudo-feedback-actions">
          <button
            type="button"
            className={`btn-secondary btn-sm ${feedback === 'gostei' ? 'is-selected' : ''}`}
            disabled={savingFeedback || !hasMainContent}
            onClick={() => handleFeedback('gostei')}
          >
            Gostei
          </button>
          <button
            type="button"
            className={`btn-danger btn-sm ${feedback === 'nao_gostei' ? 'is-selected' : ''}`}
            disabled={savingFeedback || !hasMainContent}
            onClick={() => handleFeedback('nao_gostei')}
          >
            Não gostei
          </button>
        </div>
        <label className="produto-conteudo-feedback-comment">
          Comentário (opcional)
          <textarea
            value={feedbackComment}
            onChange={(event) => setFeedbackComment(event.target.value)}
            placeholder="Ex.: títulos bons, mas a descrição ainda está curta."
            rows={3}
            disabled={savingFeedback}
          />
        </label>
      </section>

      <LoadingOverlay isOpen={produtoQuery.isLoading} message="Carregando conteúdo do produto..." />
    </div>
  );
}

export default ProdutoConteudoPage;


