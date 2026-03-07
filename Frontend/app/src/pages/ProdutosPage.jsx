/**
 * Module produtos page.
 *
 * Defines responsibilities and integration points for pages.
 */

// Frontend/app/src/pages/ProdutosPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import ProductTable from '../components/produtos/ProductTable';
import Modal from '../components/common/Modal';
import ProductEditModal from '../components/ProductEditModal';
import { useAppExperience } from '../contexts/AppExperienceContext';
import PaginationControls from '../components/common/PaginationControls';
import productService from '../services/productService';
import { showErrorToast, showSuccessToast, showInfoToast } from '../utils/notifications';
import './ProdutosPage.css';
import { useProductTypes } from '../contexts/ProductTypeContext';
import LoadingPopup from '../components/common/LoadingPopup.jsx';

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

function ProdutosPage()

  {
    const { effectiveMode } = useAppExperience();
    const showAiFeatures = effectiveMode === 'complete';
    const showGenerationFeatures = true;
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [produtos, setProdutos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [isModalOpen, setIsModalOpen] = useState(false);
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
    const [filtroFornecedor, _setFiltroFornecedor] = useState('');
    const [filtroTipoProduto, setFiltroTipoProduto] = useState('');
    const pendingRefreshTimeoutsRef = React.useRef([]);
    const webStatusPollRunRef = React.useRef(0);

    const { productTypes, isLoading: loadingProductTypes, error: productTypesError } = useProductTypes();

    useEffect(() => {
      if (productTypesError) {
        console.error('ProdutosPage: erro recebido do ProductTypeContext:', productTypesError);
      }
    }, [productTypesError]);

    const buildProductNavigationQuery = useCallback(() => {
      const query = {
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction === 'ascending' ? 'asc' : 'desc',
        search: searchTerm || undefined,
        status_enriquecimento_web: filtroStatusEnriquecimento || undefined,
        status_titulo_ia: showAiFeatures ? filtroStatusTituloIA || undefined : undefined,
        status_descricao_ia: showAiFeatures ? filtroStatusDescricaoIA || undefined : undefined,
        fornecedor_id: filtroFornecedor || undefined,
        product_type_id: filtroTipoProduto || undefined,
      };
      Object.keys(query).forEach((key) => query[key] === undefined && delete query[key]);
      return query;
    }, [
      sortConfig,
      searchTerm,
      filtroStatusEnriquecimento,
      filtroStatusTituloIA,
      filtroStatusDescricaoIA,
      filtroFornecedor,
      filtroTipoProduto,
      showAiFeatures,
    ]);

    const fetchProdutos = useCallback(async () => {
      setLoading(true);
      setError(null);
      try {
        const params = {
          ...buildProductNavigationQuery(),
          skip: currentPage * limitPerPage,
          limit: limitPerPage,
        };
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
    }, [
      currentPage,
      limitPerPage,
      buildProductNavigationQuery,
    ]
    );

    useEffect(() => {
      fetchProdutos();
    }, [fetchProdutos]);

    const removePendingRefreshTimeout = useCallback((entryToRemove) => {
      pendingRefreshTimeoutsRef.current = pendingRefreshTimeoutsRef.current.filter(
        (entry) => entry !== entryToRemove
      );
    }, []);

    const schedulePendingRefreshTimeout = useCallback((callback, delayMs, onCancel) => {
      const entry = { timeoutId: null, onCancel };
      entry.timeoutId = setTimeout(() => {
        removePendingRefreshTimeout(entry);
        callback();
      }, delayMs);
      pendingRefreshTimeoutsRef.current.push(entry);
      return entry;
    }, [removePendingRefreshTimeout]);

    const clearPendingRefreshTimeouts = useCallback(() => {
      pendingRefreshTimeoutsRef.current.forEach((entry) => {
        clearTimeout(entry.timeoutId);
        entry.onCancel?.();
      });
      pendingRefreshTimeoutsRef.current = [];
    }, []);

    useEffect(() => () => {
      clearPendingRefreshTimeouts();
      webStatusPollRunRef.current += 1;
    }, [clearPendingRefreshTimeouts]);

    const scheduleProdutosRefresh = useCallback((message) => {
      schedulePendingRefreshTimeout(() => {
        showInfoToast(message);
        fetchProdutos();
      }, 15000);
    }, [fetchProdutos, schedulePendingRefreshTimeout]);

    const handleProductUpdated = (updatedProduct) => {
      setProdutos((prevProdutos) => prevProdutos.map((p) => p.id === updatedProduct.id ? updatedProduct : p));
    };

    const handleOpenModal = (produto = null) => {
      setProdutoParaEditar(produto);
      setIsModalOpen(true);
    };

    const handleOpenContentView = (produto) => {
      if (!produto?.id) {
        return;
      }
      navigate(`/produtos/${produto.id}/conteudo`, {
        state: {
          productIds: produtos.map((item) => item.id),
          productQuery: buildProductNavigationQuery(),
        },
      });
    };

    const handleCloseModal = () => {
      setIsModalOpen(false);
      setProdutoParaEditar(null);
    };

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
    }, [searchParams, navigate]);

    const handleSort = (key) => {
      let direction = 'ascending';
      if (sortConfig.key === key && sortConfig.direction === 'ascending') {
        direction = 'descending';
      }
      setSortConfig({ key, direction });
      setCurrentPage(0);
    };

    const handleSelectProduto = (produtoId) => {
      setSelectedProdutos((prevSelected) => {
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
        setSelectedProdutos(new Set(produtos.map((p) => p.id)));
      } else {
        setSelectedProdutos(new Set());
      }
    };

    const handleDeleteSelected = async () => {
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
      const idSet = new Set(Array.from(ids).map((id) => String(id)));
      setProdutos((prev) =>
        prev.map((p) => (idSet.has(String(p.id)) ? { ...p, [statusField]: newStatus } : p))
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
            fetchProdutos();
            return;
          }
        }

        await new Promise((resolve) => {
          schedulePendingRefreshTimeout(resolve, WEB_ENRICHMENT_POLL_INTERVAL_MS, resolve);
        });
      }

      showInfoToast(
        'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
      );
      fetchProdutos();
    }, [fetchProdutos, mergeProdutosById, schedulePendingRefreshTimeout]);

    const handleEnrichSelectedWeb = async () => {
      const idsToProcess = Array.from(selectedProdutos);
      setSelectedProdutos(new Set());
      updateLocalProductStatus(new Set(idsToProcess), 'status_enriquecimento_web', 'PENDENTE');
      showInfoToast(`Enriquecimento web iniciado para ${idsToProcess.length} produto(s).`);

      const failedIds = new Set();
      await Promise.all(
        idsToProcess.map(async (produtoId) => {
          try {
            await productService.iniciarEnriquecimentoWebProduto(produtoId);
          } catch (err) {
            failedIds.add(String(produtoId));
            showErrorToast(`Erro ao iniciar enriquecimento para produto ID ${produtoId}: ${err.response?.data?.detail || err.message}`);
            updateLocalProductStatus(new Set([produtoId]), 'status_enriquecimento_web', 'FALHA');
          }
        })
      );

      const startedIds = idsToProcess.filter((produtoId) => !failedIds.has(String(produtoId)));
      if (startedIds.length > 0) {
        updateLocalProductStatus(new Set(startedIds), 'status_enriquecimento_web', 'EM_PROGRESSO');
        void pollWebEnrichmentStatuses(startedIds);
      }
    };

    const handleGenerateContentForSelected = async (contentType) => {
      const contentTypePlural = contentType === 'titulo' ? 'títulos' : 'descrições';
      showInfoToast(`Geração de ${contentTypePlural} iniciada para ${selectedProdutos.size} produto(s).`);

      const statusField = `status_${contentType}_ia`;
      updateLocalProductStatus(selectedProdutos, statusField, 'EM_PROGRESSO');

      const idsToProcess = Array.from(selectedProdutos);
      setSelectedProdutos(new Set());

      for (const produtoId of idsToProcess) {
        try {
          if (contentType === 'titulo') {
            if (showAiFeatures) {
              await productService.gerarTitulosProduto(produtoId);
            } else {
              await productService.gerarTitulosProdutoModoBasico(produtoId);
            }
          } else if (contentType === 'descricao') {
            if (showAiFeatures) {
              await productService.gerarDescricaoProduto(produtoId);
            } else {
              await productService.gerarDescricaoProdutoModoBasico(produtoId);
            }
          }
        } catch (err) {
          showErrorToast(`Erro ao gerar ${contentType} para produto ID ${produtoId}: ${err.response?.data?.detail || err.message}`);
          updateLocalProductStatus(new Set([produtoId]), statusField, 'FALHA');
        }
      }

      scheduleProdutosRefresh(
        `Atualizando lista para verificar resultados da geração de ${contentTypePlural}...`
      );
    };

    const totalPages = Math.ceil(totalProdutos / limitPerPage);

    if (error && !loading && (!produtos || produtos.length === 0)) {
      return (
        <div className="error-message">
        Erro ao carregar produtos: {error}
        <button onClick={fetchProdutos}>Tentar novamente</button>
      </div>);

    }

    return (
      <div className="app-page-shell produtos-page-shell">
      <div className="app-page-header produtos-page-header">
        <h2 className="app-page-heading">Meus Produtos</h2>
        <button onClick={() => handleOpenModal(null)} className="btn-primary">
          + Novo Produto
        </button>
      </div>

      <div className="app-toolbar-card filtros-e-busca-container">
        <input
            type="text"
            placeholder="Buscar por nome, SKU, EAN..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(0);
            }}
            className="search-input" />


        <div className="filtros-dropdowns">
          <select
              value={filtroStatusEnriquecimento}
              onChange={(e) => {
                setFiltroStatusEnriquecimento(e.target.value);
                setCurrentPage(0);
              }}
              className="filtro-select">

            <option value="">Status</option>
            <option value="NAO_INICIADO">Não iniciado</option>
            <option value="PENDENTE">Pendente</option>
            <option value="EM_PROGRESSO">Em progresso</option>
            <option value="CONCLUIDO_SUCESSO">Concluído</option>
            <option value="FALHA">Falha</option>
          </select>

          {showAiFeatures &&
          <>
              <select
              value={filtroStatusTituloIA}
              onChange={(e) => {
                setFiltroStatusTituloIA(e.target.value);
                setCurrentPage(0);
              }}
              className="filtro-select">

              <option value="">Status Título IA</option>
              <option value="NAO_INICIADO">Não iniciado</option>
              <option value="PENDENTE">Pendente</option>
              <option value="EM_PROGRESSO">Em progresso</option>
              <option value="CONCLUIDO">Concluído</option>
              <option value="FALHA">Falha</option>
            </select>

              <select
              value={filtroStatusDescricaoIA}
              onChange={(e) => {
                setFiltroStatusDescricaoIA(e.target.value);
                setCurrentPage(0);
              }}
              className="filtro-select">

              <option value="">Status Descrição IA</option>
              <option value="NAO_INICIADO">Não iniciado</option>
              <option value="PENDENTE">Pendente</option>
              <option value="EM_PROGRESSO">Em progresso</option>
              <option value="CONCLUIDO">Concluído</option>
              <option value="FALHA">Falha</option>
            </select>
            </>
          }

          <select
              value={filtroTipoProduto}
              onChange={(e) => {
                setFiltroTipoProduto(e.target.value);
                setCurrentPage(0);
              }}
              className="filtro-select"
              disabled={loadingProductTypes || productTypes && productTypes.length === 0}>

            <option value="">{loadingProductTypes ? 'Carregando tipos...' : 'Todos os tipos'}</option>
            {productTypes && productTypes.map((pt) =>
              <option key={pt.id} value={pt.id}>{pt.friendly_name}</option>
              )}
          </select>
        </div>

        <button
            onClick={fetchProdutos}
            className="btn btn-outline btn-sm"
            disabled={loading}
            title="Atualizar lista de produtos">

          Atualizar Lista
        </button>
      </div>

      {selectedProdutos.size > 0 &&
        <div className="acoes-em-lote-container">
          <span>{selectedProdutos.size} produto(s) selecionado(s)</span>
          <button onClick={handleDeleteSelected} className="btn-danger btn-sm">Deletar</button>
          <button onClick={handleEnrichSelectedWeb} className="btn-secondary btn-sm">Enriquecer Web</button>
          {showGenerationFeatures &&
          <>
              <button onClick={() => handleGenerateContentForSelected('titulo')} className="btn-secondary btn-sm">
                {showAiFeatures ? 'Gerar Títulos IA' : 'Gerar Títulos'}
              </button>
              <button onClick={() => handleGenerateContentForSelected('descricao')} className="btn-secondary btn-sm">
                {showAiFeatures ? 'Gerar Descrições IA' : 'Gerar Descrições'}
              </button>
            </>
          }
        </div>
        }

      {loading && (!produtos || produtos.length === 0) ?
        <LoadingPopup isOpen={true} message="Carregando produtos..." /> :

        <ProductTable
          produtos={produtos}
          onEdit={handleOpenModal}
          onViewContent={handleOpenContentView}
          onSort={handleSort}
          sortConfig={sortConfig}
          onSelectProduto={handleSelectProduto}
          selectedProdutos={selectedProdutos}
          onSelectAllProdutos={handleSelectAllProdutos}
          showAiColumns={showGenerationFeatures}
          loading={loading && produtos && produtos.length > 0} />

        }

      {!loading && totalProdutos > 0 &&
        <PaginationControls
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={(page) => setCurrentPage(page)}
          itemsPerPage={limitPerPage}
          onItemsPerPageChange={(value) => {
            setLimitPerPage(parseInt(value, 10));
            setCurrentPage(0);
          }}
          totalItems={totalProdutos} />

        }

      {isModalOpen &&
        <Modal isOpen={isModalOpen} onClose={handleCloseModal} title={produtoParaEditar ? 'Editar Produto' : 'Criar Novo Produto'}>
          <ProductEditModal
            isOpen={isModalOpen}
            onClose={handleCloseModal}
            product={produtoParaEditar}
            showAiFeatures={showAiFeatures}
            onOpenContentView={(produtoId) => {
              if (!produtoId) {
                return;
              }
              handleOpenContentView({ id: produtoId });
            }}
            onProductUpdated={handleProductUpdated} />

        </Modal>
        }
    </div>);

  }
export default ProdutosPage;
