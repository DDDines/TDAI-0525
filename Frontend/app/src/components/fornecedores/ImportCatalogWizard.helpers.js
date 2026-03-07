/**
 * Pure helpers kept out of the component to keep the wizard testable.
 */

import { normalizeDisplayText } from '../../utils/textNormalization';

export function cloneFornecedorMapping(value) {
  if (!value || typeof value !== 'object') return {};
  return { ...value };
}

export function buildWizardResetKey(fornecedorId, initialProductTypeId) {
  const fornecedorKey =
    fornecedorId === null || fornecedorId === undefined || fornecedorId === ''
      ? 'none'
      : String(fornecedorId);
  const productTypeKey =
    initialProductTypeId === null ||
    initialProductTypeId === undefined ||
    initialProductTypeId === ''
      ? 'none'
      : String(initialProductTypeId);
  return `${fornecedorKey}::${productTypeKey}`;
}

export function extractProductTypesCollection(data) {
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data)) return data;
  return [];
}

export function extractProductTypeAttributes(details) {
  if (Array.isArray(details?.attribute_templates)) return details.attribute_templates;
  if (Array.isArray(details?.attributeTemplates)) return details.attributeTemplates;
  return [];
}

export function resolveManualMappingPreview({
  regionPreview,
  previewData,
  manualMappingRows,
  fallbackHeaders,
}) {
  let headers = fallbackHeaders;
  if (Array.isArray(regionPreview?.headers) && regionPreview.headers.length > 0) {
    headers = regionPreview.headers;
  } else if (Array.isArray(previewData?.headers) && previewData.headers.length > 0) {
    headers = previewData.headers;
  }

  let rows = [];
  if (Array.isArray(regionPreview?.rows)) {
    rows = regionPreview.rows;
  } else if (Array.isArray(previewData?.sampleRows)) {
    rows = previewData.sampleRows;
  } else if (Array.isArray(manualMappingRows)) {
    rows = manualMappingRows;
  }

  return { headers, rows };
}

