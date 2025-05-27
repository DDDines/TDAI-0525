// Frontend/app/src/pages/EnriquecimentoPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import productService from '../services/productService'; // Usaremos para buscar produtos e iniciar enriquecimento
import ProductTable from '../components/produtos/ProductTable'; // Reutilizaremos a tabela de produtos
import PaginationControls from '../components/common/PaginationControls';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications';

function EnriquecimentoPage() {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false); // Para o botão de enriquecer
  const [error, setError] = useState(null);
  const [selectedProductIds, setSelectedProductIds] = useState([]);

  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(10); // Pode ajustar conforme preferir
  const [totalProdutosCount, setTotalProdutosCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');

  const totalPages = Math.ceil(totalProdutosCount / limitPerPage);

  const fetchProdutos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        termo_busca: searchTerm || undefined,
        // Poderíamos adicionar filtro por status_enriquecimento aqui se quiséssemos
        // status_enriquecimento: 'pendente', // Por exemplo
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
      showErrorToast(errorMsg);
      setProdutos([]);
      setTotalProdutosCount(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, limitPerPage, searchTerm]);

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
    setSelectedProductIds(prevSelected =>
      prevSelected.includes(productId)
        ? prevSelected.filter(id => id !== productId)
        : [...prevSelected, productId]
    );
  };

  const handleSelectAllRows = (event) => {
    if (event.target.checked) {
      setSelectedProductIds(produtos.map(p => p.id));
    } else {
      setSelectedProductIds([]);
    }
  };

  const handleEnrichSelected = async () => {
    if (selectedProductIds.length === 0) {
      showWarningToast("Nenhum produto selecionado para enriquecimento.");
      return;
    }

    setActionLoading(true);
    showInfoToast(`Iniciando enriquecimento web para ${selectedProductIds.length} produto(s). Isso pode levar um tempo e acontecerá em segundo plano.`);

    let successCount = 0;
    let errorCount = 0;

    for (const produtoId of selectedProductIds) {
      try {
        // Precisamos adicionar a função ao productService.js
        await productService.iniciarEnriquecimentoWebProduto(produtoId);
        successCount++;
      } catch (err) {
        errorCount++;
        const errorMsg = (err && err.detail) ? (typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))
                       : (err && err.message) ? err.message
                       : `Erro desconhecido ao iniciar enriquecimento para produto ID ${produtoId}.`;
        showErrorToast(errorMsg);
        console.error(`Erro ao iniciar enriquecimento para produto ID ${produtoId}:`, err);
      }
    }
    setActionLoading(false);
    setSelectedProductIds([]);

    if (successCount > 0) {
      showSuccessToast(`${successCount} processo(s) de enriquecimento iniciado(s) com sucesso! O status dos produtos será atualizado em breve.`);
      // Opcional: Adicionar um pequeno delay e chamar fetchProdutos() para tentar atualizar a lista
      setTimeout(() => fetchProdutos(), 5000); // Espera 5 segundos
    }
    if (errorCount > 0) {
      showWarningToast(`${errorCount} processo(s) de enriquecimento falharam ao iniciar. Verifique os detalhes e os logs do servidor.`);
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
          {/* <button onClick={handleOpenNewProductModal} disabled={loading || modalLoading}>Novo Produto</button> // Não aplicável aqui */}
        </div>

        {error && <p style={{ color: 'red' }}>Erro ao carregar produtos: {error}</p>}

        <ProductTable
            produtos={produtos}
            selectedIds={selectedProductIds}
            onSelectRow={handleSelectRow}
            onSelectAllRows={handleSelectAllRows}
            // onRowClick={handleRowClick} // Talvez não precise de modal de edição aqui, ou um diferente
            isLoading={loading}
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
            disabled={loading || actionLoading || selectedProductIds.length === 0}
            style={{backgroundColor: 'var(--info)'}} // Cor diferente para ação de enriquecer
          >
            {actionLoading ? 'Processando...' : `Enriquecer Web (${selectedProductIds.length}) Selecionado(s)`}
          </button>
        </div>
        <div style={{fontSize: '.9rem', color: '#777', textAlign: 'right', marginTop: '1rem'}}>
            * O status do enriquecimento será atualizado na tabela conforme o processo ocorre no backend.
        </div>
      </div>
    </div>
  );
}

export default EnriquecimentoPage;