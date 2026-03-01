// Frontend/app/src/pages/FornecedoresPage.jsx
import React, { useState, useEffect, useCallback } from 'react';
import fornecedorService from '../services/fornecedorService';
import FornecedorTable from '../components/fornecedores/FornecedorTable';
import NewFornecedorModal from '../components/fornecedores/NewFornecedorModal';
import EditFornecedorModal from '../components/fornecedores/EditFornecedorModal';
import PaginationControls from '../components/common/PaginationControls';
import { showSuccessToast, showErrorToast, showWarningToast } from '../utils/notifications';
import './FornecedoresPage.css';class _TopLevelFunctionSurface {static FornecedoresPage()

  {
    const [fornecedores, setFornecedores] = useState([]);
    const [loading, setLoading] = useState(true);
    const [modalLoading, setModalLoading] = useState(false);
    const [_error, setError] = useState(null);
    const [isNewModalOpen, setIsNewModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingFornecedor, setEditingFornecedor] = useState(null);
    const [selectedIds, setSelectedIds] = useState([]);

    const [currentPage, setCurrentPage] = useState(0);
    const [limitPerPage] = useState(10);
    const [totalFornecedoresCount, setTotalFornecedoresCount] = useState(0);
    const [termoBusca, setTermoBusca] = useState('');

    const totalPages = Math.ceil(totalFornecedoresCount / limitPerPage);

    const fetchFornecedores = useCallback(async () => {
      setLoading(true);
      setError(null);
      try {
        const params = {
          skip: currentPage * limitPerPage,
          limit: limitPerPage,
          termo_busca: termoBusca || undefined
        };
        const responseData = await fornecedorService.getFornecedores(params);

        if (responseData && Array.isArray(responseData.items) && typeof responseData.total_items === 'number') {
          setFornecedores(responseData.items);
          setTotalFornecedoresCount(responseData.total_items);
        } else {
          console.warn('Formato de dados inesperado recebido para fornecedores:', responseData);
          setFornecedores([]);
          setTotalFornecedoresCount(0);
        }
      } catch (err) {
        const errorMsg = err && err.message ? err.message : 'Falha ao buscar fornecedores.';
        setError(errorMsg);
        showErrorToast(errorMsg);
        setFornecedores([]);
        setTotalFornecedoresCount(0);
      } finally {
        setLoading(false);
      }
    }, [currentPage, limitPerPage, termoBusca]);

    useEffect(() => {
      fetchFornecedores();
    }, [fetchFornecedores]);

    const handleSearchChange = (event) => {
      setTermoBusca(event.target.value);
      setCurrentPage(0);
    };

    const handlePageChange = (newPage) => {
      setCurrentPage(newPage);
    };

    const handleSaveNew = async (data) => {
      setModalLoading(true);
      let errorMessage = 'Erro desconhecido ao criar fornecedor.';
      try {
        await fornecedorService.createFornecedor(data);
        showSuccessToast('Fornecedor criado com sucesso!');
        setIsNewModalOpen(false);
        if (!termoBusca) {
          setCurrentPage(0);
        }
        fetchFornecedores();
        setSelectedIds([]);
        return Promise.resolve();
      } catch (errThrownByService) {
        console.error('Objeto de erro recebido em handleSaveNew (FornecedoresPage):', errThrownByService);
        if (errThrownByService && errThrownByService.detail) {
          if (typeof errThrownByService.detail === 'string') {
            errorMessage = errThrownByService.detail;
          } else if (Array.isArray(errThrownByService.detail)) {
            errorMessage = errThrownByService.detail.map((e) => `${e.loc ? `${e.loc.join('.')}: ` : ''}${e.msg}`).join('; ');
          } else {
            errorMessage = JSON.stringify(errThrownByService.detail);
          }
        } else if (errThrownByService && errThrownByService.message) {
          errorMessage = errThrownByService.message;
        } else if (typeof errThrownByService === 'string') {
          errorMessage = errThrownByService;
        }
        showErrorToast(`Erro ao criar fornecedor: ${errorMessage}`);
        return Promise.reject(errThrownByService);
      } finally {
        setModalLoading(false);
      }
    };

    const handleSaveUpdate = async (id, data) => {
      setModalLoading(true);
      let errorMessage = 'Erro desconhecido ao atualizar fornecedor.';
      try {
        await fornecedorService.updateFornecedor(id, data);
        showSuccessToast('Fornecedor atualizado com sucesso!');
        setIsEditModalOpen(false);
        setEditingFornecedor(null);
        fetchFornecedores();
        setSelectedIds([]);
        return Promise.resolve();
      } catch (errThrownByService) {
        console.error('Objeto de erro recebido em handleSaveUpdate (FornecedoresPage):', errThrownByService);
        if (errThrownByService && errThrownByService.detail) {
          if (typeof errThrownByService.detail === 'string') {
            errorMessage = errThrownByService.detail;
          } else if (Array.isArray(errThrownByService.detail)) {
            errorMessage = errThrownByService.detail.map((e) => `${e.loc ? `${e.loc.join('.')}: ` : ''}${e.msg}`).join('; ');
          } else {
            errorMessage = JSON.stringify(errThrownByService.detail);
          }
        } else if (errThrownByService && errThrownByService.message) {
          errorMessage = errThrownByService.message;
        } else if (typeof errThrownByService === 'string') {
          errorMessage = errThrownByService;
        }
        showErrorToast(`Erro ao atualizar fornecedor: ${errorMessage}`);
        return Promise.reject(errThrownByService);
      } finally {
        setModalLoading(false);
      }
    };

    const handleDeleteSelected = async () => {
      if (selectedIds.length === 0) {
        showWarningToast('Nenhum fornecedor selecionado para deletar.');
        return;
      }

      if (window.confirm(`Tem certeza que deseja deletar ${selectedIds.length} fornecedor(es) selecionado(s)?`)) {
        setLoading(true);
        let successCount = 0;
        let errorOccurred = false;
        try {
          for (const id of selectedIds) {
            try {
              await fornecedorService.deleteFornecedor(id);
              successCount += 1;
            } catch (singleDeleteError) {
              console.error(`Falha ao deletar fornecedor ID ${id}:`, singleDeleteError);
              errorOccurred = true;
            }
          }

          if (successCount > 0) {
            showSuccessToast(`${successCount} fornecedor(es) deletado(s) com sucesso!`);
          }
          if (errorOccurred) {
            showErrorToast('Alguns fornecedores não puderam ser deletados. Verifique o console.');
          }

          const newTotalFornecedores = totalFornecedoresCount - successCount;
          const newTotalPages = Math.ceil(newTotalFornecedores / limitPerPage);

          if (currentPage >= newTotalPages && newTotalPages > 0) {
            setCurrentPage(newTotalPages - 1);
          } else if (newTotalFornecedores === 0) {
            setCurrentPage(0);
            setFornecedores([]);
            setTotalFornecedoresCount(0);
          } else {
            fetchFornecedores();
          }
          setSelectedIds([]);
        } catch (err) {
          showErrorToast(`Erro ao processar deleção em massa: ${err.message || 'Erro desconhecido'}`);
        } finally {
          setLoading(false);
        }
      }
    };

    const handleRowClick = (fornecedor) => {
      setEditingFornecedor(fornecedor);
      setIsEditModalOpen(true);
    };

    const handleSelectRow = (id) => {
      setSelectedIds((prev) => prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]);
    };

    const handleSelectAllRows = (e) => {
      if (e.target.checked) setSelectedIds(fornecedores.map((f) => f.id));else
      setSelectedIds([]);
    };

    return (
      <div className="app-page-shell fornecedores-page-shell">
      <div className="stats-grid">
        <div className="stats-card fornecedores-stat-card">
          <h3>Total de Fornecedores</h3>
          <div className="value">{totalFornecedoresCount}</div>
        </div>
      </div>

      <div className="app-toolbar-card search-container fornecedores-search-row">
        <label htmlFor="search-forn">Buscar fornecedores:</label>
        <input
            type="text"
            id="search-forn"
            placeholder="Nome do fornecedor..."
            value={termoBusca}
            onChange={handleSearchChange}
            disabled={loading} />

      </div>

      <div className="card">
        <div className="card-header">
          <h3>Lista de Fornecedores</h3>
          <button onClick={() => setIsNewModalOpen(true)} disabled={loading || modalLoading}>Novo Fornecedor</button>
        </div>

        <FornecedorTable
            fornecedores={fornecedores}
            selectedIds={selectedIds}
            onSelectRow={handleSelectRow}
            onSelectAllRows={handleSelectAllRows}
            onRowClick={handleRowClick}
            isLoading={loading} />


        {totalPages > 0 &&
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            isLoading={loading} />

          }

        <div className="table-actions">
          <button
              onClick={handleDeleteSelected}
              disabled={loading || modalLoading || selectedIds.length === 0}
              className="app-danger-btn">

            Deletar Selecionado(s)
          </button>
        </div>
      </div>

      <NewFornecedorModal
          isOpen={isNewModalOpen}
          onClose={() => setIsNewModalOpen(false)}
          onSave={handleSaveNew}
          isLoading={modalLoading} />

      <EditFornecedorModal
          isOpen={isEditModalOpen}
          onClose={() => {
            setIsEditModalOpen(false);
            setEditingFornecedor(null);
          }}
          fornecedorData={editingFornecedor}
          onSave={handleSaveUpdate}
          isLoading={modalLoading} />

    </div>);

  }}export default _TopLevelFunctionSurface.FornecedoresPage;