export function buildWizardViewModel({
  resultData,
  statusData,
  expectedPages,
  step,
  error,
  processingStartedAt,
  isLoading,
  loadingMessage,
  applyAllPages,
  selectedPageForRegion,
  startPage,
  fileId,
  mapping,
  productTypeId,
  selectedFile,
}) {
  const stats = resultData?.stats && typeof resultData.stats === 'object' ? resultData.stats : {};
  const resultErrors = Array.isArray(resultData?.errors) ? resultData.errors : [];
  const createdItems = Array.isArray(resultData?.created) ? resultData.created : [];
  const updatedItems = Array.isArray(resultData?.updated) ? resultData.updated : [];

  const criticalErrorsCount =
    typeof stats.erros === 'number' ? stats.erros : resultErrors.length;

  const partialSuccessByFlag = Boolean(stats.partial_success);
  const createdCount =
    typeof stats.produtos_criados === 'number' ? stats.produtos_criados : createdItems.length;
  const updatedCount =
    typeof stats.produtos_atualizados === 'number'
      ? stats.produtos_atualizados
      : updatedItems.length;
  const importedCount = createdCount + updatedCount;
  const hasPartialSuccess =
    partialSuccessByFlag || (importedCount > 0 && criticalErrorsCount > 0);

  const pagesProcessed =
    typeof statusData?.pages_processed === 'number'
      ? statusData.pages_processed
      : typeof stats.pages_processed === 'number'
        ? stats.pages_processed
        : 0;

  let pagesTotal = 0;
  if (typeof statusData?.total_pages === 'number') {
    pagesTotal = statusData.total_pages;
  } else if (typeof statusData?.pages_total === 'number') {
    pagesTotal = statusData.pages_total;
  } else if (typeof stats.pages_total === 'number') {
    pagesTotal = stats.pages_total;
  } else if (typeof expectedPages === 'number') {
    pagesTotal = expectedPages;
  }

  const progressPct =
    pagesTotal > 0 ? Math.min(100, Math.round((pagesProcessed / pagesTotal) * 100)) : 0;

  const statusNormalized = normalizeDisplayText(String(statusData?.status || '')).toUpperCase();
  const isTerminalStatus = ['IMPORTED', 'DONE', 'FAILED', 'PARTIAL'].includes(statusNormalized);
  const processingActive = !statusData || !isTerminalStatus;
  const waitingFinalResult =
    step === 'processing' && isTerminalStatus && !resultData && !error;

  const elapsedSec = processingStartedAt
    ? Math.max(0, Math.floor((Date.now() - processingStartedAt) / 1000))
    : 0;
  const etaSec =
    pagesProcessed > 0 && pagesTotal > pagesProcessed
      ? Math.max(0, Math.round((elapsedSec / pagesProcessed) * (pagesTotal - pagesProcessed)))
      : 0;

  const showLoadingPopup =
    isLoading || (step === 'processing' && !error && (processingActive || waitingFinalResult));

  let loadingPopupMessage = loadingMessage || 'Processando...';
  if (step === 'processing' && processingActive) {
    loadingPopupMessage = 'Processando importação do catálogo...';
  } else if (step === 'processing' && waitingFinalResult) {
    loadingPopupMessage = 'Aguardando consolidação do resultado final...';
  }

  const selectedScopeLabel = applyAllPages
    ? 'todas as páginas do PDF'
    : `somente página ${selectedPageForRegion || startPage}`;

  const canStartImport = Boolean(fileId && productTypeId) && !isLoading;
  const mappingValues = Object.values(mapping || {});
  const hasPrimaryMapping = mappingValues.some((destination) =>
    ['auto:sku_nome', 'nome_base', 'sku_original'].includes(destination)
  );

  const discardedNonCritical =
    typeof stats.descartes_nao_criticos === 'number' ? stats.descartes_nao_criticos : 0;
  const quarantineCount =
    typeof stats.quarentena_nao_critica === 'number'
      ? stats.quarentena_nao_critica
      : Array.isArray(resultData?.quarantine_non_critical)
        ? resultData.quarantine_non_critical.length
        : 0;

  const acceptedQualityAvg = stats.qualidade_score_medio_aceitas;
  const quarantineQualityAvg = stats.qualidade_score_medio_quarentena;
  const resultOutput =
    resultData?.output && typeof resultData.output === 'object' ? resultData.output : {};
  const resultOutputHeadline = normalizeDisplayText(resultOutput.headline || '');
  const resultOutputLabel = normalizeDisplayText(resultOutput.status_label || '');
  const resultOutputPages =
    resultOutput.pages && typeof resultOutput.pages === 'object' ? resultOutput.pages : {};
  const resultTopReasons = Array.isArray(resultData?.top_reasons)
    ? resultData.top_reasons.slice(0, 5)
    : [];
  const formatExt =
    typeof stats.ext === 'string' && stats.ext.trim()
      ? stats.ext
      : selectedFile?.name?.split('.').pop()?.toLowerCase() || '-';

  return {
    criticalErrorsCount,
    hasPartialSuccess,
    pagesProcessed,
    pagesTotal,
    progressPct,
    statusNormalized,
    isTerminalStatus,
    processingActive,
    waitingFinalResult,
    elapsedSec,
    etaSec,
    showLoadingPopup,
    loadingPopupMessage,
    selectedScopeLabel,
    canStartImport,
    hasPrimaryMapping,
    canStartWithMapping: canStartImport && hasPrimaryMapping,
    discardedNonCritical,
    quarantineCount,
    acceptedQualityAvg,
    quarantineQualityAvg,
    resultOutput,
    resultOutputHeadline,
    resultOutputLabel,
    resultOutputPages,
    resultTopReasons,
    formatExt,
  };
}

export function formatCellValue(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function getPreviewImageSrc(img) {
  if (typeof img === 'string') {
    if (!img.trim()) return null;
    return img.startsWith('data:image') ? img : `data:image/png;base64,${img}`;
  }
  if (img && typeof img === 'object' && img.image) return img.image;
  return null;
}

export function formatElapsed(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0s';
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

export function normalizePayloadStrings(payload) {
  if (Array.isArray(payload)) return payload.map((item) => normalizePayloadStrings(item));
  if (payload && typeof payload === 'object') {
    return Object.fromEntries(
      Object.entries(payload).map(([k, v]) => [k, normalizePayloadStrings(v)])
    );
  }
  if (typeof payload === 'string') return normalizeDisplayText(payload);
  return payload;
}

export function appendUniqueTimelineEntry(previousEntries, message, timestampLabel) {
  const safeMessage = normalizeDisplayText(message);
  const dedupeKey = safeMessage
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();

  if (!dedupeKey) {
    return {
      appended: false,
      dedupeKey: '',
      entries: previousEntries,
    };
  }

  const recentKeys = previousEntries
    .slice(-6)
    .map((entry) =>
      String(entry || '')
        .replace(/^\[[^\]]+\]\s*/, '')
        .replace(/[\u200B-\u200D\uFEFF]/g, '')
        .replace(/\s+/g, ' ')
        .trim()
        .toLowerCase()
    );

  if (recentKeys.includes(dedupeKey)) {
    return {
      appended: false,
      dedupeKey,
      entries: previousEntries,
    };
  }

  return {
    appended: true,
    dedupeKey,
    entries: [...previousEntries, `[${timestampLabel}] ${safeMessage}`].slice(-160),
  };
}
