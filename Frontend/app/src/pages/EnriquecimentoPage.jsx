// Frontend/app/src/pages/EnriquecimentoPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import productService from '../services/productService';
import usoIAService from '../services/usoIAService';
import ProductTable from '../components/produtos/ProductTable';
import PaginationControls from '../components/common/PaginationControls';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications';
import logger from '../utils/logger';

function EnriquecimentoPage() {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  // FIX: Inicializar selectedProductIds como um Set
  const [selectedProductIds, setSelectedProductIds] = useState(new Set()); 

  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(10);
  const [totalProdutosCount, setTotalProdutosCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  
  // ADICIONADO: Estado para configuração de ordenação
  const [sortConfig, setSortConfig] = useState({ key: 'id', direction: 'descending' }); 

  const totalPages = Math.ceil(totalProdutosCount / limitPerPage);

  // Função para buscar produtos (mantida para atualizar a tabela)
  const fetchProdutos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        termo_busca: searchTerm || undefined,
        sort_by: sortConfig.key,      // ADICIONADO: Parâmetro de ordenação
        sort_order: sortConfig.direction === 'ascending' ? 'asc' : 'desc', // ADICIONADO: Parâmetro de ordem
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
      const errorMsg = (err && err.message) ? err.message : 'Falha ao buscar produtos.';
      setError(errorMsg);
      setProdutos([]);
      setTotalProdutosCount(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, limitPerPage, searchTerm, sortConfig]); // sortConfig adicionado às dependências

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
    setSelectedProductIds(prevSelected => {
      const newSelection = new Set(prevSelected);
      if (newSelection.has(productId)) {
        newSelection.delete(productId);
      } else {
        newSelection.add(productId);
      }
      return newSelection;
    });
  };

  const handleSelectAllRows = (event) => {
    if (event.target.checked) {
      setSelectedProductIds(new Set(produtos.map(p => p.id)));
    } else {
      setSelectedProductIds(new Set());
    }
  };

  // ADICIONADO: Função para lidar com a ordenação da tabela
  const handleSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
    setCurrentPage(0); // Reset page on sort
  };

  // Função para verificar o histórico e notificar
  const checkResultsAndNotify = async (processedProductIds) => {
    // Dá um tempo para o backend processar e gravar no histórico
    await new Promise(resolve => setTimeout(resolve, 5000)); // 5 segundos de delay, ajuste se necessário

    let hasFailures = false;

    for (const produtoId of processedProductIds) {
      try {
        const historicoProduto = await usoIAService.getHistoricoUsoIAPorProduto(produtoId, { limit: 1, skip: 0 });
        if (historicoProduto && historicoProduto.length > 0) {
          const ultimoRegistro = historicoProduto[0];
          const tipoGeracao = ultimoRegistro.tipo_geracao || "";
          const resultadoGerado = ultimoRegistro.resultado_gerado || "Não foi possível obter detalhes do erro.";

          // Identifica se o tipo de geração indica uma falha de configuração ou erro
          if (tipoGeracao.includes('config_faltante') || tipoGeracao.includes('falha') || tipoGeracao.includes('erro')) {
            const produtoAfetado = produtos.find(p => p.id === produtoId) || { nome_base: `Produto ID ${produtoId}` };
            showErrorToast(`Enriquecimento para \"${produtoAfetado.nome_base}\": ${resultadoGerado}`);
            hasFailures = true;
          } else {
            // Pode adicionar um toast de sucesso aqui se quiser, mas pode ser redundante se a tabela atualizar bem
            // showSuccessToast(`Enriquecimento para "${produtoAfetado.nome_base}" processado.`);
          }
        }
      } catch (error) {
        console.error(`Erro ao buscar histórico de IA para produto ${produtoId}:`, error);
        showWarningToast(`Não foi possível verificar o resultado final do enriquecimento para o produto ID ${produtoId}. Verifique a tabela ou o histórico mais tarde.`);
        hasFailures = true;
      }
    }

    // Atualiza a tabela de produtos para refletir qualquer mudança de status
    fetchProdutos();
    setSelectedProductIds(new Set()); // Limpa a seleção após a verificação
    
    if (!hasFailures && processedProductIds.length > 0) {
        showSuccessToast(`Processo de enriquecimento concluído para ${processedProductIds.length} produto(s). Verifique os status na tabela.`);
    }
  };

  const handleEnrichSelected = async () => {
    if (selectedProductIds.size === 0) { // Usar .size para Set
      showWarningToast("Nenhum produto selecionado para enriquecimento.");
      return;
    }

    setActionLoading(true);
    showInfoToast(`Iniciando enriquecimento web para ${selectedProductIds.size} produto(s). Isso pode levar um tempo e acontecerá em segundo plano.`);

    let requestSuccessCount = 0;
    let requestErrorCount = 0;
    const idsParaVerificar = Array.from(selectedProductIds); // Converte Set para Array para iterar

    for (const produtoId of idsParaVerificar) {
      try {
        await productService.iniciarEnriquecimentoWebProduto(produtoId);
        requestSuccessCount++;
      } catch (err) {
        requestErrorCount++;
        const errorMsg = (err && err.detail) ? (typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))
                       : (err && err.message) ? err.message
                       : `Erro desconhecido ao iniciar enriquecimento para produto ID ${produtoId}.`;
        showErrorToast(errorMsg); // Mostra erro ao tentar iniciar a tarefa
        console.error(`Erro ao iniciar enriquecimento para produto ID ${produtoId}:`, err);
      }
    }
    setActionLoading(false);

    if (requestSuccessCount > 0) {
      checkResultsAndNotify(idsParaVerificar); // Passa a lista completa de IDs que foram processados
    } else if (requestErrorCount > 0 && requestSuccessCount === 0) {
      setSelectedProductIds(new Set()); // Limpa a seleção
      fetchProdutos(); // Atualiza a tabela, embora provavelmente não haja mudança de status por esta ação
    } else {
        setSelectedProductIds(new Set()); 
    }
  };

  const handleRowClick = (produto) => {
    logger.log("Produto clicado:", produto);
    // Tenta mostrar o log do enriquecimento web primeiro
    if (produto.log_enriquecimento_web && produto.log_enriquecimento_web.historico_mensagens && produto.log_enriquecimento_web.historico_mensagens.length > 0) {
      const logMessages = produto.log_enriquecimento_web.historico_mensagens.join("\n");
      alert(`Log de Enriquecimento para \"${produto.nome_base}\":\n--------------------------------------\n${logMessages}`);
    } 
    // Se não houver log de enriquecimento, tenta mostrar o último erro do histórico de IA
    else if (produto.status_enriquecimento_web && 
             (produto.status_enriquecimento_web.includes('falha') || produto.status_enriquecimento_web.includes('erro'))) {
      usoIAService.getHistoricoUsoIAPorProduto(produto.id, { limit: 1, skip: 0 }) 
        .then(historicoProduto => {
          if (historicoProduto && historicoProduto.length > 0 && historicoProduto[0].resultado_gerado) {
            alert(`Último erro registado para \"${produto.nome_base}\":\n--------------------------------------\n${historicoProduto[0].resultado_gerado}`);
          } else {
            alert(`Produto \"${produto.nome_base}\" com status \"${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}\", mas sem log detalhado disponível.`);
          }
        })
        .catch(err => {
          console.error("Erro ao buscar histórico para detalhes do clique:", err);
          alert(`Produto \"${produto.nome_base}\" com status \"${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}\". Não foi possível carregar o log detalhado.`);
        });
    } else if (produto.status_enriquecimento_web) {
        alert(`Produto \"${produto.nome_base}\" com status \"${String(produto.status_enriquecimento_web).replace(/_/g, ' ')}\".`);
    }
  };

  return (
    <div>
      <div className="search-container" style={{ marginTop: 0, marginBottom: '1.5rem' }}>
        <label htmlFor="search-enr-prod">Buscar Produtos para Enriquecer:</label>
        <input
          type="text"
          id="search-enr-prod"
          placeholder="Nome, SKU..."
          value={searchTerm}
          onChange={handleSearchChange}
          disabled={loading || actionLoading}
        />
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Produtos para Enriquecimento Web</h3>
        </div>

        {error && !loading && <p style={{ color: 'red', padding: '1rem' }}>Erro ao carregar produtos: {error}</p>}

        <ProductTable
            produtos={produtos}
            selectedProdutos={selectedProductIds} // Passa como Set
            onSelectProduto={handleSelectRow}
            onSelectAllProdutos={handleSelectAllRows}
            // onEdit={handleRowClick} // Old line
            // FIX: Corrected comment syntax
            onEdit={handleRowClick} 
            isLoading={loading}
            sortConfig={sortConfig} // ADICIONADO: Passando a configuração de ordenação
            onSort={handleSort}     // ADICIONADO: Passando a função de ordenação
        />

        {totalPages > 0 && !error && (
            <PaginationControls
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={handlePageChange}
                isLoading={loading || actionLoading}
            />
        )}

        <div className="table-actions" style={{ marginTop: '1.5rem' }}>
          <button
            onClick={handleEnrichSelected}
            disabled={loading || actionLoading || selectedProductIds.size === 0} // Usar .size
            style={{backgroundColor: 'var(--info)'}}
          >
            {actionLoading ? 'Processando...' : `Enriquecer Web (${selectedProductIds.size}) Selecionado(s)`}
          </button>
        </div>
        <div style={{fontSize: '.9rem', color: '#777', textAlign: 'right', marginTop: '1rem'}}>
            * O status do enriquecimento será atualizado na tabela conforme o processo ocorre no backend. Clique numa linha para ver logs (se disponíveis).
        </div>
      </div>
    </div>
  );
}

export default EnriquecimentoPage;
