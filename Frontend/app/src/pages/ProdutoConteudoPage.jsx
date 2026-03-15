/**
 * Module produto conteudo page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import ProductContentWorkspace from '../components/produtos/ProductContentWorkspace.jsx';
import { useAppExperience } from '../contexts/AppExperienceContext.jsx';
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
  if (sanitized) {
    return sanitized;
  }
  return normalized;
}

function extractGeneratedTitles(produto) {
  const directTitles = Array.isArray(produto?.titulos_sugeridos) ? produto.titulos_sugeridos : [];
  const rawTitles = Array.isArray(produto?.dados_brutos_web?.titulos_sugeridos_gerados)
    ? produto.dados_brutos_web.titulos_sugeridos_gerados
    : [];
  const primarySource = directTitles.filter((item) => normalizeText(item)).length > 0
    ? directTitles
    : rawTitles;
  const merged = primarySource
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
  const { effectiveMode } = useAppExperience();
  const [savingFeedback, setSavingFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [feedbackComment, setFeedbackComment] = useState('');
  const [usarIA, setUsarIA] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const refreshTimeoutRef = useRef(null);
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
      showErrorToast(produtoQuery.error?.message || 'Falha ao carregar conteudo do produto.');
    }
  }, [produtoQuery.error]);

  useEffect(
    () => () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
        refreshTimeoutRef.current = null;
      }
    },
    []
  );

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

  const refreshProduto = useCallback(async () => {
    if (!produto?.id) {
      return null;
    }
    const updated = await productService.getProdutoById(produto.id);
    queryClient.setQueryData(queryKeys.produto(produto.id), updated);
    return updated;
  }, [produto?.id, queryClient]);

  const scheduleProdutoRefresh = useCallback(() => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }
    refreshTimeoutRef.current = setTimeout(() => {
      void (async () => {
        try {
          const refreshed = await refreshProduto();
          void refreshed;
        } catch (error) {
          showErrorToast(error?.message || 'Nao foi possivel atualizar o conteudo gerado.');
        } finally {
          refreshTimeoutRef.current = null;
        }
      })();
    }, 7000);
  }, [refreshProduto]);

  const handleGenerateTitles = useCallback(async () => {
    if (!produto?.id) {
      return;
    }
    setIsGenerating(true);
    try {
      if (showAiFeatures && usarIA) {
        await productService.gerarTitulosProduto(produto.id);
      } else {
        await productService.gerarTitulosProdutoModoBasico(produto.id);
      }
      scheduleProdutoRefresh();
    } catch (error) {
      showErrorToast(error?.message || 'Erro ao gerar titulos.');
    } finally {
      setIsGenerating(false);
    }
  }, [produto?.id, scheduleProdutoRefresh, showAiFeatures, usarIA]);

  const handleGenerateDescription = useCallback(async () => {
    if (!produto?.id) {
      return;
    }
    setIsGenerating(true);
    try {
      if (showAiFeatures && usarIA) {
        await productService.gerarDescricaoProduto(produto.id);
      } else {
        await productService.gerarDescricaoProdutoModoBasico(produto.id);
      }
      scheduleProdutoRefresh();
    } catch (error) {
      showErrorToast(error?.message || 'Erro ao gerar descricao.');
    } finally {
      setIsGenerating(false);
    }
  }, [produto?.id, scheduleProdutoRefresh, showAiFeatures, usarIA]);

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
    if (hasExplicitReturnTo) {
      nextState.returnTo = returnTo;
    }
    navigate(`/produtos/${targetProductId}/conteudo`, {
      state: nextState,
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
          <button type="button" className="btn-secondary" onClick={() => navigate(returnTo)}>
            Voltar para Produtos
          </button>
          {produto?.id ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => navigate(buildEditTarget(returnTo, produto.id))}
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

      <div className="app-toolbar-card produto-conteudo-main-card">
        <ProductContentWorkspace
          titles={titles}
          description={description}
          onGenerateTitles={handleGenerateTitles}
          onGenerateDescription={handleGenerateDescription}
          isGenerating={isGenerating}
          disableActions={!produto?.id}
          showUseAiToggle={showAiFeatures}
          useAi={usarIA}
          onUseAiChange={setUsarIA}
          titleButtonLabel={showAiFeatures && usarIA ? 'Gerar títulos com IA' : 'Gerar títulos no básico'}
          descriptionButtonLabel={showAiFeatures && usarIA ? 'Gerar descrição com IA' : 'Gerar descrição no básico'}
        />

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

      <LoadingOverlay isOpen={produtoQuery.isLoading} message="Carregando conteudo do produto..." />
    </div>
  );
}

export default ProdutoConteudoPage;
