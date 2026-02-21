// Frontend/app/src/pages/EnriquecimentoPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import './EnriquecimentoPage.css';
import productService from '../services/productService';
import usoIAService from '../services/usoIAService';
import ProductTable from '../components/produtos/ProductTable';
import PaginationControls from '../components/common/PaginationControls';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications';
import logger from '../utils/logger';

const notifyWithConsoleLog = (title, message) => {
  console.log(`${title}:\n${message}`);
  const truncated = message.length > 200 ? `${message.slice(0, 200)}...` : message;
  showInfoToast(`${title}: ${truncated}`);
};

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

  const totalPages = Math.ceil(totalProdutosCount / limitPerPage);

  const fetchProdutos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        termo_busca: searchTerm || undefined,
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction === 'ascending' ? 'asc' : 'desc',
      };
      const responseData = await productService.getProdutos(params);

      if (responseData && Array.isArray(responseData.items) && typeof responseData.total_items === 'number') {
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

  const checkResultsAndNotify = async (processedProductIds) => {
    await new Promise((resolve) => setTimeout(resolve, 5000));

    let hasFailures = false;

    for (const produtoId of processedProductIds) {
      try {
        const historicoProduto = await usoIAService.getHistoricoUsoIAPorProduto(produtoId, { limit: 1, skip: 0 });
        if (historicoProduto && historicoProduto.length > 0) {
          const ultimoRegistro = historicoProduto[0];
          const tipoGeracao = ultimoRegistro.tipo_geracao || '';
          const resultadoGerado = ultimoRegistro.resultado_gerado || 'Não foi possível obter detalhes do erro.';

          if (tipoGeracao.includes('config_faltante') || tipoGeracao.includes('falha') || tipoGeracao.includes('erro')) {
            const produtoAfetado = produtos.find((p) => p.id === produtoId) || { nome_base: `Produto ID ${produtoId}` };
            showErrorToast(`Enriquecimento para "${produtoAfetado.nome_base}": ${resultadoGerado}`);
            hasFailures = true;
          }
        }
      } catch (apiError) {
        console.error(`Erro ao buscar histórico de IA para produto ${produtoId}:`, apiError);
        showWarningToast(`Não foi possível verificar o resultado final do enriquecimento para o produto ID ${produtoId}.`);
        hasFailures = true;
      }
    }

    fetchProdutos();
    setSelectedProductIds(new Set());

    if (!hasFailures && processedProductIds.length > 0) {
      showSuccessToast(`Processo de enriquecimento concluído para ${processedProductIds.length} produto(s).`);
    }
  };

  const handleEnrichSelected = async () => {
    if (selectedProductIds.size === 0) {
      showWarningToast('Nenhum produto selecionado para enriquecimento.');
      return;
    }

    setActionLoading(true);
    showInfoToast(`Iniciando enriquecimento web para ${selectedProductIds.size} produto(s). Isso ocorrerá em segundo plano.`);

    let requestSuccessCount = 0;
    let requestErrorCount = 0;
    const idsParaVerificar = Array.from(selectedProductIds);

    for (const produtoId of idsParaVerificar) {
      try {
        await productService.iniciarEnriquecimentoWebProduto(produtoId);
        requestSuccessCount += 1;
      } catch (err) {
        requestErrorCount += 1;
        const errorMsg = err && err.detail
          ? typeof err.detail === 'string'
            ? err.detail
            : JSON.stringify(err.detail)
          : err && err.message
            ? err.message
            : `Erro desconhecido ao iniciar enriquecimento para produto ID ${produtoId}.`;
        showErrorToast(errorMsg);
        console.error(`Erro ao iniciar enriquecimento para produto ID ${produtoId}:`, err);
      }
    }
    setActionLoading(false);

    if (requestSuccessCount > 0) {
      checkResultsAndNotify(idsParaVerificar);
    } else if (requestErrorCount > 0) {
      setSelectedProductIds(new Set());
      fetchProdutos();
    } else {
      setSelectedProductIds(new Set());
    }
  };

  const handleRowClick = (produto) => {
    logger.log('Produto clicado:', produto);

    if (produto.log_enriquecimento_web?.historico_mensagens?.length > 0) {
      const logMessages = produto.log_enriquecimento_web.historico_mensagens.join('\n');
      notifyWithConsoleLog(`Log de enriquecimento para "${produto.nome_base}"`, logMessages);
      return;
    }

    if (produto.status_enriquecimento_web && (produto.status_enriquecimento_web.includes('falha') || produto.status_enriquecimento_web.includes('erro'))) {
      usoIAService.getHistoricoUsoIAPorProduto(produto.id, { limit: 1, skip: 0 })
        .then((historicoProduto) => {
          if (historicoProduto && historicoProduto.length > 0 && historicoProduto[0].resultado_gerado) {
            notifyWithConsoleLog(`Último erro registrado para "${produto.nome_base}"`, historicoProduto[0].resultado_gerado);
          } else {
            showInfoToast(`Produto "${produto.nome_base}" com status "${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}", sem log detalhado.`);
          }
        })
        .catch((err) => {
          console.error('Erro ao buscar histórico para detalhes do clique:', err);
          showErrorToast(`Produto "${produto.nome_base}" com status "${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}" sem log detalhado.`);
        });
    } else if (produto.status_enriquecimento_web) {
      showInfoToast(`Produto "${produto.nome_base}" com status "${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}".`);
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

        {totalPages > 0 && !error && (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            isLoading={loading || actionLoading}
          />
        )}

        <div className="table-actions">
          <button
            onClick={handleEnrichSelected}
            disabled={loading || actionLoading || selectedProductIds.size === 0}
            className="btn-info"
          >
            {actionLoading ? 'Processando...' : `Enriquecer Web (${selectedProductIds.size}) selecionado(s)`}
          </button>
        </div>
        <div className="enrich-note app-muted-note">
          O status do enriquecimento será atualizado na tabela conforme o processo ocorre no backend. Clique em uma linha para ver logs.
        </div>
      </div>
    </div>
  );
}

export default EnriquecimentoPage;
