/**
 * Module enriquecimento page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useCallback, useMemo, useState } from 'react';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LuBoxes,
  LuCircleAlert,
  LuClock3,
  LuGlobe,
  LuSearch,
} from 'react-icons/lu';
import './EnriquecimentoPage.css';
import productService from '../services/productService';
import usoIAService from '../services/usoIAService';
import ProductTable from '../components/produtos/ProductTable';
import PaginationControls from '../components/common/PaginationControls';
import {
  showSuccessToast,
  showErrorToast,
  showInfoToast,
  showWarningToast,
} from '../utils/notifications';
import logger from '../utils/logger';
import { extractErrorMessage } from '../utils/errorDetails';
import { queryKeys } from '../lib/queryKeys.js';
import { useAppExperience } from '../contexts/AppExperienceContext.jsx';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import OperationalStatChip from '../components/common/OperationalStatChip.jsx';
import PageHeader from '../components/PageHeader.jsx';

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
const WEB_ENRICHMENT_FAILURE_STATUSES = new Set([
  'FALHA',
  'FALHOU',
  'FALHA_API_EXTERNA',
  'FALHA_CONFIGURACAO_API_EXTERNA',
  'NENHUMA_FONTE_ENCONTRADA',
]);
const WEB_ENRICHMENT_WARNING_STATUSES = new Set([
  'CONCLUIDO_COM_DADOS_PARCIAIS',
  ...WEB_ENRICHMENT_FAILURE_STATUSES,
]);
const WEB_ENRICHMENT_RUNNING_STATUSES = new Set([
  'PENDENTE',
  'EM_PROGRESSO',
]);
const WEB_ENRICHMENT_POLL_INTERVAL_MS = 3000;
const WEB_ENRICHMENT_MAX_POLLS = 120;

function notifyWithConsoleLog(title, message) {
  console.log(`${title}:\n${message}`);
  const truncated = message.length > 200 ? `${message.slice(0, 200)}...` : message;
  showInfoToast(`${title}: ${truncated}`);
}

function normalizeProductListPayload(responseData) {
  if (
    responseData &&
    Array.isArray(responseData.items) &&
    typeof responseData.total_items === 'number'
  ) {
    return responseData;
  }
  console.warn('Formato de dados inesperado recebido para produtos:', responseData);
  return {
    items: [],
    total_items: 0,
  };
}

function formatSelectionSummary(selectedCount, selectionScope) {
  if (selectedCount <= 0) {
    return '';
  }
  if (selectionScope === 'all') {
    return `${selectedCount} item(ns) selecionado(s) (todos os resultados)`;
  }
  if (selectionScope === 'page') {
    return `${selectedCount} item(ns) selecionado(s) (página atual)`;
  }
  return `${selectedCount} item(ns) selecionado(s) (seleção manual)`;
}

function normalizeStatus(status) {
  return String(status || '').toUpperCase();
}

function EnriquecimentoPage() {
  const { effectiveMode } = useAppExperience();
  const showAiFeatures = effectiveMode === 'complete';
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedProductIds, setSelectedProductIds] = useState(new Set());
  const [selectionScope, setSelectionScope] = useState('none');
  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'id', direction: 'descending' });
  const [enrichmentScope, setEnrichmentScope] = useState('enriched');
  const [usarIAEnriquecimento, setUsarIAEnriquecimento] = useState(false);
  const webStatusPollRunRef = React.useRef(0);
  const isMountedRef = React.useRef(true);
  const queryClient = useQueryClient();

  React.useEffect(() => () => {
    isMountedRef.current = false;
    webStatusPollRunRef.current += 1;
  }, []);

  const queryParams = useMemo(
    () => ({
      skip: currentPage * limitPerPage,
      limit: limitPerPage,
      search: searchTerm || undefined,
      sort_by: sortConfig.key,
      sort_order: sortConfig.direction === 'ascending' ? 'asc' : 'desc',
      enrichment_scope: enrichmentScope,
    }),
    [currentPage, limitPerPage, searchTerm, sortConfig, enrichmentScope]
  );
  const produtosQueryKey = queryKeys.produtos(queryParams);
  const produtosQuery = useQuery({
    queryKey: produtosQueryKey,
    queryFn: async () => normalizeProductListPayload(await productService.getProdutos(queryParams)),
    placeholderData: keepPreviousData,
  });

  const produtos = Array.isArray(produtosQuery.data?.items) ? produtosQuery.data.items : [];
  const totalProdutosCount =
    typeof produtosQuery.data?.total_items === 'number' ? produtosQuery.data.total_items : 0;
  const loadingInitial = produtosQuery.isLoading;
  const loading = produtosQuery.isLoading || produtosQuery.isFetching;
  const error = produtosQuery.error
    ? extractErrorMessage(produtosQuery.error, 'Falha ao buscar produtos.')
    : null;
  const totalPages = Math.ceil(totalProdutosCount / limitPerPage);
  const selectedCount = selectedProductIds.size;
  const selectionSummary = formatSelectionSummary(selectedCount, selectionScope);
  const produtosEmAndamentoNaPagina = produtos.filter((produto) =>
    WEB_ENRICHMENT_RUNNING_STATUSES.has(normalizeStatus(produto?.status_enriquecimento_web))
  ).length;
  const produtosComFalhaNaPagina = produtos.filter((produto) =>
    WEB_ENRICHMENT_FAILURE_STATUSES.has(normalizeStatus(produto?.status_enriquecimento_web))
  ).length;

  const clearSelectionState = useCallback(() => {
    setSelectedProductIds(new Set());
    setSelectionScope('none');
  }, []);

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
    setCurrentPage(0);
    clearSelectionState();
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    clearSelectionState();
  };

  const handleSelectRow = (productId) => {
    setSelectedProductIds((prevSelected) => {
      const newSelection = new Set(prevSelected);
      if (newSelection.has(productId)) {
        newSelection.delete(productId);
      } else {
        newSelection.add(productId);
      }
      return newSelection;
    });
    setSelectionScope('custom');
  };

  const handleSelectAllRows = (isChecked) => {
    if (isChecked) {
      setSelectedProductIds(new Set(produtos.map((produto) => produto.id)));
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
      const response = await productService.getProdutosIds({
        ...queryParams,
        skip: undefined,
        limit: undefined,
      });
      const ids = Array.isArray(response?.ids) ? response.ids : [];
      setSelectedProductIds(new Set(ids));
      setSelectionScope('all');
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao selecionar todos os resultados.'));
    }
  };

  const handleSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
    setCurrentPage(0);
    clearSelectionState();
  };

  const enrichmentSelectionMenuItems = useMemo(() => ([
    {
      key: 'page',
      label: 'Selecionar página atual',
      onClick: () => handleSelectAllRows(true),
      disabled: produtos.length === 0,
    },
    {
      key: 'all',
      label: 'Selecionar todos os resultados da pesquisa',
      onClick: () => void handleSelectAllResults(true),
      disabled: totalProdutosCount === 0,
    },
    {
      key: 'clear',
      label: 'Limpar seleção',
      onClick: clearSelectionState,
      disabled: selectedCount === 0,
    },
  ]), [clearSelectionState, produtos.length, selectedCount, totalProdutosCount]);

  const updateCurrentProdutosData = useCallback((updater) => {
    queryClient.setQueryData(produtosQueryKey, (previous) => {
      const safePrevious = normalizeProductListPayload(previous);
      return {
        ...safePrevious,
        items: updater(safePrevious.items),
      };
    });
  }, [produtosQueryKey, queryClient]);

  const updateLocalProductStatus = (ids, newStatus) => {
    const idSet = new Set(Array.from(ids).map((id) => String(id)));
    updateCurrentProdutosData((prev) =>
      prev.map((produto) => (
        idSet.has(String(produto.id))
          ? { ...produto, status_enriquecimento_web: newStatus }
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
    updateCurrentProdutosData((prev) =>
      prev.map((produtoAtual) => {
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

  const pollWebEnrichmentStatuses = useCallback(async (produtoIds) => {
    const pollRunId = webStatusPollRunRef.current + 1;
    webStatusPollRunRef.current = pollRunId;
    const ids = Array.from(produtoIds).map((id) => String(id));

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
            WEB_ENRICHMENT_WARNING_STATUSES.has(
              String(produto.status_enriquecimento_web || '').toUpperCase()
            )
          );
          if (hasWarnings) {
            showWarningToast(
              'Enriquecimento web finalizado com pendências para os produtos selecionados.'
            );
          } else {
            showSuccessToast('Enriquecimento web finalizado para os produtos selecionados.');
          }
          await queryClient.invalidateQueries({ queryKey: ['produtos'] });
          return;
        }
      }

      await new Promise((resolve) => setTimeout(resolve, WEB_ENRICHMENT_POLL_INTERVAL_MS));
    }

    if (webStatusPollRunRef.current !== pollRunId || !isMountedRef.current) {
      return;
    }
    showInfoToast(
      'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
    );
    await queryClient.invalidateQueries({ queryKey: ['produtos'] });
  }, [fetchRequestedProducts, mergeProdutosById, queryClient]);

  const handleEnrichSelected = async () => {
    setActionLoading(true);
    const idsParaProcessar = Array.from(selectedProductIds);
    clearSelectionState();
    updateLocalProductStatus(new Set(idsParaProcessar), 'PENDENTE');
    const modeLabel = showAiFeatures && usarIAEnriquecimento ? ' com IA' : ' básico';
    showInfoToast(
      `Iniciando enriquecimento web${modeLabel} para ${idsParaProcessar.length} produto(s). Isso ocorrera em segundo plano.`
    );

    const failedIds = new Set();
    const ENRICH_CHUNK = 3;
    for (let i = 0; i < idsParaProcessar.length; i += ENRICH_CHUNK) {
      const chunk = idsParaProcessar.slice(i, i + ENRICH_CHUNK);
      await Promise.all(
        chunk.map(async (produtoId) => {
          try {
            if (showAiFeatures && usarIAEnriquecimento) {
              await productService.iniciarEnriquecimentoWebProduto(produtoId, { usarIA: true });
            } else {
              await productService.iniciarEnriquecimentoWebProduto(produtoId);
            }
          } catch (err) {
            failedIds.add(String(produtoId));
            const errorMsg = extractErrorMessage(
              err,
              `Erro desconhecido ao iniciar enriquecimento para produto ID ${produtoId}.`
            );
            showErrorToast(errorMsg);
            console.error(`Erro ao iniciar enriquecimento para produto ID ${produtoId}:`, err);
            updateLocalProductStatus(new Set([produtoId]), 'FALHA');
          }
        })
      );
    }
    if (!isMountedRef.current) {
      return;
    }
    setActionLoading(false);

    const startedIds = idsParaProcessar.filter((id) => !failedIds.has(String(id)));
    if (startedIds.length > 0) {
      updateLocalProductStatus(new Set(startedIds), 'EM_PROGRESSO');
      void pollWebEnrichmentStatuses(startedIds);
    }
  };

  const handleRowClick = (produto) => {
    logger.log('Produto clicado:', produto);

    if (produto.log_enriquecimento_web?.historico_mensagens?.length > 0) {
      const logMessages = produto.log_enriquecimento_web.historico_mensagens.join('\n');
      notifyWithConsoleLog(`Log de enriquecimento para "${produto.nome_base}"`, logMessages);
      return;
    }

    const currentStatus = String(produto.status_enriquecimento_web || '').toLowerCase();
    if (currentStatus.includes('falha') || currentStatus.includes('erro')) {
      usoIAService.getHistoricoUsoIAPorProduto(produto.id, { limit: 1, skip: 0 })
        .then((historicoProduto) => {
          if (
            historicoProduto &&
            historicoProduto.length > 0 &&
            historicoProduto[0].resultado_gerado
          ) {
            notifyWithConsoleLog(
              `Ultimo erro registrado para "${produto.nome_base}"`,
              historicoProduto[0].resultado_gerado
            );
          } else {
            showInfoToast(
              `Produto "${produto.nome_base}" com status "${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}", sem log detalhado.`
            );
          }
        })
        .catch((err) => {
          console.error('Erro ao buscar historico para detalhes do clique:', err);
          showErrorToast(
            `Produto "${produto.nome_base}" com status "${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}" sem log detalhado.`
          );
        });
      return;
    }

    if (produto.status_enriquecimento_web) {
      showInfoToast(
        `Produto "${produto.nome_base}" com status "${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}".`
      );
    }
  };

  return (
    <div className="app-page-shell ops-page-shell enriquecimento-page-shell">
      <PageHeader title="Enriquecimento" subtitle="Produtos enriquecidos com dados da web" />
      <section className="ops-card ops-toolbar-card enriquecimento-stats-card">
        <div className="ops-metrics-row enriquecimento-metrics-row">
          <OperationalStatChip
            icon={<LuBoxes />}
            label="Na base"
            value={totalProdutosCount}
            tone="neutral"
          />
          <OperationalStatChip
            icon={<LuGlobe />}
            label="Na página"
            value={produtos.length}
            tone="info"
          />
          <OperationalStatChip
            icon={<LuClock3 />}
            label="Em andamento"
            value={produtosEmAndamentoNaPagina}
            tone={produtosEmAndamentoNaPagina > 0 ? 'warn' : 'neutral'}
          />
          <OperationalStatChip
            icon={<LuCircleAlert />}
            label="Com falha"
            value={produtosComFalhaNaPagina}
            tone={produtosComFalhaNaPagina > 0 ? 'danger' : 'success'}
          />
          {selectedCount > 0 ? (
            <OperationalStatChip
              icon={<LuGlobe />}
              label="Selecionados"
              value={selectedCount}
              tone="warn"
            />
          ) : null}
        </div>
      </section>

      <section className="ops-card ops-table-card enriquecimento-table-card">
        <div className="enriquecimento-list-toolbar">
          <div className="ops-search-field enriquecimento-search-field">
            <div className="ops-search-input-wrap">
              <LuSearch />
              <input
                type="text"
                id="search-enr-prod"
                aria-label="Buscar produtos para enriquecer"
                placeholder="Buscar por nome, SKU..."
                value={searchTerm}
                onChange={handleSearchChange}
                disabled={loading || actionLoading}
              />
            </div>
          </div>
          <div className="ops-filters-row enriquecimento-filters-row">
            <select
              value={enrichmentScope}
              onChange={(event) => {
                setEnrichmentScope(event.target.value);
                setCurrentPage(0);
                clearSelectionState();
              }}
              className="ops-select enriquecimento-filter-select"
              disabled={loading || actionLoading}
            >
              <option value="enriched">Enriquecidos</option>
              <option value="all">Todos</option>
              <option value="pending">Pendentes</option>
              <option value="failed">Falharam</option>
            </select>
          </div>
        </div>

        {error && !loadingInitial ? (
          <div className="enriquecimento-error-state" role="alert">
            <p className="error-text">Erro ao carregar produtos: {error}</p>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => void produtosQuery.refetch()}
              disabled={loading || actionLoading}
            >
              Tentar novamente
            </button>
          </div>
        ) : null}

        {selectedCount > 0 ? (
          <div className="ops-selection-bar enriquecimento-selection-bar">
            <div className="ops-selection-copy">
              <p className="ops-selection-summary">{selectionSummary}</p>
              {showAiFeatures ? (
                <label className="ops-inline-toggle">
                  <input
                    type="checkbox"
                    checked={usarIAEnriquecimento}
                    onChange={(event) => setUsarIAEnriquecimento(event.target.checked)}
                    disabled={loading || actionLoading}
                  />
                  Usar IA no enriquecimento web
                </label>
              ) : null}
            </div>
            <div className="ops-selection-actions">
              <button
                onClick={handleEnrichSelected}
                disabled={loading || actionLoading || selectedCount === 0}
                className="btn-secondary btn-sm"
              >
                {actionLoading
                  ? 'Processando...'
                  : `Enriquecer Web${showAiFeatures && usarIAEnriquecimento ? ' + IA' : ''}`}
              </button>
            </div>
          </div>
        ) : null}

        {loadingInitial && (!produtos || produtos.length === 0) ? (
          <LoadingOverlay isOpen={true} message="Carregando produtos para enriquecimento..." />
        ) : (
          <ProductTable
            produtos={produtos}
            selectedProdutos={selectedProductIds}
            onSelectProduto={handleSelectRow}
            onSelectAllProdutos={handleSelectAllRows}
            selectionMenuItems={enrichmentSelectionMenuItems}
            onEdit={handleRowClick}
            loading={loading}
            sortConfig={sortConfig}
            onSort={handleSort}
          />
        )}

        {totalPages > 0 && !error ? (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            isLoading={loading || actionLoading}
          />
        ) : null}

        <p className="enrich-note app-muted-note">
          O status do enriquecimento será atualizado conforme o processo termina no backend.
          {showAiFeatures ? ' Sem marcar a opção de IA, o fluxo roda apenas na versão básica.' : ''}
          {' '}
          Use o ícone de ação para revisar detalhes e logs.
        </p>
      </section>
    </div>
  );
}

export default EnriquecimentoPage;
