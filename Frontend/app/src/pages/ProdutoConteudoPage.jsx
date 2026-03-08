/**
 * Module produto conteudo page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import productService from '../services/productService';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import { queryKeys } from '../lib/queryKeys.js';
import './ProdutoConteudoPage.css';

function normalizeText(value) {
  return String(value || '').trim();
}

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

function hasCompanyTimelineClaim(text) {
  const normalized = normalizeText(text).toLowerCase();
  if (COMPANY_TIMELINE_HINTS.some((hint) => normalized.includes(hint))) return true;
  return /(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|iniciou\s+suas?\s+atividades)/i.test(
    normalized,
  );
}

function sanitizeCompanyTimelineText(text) {
  const normalized = normalizeText(text);
  const chunks = normalized.split(/(?<=[.!?])\s+|\n+/);
  const filtered = chunks
    .map((chunk) => normalizeText(chunk))
    .filter((chunk) => chunk && !hasCompanyTimelineClaim(chunk));
  if (filtered.length > 0) {
    return filtered.join(' ');
  }
  return normalized;
}

function extractGeneratedTitles(produto) {
  const directTitles = Array.isArray(produto?.titulos_sugeridos) ? produto.titulos_sugeridos : [];
  const rawTitles = Array.isArray(produto?.dados_brutos_web?.titulos_sugeridos_gerados)
    ? produto.dados_brutos_web.titulos_sugeridos_gerados
    : [];
  const merged = [...directTitles, ...rawTitles]
    .map((item) => normalizeText(item))
    .filter(Boolean);
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
    return {
      sort_by: 'id',
      sort_order: 'asc',
    };
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
  if (!sanitized.sort_by) {
    sanitized.sort_by = 'id';
  }
  if (!sanitized.sort_order) {
    sanitized.sort_order = 'asc';
  }
  return sanitized;
}

async function fetchOrderedProductIds(queryParams) {
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

    if (items.length === 0) {
      break;
    }

    skip += items.length;
    const totalItems = Number(response?.total_items);
    if (Number.isFinite(totalItems) && totalItems >= 0 && skip >= totalItems) {
      break;
    }
    if (items.length < pageLimit) {
      break;
    }
  }

  return Array.from(new Set(allIds));
}

function ProdutoConteudoPage() {
  const { produtoId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [savingFeedback, setSavingFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [feedbackComment, setFeedbackComment] = useState('');

  const idsFromState = useMemo(() => extractOrderedProductIdsFromState(location.state), [location.state]);
  const listQueryFromState = useMemo(() => extractListQueryFromState(location.state), [location.state]);

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
      showErrorToast(produtoQuery.error?.message || 'Falha ao carregar conteudo do produto.');
    }
  }, [produtoQuery.error]);

  const produto = produtoQuery.data;
  const titles = useMemo(() => extractGeneratedTitles(produto), [produto]);
  const description = useMemo(() => extractMainDescription(produto), [produto]);

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
      if (!merged.includes(id)) {
        merged.push(id);
      }
    });
    const productIdFromData = Number(produto?.id);
    if (Number.isInteger(productIdFromData) && productIdFromData > 0 && !merged.includes(productIdFromData)) {
      merged.push(productIdFromData);
    }
    return merged;
  }, [idsFromState, orderedIdsQuery.data, produto?.id]);

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
      showErrorToast(error?.message || 'Falha ao salvar feedback.');
    } finally {
      setSavingFeedback(false);
    }
  };

  const hasMainContent = titles.length > 0 || Boolean(description);
  const currentProductId = Number(produto?.id ?? produtoId ?? 0);
  const currentProductIndex = orderedProductIds.findIndex((id) => id === currentProductId);
  const previousProductId = currentProductIndex > 0 ? orderedProductIds[currentProductIndex - 1] : null;
  const nextProductId =
    currentProductIndex >= 0 && currentProductIndex < orderedProductIds.length - 1
      ? orderedProductIds[currentProductIndex + 1]
      : null;

  const navigateToProduct = (targetProductId) => {
    navigate(`/produtos/${targetProductId}/conteudo`, {
      state: {
        productIds: orderedProductIds,
        productQuery: listQueryFromState,
      },
    });
  };

  return (
    <div className="app-page-shell produto-conteudo-shell">
      <div className="app-page-header produto-conteudo-header">
        <div>
          <h2 className="app-page-heading">Conteudo Gerado do Produto</h2>
          <p className="app-muted-note">
            Produto #{produto?.id || produtoId} - {produto?.nome_base || 'Sem nome'}
          </p>
        </div>
        <div className="produto-conteudo-header-actions">
          <button type="button" className="btn-secondary" onClick={() => navigate('/produtos')}>
            Voltar para Produtos
          </button>
          {produto?.id ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => navigate(`/produtos?id=${produto.id}`)}
            >
              Abrir Edicao
            </button>
          ) : null}
        </div>
      </div>

      <div className="app-toolbar-card produto-conteudo-nav-strip">
        <button
          type="button"
          className="btn-secondary produto-conteudo-nav-btn left"
          disabled={!previousProductId}
          onClick={() => navigateToProduct(previousProductId)}
        >
          Produto Anterior
        </button>
        <button
          type="button"
          className="btn-secondary produto-conteudo-nav-btn right"
          disabled={!nextProductId}
          onClick={() => navigateToProduct(nextProductId)}
        >
          Proximo Produto
        </button>
      </div>

      <div className="app-toolbar-card produto-conteudo-grid">
        <div className="produto-conteudo-left-column">
          <section className="produto-conteudo-block produto-conteudo-titles-block">
            <h3>5 Titulos Sugeridos</h3>
            <div className="produto-conteudo-title-list">
              {Array.from({ length: 5 }).map((_, index) => {
                const title = titles[index] || '';
                return (
                  <article key={`title-${index}`} className="produto-conteudo-title-card">
                    <span className="produto-conteudo-title-index">{index + 1}</span>
                    <p>{title || 'Titulo ainda nao gerado para esta posicao.'}</p>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="produto-conteudo-block produto-conteudo-feedback-card">
            <h3>Feedback Rapido</h3>
            <p className="app-muted-note">
              Marque se o resultado esta bom. Isso fica salvo para analise de qualidade.
            </p>
            <div className="produto-conteudo-feedback-actions">
              <button
                type="button"
                className={`btn-secondary ${feedback === 'gostei' ? 'is-selected' : ''}`}
                disabled={savingFeedback || !hasMainContent}
                onClick={() => handleFeedback('gostei')}
              >
                Gostei
              </button>
              <button
                type="button"
                className={`btn-danger ${feedback === 'nao_gostei' ? 'is-selected' : ''}`}
                disabled={savingFeedback || !hasMainContent}
                onClick={() => handleFeedback('nao_gostei')}
              >
                Nao Gostei
              </button>
            </div>
            <label className="produto-conteudo-feedback-comment">
              Comentario (opcional):
              <textarea
                value={feedbackComment}
                onChange={(event) => setFeedbackComment(event.target.value)}
                placeholder="Ex: titulos bons, mas descricao muito curta."
                rows={3}
                disabled={savingFeedback}
              />
            </label>
          </section>
        </div>

        <section className="produto-conteudo-block produto-conteudo-description-block">
          <h3>Descricao Completa</h3>
          <div className="produto-conteudo-description">
            {description || 'Descricao ainda nao gerada.'}
          </div>
        </section>
      </div>

      <LoadingOverlay isOpen={produtoQuery.isLoading} message="Carregando conteudo do produto..." />
    </div>
  );
}

export default ProdutoConteudoPage;
