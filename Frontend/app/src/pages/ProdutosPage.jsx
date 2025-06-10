// Frontend/app/src/pages/ProdutosPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import ProductTable from '../components/produtos/ProductTable';
// REMOVIDO: import NewProductModal from '../components/produtos/NewProductModal';
// REMOVIDO: import ProductEditModal from '../components/ProductEditModal';
// NOVO: Importando o modal unificado.
// (O nome do arquivo pode ser ProductModal.jsx, estou mantendo este por consistência com o passo anterior)
import ProductModal from '../components/ProductEditModal';
import PaginationControls from '../components/common/PaginationControls';
import productService from '../services/productService';
import { showErrorToast, showSuccessToast, showInfoToast, showWarningToast } from '../utils/notifications';
import './ProdutosPage.css';
import { useProductTypes } from '../contexts/ProductTypeContext';

function ProdutosPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // ALTERADO: Estados de controle dos modais unificados em dois.
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [produtoParaEditar, setProdutoParaEditar] = useState(null);

  // REMOVIDO: Estados antigos para os modais separados.
  // const [isNewProductModalOpen, setIsNewProductModalOpen] = useState(false);
  // const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  
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

  const {
    productTypes,
    isLoading: loadingProductTypes,
    error: productTypesError,
  } = useProductTypes();

  useEffect(() => {
    if (productTypesError) {
      console.error('ProdutosPage: Erro recebido do ProductTypeContext:', productTypesError);
    }
  }, [productTypesError]);

  const fetchProdutos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        skip: currentPage * limitPerPage,
        limit: limitPerPage,
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction === 'ascending' ? 'asc' : 'desc',
        search: searchTerm,
        status_enriquecimento_web: filtroStatusEnriquecimento || undefined,
        status_titulo_ia: filtroStatusTituloIA || undefined,
        status_descricao_ia: filtroStatusDescricaoIA || undefined,
        fornecedor_id: filtroFornecedor || undefined,
        product_type_id: filtroTipoProduto || undefined,
      };
      Object.keys(params).forEach(key => params[key] === undefined && delete params[key]);
      const data = await productService.getProdutos(params);
      setProdutos(Array.isArray(data.items) ? data.items : []);
      setTotalProdutos(data.total_items || 0);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao carregar produtos.';
      setError(errorMessage);
      setProdutos([]);
      setTotalProdutos(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, limitPerPage, sortConfig, searchTerm, filtroStatusEnriquecimento, filtroStatusTituloIA, filtroStatusDescricaoIA, filtroFornecedor, filtroTipoProduto]);

  useEffect(() => {
    fetchProdutos();
  }, [fetchProdutos]);
  
  const handleProductUpdated = (updatedProduct) => {
    // Atualiza a lista de produtos no estado para refletir a mudança imediatamente
    setProdutos(prevProdutos => 
        prevProdutos.map(p => (p.id === updatedProduct.id ? updatedProduct : p))
    );
  };

  // NOVO: Funções unificadas para abrir e fechar o modal
  const handleOpenModal = (produto = null) => {
    setProdutoParaEditar(produto); // null para criar, objeto para editar
    setIsModalOpen(true);
  };
  const handleCloseModal = () => {
    setIsModalOpen(false);
    setProdutoParaEditar(null);
  };

  // Abra o modal automaticamente se um ID de produto for fornecido na URL
  useEffect(() => {
    const productId = searchParams.get('id');
    if (productId) {
      const openById = async () => {
        try {
          const prod = await productService.getProdutoById(productId);
          handleOpenModal(prod);
          navigate('/produtos', { replace: true });
        } catch (err) {
          const msg = err.response?.data?.detail || err.message || 'Falha ao carregar produto.';
          showErrorToast(msg);
        }
      };
      openById();
    }
  }, [searchParams]);

  // REMOVIDO: Handlers antigos dos modais separados
  // const handleOpenNewProductModal = () => setIsNewProductModalOpen(true);
  // const handleCloseNewProductModal = () => setIsNewProductModalOpen(false);
  // const handleOpenEditModal = (produto) => { ... };
  // const handleCloseEditModal = () => { ... };

  const handleSaveProdutoCallback = async (produtoData, produtoId = null) => {
    try {
      if (produtoId) {
        const updatedProduct = await productService.updateProduto(produtoId, produtoData);
        handleProductUpdated(updatedProduct);
      } else {
        await productService.createProduto(produtoData);
        fetchProdutos(); // Recarrega tudo ao criar um novo produto
      }
      showSuccessToast(`Produto ${produtoId ? 'atualizado' : 'criado'} com sucesso!`);
      return Promise.resolve();
    } catch (err) {
      const actionType = produtoId ? 'atualizar' : 'criar';
      const errorMsg = err.response?.data?.detail || err.message || `Falha ao ${actionType} produto.`;
      showErrorToast(errorMsg);
      return Promise.reject(err);
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
      showErrorToast('Nenhum produto selecionado para deletar.');
      return;
    }
    if (window.confirm(`Tem certeza que deseja deletar ${selectedProdutos.size} produto(s) selecionado(s)?`)) {
      setLoading(true);
      try {
        await productService.batchDeleteProdutos(Array.from(selectedProdutos));
        showSuccessToast(`${selectedProdutos.size} produto(s) deletado(s) com sucesso!`);
        setSelectedProdutos(new Set());
        fetchProdutos();
      } catch (err) {
        showErrorToast(err.response?.data?.detail || err.message || 'Falha ao deletar produtos.');
      } finally {
        setLoading(false);
      }
    }
  };

  const updateLocalProductStatus = (ids, statusField, newStatus) => {
    setProdutos(prev => 
      prev.map(p => 
        ids.has(p.id) ? { ...p, [statusField]: newStatus } : p
      )
    );
  };

  const handleEnrichSelectedWeb = async () => {
    if (selectedProdutos.size === 0) {
      showWarningToast('Nenhum produto selecionado para enriquecimento web.');
      return;
    }
    
    showInfoToast(`Enriquecimento web iniciado para ${selectedProdutos.size} produto(s).`);
    updateLocalProductStatus(selectedProdutos, 'status_enriquecimento_web', 'EM_PROGRESSO');

    const idsToProcess = Array.from(selectedProdutos);
    setSelectedProdutos(new Set()); 

    for (const produtoId of idsToProcess) {
      try {
        await productService.iniciarEnriquecimentoWebProduto(produtoId);
      } catch (err) {
        showErrorToast(`Erro ao iniciar enriquecimento para produto ID ${produtoId}: ${err.response?.data?.detail || err.message}`);
        updateLocalProductStatus(new Set([produtoId]), 'status_enriquecimento_web', 'FALHA');
      }
    }
    
    setTimeout(() => {
        showInfoToast("Atualizando lista para verificar resultados do enriquecimento...");
        fetchProdutos();
    }, 15000);
  };
  
  const handleGenerateContentForSelected = async (contentType) => {
    if (selectedProdutos.size === 0) {
      showWarningToast(`Nenhum produto selecionado para gerar ${contentType}s.`);
      return;
    }
    const contentTypePlural = contentType === 'titulo' ? 'títulos' : 'descrições';
    showInfoToast(`Geração de ${contentTypePlural} iniciada para ${selectedProdutos.size} produto(s).`);

    const statusField = `status_${contentType}_ia`;
    updateLocalProductStatus(selectedProdutos, statusField, 'EM_PROGRESSO');

    const idsToProcess = Array.from(selectedProdutos);
    setSelectedProdutos(new Set()); 

    for (const produtoId of idsToProcess) {
      try {
        if (contentType === 'titulo') {
          await productService.gerarTitulosProduto(produtoId);
        } else if (contentType === 'descricao') {
          await productService.gerarDescricaoProduto(produtoId);
        }
      } catch (err) {
        showErrorToast(`Erro ao gerar ${contentType} para produto ID ${produtoId}: ${err.response?.data?.detail || err.message}`);
        updateLocalProductStatus(new Set([produtoId]), statusField, 'FALHA');
      }
    }

    setTimeout(() => {
      showInfoToast(`Atualizando lista para verificar resultados da geração de ${contentTypePlural}...`);
      fetchProdutos();
    }, 15000);
  };
  
  const totalPages = Math.ceil(totalProdutos / limitPerPage);

  if (error && !loading && (!produtos || produtos.length === 0)) {
    return <div className="error-message">Erro ao carregar produtos: {error} <button onClick={fetchProdutos}>Tentar Novamente</button></div>;
  }

  return (
    <div className="produtos-page-container">
      <div className="page-header">
        <h1>Meus Produtos</h1>
        {/* ALTERADO: Botão de novo produto chama o handler unificado */}
        <button onClick={() => handleOpenModal(null)} className="btn-primary">
          <span className="icon-add"></span> Novo Produto
        </button>
      </div>
      <div className="filtros-e-busca-container">
        <input
          type="text"
          placeholder="Buscar por nome, SKU, EAN..."
          value={searchTerm}
          onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(0); }}
          className="search-input"
        />
        <div className="filtros-dropdowns">
          <select value={filtroStatusEnriquecimento} onChange={(e) => {setFiltroStatusEnriquecimento(e.target.value); setCurrentPage(0);}} className="filtro-select">
            <option value="">Status Web</option>
            <option value="NAO_INICIADO">Não Iniciado</option>
            <option value="PENDENTE">Pendente</option>
            <option value="EM_PROGRESSO">Em Progresso</option>
            <option value="CONCLUIDO_SUCESSO">Concluído</option>
            <option value="FALHA">Falha</option>
          </select>
          <select value={filtroStatusTituloIA} onChange={(e) => {setFiltroStatusTituloIA(e.target.value); setCurrentPage(0);}} className="filtro-select">
            <option value="">Status Título IA</option>
            <option value="NAO_INICIADO">Não Iniciado</option>
            <option value="PENDENTE">Pendente</option>
            <option value="EM_PROGRESSO">Em Progresso</option>
            <option value="CONCLUIDO">Concluído</option>
            <option value="FALHA">Falha</option>
          </select>
          <select value={filtroStatusDescricaoIA} onChange={(e) => {setFiltroStatusDescricaoIA(e.target.value); setCurrentPage(0);}} className="filtro-select">
            <option value="">Status Descrição IA</option>
            <option value="NAO_INICIADO">Não Iniciado</option>
            <option value="PENDENTE">Pendente</option>
            <option value="EM_PROGRESSO">Em Progresso</option>
            <option value="CONCLUIDO">Concluído</option>
            <option value="FALHA">Falha</option>
          </select>
          <select
            value={filtroTipoProduto}
            onChange={(e) => {setFiltroTipoProduto(e.target.value); setCurrentPage(0);}}
            className="filtro-select"
            disabled={loadingProductTypes || (productTypes && productTypes.length === 0)}
          >
            <option value="">
                {loadingProductTypes ? "Carregando Tipos..." : "Todos Tipos"}
            </option>
            {productTypes && productTypes.map(pt => (
              <option key={pt.id} value={pt.id}>{pt.friendly_name}</option>
            ))}
          </select>
        </div>
        <button onClick={fetchProdutos} className="btn btn-outline btn-sm" disabled={loading} title="Atualizar lista de produtos">
            Atualizar Lista
        </button>
      </div>
      {selectedProdutos.size > 0 && (
        <div className="acoes-em-lote-container">
          <span>{selectedProdutos.size} produto(s) selecionado(s)</span>
          <button onClick={handleDeleteSelected} className="btn-danger btn-sm">Deletar</button>
          <button onClick={handleEnrichSelectedWeb} className="btn-secondary btn-sm">Enriquecer Web</button>
          <button onClick={() => handleGenerateContentForSelected('titulo')} className="btn-secondary btn-sm">Gerar Títulos IA</button>
          <button onClick={() => handleGenerateContentForSelected('descricao')} className="btn-secondary btn-sm">Gerar Descrições IA</button>
        </div>
      )}
      {loading && (!produtos || produtos.length === 0) ? (
        <div className="loading-message">Carregando produtos...</div>
      ) : (
        <ProductTable
          produtos={produtos}
          // ALTERADO: onEdit agora usa o handler unificado
          onEdit={handleOpenModal}
          onSort={handleSort}
          sortConfig={sortConfig}
          onSelectProduto={handleSelectProduto}
          selectedProdutos={selectedProdutos}
          onSelectAllProdutos={handleSelectAllProdutos}
          loading={loading && (produtos && produtos.length > 0)}
        />
      )}
      {!loading && totalProdutos > 0 && (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => setCurrentPage(page)}
            itemsPerPage={limitPerPage}
            onItemsPerPageChange={(value) => { setLimitPerPage(parseInt(value, 10)); setCurrentPage(0); }}
            totalItems={totalProdutos}
          />
        )}
        
      {/* REMOVIDO: A renderização dos dois componentes de modal separados
      {isNewProductModalOpen && ( ... )}
      {isEditModalOpen && produtoParaEditar && ( ... )}
      */}

      {/* NOVO: Renderiza um único modal unificado */}
      {isModalOpen && (
        <ProductModal
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          product={produtoParaEditar}
          onProductUpdated={handleProductUpdated}
        />
      )}
    </div>
  );
}

export default ProdutosPage;
