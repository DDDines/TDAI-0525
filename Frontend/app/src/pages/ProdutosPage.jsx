// Frontend/app/src/pages/ProdutosPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import productService from '../services/productService';
import ProductEditModal from '../components/ProductEditModal';
import ProductTable from '../components/produtos/ProductTable';
import NewProductModal from '../components/produtos/NewProductModal';
import PaginationControls from '../components/common/PaginationControls';
import { showSuccessToast, showErrorToast, showWarningToast, showInfoToast } from '../utils/notifications';

// Opções para os filtros de status
const statusEnriquecimentoWebOptions = [
  { value: "", label: "Todos Status Enriq. Web" },
  { value: "PENDENTE", label: "Pendente (Web)" },
  { value: "EM_PROGRESSO", label: "Em Progresso (Web)" },
  { value: "CONCLUIDO_SUCESSO", label: "Sucesso (Web)" },
  { value: "FALHOU", label: "Falhou (Web)" },
  { value: "NENHUMA_FONTE_ENCONTRADA", label: "Fonte Ñ Encontrada (Web)" },
  { value: "CONCLUIDO_COM_DADOS_PARCIAIS", label: "Parcial (Web)" },
  { value: "FALHA_CONFIGURACAO_API_EXTERNA", label: "Falha Config API (Web)" },
  { value: "FALHA_API_EXTERNA", label: "Falha API (Web)" },
];

const statusGeracaoIAOptions = [
  { value: "", label: "Todos Status IA" },
  { value: "NAO_SOLICITADO", label: "Não Solicitado (IA)" },
  { value: "PENDENTE", label: "Pendente (IA)" },
  { value: "EM_PROGRESSO", label: "Em Progresso (IA)" },
  { value: "CONCLUIDO_SUCESSO", label: "Sucesso (IA)" },
  { value: "FALHOU", label: "Falhou (IA)" },
  { value: "FALHA_CONFIGURACAO_IA", label: "Falha Config (IA)" },
  { value: "LIMITE_ATINGIDO", label: "Limite Atingido (IA)" },
];


