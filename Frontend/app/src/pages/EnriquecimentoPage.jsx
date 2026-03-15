/**
 * Module enriquecimento page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useCallback, useMemo, useState } from 'react';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import './EnriquecimentoPage.css';
import productService from '../services/productService';
import usoIAService from '../services/usoIAService';
import ProductTable from '../components/produtos/ProductTable';
import PaginationControls from '../components/common/PaginationControls';
import {
  showSuccessToast,
  showErrorToast,
  showInfoToast,
} from '../utils/notifications';
import logger from '../utils/logger';
import { extractErrorMessage } from '../utils/errorDetails';
import { queryKeys } from '../lib/queryKeys.js';
import { useAppExperience } from '../contexts/AppExperienceContext.jsx';

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
    return `${selectedCount} item(ns) selecionado(s) (pagina atual)`;
  }
  return `${selectedCount} item(ns) selecionado(s) (selecao manual)`;
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
  const queryClient = useQueryClient();

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
  const loading = produtosQuery.isLoading || produtosQuery.isFetching;
  const error = produtosQuery.error
    ? extractErrorMessage(produtosQuery.error, 'Falha ao buscar produtos.')
    : null;
  const totalPages = Math.ceil(totalProdutosCount / limitPerPage);
  const selectedCount = selectedProductIds.size;
  const selectionSummary = formatSelectionSummary(selectedCount, selectionScope);
  const canSelectAllFilteredResults =
    selectedCount > 0
    && selectionScope !== 'all'
    && totalProdutosCount > selectedCount;
  const canReduceSelectionToPage =
    selectionScope === 'all'
    && produtos.length > 0;

  const clearSelectionState = useCallback(() => {
    setSelectedProductIds(new Set());
    setSelectionScope('none');
  }, []);

  const refreshProdutos = useCallback(async () => {
    await produtosQuery.refetch();
  }, [produtosQuery]);

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
      showErrorToast(error.message || 'Falha ao selecionar todos os resultados.');
    }
  };

  const handleSelectCurrentPageOnly = useCallback(() => {
    if (!produtos.length) {
      clearSelectionState();
      return;
    }
    setSelectedProductIds(new Set(produtos.map((produto) => produto.id)));
    setSelectionScope('page');
  }, [clearSelectionState, produtos]);

  const handleSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
    setCurrentPage(0);
    clearSelectionState();
  };

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
          showSuccessToast('Enriquecimento web finalizado para os produtos selecionados.');
          await queryClient.invalidateQueries({ queryKey: ['produtos'] });
          return;
        }
      }

      await new Promise((resolve) => setTimeout(resolve, WEB_ENRICHMENT_POLL_INTERVAL_MS));
    }

    showInfoToast(
      'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
    );
    await queryClient.invalidateQueries({ queryKey: ['produtos'] });
  }, [mergeProdutosById, queryClient]);

  const handleEnrichSelected = async () => {
    setActionLoading(true);
    const idsParaProcessar = Array.from(selectedProductIds);
    clearSelectionState();
    updateLocalProductStatus(new Set(idsParaProcessar), 'PENDENTE');
    const modeLabel = showAiFeatures && usarIAEnriquecimento ? ' com IA' : ' basico';
    showInfoToast(
      `Iniciando enriquecimento web${modeLabel} para ${idsParaProcessar.length} produto(s). Isso ocorrera em segundo plano.`
    );

    const failedIds = new Set();
    await Promise.all(
      idsParaProcessar.map(async (produtoId) => {
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
    setActionLoading(false);

    const startedIds = idsParaProcessar.filter((id) => !failedIds.has(String(id)));
    if (startedIds.length > 0) {
      updateLocalProductStatus(new Set(startedIds), 'EM_PROGRESSO');
      void pollWebEnrichmentStatuses(startedIds);
      return;
    }

    await refreshProdutos();
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
    <div className="app-page-shell enriquecimento-page-shell">
      <div className="app-toolbar-card">
        <div className="search-container enrich-search-row">
          <label htmlFor="search-enr-prod">Buscar produtos para enriquecer:</label>
          <input
            type="text"
            id="search-enr-prod"
            placeholder="Nome, SKU..."
            value={searchTerm}
            onChange={handleSearchChange}
            disabled={loading || actionLoading}
          />
          <select
            value={enrichmentScope}
            onChange={(event) => {
              setEnrichmentScope(event.target.value);
              setCurrentPage(0);
              clearSelectionState();
            }}
            disabled={loading || actionLoading}
          >
            <option value="enriched">Enriquecidos</option>
            <option value="all">Todos</option>
            <option value="pending">Pendentes</option>
            <option value="failed">Falharam</option>
          </select>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Produtos para Enriquecimento Web</h3>
        </div>

        {error && !loading ? <p className="error-text">Erro ao carregar produtos: {error}</p> : null}

        {selectionSummary ? (
          <div className="ops-selection-bar">
            <div className="ops-selection-copy">
              <p className="ops-selection-summary">{selectionSummary}</p>
              {canSelectAllFilteredResults ? (
                <button
                  type="button"
                  className="ops-selection-inline-action"
                  onClick={() => void handleSelectAllResults(true)}
                >
                  Selecionar todos os {totalProdutosCount} resultados
                </button>
              ) : null}
              {canReduceSelectionToPage ? (
                <button
                  type="button"
                  className="ops-selection-inline-action"
                  onClick={handleSelectCurrentPageOnly}
                >
                  Manter apenas os {produtos.length} itens desta pagina
                </button>
              ) : null}
            </div>
          </div>
        ) : null}

        <ProductTable
          produtos={produtos}
          selectedProdutos={selectedProductIds}
          onSelectProduto={handleSelectRow}
          onSelectAllProdutos={handleSelectAllRows}
          onEdit={handleRowClick}
          loading={loading}
          sortConfig={sortConfig}
          onSort={handleSort}
        />

        {totalPages > 0 && !error ? (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            isLoading={loading || actionLoading}
          />
        ) : null}

        <div className="table-actions">
          {showAiFeatures ? (
            <label className="app-muted-note" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="checkbox"
                checked={usarIAEnriquecimento}
                onChange={(event) => setUsarIAEnriquecimento(event.target.checked)}
                disabled={loading || actionLoading}
              />
              Usar IA no enriquecimento web
            </label>
          ) : null}
          <button
            onClick={handleEnrichSelected}
            disabled={loading || actionLoading || selectedCount === 0}
            className="btn-info"
          >
            {actionLoading
              ? 'Processando...'
              : `Enriquecer Web${showAiFeatures && usarIAEnriquecimento ? ' + IA' : ''} (${selectedCount}) selecionado(s)`}
          </button>
        </div>
        <div className="enrich-note app-muted-note">
          O status do enriquecimento sera atualizado na tabela conforme o processo ocorre no backend.
          {showAiFeatures ? ' Sem marcar a opcao de IA, o fluxo roda apenas na versao basica.' : ''}
          Clique em uma linha para ver logs.
        </div>
      </div>
    </div>
  );
}

export default EnriquecimentoPage;
