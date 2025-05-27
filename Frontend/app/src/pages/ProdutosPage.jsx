// Frontend/app/src/pages/ProdutosPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import productService from '../services/productService';
import ProductEditModal from '../components/ProductEditModal';
import ProductTable from '../components/produtos/ProductTable';
import NewProductModal from '../components/produtos/NewProductModal';
import PaginationControls from '../components/common/PaginationControls';
import { showSuccessToast, showErrorToast, showWarningToast } from '../utils/notifications'; // Importar as funções de toast

function ProdutosPage() {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalLoading, setModalLoading] = useState(false);
  const [error, setError] = useState(null); // Ainda pode ser útil para um erro geral na página
  const [isNewProductModalOpen, setIsNewProductModalOpen] = useState(false);
  const [selectedProductIds, setSelectedProductIds] = useState([]);

  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(10);
  const [totalProdutosCount, setTotalProdutosCount] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');

  const [editingProduct, setEditingProduct] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const totalPages = Math.ceil(totalProdutosCount / limitPerPage);

  const fetchProdutos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        termo_busca: searchTerm || undefined,
      };
      const responseData = await productService.getProdutos(params);
      
      if (responseData && Array.isArray(responseData.items) && typeof responseData.total_items === 'number') {
        setProdutos(responseData.items);
        setTotalProdutosCount(responseData.total_items); 
      } else {
        console.warn('Formato de dados inesperado recebido para produtos:', responseData);
        setProdutos([]);
        setTotalProdutosCount(0);
        // Não mostra toast aqui, pois o erro de fetch já mostraria um se ocorresse no service ou no catch abaixo
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

  const handleOpenNewProductModal = () => setIsNewProductModalOpen(true);
  const handleCloseNewProductModal = () => {
    if (modalLoading) return;
    setIsNewProductModalOpen(false);
  }

  const handleSaveNewProduct = async (produtoData) => {
    setModalLoading(true);
    let errorMessage = 'Erro desconhecido ao criar produto.';
    try {
      await productService.createProduto(produtoData);
      showSuccessToast('Produto criado com sucesso!'); // <--- USO DO TOAST
      handleCloseNewProductModal();
      // Para ver o novo produto, idealmente iríamos para a última página se não houver busca
      // ou recarregar a primeira/atual dependendo da lógica.
      // Por simplicidade, recarregamos a página atual ou a primeira se não houver busca.
      if (!searchTerm) {
        setCurrentPage(0); // Ou lógica para ir à última página
      }
      fetchProdutos();
      setSelectedProductIds([]);
      return Promise.resolve();
    } catch (saveError) {
      console.error("Objeto de erro recebido em handleSaveNewProduct (ProdutosPage):", saveError); 
      if (saveError && saveError.detail) {
        if (typeof saveError.detail === 'string') {
          errorMessage = saveError.detail;
        } else if (Array.isArray(saveError.detail)) {
          errorMessage = saveError.detail.map(e => `${e.loc ? e.loc.join('.') + ': ' : ''}${e.msg}`).join('; ');
        } else {
            errorMessage = JSON.stringify(saveError.detail);
        }
      } else if (saveError && saveError.message) {
        errorMessage = saveError.message;
      } else if (typeof saveError === 'string') {
        errorMessage = saveError;
      }
      showErrorToast(`Erro ao criar produto: ${errorMessage}`); // <--- USO DO TOAST
      return Promise.reject(saveError);
    } finally {
      setModalLoading(false);
    }
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

  const handleDeleteSelected = async () => {
    if (selectedProductIds.length === 0) {
      showWarningToast("Nenhum produto selecionado para deletar."); // <--- USO DO TOAST
      return;
    }
    if (window.confirm(`Tem certeza que deseja deletar ${selectedProductIds.length} produto(s) selecionado(s)?`)) {
      setLoading(true);
      let successCount = 0;
      let errorOccurred = false;
      try {
        for (const id of selectedProductIds) {
            try {
                await productService.deleteProduto(id);
                successCount++;
            } catch (singleDeleteError) {
                console.error(`Falha ao deletar produto ID ${id}:`, singleDeleteError);
                errorOccurred = true;
            }
        }
        if (successCount > 0) {
            showSuccessToast(`${successCount} produto(s) deletado(s) com sucesso!`); // <--- USO DO TOAST
        }
        if (errorOccurred) {
            showErrorToast(`Alguns produtos não puderam ser deletados. Verifique o console.`); // <--- USO DO TOAST
        }
        
        const newTotalProdutos = totalProdutosCount - successCount;
        const newTotalPages = Math.ceil(newTotalProdutos / limitPerPage);

        if (currentPage >= newTotalPages && newTotalPages > 0) { 
            setCurrentPage(newTotalPages - 1);
        } else if (newTotalProdutos === 0) { 
            setCurrentPage(0);
            setProdutos([]); 
            setTotalProdutosCount(0);
        } else {
             fetchProdutos(); 
        }
        setSelectedProductIds([]);
      } catch (err) { 
        showErrorToast(`Erro ao processar deleção em massa: ${err.message || 'Erro desconhecido'}`); // <--- USO DO TOAST
      } finally {
        setLoading(false);
      }
    }
  };

  const handleGenerateContentForSelected = async (contentType) => {
    if (selectedProductIds.length === 0) {
      showWarningToast(`Nenhum produto selecionado para gerar ${contentType}.`); // <--- USO DO TOAST
      return;
    }
    showInfoToast(`Iniciando geração de ${contentType} para ${selectedProductIds.length} produto(s). Isso pode levar um tempo e acontecerá em segundo plano.`); // <--- USO DO TOAST
    setLoading(true); 
    let hasError = false;
    for (const produtoId of selectedProductIds) {
        try {
            if (contentType === 'titulos') {
                await productService.gerarTitulosProduto(produtoId);
            } else if (contentType === 'descricoes') {
                await productService.gerarDescricaoProduto(produtoId);
            }
        } catch (genError) {
            console.error(`Erro ao solicitar geração de ${contentType} para produto ID ${produtoId}:`, genError);
            let errorMsg = (genError && genError.message) ? genError.message : `Erro desconhecido ao gerar ${contentType} para produto ID ${produtoId}`;
            if (genError && genError.detail) {
                 errorMsg = typeof genError.detail === 'string' ? genError.detail : JSON.stringify(genError.detail);
            }
            showErrorToast(errorMsg); // <--- USO DO TOAST
            hasError = true;
        }
    }
    setLoading(false);
    if (!hasError) {
        showSuccessToast(`Solicitação de geração de ${contentType} enviada para os produtos selecionados! A atualização do status pode demorar alguns instantes.`); // <--- USO DO TOAST
    } else {
        showWarningToast(`Algumas solicitações de geração de ${contentType} falharam. Verifique o console. A atualização dos produtos bem-sucedidos pode demorar.`); // <--- USO DO TOAST
    }
    setSelectedProductIds([]);
    // Opcional: setTimeout(() => fetchProdutos(), 3000); // Pequeno delay para dar tempo ao backend
  };

  const handleRowClick = (produto) => {
    setEditingProduct(produto);
    setIsEditModalOpen(true);
  };

  const handleCloseEditModal = () => {
    if (modalLoading) return;
    setIsEditModalOpen(false);
    setEditingProduct(null);
  };

  const handleSaveProductUpdate = async (productId, updateData) => {
    setModalLoading(true);
    let errorMessage = 'Erro desconhecido ao atualizar produto.';
    try {
      await productService.updateProduto(productId, updateData);
      showSuccessToast('Produto atualizado com sucesso!'); // <--- USO DO TOAST
      handleCloseEditModal();
      fetchProdutos();
      setSelectedProductIds([]);
      return Promise.resolve();
    } catch (updateError) {
      console.error("Objeto de erro recebido em handleSaveProductUpdate (ProdutosPage):", updateError);
      if (updateError && updateError.detail) {
        if (typeof updateError.detail === 'string') {
          errorMessage = updateError.detail;
        } else if (Array.isArray(updateError.detail)) {
          errorMessage = updateError.detail.map(e => `${e.loc ? e.loc.join('.') + ': ' : ''}${e.msg}`).join('; ');
        } else {
            errorMessage = JSON.stringify(updateError.detail);
        }
      } else if (updateError && updateError.message) {
        errorMessage = updateError.message;
      } else if (typeof updateError === 'string') {
        errorMessage = updateError;
      }
      showErrorToast(`Erro ao atualizar produto: ${errorMessage}`); // <--- USO DO TOAST
      return Promise.reject(updateError);
    } finally {
      setModalLoading(false);
    }
  };
  
  return (
    <div>
      <div className="stats-grid">
        <div className="stats-card"><h3>Total de Produtos Registrados</h3><div className="value">{totalProdutosCount}</div></div>
        <div className="stats-card"><h3>Pendentes Enriq. (Página)</h3><div className="value">{produtos.filter(p => p.status_enriquecimento_web === 'pendente' || !p.status_enriquecimento_web).length}</div></div>
        <div className="stats-card"><h3>Enriquecidos Web (Página)</h3><div className="value">{produtos.filter(p => p.status_enriquecimento_web === 'concluido_sucesso').length}</div></div>
      </div>

      <div className="search-container">
        <label htmlFor="search-prod">Buscar Produtos:</label>
        <input
          type="text"
          id="search-prod"
          placeholder="Nome ou SKU..."
          value={searchTerm}
          onChange={handleSearchChange}
          disabled={loading}
        />
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Lista de Produtos</h3>
          <button onClick={handleOpenNewProductModal} disabled={loading || modalLoading}>Novo Produto</button>
        </div>

        <ProductTable
            produtos={produtos}
            selectedIds={selectedProductIds}
            onSelectRow={handleSelectRow}
            onSelectAllRows={handleSelectAllRows}
            onRowClick={handleRowClick}
            isLoading={loading}
        />
        
        {totalPages > 0 && (
            <PaginationControls 
                currentPage={currentPage} 
                totalPages={totalPages} 
                onPageChange={handlePageChange} 
                isLoading={loading} 
            />
        )}
        
        <div className="table-actions">
          <button
            onClick={() => handleGenerateContentForSelected('titulos')}
            disabled={loading || modalLoading || selectedProductIds.length === 0}
          >
            Gerar Títulos (IA)
          </button>
          <button
            onClick={() => handleGenerateContentForSelected('descricoes')}
            disabled={loading || modalLoading || selectedProductIds.length === 0}
          >
            Gerar Descrições (IA)
          </button>
          <button
            onClick={handleDeleteSelected}
            disabled={loading || modalLoading || selectedProductIds.length === 0}
            style={{ backgroundColor: 'var(--danger)'}}
          >
            Deletar Selecionado(s)
          </button>
        </div>
      </div>

      <NewProductModal
        isOpen={isNewProductModalOpen}
        onClose={handleCloseNewProductModal}
        onSave={handleSaveNewProduct}
        isLoading={modalLoading}
      />

      <ProductEditModal
        isOpen={isEditModalOpen}
        onClose={handleCloseEditModal}
        productData={editingProduct}
        onSave={handleSaveProductUpdate}
        isLoading={modalLoading}
      />
    </div>
  );
}

export default ProdutosPage;