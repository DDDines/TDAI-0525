/**
 * Module produtos page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  LuBox,
  LuBoxes,
  LuCircleAlert,
  LuPlus,
  LuSearch,
} from 'react-icons/lu';
import ProductTable from '../components/produtos/ProductTable';
import Modal from '../components/common/Modal';
import ProductEditModal from '../components/ProductEditModal';
import { useAppExperience } from '../contexts/AppExperienceContext';
import PaginationControls from '../components/common/PaginationControls';
import productService from '../services/productService';
import { showErrorToast } from '../utils/notifications';
import './ProdutosPage.css';
import { useProductTypes } from '../contexts/ProductTypeContext';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import OperationalStatChip from '../components/common/OperationalStatChip.jsx';
import {
  normalizeProductListPayload,
  resolveGenerationHandler,
} from './ProdutosPage.helpers.js';
import { queryKeys } from '../lib/queryKeys.js';

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
const FAILURE_STATUSES = new Set([
  'FALHA',
  'FALHOU',
  'FALHA_API_EXTERNA',
  'FALHA_CONFIGURACAO_API_EXTERNA',
  'NENHUMA_FONTE_ENCONTRADA',
]);

function formatProductSelectionSummary(count, scope) {
  if (count <= 0) {
    return '';
  }
  if (scope === 'all') {
    return `${count} item(ns) selecionado(s) (todos os resultados)`;
  }
  if (scope === 'page') {
    return `${count} item(ns) selecionado(s) (pagina atual)`;
  }
  return `${count} item(ns) selecionado(s) (selecao manual)`;
}

function hasFailureStatus(statusValue) {
  return FAILURE_STATUSES.has(String(statusValue || '').toUpperCase());
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

  const { productTypes, isLoading: loadingProductTypes, error: productTypesError } = useProductTypes();

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
  const loadingInitial = produtosQuery.isLoading;
  const loading = produtosQuery.isFetching;
  const error = produtosQuery.error?.response?.data?.detail ||
    produtosQuery.error?.message ||
    (produtosQuery.error ? 'Falha ao carregar produtos.' : null);

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
    clearPendingRefreshTimeouts();
    webStatusPollRunRef.current += 1;
  }, [clearPendingRefreshTimeouts]);

  const scheduleProdutosRefresh = useCallback(() => {
    schedulePendingRefreshTimeout(() => {
      void refreshProdutos();
    }, 15000);
  }, [refreshProdutos, schedulePendingRefreshTimeout]);

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
          const msg = err.response?.data?.detail || err.message || 'Falha ao carregar produto.';
          showErrorToast(msg);
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
      showErrorToast(error.message || 'Falha ao selecionar todos os resultados.');
    }
  };

  const handleDeleteSelected = async () => {
    if (!window.confirm(`Tem certeza que deseja deletar ${selectedProdutos.size} produto(s) selecionado(s)?`)) {
      return;
    }
    try {
      await productService.batchDeleteProdutos(Array.from(selectedProdutos));
      clearSelectionState();
      await queryClient.invalidateQueries({ queryKey: ['produtos'] });
    } catch (err) {
      showErrorToast(err.response?.data?.detail || err.message || 'Falha ao deletar produtos.');
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

  const pollWebEnrichmentStatuses = useCallback(async (produtoIds) => {
    const pollRunId = webStatusPollRunRef.current + 1;
    webStatusPollRunRef.current = pollRunId;
    const ids = Array.from(produtoIds).map((id) => String(id));

    for (let attempt = 0; attempt < WEB_ENRICHMENT_MAX_POLLS; attempt += 1) {
      if (webStatusPollRunRef.current !== pollRunId) {
        return;
      }
      const fetched = await Promise.all(
        ids.map(async (produtoId) => {
          try {
            return await productService.getProdutoById(produtoId);
          } catch {
            return null;
          }
        })
      );
      const validFetched = fetched.filter(Boolean);
      mergeProdutosById(validFetched);

      if (validFetched.length > 0) {
        const allTerminal = validFetched.every((produto) =>
          WEB_ENRICHMENT_TERMINAL_STATUSES.has(
            String(produto.status_enriquecimento_web || '').toUpperCase()
          )
        );
        if (allTerminal) {
          await queryClient.invalidateQueries({ queryKey: ['produtos'] });
          return;
        }
      }

      await new Promise((resolve) => {
        schedulePendingRefreshTimeout(resolve, WEB_ENRICHMENT_POLL_INTERVAL_MS, resolve);
      });
    }

    await queryClient.invalidateQueries({ queryKey: ['produtos'] });
  }, [mergeProdutosById, queryClient, schedulePendingRefreshTimeout]);

  const handleEnrichSelectedWeb = async () => {
    const idsToProcess = Array.from(selectedProdutos);
    clearSelectionState();
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
          showErrorToast(
            `Erro ao iniciar enriquecimento para produto ID ${produtoId}: ${
              err.response?.data?.detail || err.message
            }`
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
    const contentTypePlural = contentType === 'titulo' ? 'títulos' : 'descrições';

    const statusField = `status_${contentType}_ia`;
    updateLocalProductStatus(selectedProdutos, statusField, 'EM_PROGRESSO');

    const idsToProcess = Array.from(selectedProdutos);
    clearSelectionState();
    const generationHandler = resolveGenerationHandler(contentType, showAiFeatures, productService);

    for (const produtoId of idsToProcess) {
      try {
        await generationHandler(produtoId);
      } catch (err) {
        showErrorToast(
          `Erro ao gerar ${contentType} para produto ID ${produtoId}: ${
            err.response?.data?.detail || err.message
          }`
        );
        updateLocalProductStatus(new Set([produtoId]), statusField, 'FALHA');
      }
    }

    scheduleProdutosRefresh();
  };

  const totalPages = Math.ceil(totalProdutos / limitPerPage);
  const produtosComFalhaNaPagina = produtos.filter((produto) =>
    hasFailureStatus(produto.status_enriquecimento_web)
    || hasFailureStatus(produto.status_titulo_ia)
    || hasFailureStatus(produto.status_descricao_ia)
  ).length;
  const selectionSummary = formatProductSelectionSummary(selectedProdutos.size, selectionScope);
  const productSelectionMenuItems = [
    {
      key: 'page',
      label: 'Selecionar pagina atual',
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
      label: 'Limpar selecao',
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
      <section className="ops-card ops-toolbar-card produtos-stats-card">
        <div className="produtos-stats-header">
          <div className="ops-metrics-row produtos-metrics-row">
            <OperationalStatChip
              icon={<LuBoxes />}
              label="Na base"
              value={totalProdutos}
              tone="neutral"
            />
            <OperationalStatChip
              icon={<LuBox />}
              label="Na pagina"
              value={produtos.length}
              tone="info"
            />
            <OperationalStatChip
              icon={<LuCircleAlert />}
              label="Com falha"
              value={produtosComFalhaNaPagina}
              tone={produtosComFalhaNaPagina > 0 ? 'danger' : 'success'}
            />
            {selectedProdutos.size > 0 ? (
              <OperationalStatChip
                icon={<LuBox />}
                label="Selecionados"
                value={selectedProdutos.size}
                tone="warn"
              />
            ) : null}
          </div>
          <button onClick={() => handleOpenModal(null)} className="ops-primary-btn">
            <LuPlus />
            Novo Produto
          </button>
        </div>
      </section>

      <section className="ops-card ops-table-card produtos-table-card">
        <div className="produtos-list-toolbar">
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
                <option value="">Status Título IA</option>
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
                <option value="">Status Descrição IA</option>
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
              <button onClick={handleDeleteSelected} className="btn-danger btn-sm">Deletar</button>
              <button onClick={handleEnrichSelectedWeb} className="btn-secondary btn-sm">
                {showAiFeatures && usarIAEnriquecimento ? 'Enriquecer Web + IA' : 'Enriquecer Web'}
              </button>
              <button onClick={() => void handleGenerateContentForSelected('titulo')} className="btn-secondary btn-sm">
                {showAiFeatures ? 'Gerar Titulos IA' : 'Gerar Titulos'}
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
