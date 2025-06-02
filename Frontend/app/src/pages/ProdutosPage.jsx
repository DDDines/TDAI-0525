// Frontend/app/src/pages/ProdutosPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import ProductTable from '../components/produtos/ProductTable';
import NewProductModal from '../components/produtos/NewProductModal';
import ProductEditModal from '../components/ProductEditModal';
import PaginationControls from '../components/common/PaginationControls';
import productService from '../services/productService';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import './ProdutosPage.css';

// CORREÇÃO: Importar o hook useProductTypes
import { useProductTypes } from '../contexts/ProductTypeContext';


function ProdutosPage() {
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null); // Erro específico da busca de produtos

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

  // CORREÇÃO: Usar o hook useProductTypes
  const {
    productTypes,
    isLoading: loadingProductTypes,
    error: productTypesError, // Erro vindo do ProductTypeContext
    // reloadProductTypes // Descomente se precisar de um botão para recarregar tipos manualmente
  } = useProductTypes();

  // Observar erros do ProductTypeContext
  useEffect(() => {
    if (productTypesError) {
      // A mensagem de erro já deve ter sido logada pelo ProductTypeContext.
      // Se precisar mostrar um toast específico aqui, pode fazer, mas cuidado com duplicidade
      // se o erro 401 já causa redirecionamento pelo apiClient.
      // Ex: showErrorToast(productTypesError.detail || productTypesError.message || "Erro ao carregar dados de Tipos de Produto.");
      console.error("ProdutosPage: Erro recebido do ProductTypeContext:", productTypesError);
    }
  }, [productTypesError]);


  const fetchProdutos = useCallback(async () => {
    // console.log("ProdutosPage: Iniciando fetchProdutos..."); // Pode ser removido se estiver muito verboso
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

      const data = await productService.getProdutos(params);
      setProdutos(Array.isArray(data.items) ? data.items : []);
      setTotalProdutos(data.total_items || 0);

    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Falha ao carregar produtos.';
      setError(errorMessage);
      // Não mostre toast de erro aqui se o apiClient já trata 401 com redirecionamento.
      // Apenas defina o estado de erro para a UI da página.
      console.error("ProdutosPage: Erro ao buscar produtos:", err);
      setProdutos([]);
      setTotalProdutos(0);
    } finally {
      setLoading(false);
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

  const handleSaveProdutoCallback = async (produtoData, produtoId = null) => {
    // isLoading da página principal pode ser usado para feedback geral,
    // mas os modais também têm seu próprio estado 'isSubmitting'
    // setLoading(true); // O modal já terá seu próprio feedback de submissão

    try {
      if (produtoId) {
        await productService.updateProduto(produtoId, produtoData);
      } else {
        await productService.createProduto(produtoData);
      }
      fetchProdutos(); // Recarrega a lista de produtos
      showSuccessToast(`Produto ${produtoId ? 'atualizado' : 'criado'} com sucesso!`);
      return Promise.resolve(); // Para o .then() no modal
    } catch (err) {
      const actionType = produtoId ? 'atualizar' : 'criar';
      console.error(`ProdutosPage: Erro ao ${actionType} produto:`, err.response?.data || err.message);
      const errorMsg = err.response?.data?.detail || err.message || `Falha ao ${actionType} produto.`;
      showErrorToast(errorMsg);
      return Promise.reject(err); // Para o .catch() no modal
    } finally {
      // setLoading(false); // O modal controlará seu próprio estado de submissão
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
      showErrorToast("Nenhum produto selecionado para deletar.");
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
        console.error("Erro ao deletar produtos selecionados:", err.response?.data || err.message);
        showErrorToast(err.response?.data?.detail || err.message || "Falha ao deletar produtos.");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleEnrichSelectedWeb = async () => {
    if (selectedProdutos.size === 0) {
      showErrorToast("Nenhum produto selecionado para enriquecimento web.");
      return;
    }
    showSuccessToast(`Enriquecimento web iniciado para ${selectedProdutos.size} produto(s).`);
    setLoading(true);
    try {
        for (const produtoId of selectedProdutos) {
            await productService.iniciarEnriquecimentoWebProduto(produtoId);
        }
        setTimeout(fetchProdutos, 3000); // Aumentar um pouco o delay para dar tempo ao backend
    } catch (err) {
        console.error("Erro ao iniciar enriquecimento web:", err.response?.data || err.message);
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
    showSuccessToast(`Geração de ${contentType}s iniciada para ${selectedProdutos.size} produto(s).`);
    setLoading(true);
    try {
        for (const produtoId of selectedProdutos) {
            if (contentType === 'titulo') {
                await productService.gerarTitulosProduto(produtoId);
            } else if (contentType === 'descricao') {
                await productService.gerarDescricaoProduto(produtoId);
            }
        }
        setTimeout(fetchProdutos, 3000); // Aumentar um pouco o delay para dar tempo ao backend
    } catch (err) {
        console.error(`Erro ao gerar ${contentType}s:`, err.response?.data || err.message);
        showErrorToast(err.response?.data?.detail || err.message || `Falha ao gerar ${contentType}s.`);
    } finally {
        setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalProdutos / limitPerPage);

  // Se houver um erro na busca de produtos, mostrar mensagem de erro
  if (error && !loading && (!produtos || produtos.length === 0)) {
    return <div className="error-message">Erro ao carregar produtos: {error} <button onClick={fetchProdutos}>Tentar Novamente</button></div>;
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
          onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(0); }}
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
          <select
            value={filtroTipoProduto}
            onChange={(e) => {setFiltroTipoProduto(e.target.value); setCurrentPage(0);}}
            className="filtro-select"
            disabled={loadingProductTypes || (productTypes && productTypes.length === 0)}
          >
            <option value="">
                {loadingProductTypes ? "Carregando Tipos..." : ((productTypes && productTypes.length === 0 && !productTypesError) ? "Nenhum Tipo Cadastrado" : "Todos Tipos de Produto")}
            </option>
            {productTypes && productTypes.map(pt => (
              <option key={pt.id} value={pt.id}>{pt.friendly_name}</option>
            ))}
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

      {loading && (!produtos || produtos.length === 0) ? (
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

      {isNewProductModalOpen && (
        <NewProductModal
          isOpen={isNewProductModalOpen}
          onClose={handleCloseNewProductModal}
          onSave={(produtoData) => handleSaveProdutoCallback(produtoData)}
          productTypes={productTypes}
          loadingProductTypes={loadingProductTypes}
          isLoading={loading} // Passa o loading da página para o modal
        />
      )}
      {isEditModalOpen && produtoParaEditar && (
        <ProductEditModal
          isOpen={isEditModalOpen}
          onClose={handleCloseEditModal}
          productData={produtoParaEditar}
          onSave={(produtoId, produtoUpdateData) => handleSaveProdutoCallback(produtoUpdateData, produtoId)}
          productTypes={productTypes}
          loadingProductTypes={loadingProductTypes}
          isLoading={loading} // Passa o loading da página para o modal
        />
      )}
    </div>
  );
}

export default ProdutosPage;