function ProdutosPage() {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true); // Loading da tabela principal
  const [actionLoading, setActionLoading] = useState(false); // Loading para ações como enriquecer, gerar IA
  const [modalLoading, setModalLoading] = useState(false);
  const [error, setError] = useState(null); 
  const [isNewProductModalOpen, setIsNewProductModalOpen] = useState(false);
  const [selectedProductIds, setSelectedProductIds] = useState([]);

  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(10);
  const [totalProdutosCount, setTotalProdutosCount] = useState(0);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatusEnriquecimento, setSelectedStatusEnriquecimento] = useState('');
  const [selectedStatusTituloIA, setSelectedStatusTituloIA] = useState('');
  const [selectedStatusDescricaoIA, setSelectedStatusDescricaoIA] = useState('');

  const [editingProduct, setEditingProduct] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const totalPages = Math.ceil(totalProdutosCount / limitPerPage);

  const fetchProdutos = useCallback(async () => {
    setLoading(true); // Loading principal da tabela
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        termo_busca: searchTerm || undefined,
        status_enriquecimento: selectedStatusEnriquecimento || undefined,
        status_titulo_ia: selectedStatusTituloIA || undefined,
        status_descricao_ia: selectedStatusDescricaoIA || undefined,
      };
      const responseData = await productService.getProdutos(params);
      
      if (responseData && Array.isArray(responseData.items) && typeof responseData.total_items === 'number') {
        setProdutos(responseData.items);
        setTotalProdutosCount(responseData.total_items); 
      } else {
        console.warn('Formato de dados inesperado recebido para produtos:', responseData);
        setProdutos([]); setTotalProdutosCount(0);
      }
    } catch (err) {
      const errorMsg = (err && err.message) ? err.message : 'Falha ao buscar produtos.';
      setError(errorMsg); 
      showErrorToast(errorMsg); 
      setProdutos([]); setTotalProdutosCount(0);
    } finally {
      setLoading(false); // Finaliza loading principal
    }
  }, [currentPage, limitPerPage, searchTerm, selectedStatusEnriquecimento, selectedStatusTituloIA, selectedStatusDescricaoIA]);

  useEffect(() => {
    fetchProdutos();
  }, [fetchProdutos]);

  const handleFilterChange = (setterFunction, value) => {
    setterFunction(value);
    setCurrentPage(0); 
  };

  const handleSearchChange = (event) => {
    handleFilterChange(setSearchTerm, event.target.value);
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
      showSuccessToast('Produto criado com sucesso!');
      handleCloseNewProductModal();
      if (!searchTerm && !selectedStatusEnriquecimento && !selectedStatusTituloIA && !selectedStatusDescricaoIA) {
        setCurrentPage(0); 
      }
      fetchProdutos();
      setSelectedProductIds([]);
      return Promise.resolve();
    } catch (saveError) {
      console.error("Objeto de erro recebido em handleSaveNewProduct (ProdutosPage):", saveError); 
      if (saveError && saveError.detail) {
        if (typeof saveError.detail === 'string') errorMessage = saveError.detail;
        else if (Array.isArray(saveError.detail)) errorMessage = saveError.detail.map(e => `${e.loc ? e.loc.join('.') + ': ' : ''}${e.msg}`).join('; ');
        else errorMessage = JSON.stringify(saveError.detail);
      } else if (saveError && saveError.message) errorMessage = saveError.message;
      else if (typeof saveError === 'string') errorMessage = saveError;
      showErrorToast(`Erro ao criar produto: ${errorMessage}`);
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
      showWarningToast("Nenhum produto selecionado para deletar."); return;
    }
    if (window.confirm(`Tem certeza que deseja deletar ${selectedProductIds.length} produto(s) selecionado(s)?`)) {
      setActionLoading(true); // Inicia loading da ação
      let successCount = 0; let errorOccurred = false;
      try {
        for (const id of selectedProductIds) {
            try { await productService.deleteProduto(id); successCount++; } 
            catch (singleDeleteError) { console.error(`Falha ao deletar produto ID ${id}:`, singleDeleteError); errorOccurred = true; }
        }
        if (successCount > 0) showSuccessToast(`${successCount} produto(s) deletado(s) com sucesso!`);
        if (errorOccurred) showErrorToast(`Alguns produtos não puderam ser deletados. Verifique o console.`);
        
        const newTotalProdutos = totalProdutosCount - successCount;
        const newTotalPages = Math.ceil(newTotalProdutos / limitPerPage);
        if (currentPage >= newTotalPages && newTotalPages > 0) setCurrentPage(newTotalPages - 1);
        else if (newTotalProdutos === 0) { setCurrentPage(0); setProdutos([]); setTotalProdutosCount(0); }
        else fetchProdutos(); 
        setSelectedProductIds([]);
      } catch (err) { 
        showErrorToast(`Erro ao processar deleção em massa: ${err.message || 'Erro desconhecido'}`);
      } finally {
        setActionLoading(false); // Finaliza loading da ação
      }
    }
  };

  const handleGenerateContentForSelected = async (contentType) => {
    if (selectedProductIds.length === 0) {
      showWarningToast(`Nenhum produto selecionado para gerar ${contentType}.`); return;
    }
    showInfoToast(`Iniciando geração de ${contentType} para ${selectedProductIds.length} produto(s). Isso pode levar um tempo e acontecerá em segundo plano.`);
    setActionLoading(true); 
    let успіхRequests = 0; // contador de sucessos na solicitação
    let errorRequests = 0; // contador de erros na solicitação

    for (const produtoId of selectedProductIds) {
        try {
            if (contentType === 'titulos') await productService.gerarTitulosProduto(produtoId);
            else if (contentType === 'descricoes') await productService.gerarDescricaoProduto(produtoId);
            успіхRequests++;
        } catch (genError) {
            errorRequests++;
            console.error(`Erro ao solicitar geração de ${contentType} para produto ID ${produtoId}:`, genError);
            let errorMsg = (genError && genError.message) ? genError.message : `Erro desconhecido ao gerar ${contentType} para produto ID ${produtoId}`;
            if (genError && genError.detail) errorMsg = typeof genError.detail === 'string' ? genError.detail : JSON.stringify(genError.detail);
            showErrorToast(errorMsg); 
        }
    }
    setActionLoading(false);
    if (успіхRequests > 0) {
      showSuccessToast(`${успіхRequests} solicitação(ões) de geração de ${contentType} enviada(s)! A atualização do status pode demorar.`);
    }
    if (errorRequests > 0) {
      showWarningToast(`${errorRequests} solicitação(ões) de geração de ${contentType} falharam ao enviar. Verifique o console.`);
    }
    setSelectedProductIds([]);
    // Adiciona um pequeno delay para dar tempo ao backend de mudar o status para "EM_PROGRESSO"
    setTimeout(() => fetchProdutos(), 2000); 
  };

  // NOVA FUNÇÃO PARA ENRIQUECER WEB
  const handleEnrichSelectedWeb = async () => {
    if (selectedProductIds.length === 0) {
      showWarningToast("Nenhum produto selecionado para enriquecimento web.");
      return;
    }
    showInfoToast(`Iniciando enriquecimento web para ${selectedProductIds.length} produto(s). O processo ocorre em segundo plano e pode levar alguns minutos.`);
    setActionLoading(true);
    let requestSuccessCount = 0;
    let requestErrorCount = 0;

    for (const produtoId of selectedProductIds) {
      try {
        await productService.iniciarEnriquecimentoWebProduto(produtoId);
        requestSuccessCount++;
      } catch (err) {
        requestErrorCount++;
        const errorMsg = (err && err.detail) 
                       ? (typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail))
                       : (err && err.message) 
                       ? err.message 
                       : `Erro desconhecido ao iniciar enriquecimento para produto ID ${produtoId}.`;
        showErrorToast(errorMsg);
        console.error(`Erro ao iniciar enriquecimento web para produto ID ${produtoId}:`, err);
      }
    }
    setActionLoading(false);

    if (requestSuccessCount > 0) {
      showSuccessToast(`${requestSuccessCount} processo(s) de enriquecimento web iniciado(s) com sucesso. Verifique o status na tabela em breve.`);
    }
    if (requestErrorCount > 0) {
      showWarningToast(`${requestErrorCount} processo(s) de enriquecimento web falharam ao iniciar. Verifique o console.`);
    }
    
    setSelectedProductIds([]);
    // Atualiza a tabela para mostrar o status "EM_PROGRESSO"
    // O backend deve atualizar o status para EM_PROGRESSO assim que a tarefa é agendada.
    // Um pequeno delay pode ajudar a garantir que o status seja refletido.
    setTimeout(() => {
        fetchProdutos();
    }, 2000); // Delay de 2 segundos antes de recarregar
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
      showSuccessToast('Produto atualizado com sucesso!');
      handleCloseEditModal();
      fetchProdutos();
      setSelectedProductIds([]);
      return Promise.resolve();
    } catch (updateError) {
      console.error("Objeto de erro recebido em handleSaveProductUpdate (ProdutosPage):", updateError);
      if (updateError && updateError.detail) {
        if (typeof updateError.detail === 'string') errorMessage = updateError.detail;
        else if (Array.isArray(updateError.detail)) errorMessage = updateError.detail.map(e => `${e.loc ? e.loc.join('.') + ': ' : ''}${e.msg}`).join('; ');
        else errorMessage = JSON.stringify(updateError.detail);
      } else if (updateError && updateError.message) errorMessage = updateError.message;
      else if (typeof updateError === 'string') errorMessage = updateError;
      showErrorToast(`Erro ao atualizar produto: ${errorMessage}`);
      return Promise.reject(updateError);
    } finally {
      setModalLoading(false);
    }
  };
  
  return (
    <div>
      <div className="stats-grid">
        <div className="stats-card"><h3>Total de Produtos Registrados</h3><div className="value">{totalProdutosCount}</div></div>
        <div className="stats-card"><h3>Pendentes Enriq. (Página)</h3><div className="value">{produtos.filter(p => p.status_enriquecimento_web === 'PENDENTE' || !p.status_enriquecimento_web).length}</div></div>
        <div className="stats-card"><h3>Enriquecidos Web (Página)</h3><div className="value">{produtos.filter(p => p.status_enriquecimento_web === 'CONCLUIDO_SUCESSO').length}</div></div>
      </div>

      <div className="filters-container" style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div className="search-container" style={{ margin: 0, flexGrow: 1, minWidth: '200px' }}>
          <label htmlFor="search-prod" style={{ display: 'block', marginBottom: '0.25rem' }}>Buscar Produtos:</label>
          <input
            type="text" id="search-prod" placeholder="Nome ou SKU..."
            value={searchTerm} onChange={handleSearchChange} disabled={loading || actionLoading}
            style={{width: '100%'}} />
        </div>
        <div className="filter-group" style={{flexGrow: 1, minWidth: '180px'}}>
          <label htmlFor="filter-status-enr" style={{ display: 'block', marginBottom: '0.25rem' }}>Status Enriq. Web:</label>
          <select id="filter-status-enr" value={selectedStatusEnriquecimento} 
            onChange={(e) => handleFilterChange(setSelectedStatusEnriquecimento, e.target.value)}
            disabled={loading || actionLoading}
            style={{width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem'}}
          >
            {statusEnriquecimentoWebOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </div>
        <div className="filter-group" style={{flexGrow: 1, minWidth: '180px'}}>
          <label htmlFor="filter-status-tit-ia" style={{ display: 'block', marginBottom: '0.25rem' }}>Status Títulos IA:</label>
          <select id="filter-status-tit-ia" value={selectedStatusTituloIA}
            onChange={(e) => handleFilterChange(setSelectedStatusTituloIA, e.target.value)}
            disabled={loading || actionLoading}
            style={{width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem'}}
          >
            {statusGeracaoIAOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </div>
        <div className="filter-group" style={{flexGrow: 1, minWidth: '180px'}}>
          <label htmlFor="filter-status-desc-ia" style={{ display: 'block', marginBottom: '0.25rem' }}>Status Descrição IA:</label>
          <select id="filter-status-desc-ia" value={selectedStatusDescricaoIA}
            onChange={(e) => handleFilterChange(setSelectedStatusDescricaoIA, e.target.value)}
            disabled={loading || actionLoading}
            style={{width: '100%', padding: '0.5rem', border: '1px solid #ccc', borderRadius: 'var(--radius)', fontSize: '1rem'}}
          >
            {statusGeracaoIAOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
          </select>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Lista de Produtos</h3>
          <button onClick={handleOpenNewProductModal} disabled={loading || modalLoading || actionLoading}>Novo Produto</button>
        </div>

        <ProductTable
            produtos={produtos} selectedIds={selectedProductIds}
            onSelectRow={handleSelectRow} onSelectAllRows={handleSelectAllRows}
            onRowClick={handleRowClick} isLoading={loading} />
        
        {totalPages > 0 && (
            <PaginationControls 
                currentPage={currentPage} totalPages={totalPages} 
                onPageChange={handlePageChange} isLoading={loading || actionLoading} />
        )}
        
        <div className="table-actions">
          {/* NOVO BOTÃO ADICIONADO */}
          <button
            onClick={handleEnrichSelectedWeb}
            disabled={loading || actionLoading || selectedProductIds.length === 0}
            style={{ backgroundColor: 'var(--info)' }} // Cor diferente para distinguir
          >
            🌐 Enriquecer Web ({selectedProductIds.length})
          </button>
          <button
            onClick={() => handleGenerateContentForSelected('titulos')}
            disabled={loading || actionLoading || selectedProductIds.length === 0}
          >
            Gerar Títulos (IA)
          </button>
          <button
            onClick={() => handleGenerateContentForSelected('descricoes')}
            disabled={loading || actionLoading || selectedProductIds.length === 0}
          >
            Gerar Descrições (IA)
          </button>
          <button
            onClick={handleDeleteSelected}
            disabled={loading || actionLoading || selectedProductIds.length === 0}
            style={{ backgroundColor: 'var(--danger)'}}
          >
            Deletar Selecionado(s)
          </button>
        </div>
      </div>

      <NewProductModal
        isOpen={isNewProductModalOpen} onClose={handleCloseNewProductModal}
        onSave={handleSaveNewProduct} isLoading={modalLoading} />

      <ProductEditModal
        isOpen={isEditModalOpen} onClose={handleCloseEditModal}
        productData={editingProduct} onSave={handleSaveProductUpdate}
        isLoading={modalLoading} />
    </div>
  );
}

export default ProdutosPage;