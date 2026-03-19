/**
 * Content Quality Score utility.
 *
 * Calculates a 0–100 score reflecting how complete a product's AI-generated
 * content is. Distinct from import_quality_score (which measures raw data quality).
 *
 * Breakdown (100 pts total):
 *   35 — AI title generated (nome_chat_api)
 *   35 — AI description generated (descricao_chat_api)
 *   15 — Web enrichment completed
 *    5 — SKU present
 *    5 — Image present
 *    5 — Brand or model present
 */

const TERMINAL_ENRICHMENT = new Set([
  'CONCLUIDO_SUCESSO',
  'CONCLUIDO_COM_DADOS_PARCIAIS',
]);

function normalizeStatus(raw) {
  if (!raw) return '';
  const s = typeof raw === 'object' && raw !== null && 'value' in raw ? raw.value : raw;
  return String(s).split('.').pop().toUpperCase();
}

/**
 * Returns a score 0–100.
 * @param {object} produto - product object from the API
 */
export function calculateContentQualityScore(produto) {
  if (!produto) return 0;
  let score = 0;

  if (produto.nome_chat_api && String(produto.nome_chat_api).trim()) score += 35;
  if (produto.descricao_chat_api && String(produto.descricao_chat_api).trim()) score += 35;
  if (TERMINAL_ENRICHMENT.has(normalizeStatus(produto.status_enriquecimento_web))) score += 15;
  if (produto.sku && String(produto.sku).trim()) score += 5;
  if (produto.imagem_principal_url && String(produto.imagem_principal_url).trim()) score += 5;
  if (
    (produto.marca && String(produto.marca).trim()) ||
    (produto.modelo && String(produto.modelo).trim())
  ) score += 5;

  return score;
}

/**
 * Returns the breakdown of which components are complete.
 * @param {object} produto
 */
export function getContentQualityBreakdown(produto) {
  if (!produto) return [];
  return [
    {
      label: 'Título IA',
      points: 35,
      earned: produto.nome_chat_api && String(produto.nome_chat_api).trim() ? 35 : 0,
      done: !!(produto.nome_chat_api && String(produto.nome_chat_api).trim()),
    },
    {
      label: 'Descrição IA',
      points: 35,
      earned: produto.descricao_chat_api && String(produto.descricao_chat_api).trim() ? 35 : 0,
      done: !!(produto.descricao_chat_api && String(produto.descricao_chat_api).trim()),
    },
    {
      label: 'Enriquecimento web',
      points: 15,
      earned: TERMINAL_ENRICHMENT.has(normalizeStatus(produto.status_enriquecimento_web)) ? 15 : 0,
      done: TERMINAL_ENRICHMENT.has(normalizeStatus(produto.status_enriquecimento_web)),
    },
    {
      label: 'SKU',
      points: 5,
      earned: produto.sku && String(produto.sku).trim() ? 5 : 0,
      done: !!(produto.sku && String(produto.sku).trim()),
    },
    {
      label: 'Imagem',
      points: 5,
      earned: produto.imagem_principal_url && String(produto.imagem_principal_url).trim() ? 5 : 0,
      done: !!(produto.imagem_principal_url && String(produto.imagem_principal_url).trim()),
    },
    {
      label: 'Marca/Modelo',
      points: 5,
      earned:
        (produto.marca && String(produto.marca).trim()) ||
        (produto.modelo && String(produto.modelo).trim())
          ? 5
          : 0,
      done: !!(
        (produto.marca && String(produto.marca).trim()) ||
        (produto.modelo && String(produto.modelo).trim())
      ),
    },
  ];
}

/**
 * Returns label and color tier for a given score.
 */
export function getContentQualityTier(score) {
  if (score >= 85) return { label: 'Completo', tier: 'complete' };
  if (score >= 60) return { label: 'Bom', tier: 'good' };
  if (score >= 35) return { label: 'Parcial', tier: 'partial' };
  return { label: 'Básico', tier: 'basic' };
}
