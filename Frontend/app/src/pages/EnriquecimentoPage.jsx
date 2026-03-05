/**
 * Module enriquecimento page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useState, useEffect, useCallback } from 'react';
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

function EnriquecimentoPage() {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedProductIds, setSelectedProductIds] = useState(new Set());

  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(10);
  const [totalProdutosCount, setTotalProdutosCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'id', direction: 'descending' });
  const webStatusPollRunRef = React.useRef(0);

  const totalPages = Math.ceil(totalProdutosCount / limitPerPage);

  const fetchProdutos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        search: searchTerm || undefined,
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction === 'ascending' ? 'asc' : 'desc',
      };
      const responseData = await productService.getProdutos(params);

      if (
        responseData &&
        Array.isArray(responseData.items) &&
        typeof responseData.total_items === 'number'
      ) {
        setProdutos(responseData.items);
        setTotalProdutosCount(responseData.total_items);
      } else {
        console.warn('Formato de dados inesperado recebido para produtos:', responseData);
        setProdutos([]);
        setTotalProdutosCount(0);
      }
    } catch (err) {
      const errorMsg = err && err.message ? err.message : 'Falha ao buscar produtos.';
      setError(errorMsg);
      setProdutos([]);
      setTotalProdutosCount(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, limitPerPage, searchTerm, sortConfig]);

  useEffect(() => {
    fetchProdutos();
  }, [fetchProdutos]);

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
    setCurrentPage(0);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
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
  };

  const handleSelectAllRows = (isChecked) => {
    if (isChecked) {
      setSelectedProductIds(new Set(produtos.map((p) => p.id)));
    } else {
      setSelectedProductIds(new Set());
    }
  };

  const handleSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
    setCurrentPage(0);
  };

  const updateLocalProductStatus = (ids, newStatus) => {
    const idSet = new Set(Array.from(ids).map((id) => String(id)));
    setProdutos((prev) =>
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
    setProdutos((prev) =>
      prev.map((produtoAtual) => {
        const fresh = fetchedMap.get(String(produtoAtual.id));
        return fresh ? { ...produtoAtual, ...fresh } : produtoAtual;
      })
    );
  }, []);

  const pollWebEnrichmentStatuses = useCallback(async (produtoIds) => {
    const pollRunId = webStatusPollRunRef.current + 1;
    webStatusPollRunRef.current = pollRunId;
    const ids = Array.from(produtoIds).map((id) => String(id));
    if (ids.length === 0) {
      return;
    }

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
          fetchProdutos();
          return;
        }
      }

      await new Promise((resolve) => setTimeout(resolve, WEB_ENRICHMENT_POLL_INTERVAL_MS));
    }

    showInfoToast(
      'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
    );
    fetchProdutos();
  }, [fetchProdutos, mergeProdutosById]);

  const handleEnrichSelected = async () => {
    if (selectedProductIds.size === 0) {
      showWarningToast('Nenhum produto selecionado para enriquecimento.');
      return;
    }

    setActionLoading(true);
    const idsParaProcessar = Array.from(selectedProductIds);
    setSelectedProductIds(new Set());
    updateLocalProductStatus(new Set(idsParaProcessar), 'PENDENTE');
    showInfoToast(
      `Iniciando enriquecimento web para ${idsParaProcessar.length} produto(s). Isso ocorrera em segundo plano.`
    );

    const failedIds = new Set();
    await Promise.all(
      idsParaProcessar.map(async (produtoId) => {
        try {
          await productService.iniciarEnriquecimentoWebProduto(produtoId);
        } catch (err) {
          failedIds.add(String(produtoId));
          const errorMsg = err && err.message
            ? err.message
            : `Erro desconhecido ao iniciar enriquecimento para produto ID ${produtoId}.`;
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

    fetchProdutos();
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
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Produtos para Enriquecimento Web</h3>
        </div>

        {error && !loading && <p className="error-text">Erro ao carregar produtos: {error}</p>}

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
          <button
            onClick={handleEnrichSelected}
            disabled={loading || actionLoading || selectedProductIds.size === 0}
            className="btn-info"
          >
            {actionLoading
              ? 'Processando...'
              : `Enriquecer Web (${selectedProductIds.size}) selecionado(s)`}
          </button>
        </div>
        <div className="enrich-note app-muted-note">
          O status do enriquecimento sera atualizado na tabela conforme o processo ocorre no backend.
          Clique em uma linha para ver logs.
        </div>
      </div>
    </div>
  );
}

export default EnriquecimentoPage;

