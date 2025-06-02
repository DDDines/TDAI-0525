// Frontend/app/src/pages/ProdutosPage.jsx
import React, { useState, useEffect, useCallback, useContext } from 'react';
import ProductTable from '../components/produtos/ProductTable';
import NewProductModal from '../components/produtos/NewProductModal';
import ProductEditModal from '../components/ProductEditModal';
import PaginationControls from '../components/common/PaginationControls';
import productService from '../services/productService'; 
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import './ProdutosPage.css'; // CSS específico para a página de Produtos. Deve existir em src/pages/ProdutosPage.css

// Importar o contexto de Tipos de Produto
import { ProductTypeContext } from '../contexts/ProductTypeContext';


function ProdutosPage() {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [isNewProductModalOpen, setIsNewProductModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [produtoParaEditar, setProdutoParaEditar] = useState(null);
  
  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage, setLimitPerPage] = useState(10);
  const [totalProdutos, setTotalProdutos] = useState(0);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'id', direction: 'descending' });
  const [selectedProdutos, setSelectedProdutos] = useState(new Set());

  const [filtroStatusEnriquecimento, setFiltroStatusEnriquecimento] = useState('');
  const [filtroStatusTituloIA, setFiltroStatusTituloIA] = useState('');
  const [filtroStatusDescricaoIA, setFiltroStatusDescricaoIA] = useState('');
  const [filtroFornecedor, setFiltroFornecedor] = useState(''); 
  const [filtroTipoProduto, setFiltroTipoProduto] = useState(''); 

  const { productTypes, loading: loadingProductTypes } = useContext(ProductTypeContext);


  const fetchProdutos = useCallback(async () => {
    console.log("ProdutosPage: Iniciando fetchProdutos..."); 
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction,
        search: searchTerm, 
        status_enriquecimento_web: filtroStatusEnriquecimento || undefined, 
        status_titulo_ia: filtroStatusTituloIA || undefined,
        status_descricao_ia: filtroStatusDescricaoIA || undefined,
        fornecedor_id: filtroFornecedor || undefined,
        product_type_id: filtroTipoProduto || undefined,
      };
      Object.keys(params).forEach(key => params[key] === undefined && delete params[key]);

      console.log("ProdutosPage: Parâmetros para productService.getProdutos:", params); 

      const data = await productService.getProdutos(params);
      
      console.log('ProdutosPage: Dados recebidos da API de produtos:', data); 
      
      setProdutos(Array.isArray(data.items) ? data.items : []);
      setTotalProdutos(data.total_items || 0);

    } catch (err) {
      console.error("ProdutosPage: Erro ao buscar produtos:", err); 
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao carregar produtos.';
      setError(errorMessage);
      showErrorToast(errorMessage);
      setProdutos([]); 
      setTotalProdutos(0);
    } finally {
      setLoading(false);
      console.log("ProdutosPage: fetchProdutos finalizado."); 
    }
  }, [currentPage, limitPerPage, sortConfig, searchTerm, filtroStatusEnriquecimento, filtroStatusTituloIA, filtroStatusDescricaoIA, filtroFornecedor, filtroTipoProduto]); 

  useEffect(() => {
    fetchProdutos();
  }, [fetchProdutos]);

  const handleOpenNewProductModal = () => setIsNewProductModalOpen(true);
  const handleCloseNewProductModal = () => setIsNewProductModalOpen(false);

  const handleOpenEditModal = (produto) => {
    setProdutoParaEditar(produto);
    setIsEditModalOpen(true);
  };
  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
    setProdutoParaEditar(null);
  };

  const handleProdutoSaved = () => {
    fetchProdutos(); 
    showSuccessToast("Produto salvo com sucesso!");
  };

  const handleSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
    setCurrentPage(0); 
  };
  
  const handleSelectProduto = (produtoId) => {
    setSelectedProdutos(prevSelected => {
      const newSelected = new Set(prevSelected);
      if (newSelected.has(produtoId)) {
        newSelected.delete(produtoId);
      } else {
        newSelected.add(produtoId);
      }
      return newSelected;
    });
  };

  const handleSelectAllProdutos = (isChecked) => {
    if (isChecked) {
      setSelectedProdutos(new Set(produtos.map(p => p.id)));
    } else {
      setSelectedProdutos(new Set());
    }
  };
  
  const handleDeleteSelected = async () => {
    if (selectedProdutos.size === 0) {
      showErrorToast("Nenhum produto selecionado para deletar.");
      return;
    }
    if (window.confirm(`Tem certeza que deseja deletar ${selectedProdutos.size} produto(s) selecionado(s)?`)) {
      try {
        setLoading(true);
        await productService.batchDeleteProdutos(Array.from(selectedProdutos));
        showSuccessToast(`${selectedProdutos.size} produto(s) deletado(s) com sucesso!`);
        setSelectedProdutos(new Set()); 
        fetchProdutos(); 
      } catch (err) {
        console.error("Erro ao deletar produtos selecionados:", err);
        showErrorToast(err.response?.data?.detail || err.message || "Falha ao deletar produtos.");
        setLoading(false);
      }
    }
  };

  const handleEnrichSelectedWeb = async () => {
    if (selectedProdutos.size === 0) {
      showErrorToast("Nenhum produto selecionado para enriquecimento web.");
      return;
    }
    const primeiraUrl = produtos.find(p => selectedProdutos.has(p.id))?.link_referencia_fornecedor;
    if (!primeiraUrl && selectedProdutos.size === 1) {
        showErrorToast("O produto selecionado não tem um link de referência do fornecedor para enriquecimento.");
        return;
    }
    if (selectedProdutos.size > 1 && !produtos.every(p => selectedProdutos.has(p.id) && p.link_referencia_fornecedor === primeiraUrl)) {
        // Se múltiplas URLs diferentes ou algumas sem URL, precisa de tratamento especial
        // Por ora, vamos simplificar e pedir para selecionar um ou garantir que todos tenham a mesma URL (pouco prático)
        // Idealmente, cada um seria processado individualmente.
        showErrorToast("Para enriquecimento em lote, todos os produtos selecionados devem ter o mesmo link de referência ou selecione um por vez.");
        // return; // Comentado para permitir o loop abaixo, que tratará individualmente
    }

    console.log("Iniciar enriquecimento web para:", Array.from(selectedProdutos));
    showSuccessToast(`Enriquecimento web iniciado para ${selectedProdutos.size} produto(s).`);
    
    try {
        setLoading(true); 
        for (const produtoId of selectedProdutos) {
            const produto = produtos.find(p => p.id === produtoId);
            if (produto && produto.link_referencia_fornecedor) {
                 await productService.iniciarEnriquecimentoWebProduto(produtoId, produto.link_referencia_fornecedor);
            } else {
                showErrorToast(`Produto ID ${produtoId} não tem link de referência ou não foi encontrado para enriquecimento.`);
            }
        }
        fetchProdutos(); 
    } catch (err) {
        console.error("Erro ao iniciar enriquecimento web:", err);
        showErrorToast(err.response?.data?.detail || err.message || "Falha ao iniciar enriquecimento web.");
    } finally {
        setLoading(false);
    }
  };

  const handleGenerateContentForSelected = async (contentType) => { 
    if (selectedProdutos.size === 0) {
      showErrorToast(`Nenhum produto selecionado para gerar ${contentType}s.`);
      return;
    }
    console.log(`Iniciar geração de ${contentType}s para:`, Array.from(selectedProdutos));
    showSuccessToast(`Geração de ${contentType}s iniciada para ${selectedProdutos.size} produto(s).`);
    
    try {
        setLoading(true);
        for (const produtoId of selectedProdutos) {
            if (contentType === 'titulo') {
                await productService.gerarTitulosProduto(produtoId, {}); 
            } else if (contentType === 'descricao') {
                await productService.gerarDescricaoProduto(produtoId, {}); 
            }
        }
        fetchProdutos(); 
    } catch (err) {
        console.error(`Erro ao gerar ${contentType}s:`, err);
        showErrorToast(err.response?.data?.detail || err.message || `Falha ao gerar ${contentType}s.`);
    } finally {
        setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalProdutos / limitPerPage);

  if (error && !loading && produtos.length === 0) { 
    return <div className="error-message">Erro: {error} <button onClick={fetchProdutos}>Tentar Novamente</button></div>;
  }

  return (
    <div className="produtos-page-container">
      <div className="page-header">
        <h1>Meus Produtos</h1>
        <button onClick={handleOpenNewProductModal} className="btn-primary">
          <span className="icon-add"></span> Novo Produto
        </button>
      </div>

      <div className="filtros-e-busca-container">
        <input
          type="text"
          placeholder="Buscar por nome, SKU, EAN..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setCurrentPage(0); 
          }}
          className="search-input"
        />
        <div className="filtros-dropdowns">
          <select value={filtroStatusEnriquecimento} onChange={(e) => {setFiltroStatusEnriquecimento(e.target.value); setCurrentPage(0);}} className="filtro-select">
            <option value="">Status Web</option>
            <option value="NAO_INICIADO">Não Iniciado</option>
            <option value="PENDENTE">Pendente</option>
            <option value="EM_PROGRESSO">Em Progresso</option>
            <option value="CONCLUIDO">Concluído</option>
            <option value="FALHA">Falha</option>
          </select>
          <select value={filtroStatusTituloIA} onChange={(e) => {setFiltroStatusTituloIA(e.target.value); setCurrentPage(0);}} className="filtro-select">
            <option value="">Status Título IA</option>
            <option value="NAO_INICIADO">Não Iniciado</option>
            <option value="PENDENTE">Pendente</option>
            <option value="EM_PROGRESSO">Em Progresso</option>
            <option value="CONCLUIDO">Concluído</option>
            <option value="FALHA">Falha</option>
            <option value="NAO_APLICAVEL">Não Aplicável</option>
          </select>
          <select value={filtroStatusDescricaoIA} onChange={(e) => {setFiltroStatusDescricaoIA(e.target.value); setCurrentPage(0);}} className="filtro-select">
            <option value="">Status Descrição IA</option>
            <option value="NAO_INICIADO">Não Iniciado</option>
            <option value="PENDENTE">Pendente</option>
            <option value="EM_PROGRESSO">Em Progresso</option>
            <option value="CONCLUIDO">Concluído</option>
            <option value="FALHA">Falha</option>
            <option value="NAO_APLICAVEL">Não Aplicável</option>
          </select>
        </div>
      </div>

      {selectedProdutos.size > 0 && (
        <div className="acoes-em-lote-container">
          <span>{selectedProdutos.size} produto(s) selecionado(s)</span>
          <button onClick={handleDeleteSelected} className="btn-danger btn-sm">Deletar Selecionados</button>
          <button onClick={handleEnrichSelectedWeb} className="btn-secondary btn-sm">Enriquecer Web</button>
          <button onClick={() => handleGenerateContentForSelected('titulo')} className="btn-secondary btn-sm">Gerar Títulos IA</button>
          <button onClick={() => handleGenerateContentForSelected('descricao')} className="btn-secondary btn-sm">Gerar Descrições IA</button>
        </div>
      )}

      {loading && produtos.length === 0 ? ( 
        <div className="loading-message">Carregando produtos...</div>
      ) : (
        <ProductTable
          produtos={produtos}
          onEdit={handleOpenEditModal}
          onSort={handleSort}
          sortConfig={sortConfig}
          onSelectProduto={handleSelectProduto}
          selectedProdutos={selectedProdutos}
          onSelectAllProdutos={handleSelectAllProdutos}
          loading={loading && produtos.length > 0} 
        />
      )}
      
      {!loading && totalProdutos > 0 && (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => setCurrentPage(page)}
            itemsPerPage={limitPerPage}
            onItemsPerPageChange={(value) => {
              setLimitPerPage(parseInt(value, 10));
              setCurrentPage(0); 
            }}
            totalItems={totalProdutos}
          />
        )}

      {isNewProductModalOpen && (
        <NewProductModal
          isOpen={isNewProductModalOpen}
          onClose={handleCloseNewProductModal}
          onProdutoSaved={handleProdutoSaved}
          productTypes={productTypes} 
          loadingProductTypes={loadingProductTypes} 
        />
      )}
      {isEditModalOpen && produtoParaEditar && (
        <ProductEditModal
          isOpen={isEditModalOpen}
          onClose={handleCloseEditModal}
          produtoParaEditar={produtoParaEditar}
          onProdutoSaved={handleProdutoSaved}
          productTypes={productTypes} 
          loadingProductTypes={loadingProductTypes} 
        />
      )}
    </div>
  );
}

export default ProdutosPage;