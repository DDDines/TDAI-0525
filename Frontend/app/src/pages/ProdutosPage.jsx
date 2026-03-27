/**
 * Module produtos page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  LuDownload,
  LuPlus,
  LuSearch,
} from 'react-icons/lu';
import ProductTable from '../components/produtos/ProductTable';
import Modal from '../components/common/Modal';
import ProductEditModal from '../components/ProductEditModal';
import { useAppExperience } from '../contexts/AppExperienceContext';
import PaginationControls from '../components/common/PaginationControls';
import productService from '../services/productService';
import {
  showErrorToast,
  showInfoToast,
  showSuccessToast,
  showWarningToast,
} from '../utils/notifications';
import './ProdutosPage.css';
import { useProductTypes } from '../contexts/ProductTypeContext';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import PageHeader from '../components/PageHeader.jsx';
import {
  normalizeProductListPayload,
  resolveGenerationHandler,
} from './ProdutosPage.helpers.js';
import { queryKeys } from '../lib/queryKeys.js';
import { extractErrorMessage } from '../utils/errorDetails';

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
const WEB_ENRICHMENT_POLL_INTERVAL_MS = 3000;
const WEB_ENRICHMENT_MAX_POLLS = 120;
const GENERATION_POLL_INTERVAL_MS = 3000;
const GENERATION_MAX_POLLS = 120;
const GENERATION_TERMINAL_STATUSES = new Set([
  'CONCLUIDO',
  'CONCLUIDO_SUCESSO',
  'FALHA',
  'FALHOU',
  'NAO_APLICAVEL',
]);
const FAILURE_STATUSES = new Set([
  'FALHA',
  'FALHOU',
  'FALHA_API_EXTERNA',
  'FALHA_CONFIGURACAO_API_EXTERNA',
  'NENHUMA_FONTE_ENCONTRADA',
]);
const ENRICHMENT_WARNING_STATUSES = new Set([
  'CONCLUIDO_COM_DADOS_PARCIAIS',
  ...FAILURE_STATUSES,
]);
const GENERATION_WARNING_STATUSES = new Set([
  'FALHA',
  'FALHOU',
]);
const PROCESS_ACTIVE_STATUSES = new Set([
  'PENDENTE',
  'EM_PROGRESSO',
]);
const REPROCESS_CONFIRM_STATUSES = new Set([
  'CONCLUIDO',
  'CONCLUIDO_SUCESSO',
  'CONCLUIDO_COM_DADOS_PARCIAIS',
]);

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

function formatProductSelectionSummary(count, scope) {
  if (count <= 0) {
    return '';
  }
  if (scope === 'all') {
    return `${count} item(ns) selecionado(s) (todos os resultados)`;
  }
  if (scope === 'page') {
    return `${count} item(ns) selecionado(s) (página atual)`;
  }
  return `${count} item(ns) selecionado(s) (seleção manual)`;
}

function formatSelectedCountSuffix(count) {
  return count === 1 ? 'para o produto selecionado.' : 'para os produtos selecionados.';
}

function _formatContentTypeLabel(contentType) {
  return contentType === 'titulo' ? 'título' : 'descrição';
}

function CatalogHealthPanel({ stats }) {
  if (!stats || stats.total === 0) return null;

  const cards = [
    { key: 'total', label: 'Total', value: stats.total, tone: 'neutral' },
    { key: 'com_sku', label: 'Com SKU', value: stats.com_sku, tone: 'muted' },
    { key: 'com_marca', label: 'Com Marca', value: stats.com_marca, tone: 'muted' },
    { key: 'enriquecidos', label: 'Enriquecidos', value: stats.enriquecidos, tone: 'info' },
    { key: 'com_titulo_ia', label: 'Conteúdo IA', value: stats.com_titulo_ia, tone: 'success' },
    { key: 'criticos', label: 'Críticos', value: stats.criticos, tone: stats.criticos > 0 ? 'danger' : 'muted' },
  ];

  return (
    <div className="catalog-health-panel">
      <div className="catalog-health-title">Saúde do Catálogo</div>
      <div className="catalog-health-grid">
        {cards.map((card) => (
          <div key={card.key} className={`catalog-health-card tone-${card.tone}`}>
            <strong>{card.value}</strong>
            <span>{card.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProdutosPage() {
  const { effectiveMode } = useAppExperience();
  const showAiFeatures = effectiveMode === 'complete';
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const modalQueryId = searchParams.get('id');

  const initialPage = Math.max(Number.parseInt(searchParams.get('page') || '1', 10) - 1, 0);
  const initialLimit = Math.max(Number.parseInt(searchParams.get('limit') || '10', 10), 1);
  const initialSortBy = searchParams.get('sort_by') || 'id';
  const initialSortOrder = (searchParams.get('sort_order') || 'desc').toLowerCase();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [produtoParaEditar, setProdutoParaEditar] = useState(null);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [limitPerPage, setLimitPerPage] = useState(initialLimit);
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '');
  const [sortConfig, setSortConfig] = useState({
    key: initialSortBy,
    direction: initialSortOrder === 'asc' ? 'ascending' : 'descending',
  });
  const [selectedProdutos, setSelectedProdutos] = useState(new Set());
  const [selectionScope, setSelectionScope] = useState('none');
  const [filtroStatusEnriquecimento, setFiltroStatusEnriquecimento] = useState(searchParams.get('status_enriquecimento_web') || '');
  const [filtroStatusTituloIA, setFiltroStatusTituloIA] = useState(searchParams.get('status_titulo_ia') || '');
  const [filtroStatusDescricaoIA, setFiltroStatusDescricaoIA] = useState(searchParams.get('status_descricao_ia') || '');
  const [filtroFornecedor] = useState('');
  const [filtroTipoProduto, setFiltroTipoProduto] = useState(searchParams.get('product_type_id') || '');
  const [usarIAEnriquecimento, setUsarIAEnriquecimento] = useState(false);
  const pendingRefreshTimeoutsRef = React.useRef([]);
  const webStatusPollRunRef = React.useRef(0);
  const generationPollRunsRef = React.useRef({
    status_titulo_ia: 0,
    status_descricao_ia: 0,
  });
  const isMountedRef = React.useRef(true);

  const { productTypes, isLoading: loadingProductTypes, error: productTypesError } = useProductTypes();

  const { data: catalogStats } = useQuery({
    queryKey: queryKeys.catalogStats(),
    queryFn: productService.getCatalogStats,
    staleTime: 2 * 60_000,
  });

  useEffect(() => {
    if (productTypesError) {
      console.error('ProdutosPage: erro recebido do ProductTypeContext:', productTypesError);
    }
  }, [productTypesError]);

  const buildProductNavigationQuery = useCallback(() => {
    const query = {
      sort_by: sortConfig.key,
      sort_order: sortConfig.direction === 'ascending' ? 'asc' : 'desc',
      search: searchTerm || undefined,
      status_enriquecimento_web: filtroStatusEnriquecimento || undefined,
      status_titulo_ia: showAiFeatures ? filtroStatusTituloIA || undefined : undefined,
      status_descricao_ia: showAiFeatures ? filtroStatusDescricaoIA || undefined : undefined,
      fornecedor_id: filtroFornecedor || undefined,
      product_type_id: filtroTipoProduto || undefined,
    };
    Object.keys(query).forEach((key) => query[key] === undefined && delete query[key]);
    return query;
  }, [
    sortConfig,
    searchTerm,
    filtroStatusEnriquecimento,
    filtroStatusTituloIA,
    filtroStatusDescricaoIA,
    filtroFornecedor,
    filtroTipoProduto,
    showAiFeatures,
  ]);

  const buildReturnToUrl = useCallback(() => {
    const params = new URLSearchParams();
    params.set('page', String(currentPage + 1));
    params.set('limit', String(limitPerPage));
    const query = buildProductNavigationQuery();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value));
      }
    });
    return `/produtos?${params.toString()}`;
  }, [buildProductNavigationQuery, currentPage, limitPerPage]);

  const productListParams = useMemo(
    () => ({
      ...buildProductNavigationQuery(),
      skip: currentPage * limitPerPage,
      limit: limitPerPage,
    }),
    [buildProductNavigationQuery, currentPage, limitPerPage]
  );

  const produtosQueryKey = queryKeys.produtos(productListParams);
  const produtosQuery = useQuery({
    queryKey: produtosQueryKey,
    queryFn: async () => normalizeProductListPayload(await productService.getProdutos(productListParams)),
    placeholderData: keepPreviousData,
  });

  const produtos = Array.isArray(produtosQuery.data?.items) ? produtosQuery.data.items : [];
  const totalProdutos =
    typeof produtosQuery.data?.total_items === 'number' ? produtosQuery.data.total_items : 0;
  const currentProdutosById = useMemo(
    () =>
      new Map(
        produtos
          .filter((produto) => produto?.id !== undefined && produto?.id !== null)
          .map((produto) => [String(produto.id), produto])
      ),
    [produtos]
  );
  const loadingInitial = produtosQuery.isLoading;
  const loading = produtosQuery.isFetching;
  const error = produtosQuery.error
    ? extractErrorMessage(produtosQuery.error, 'Falha ao carregar produtos.')
    : null;

  const refreshProdutos = useCallback(async () => {
    await produtosQuery.refetch();
  }, [produtosQuery]);

  const clearSelectionState = useCallback(() => {
    setSelectedProdutos(new Set());
    setSelectionScope('none');
  }, []);

  useEffect(() => {
    const nextParams = new URLSearchParams();
    nextParams.set('page', String(currentPage + 1));
    nextParams.set('limit', String(limitPerPage));
    if (modalQueryId) {
      nextParams.set('id', modalQueryId);
    }
    const query = buildProductNavigationQuery();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        nextParams.set(key, String(value));
      }
    });
    if (nextParams.toString() !== searchParams.toString()) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [
    buildProductNavigationQuery,
    currentPage,
    limitPerPage,
    modalQueryId,
    searchParams,
    setSearchParams,
  ]);

  const updateCurrentProdutosData = useCallback((updater) => {
    queryClient.setQueryData(produtosQueryKey, (previous) => {
      const safePrevious = normalizeProductListPayload(previous);
      return {
        ...safePrevious,
        items: updater(safePrevious.items),
      };
    });
  }, [produtosQueryKey, queryClient]);

  const removePendingRefreshTimeout = useCallback((entryToRemove) => {
    pendingRefreshTimeoutsRef.current = pendingRefreshTimeoutsRef.current.filter(
      (entry) => entry !== entryToRemove
    );
  }, []);

  const schedulePendingRefreshTimeout = useCallback((callback, delayMs, onCancel) => {
    const entry = { timeoutId: null, onCancel };
    entry.timeoutId = setTimeout(() => {
      removePendingRefreshTimeout(entry);
      callback();
    }, delayMs);
    pendingRefreshTimeoutsRef.current.push(entry);
    return entry;
  }, [removePendingRefreshTimeout]);

  const clearPendingRefreshTimeouts = useCallback(() => {
    pendingRefreshTimeoutsRef.current.forEach((entry) => {
      clearTimeout(entry.timeoutId);
      entry.onCancel?.();
    });
    pendingRefreshTimeoutsRef.current = [];
  }, []);

  useEffect(() => () => {
    isMountedRef.current = false;
    clearPendingRefreshTimeouts();
    webStatusPollRunRef.current += 1;
    generationPollRunsRef.current.status_titulo_ia += 1;
    generationPollRunsRef.current.status_descricao_ia += 1;
  }, [clearPendingRefreshTimeouts]);

  const handleProductUpdated = useCallback((updatedProduct) => {
    updateCurrentProdutosData((prevProdutos) => {
      let matched = false;
      const nextProducts = prevProdutos.map((produto) => {
        if (produto.id !== updatedProduct.id) {
          return produto;
        }
        matched = true;
        return updatedProduct;
      });
      return matched ? nextProducts : [...nextProducts, updatedProduct];
    });
    queryClient.setQueryData(queryKeys.produto(updatedProduct.id), updatedProduct);
  }, [queryClient, updateCurrentProdutosData]);

  const handleOpenModal = (produto) => {
    setProdutoParaEditar(produto ?? null);
    setIsModalOpen(true);
  };

  const handleOpenContentView = (produto) => {
    if (!produto?.id) {
      return;
    }
    navigate(`/produtos/${produto.id}/conteudo`, {
      state: {
        productIds: produtos.map((item) => item.id),
        productQuery: buildProductNavigationQuery(),
        returnTo: buildReturnToUrl(),
      },
    });
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setProdutoParaEditar(null);
  };

  useEffect(() => {
    const productId = searchParams.get('id');
    if (productId) {
      const openById = async () => {
        try {
          const prod = await productService.getProdutoById(productId);
          queryClient.setQueryData(queryKeys.produto(productId), prod);
          handleOpenModal(prod);
          const nextParams = new URLSearchParams(searchParams);
          nextParams.delete('id');
          setSearchParams(nextParams, { replace: true });
        } catch (err) {
          showErrorToast(extractErrorMessage(err, 'Falha ao carregar produto.'));
        }
      };
      void openById();
    }
  }, [queryClient, searchParams, setSearchParams]);

  const handleSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
    setCurrentPage(0);
    clearSelectionState();
  };

  const handleSelectProduto = (produtoId) => {
    setSelectedProdutos((prevSelected) => {
      const newSelected = new Set(prevSelected);
      if (newSelected.has(produtoId)) {
        newSelected.delete(produtoId);
      } else {
        newSelected.add(produtoId);
      }
      return newSelected;
    });
    setSelectionScope('custom');
  };

  const handleSelectAllProdutos = (isChecked) => {
    if (isChecked) {
      setSelectedProdutos(new Set(produtos.map((produto) => produto.id)));
      setSelectionScope('page');
    } else {
      clearSelectionState();
    }
  };

  const handleSelectAllResults = async (isChecked) => {
    if (!isChecked) {
      clearSelectionState();
      return;
    }
    try {
      const response = await productService.getProdutosIds(buildProductNavigationQuery());
      const ids = Array.isArray(response?.ids) ? response.ids : [];
      setSelectedProdutos(new Set(ids));
      setSelectionScope('all');
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao selecionar todos os resultados.'));
    }
  };

  const [exportLoading, setExportLoading] = React.useState(false);

  const handleExportProdutos = async () => {
    setExportLoading(true);
    try {
      const hasSelection = selectedProdutos.size > 0;
      const exportParams = hasSelection
        ? { ids: Array.from(selectedProdutos) }
        : {
            search: filtroStatusEnriquecimento ? undefined : searchTerm || undefined,
            fornecedor_id: filtroFornecedor || undefined,
            categoria: undefined,
            status_enriquecimento_web: filtroStatusEnriquecimento || undefined,
            status_titulo_ia: filtroStatusTituloIA || undefined,
            status_descricao_ia: filtroStatusDescricaoIA || undefined,
            product_type_id: filtroTipoProduto || undefined,
          };
      await productService.exportarProdutos(exportParams);
      showSuccessToast(hasSelection
        ? `${selectedProdutos.size} produto(s) exportado(s).`
        : 'Planilha exportada com sucesso.');
    } catch (err) {
      showErrorToast(extractErrorMessage(err, 'Falha ao exportar produtos.'));
    } finally {
      setExportLoading(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (!window.confirm(`Tem certeza que deseja ocultar ${selectedProdutos.size} produto(s) selecionado(s)?`)) {
      return;
    }
    const deletedCount = selectedProdutos.size;
    try {
      await productService.batchDeleteProdutos(Array.from(selectedProdutos));
      clearSelectionState();
      await queryClient.invalidateQueries({ queryKey: ['produtos'] });
      showSuccessToast(
        `${deletedCount} produto(s) ocultado(s) com sucesso.`
      );
    } catch (err) {
      showErrorToast(extractErrorMessage(err, 'Falha ao ocultar produtos.'));
    }
  };

  const updateLocalProductStatus = (ids, statusField, newStatus) => {
    const idSet = new Set(Array.from(ids).map((id) => String(id)));
    updateCurrentProdutosData((prevProdutos) =>
      prevProdutos.map((produto) => (
        idSet.has(String(produto.id))
          ? { ...produto, [statusField]: newStatus }
          : produto
      ))
    );
  };

  const mergeProdutosById = useCallback((fetchedProdutos) => {
    const fetchedMap = new Map(
      fetchedProdutos
        .filter((item) => item?.id !== undefined && item?.id !== null)
        .map((item) => [String(item.id), item])
    );
    if (fetchedMap.size === 0) {
      return;
    }

    fetchedProdutos.forEach((produto) => {
      if (produto?.id !== undefined && produto?.id !== null) {
        queryClient.setQueryData(queryKeys.produto(produto.id), produto);
      }
    });

    updateCurrentProdutosData((prevProdutos) =>
      prevProdutos.map((produtoAtual) => {
        const fresh = fetchedMap.get(String(produtoAtual.id));
        return fresh ? { ...produtoAtual, ...fresh } : produtoAtual;
      })
    );
  }, [queryClient, updateCurrentProdutosData]);

  const fetchRequestedProducts = useCallback(async (produtoIds) => {
    const requestedIds = new Set(Array.from(produtoIds).map((id) => String(id)));
    const fetched = await Promise.all(
      Array.from(requestedIds).map(async (produtoId) => {
        try {
          return await productService.getProdutoById(produtoId);
        } catch {
          return null;
        }
      })
    );
    return fetched.filter((produto) => {
      const produtoId = produto?.id;
      return produtoId !== undefined && produtoId !== null && requestedIds.has(String(produtoId));
    });
  }, []);

  const filterActiveProcessIds = useCallback(async (produtoIds, statusField, processLabel) => {
    const ids = Array.from(produtoIds);
    const shouldRefreshBatchStatuses = ids.length > 1;
    const idsToInspect = shouldRefreshBatchStatuses
      ? ids
      : ids.filter((id) => !currentProdutosById.has(String(id)));
    const fetched = idsToInspect.length > 0 ? await fetchRequestedProducts(idsToInspect) : [];
    const fetchedById = new Map(
      fetched.map((produto) => [String(produto.id), produto])
    );
    const knownProdutos = ids
      .map((id) => fetchedById.get(String(id)) ?? currentProdutosById.get(String(id)))
      .filter(Boolean);
    const activeIds = new Set(
      [...knownProdutos, ...fetched]
        .filter((produto) =>
          PROCESS_ACTIVE_STATUSES.has(normalizeProcessStatusValue(produto?.[statusField]))
        )
        .map((produto) => String(produto.id))
    );

    if (activeIds.size > 0) {
      const skippedMessage =
        activeIds.size === 1
          ? `1 produto já estava em processamento de ${processLabel} e foi ignorado.`
          : `${activeIds.size} produtos já estavam em processamento de ${processLabel} e foram ignorados.`;
      showInfoToast(skippedMessage);
    }

    return ids.filter((id) => !activeIds.has(String(id)));
  }, [currentProdutosById, fetchRequestedProducts]);

  const pollWebEnrichmentStatuses = useCallback(async (produtoIds) => {
    const pollRunId = webStatusPollRunRef.current + 1;
    webStatusPollRunRef.current = pollRunId;
    const ids = Array.from(produtoIds).map((id) => String(id));
    const countSuffix = formatSelectedCountSuffix(ids.length);

    for (let attempt = 0; attempt < WEB_ENRICHMENT_MAX_POLLS; attempt += 1) {
      if (webStatusPollRunRef.current !== pollRunId || !isMountedRef.current) {
        return;
      }
      const validFetched = await fetchRequestedProducts(ids);
      if (webStatusPollRunRef.current !== pollRunId || !isMountedRef.current) {
        return;
      }
      mergeProdutosById(validFetched);

      if (validFetched.length > 0) {
        const allTerminal = validFetched.every((produto) =>
          WEB_ENRICHMENT_TERMINAL_STATUSES.has(
            String(produto.status_enriquecimento_web || '').toUpperCase()
          )
        );
        if (allTerminal) {
          if (webStatusPollRunRef.current !== pollRunId || !isMountedRef.current) {
            return;
          }
          const hasWarnings = validFetched.some((produto) =>
            ENRICHMENT_WARNING_STATUSES.has(
              String(produto.status_enriquecimento_web || '').toUpperCase()
            )
          );
          if (hasWarnings) {
            showWarningToast(
              `Enriquecimento web finalizado com pendências ${countSuffix}`
            );
          } else {
            showSuccessToast(`Enriquecimento web finalizado ${countSuffix}`);
          }
          await queryClient.invalidateQueries({ queryKey: ['produtos'] });
          return;
        }
      }

      await new Promise((resolve) => {
        schedulePendingRefreshTimeout(resolve, WEB_ENRICHMENT_POLL_INTERVAL_MS, resolve);
      });
    }

    if (webStatusPollRunRef.current !== pollRunId || !isMountedRef.current) {
      return;
    }
    await queryClient.invalidateQueries({ queryKey: ['produtos'] });
  }, [fetchRequestedProducts, mergeProdutosById, queryClient, schedulePendingRefreshTimeout]);

  const pollGenerationStatuses = useCallback(async (produtoIds, statusField) => {
    const pollRunId = generationPollRunsRef.current[statusField] + 1;
    generationPollRunsRef.current[statusField] = pollRunId;
    const ids = Array.from(produtoIds).map((id) => String(id));
    const countSuffix = formatSelectedCountSuffix(ids.length);

    for (let attempt = 0; attempt < GENERATION_MAX_POLLS; attempt += 1) {
      if (generationPollRunsRef.current[statusField] !== pollRunId || !isMountedRef.current) {
        return;
      }

      const validFetched = await fetchRequestedProducts(ids);
      if (generationPollRunsRef.current[statusField] !== pollRunId || !isMountedRef.current) {
        return;
      }
      mergeProdutosById(validFetched);

      if (validFetched.length > 0) {
        const allTerminal = validFetched.every((produto) =>
          GENERATION_TERMINAL_STATUSES.has(
            normalizeProcessStatusValue(produto?.[statusField])
          )
        );
        if (allTerminal) {
          const processLabel =
            statusField === 'status_titulo_ia' ? 'títulos' : 'descrições';
          if (generationPollRunsRef.current[statusField] !== pollRunId || !isMountedRef.current) {
            return;
          }
          const hasWarnings = validFetched.some((produto) =>
            GENERATION_WARNING_STATUSES.has(
              normalizeProcessStatusValue(produto?.[statusField])
            )
          );
          if (hasWarnings) {
            showWarningToast(
              `A geração de ${processLabel} terminou com pendências ${countSuffix}`
            );
          } else {
            showSuccessToast(
              `Geração de ${processLabel} finalizada ${countSuffix}`
            );
          }
          await queryClient.invalidateQueries({ queryKey: ['produtos'] });
          return;
        }
      }

      await new Promise((resolve) => {
        schedulePendingRefreshTimeout(resolve, GENERATION_POLL_INTERVAL_MS, resolve);
      });
    }

    if (generationPollRunsRef.current[statusField] !== pollRunId || !isMountedRef.current) {
      return;
    }
    showInfoToast(
      'A geração ainda pode estar em andamento em segundo plano. Atualizando a lista.'
    );
    await queryClient.invalidateQueries({ queryKey: ['produtos'] });
  }, [fetchRequestedProducts, mergeProdutosById, queryClient, schedulePendingRefreshTimeout]);

  const handleEnrichSelectedWeb = async () => {
    const idsToProcess = await filterActiveProcessIds(
      selectedProdutos,
      'status_enriquecimento_web',
      'enriquecimento web'
    );
    clearSelectionState();
    if (idsToProcess.length === 0) {
      return;
    }
    updateLocalProductStatus(new Set(idsToProcess), 'status_enriquecimento_web', 'PENDENTE');
    const failedIds = new Set();
    await Promise.all(
      idsToProcess.map(async (produtoId) => {
        try {
          if (showAiFeatures && usarIAEnriquecimento) {
            await productService.iniciarEnriquecimentoWebProduto(produtoId, {
              usarIA: true,
            });
          } else {
            await productService.iniciarEnriquecimentoWebProduto(produtoId);
          }
        } catch (err) {
          failedIds.add(String(produtoId));
          const detail = extractErrorMessage(err, '');
          showErrorToast(
            detail
              ? `Erro ao iniciar enriquecimento para produto ID ${produtoId}: ${detail}`
              : `Erro ao iniciar enriquecimento para produto ID ${produtoId}.`
          );
          updateLocalProductStatus(new Set([produtoId]), 'status_enriquecimento_web', 'FALHA');
        }
      })
    );

    const startedIds = idsToProcess.filter((produtoId) => !failedIds.has(String(produtoId)));
    if (startedIds.length > 0) {
      updateLocalProductStatus(new Set(startedIds), 'status_enriquecimento_web', 'EM_PROGRESSO');
      void pollWebEnrichmentStatuses(startedIds);
    }
  };

  const handleGenerateContentForSelected = async (contentType) => {
    const statusField = `status_${contentType}_ia`;
    const idsToProcess = await filterActiveProcessIds(
      selectedProdutos,
      statusField,
      contentType === 'titulo' ? 'geração de títulos' : 'geração de descrições'
    );
    clearSelectionState();
    if (idsToProcess.length === 0) return;

    updateLocalProductStatus(new Set(idsToProcess), statusField, 'PENDENTE');
    const provider = showAiFeatures ? 'openai' : 'basico';

    try {
      const result = await productService.batchGeneration({
        produtoIds: idsToProcess,
        tipo: contentType,
        provider,
      });
      if (result.agendados > 0) {
        updateLocalProductStatus(new Set(idsToProcess), statusField, 'EM_PROGRESSO');
        void pollGenerationStatuses(idsToProcess, statusField);
        showSuccessToast(`${result.agendados} produto(s) agendado(s) para geração.`);
      }
      if (result.ignorados > 0) {
        showErrorToast(`${result.ignorados} produto(s) ignorado(s). Verifique os limites do plano.`);
      }
    } catch (err) {
      updateLocalProductStatus(new Set(idsToProcess), statusField, 'FALHA');
      showErrorToast(extractErrorMessage(err, 'Falha ao agendar geração em lote.'));
    }
  };

  const handleProductProcessAction = useCallback(async (produto, processKey) => {
    if (!produto?.id) {
      return;
    }

    const processMap = {
      status_enriquecimento_web: {
        label: 'enriquecimento web',
        run: async () => {
          updateLocalProductStatus(new Set([produto.id]), 'status_enriquecimento_web', 'PENDENTE');
          try {
            if (showAiFeatures && usarIAEnriquecimento) {
              await productService.iniciarEnriquecimentoWebProduto(produto.id, { usarIA: true });
          } else {
            await productService.iniciarEnriquecimentoWebProduto(produto.id);
          }
          updateLocalProductStatus(new Set([produto.id]), 'status_enriquecimento_web', 'EM_PROGRESSO');
          void pollWebEnrichmentStatuses([produto.id]);
        } catch (error) {
          updateLocalProductStatus(new Set([produto.id]), 'status_enriquecimento_web', 'FALHA');
          const detail = extractErrorMessage(error, '');
          showErrorToast(
            detail
              ? `Erro ao iniciar enriquecimento para produto ID ${produto.id}: ${detail}`
              : `Erro ao iniciar enriquecimento para produto ID ${produto.id}.`
          );
        }
      },
    },
      status_titulo_ia: {
        label: showAiFeatures ? 'geração de títulos com IA' : 'geração de títulos',
        requiresWebEnrichment: true,
        incompleteWarningLabel: 'os títulos serão gerados',
        run: async () => {
          const generationHandler = resolveGenerationHandler('titulo', showAiFeatures, productService);
          updateLocalProductStatus(new Set([produto.id]), 'status_titulo_ia', 'PENDENTE');
          try {
            await generationHandler(produto.id);
            updateLocalProductStatus(new Set([produto.id]), 'status_titulo_ia', 'EM_PROGRESSO');
            void pollGenerationStatuses([produto.id], 'status_titulo_ia');
          } catch (error) {
            updateLocalProductStatus(new Set([produto.id]), 'status_titulo_ia', 'FALHA');
            const detail = extractErrorMessage(error, '');
            showErrorToast(
              detail
                ? `Erro ao gerar título para produto ID ${produto.id}: ${detail}`
                : `Erro ao gerar título para produto ID ${produto.id}.`
            );
          }
        },
      },
      status_descricao_ia: {
        label: showAiFeatures ? 'geração de descrições com IA' : 'geração de descrições',
        requiresWebEnrichment: true,
        incompleteWarningLabel: 'as descrições serão geradas',
        run: async () => {
          const generationHandler = resolveGenerationHandler('descricao', showAiFeatures, productService);
          updateLocalProductStatus(new Set([produto.id]), 'status_descricao_ia', 'PENDENTE');
          try {
            await generationHandler(produto.id);
            updateLocalProductStatus(new Set([produto.id]), 'status_descricao_ia', 'EM_PROGRESSO');
            void pollGenerationStatuses([produto.id], 'status_descricao_ia');
          } catch (error) {
            updateLocalProductStatus(new Set([produto.id]), 'status_descricao_ia', 'FALHA');
            const detail = extractErrorMessage(error, '');
            showErrorToast(
              detail
                ? `Erro ao gerar descrição para produto ID ${produto.id}: ${detail}`
                : `Erro ao gerar descrição para produto ID ${produto.id}.`
            );
          }
        },
      },
    };

    const process = processMap[processKey];
    if (!process) {
      return;
    }

    const currentStatus = normalizeProcessStatusValue(produto?.[processKey]);
    const webEnrichmentStatus = normalizeProcessStatusValue(produto?.status_enriquecimento_web);
    if (PROCESS_ACTIVE_STATUSES.has(currentStatus)) {
      return;
    }

    if (
      process.requiresWebEnrichment
      && !WEB_ENRICHMENT_TERMINAL_STATUSES.has(webEnrichmentStatus)
    ) {
      const confirmed = window.confirm(
        `O enriquecimento web de "${produto.nome_base}" ainda não foi concluído. Se continuar agora, ${process.incompleteWarningLabel} com informações incompletas. Deseja continuar mesmo assim?`
      );
      if (!confirmed) {
        return;
      }
    }

    if (REPROCESS_CONFIRM_STATUSES.has(currentStatus)) {
      const confirmed = window.confirm(
        `A etapa de ${process.label} para "${produto.nome_base}" já foi concluída. Deseja executar novamente?`
      );
      if (!confirmed) {
        return;
      }
    }

    await process.run();
  }, [
    pollWebEnrichmentStatuses,
    pollGenerationStatuses,
    showAiFeatures,
    updateLocalProductStatus,
    usarIAEnriquecimento,
  ]);

  const totalPages = Math.ceil(totalProdutos / limitPerPage);
  const selectionSummary = formatProductSelectionSummary(selectedProdutos.size, selectionScope);
  const productSelectionMenuItems = [
    {
      key: 'page',
      label: 'Selecionar página atual',
      onClick: () => handleSelectAllProdutos(true),
      disabled: produtos.length === 0,
    },
    {
      key: 'all',
      label: 'Selecionar todos os resultados da pesquisa',
      onClick: () => void handleSelectAllResults(true),
      disabled: totalProdutos === 0,
    },
    {
      key: 'clear',
      label: 'Limpar seleção',
      onClick: clearSelectionState,
      disabled: selectedProdutos.size === 0,
    },
  ];
  if (error && !loadingInitial && (!produtos || produtos.length === 0)) {
    return (
      <div className="error-message">
        Erro ao carregar produtos: {error}
        <button onClick={() => void refreshProdutos()}>Tentar novamente</button>
      </div>
    );
  }

  return (
    <div className="app-page-shell ops-page-shell produtos-page-shell">
      <PageHeader title="Catálogo de Produtos" subtitle="Gerencie, importe e enriqueça seus produtos" />
      <CatalogHealthPanel stats={catalogStats} />
      <section className="ops-card ops-table-card produtos-table-card">
        <div className="produtos-list-toolbar">
          <div className="produtos-toolbar-main">
            <div className="ops-search-field produtos-search-field">
              <div className="ops-search-input-wrap">
                <LuSearch />
                <input
                  id="produtos-search"
                  type="text"
                  aria-label="Buscar produtos"
                  placeholder="Buscar por nome, SKU, EAN..."
                  value={searchTerm}
                  onChange={(event) => {
                    setSearchTerm(event.target.value);
                    setCurrentPage(0);
                    clearSelectionState();
                  }}
                />
              </div>
            </div>

            <button onClick={() => handleOpenModal(null)} className="ops-primary-btn produtos-create-btn">
              <LuPlus />
              Novo Produto
            </button>
          </div>

          <div className="ops-filters-row produtos-filters-row">
            <select
              id="produtos-status-filter"
              value={filtroStatusEnriquecimento}
              onChange={(event) => {
                setFiltroStatusEnriquecimento(event.target.value);
                setCurrentPage(0);
                clearSelectionState();
              }}
              className="ops-select produtos-filter-select"
            >
              <option value="">Status</option>
              <option value="NAO_INICIADO">Não iniciado</option>
              <option value="PENDENTE">Pendente</option>
              <option value="EM_PROGRESSO">Em progresso</option>
              <option value="CONCLUIDO_SUCESSO">Concluído</option>
              <option value="FALHA">Falha</option>
            </select>

            {showAiFeatures ? (
              <>
                <select
                  value={filtroStatusTituloIA}
                  onChange={(event) => {
                    setFiltroStatusTituloIA(event.target.value);
                    setCurrentPage(0);
                    clearSelectionState();
                  }}
                  className="ops-select produtos-filter-select"
                >
                  <option value="">Título IA</option>
                  <option value="NAO_INICIADO">Não iniciado</option>
                  <option value="PENDENTE">Pendente</option>
                  <option value="EM_PROGRESSO">Em progresso</option>
                  <option value="CONCLUIDO">Concluído</option>
                  <option value="FALHA">Falha</option>
                </select>

                <select
                  value={filtroStatusDescricaoIA}
                  onChange={(event) => {
                    setFiltroStatusDescricaoIA(event.target.value);
                    setCurrentPage(0);
                    clearSelectionState();
                  }}
                  className="ops-select produtos-filter-select"
                >
                  <option value="">Descrição IA</option>
                  <option value="NAO_INICIADO">Não iniciado</option>
                  <option value="PENDENTE">Pendente</option>
                  <option value="EM_PROGRESSO">Em progresso</option>
                  <option value="CONCLUIDO">Concluído</option>
                  <option value="FALHA">Falha</option>
                </select>
              </>
            ) : null}

            <select
              aria-label="Filtrar por tipo de produto"
              value={filtroTipoProduto}
              onChange={(event) => {
                setFiltroTipoProduto(event.target.value);
                setCurrentPage(0);
                clearSelectionState();
              }}
              className="ops-select produtos-filter-select produtos-filter-select-wide"
              disabled={loadingProductTypes || (productTypes && productTypes.length === 0)}
            >
              <option value="">{loadingProductTypes ? 'Carregando tipos...' : 'Todos os tipos'}</option>
              {productTypes && productTypes.map((productType) => (
                <option key={productType.id} value={productType.id}>
                  {productType.friendly_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {selectedProdutos.size > 0 ? (
          <div className="ops-selection-bar produtos-selection-bar">
            <div className="ops-selection-copy">
              <p className="ops-selection-summary">{selectionSummary}</p>
              {showAiFeatures ? (
                <label className="ops-inline-toggle">
                  <input
                    type="checkbox"
                    checked={usarIAEnriquecimento}
                    onChange={(event) => setUsarIAEnriquecimento(event.target.checked)}
                  />
                  Usar IA no enriquecimento web
                </label>
              ) : null}
            </div>
            <div className="ops-selection-actions">
              <button onClick={handleExportProdutos} className="btn-secondary btn-sm" disabled={exportLoading}>
                <LuDownload style={{ marginRight: 4 }} />
                {exportLoading ? 'Exportando...' : 'Exportar'}
              </button>
              <button onClick={handleDeleteSelected} className="btn-danger btn-sm">Ocultar</button>
              <button onClick={handleEnrichSelectedWeb} className="btn-secondary btn-sm">
                {showAiFeatures && usarIAEnriquecimento ? 'Enriquecer Web + IA' : 'Enriquecer Web'}
              </button>
              <button onClick={() => void handleGenerateContentForSelected('titulo')} className="btn-secondary btn-sm">
                {showAiFeatures ? 'Gerar Títulos IA' : 'Gerar Títulos'}
              </button>
              <button onClick={() => void handleGenerateContentForSelected('descricao')} className="btn-secondary btn-sm">
                {showAiFeatures ? 'Gerar Descricoes IA' : 'Gerar Descricoes'}
              </button>
            </div>
          </div>
        ) : null}

        {loadingInitial && (!produtos || produtos.length === 0) ? (
          <LoadingOverlay isOpen={true} message="Carregando produtos..." />
        ) : (
          <ProductTable
            produtos={produtos}
            onEdit={handleOpenModal}
            onViewContent={handleOpenContentView}
            onProcessAction={handleProductProcessAction}
            onSort={handleSort}
            sortConfig={sortConfig}
            onSelectProduto={handleSelectProduto}
            selectedProdutos={selectedProdutos}
            onSelectAllProdutos={handleSelectAllProdutos}
            selectionMenuItems={productSelectionMenuItems}
            showAiColumns={true}
            loading={loading && produtos && produtos.length > 0}
          />
        )}

        {!loadingInitial && totalProdutos > 0 ? (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => {
              setCurrentPage(page);
              clearSelectionState();
            }}
            itemsPerPage={limitPerPage}
            onItemsPerPageChange={(value) => {
              setLimitPerPage(parseInt(value, 10));
              setCurrentPage(0);
              clearSelectionState();
            }}
            totalItems={totalProdutos}
          />
        ) : null}
      </section>

      {isModalOpen ? (
        <Modal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          title={produtoParaEditar ? 'Editar Produto' : 'Criar Novo Produto'}
        >
          <ProductEditModal
            isOpen={isModalOpen}
            onClose={handleCloseModal}
            product={produtoParaEditar}
            showAiFeatures={showAiFeatures}
            returnTo={buildReturnToUrl()}
            onOpenContentView={(produtoId) => {
              if (!produtoId) {
                return;
              }
              handleOpenContentView({ id: produtoId });
            }}
            onProductUpdated={handleProductUpdated}
          />
        </Modal>
      ) : null}
    </div>
  );
}

export default ProdutosPage;
