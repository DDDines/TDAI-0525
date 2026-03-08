/**
 * Module fornecedores page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import fornecedorService from '../services/fornecedorService';
import FornecedorTable from '../components/fornecedores/FornecedorTable';
import NewFornecedorModal from '../components/fornecedores/NewFornecedorModal';
import EditFornecedorModal from '../components/fornecedores/EditFornecedorModal';
import PaginationControls from '../components/common/PaginationControls';
import { showSuccessToast, showErrorToast } from '../utils/notifications';
import { extractErrorMessage } from '../utils/errorDetails';
import { queryKeys } from '../lib/queryKeys.js';
import './FornecedoresPage.css';

function normalizeFornecedoresPayload(responseData) {
  if (responseData && Array.isArray(responseData.items) && typeof responseData.total_items === 'number') {
    return responseData;
  }
  console.warn('Formato de dados inesperado recebido para fornecedores:', responseData);
  return {
    items: [],
    total_items: 0,
  };
}

function FornecedoresPage() {
  const [modalLoading, setModalLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingFornecedor, setEditingFornecedor] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [limitPerPage] = useState(10);
  const [termoBusca, setTermoBusca] = useState('');
  const queryClient = useQueryClient();

  const queryParams = useMemo(
    () => ({
      skip: currentPage * limitPerPage,
      limit: limitPerPage,
      termo_busca: termoBusca || undefined,
    }),
    [currentPage, limitPerPage, termoBusca]
  );
  const fornecedoresQueryKey = queryKeys.fornecedores(queryParams);
  const fornecedoresQuery = useQuery({
    queryKey: fornecedoresQueryKey,
    queryFn: async () => normalizeFornecedoresPayload(await fornecedorService.getFornecedores(queryParams)),
    placeholderData: keepPreviousData,
  });

  useEffect(() => {
    if (fornecedoresQuery.error) {
      showErrorToast(fornecedoresQuery.error?.message || 'Falha ao buscar fornecedores.');
    }
  }, [fornecedoresQuery.error]);

  const fornecedores = Array.isArray(fornecedoresQuery.data?.items)
    ? fornecedoresQuery.data.items
    : [];
  const totalFornecedoresCount =
    typeof fornecedoresQuery.data?.total_items === 'number' ? fornecedoresQuery.data.total_items : 0;
  const loading = fornecedoresQuery.isLoading;
  const totalPages = Math.ceil(totalFornecedoresCount / limitPerPage);

  const handleSearchChange = (event) => {
    setTermoBusca(event.target.value);
    setCurrentPage(0);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  const invalidateFornecedores = async () => {
    await queryClient.invalidateQueries({ queryKey: ['fornecedores'] });
  };

  const handleSaveNew = async (data) => {
    setModalLoading(true);
    try {
      await fornecedorService.createFornecedor(data);
      showSuccessToast('Fornecedor criado com sucesso!');
      setIsNewModalOpen(false);
      if (!termoBusca) {
        setCurrentPage(0);
      }
      await invalidateFornecedores();
      setSelectedIds([]);
      return Promise.resolve();
    } catch (errThrownByService) {
      console.error('Objeto de erro recebido em handleSaveNew (FornecedoresPage):', errThrownByService);
      const errorMessage = extractErrorMessage(
        errThrownByService,
        'Erro desconhecido ao criar fornecedor.'
      );
      showErrorToast(`Erro ao criar fornecedor: ${errorMessage}`);
      return Promise.reject(errThrownByService);
    } finally {
      setModalLoading(false);
    }
  };

  const handleSaveUpdate = async (id, data) => {
    setModalLoading(true);
    try {
      await fornecedorService.updateFornecedor(id, data);
      showSuccessToast('Fornecedor atualizado com sucesso!');
      setIsEditModalOpen(false);
      setEditingFornecedor(null);
      await invalidateFornecedores();
      setSelectedIds([]);
      return Promise.resolve();
    } catch (errThrownByService) {
      console.error('Objeto de erro recebido em handleSaveUpdate (FornecedoresPage):', errThrownByService);
      const errorMessage = extractErrorMessage(
        errThrownByService,
        'Erro desconhecido ao atualizar fornecedor.'
      );
      showErrorToast(`Erro ao atualizar fornecedor: ${errorMessage}`);
      return Promise.reject(errThrownByService);
    } finally {
      setModalLoading(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (!window.confirm(`Tem certeza que deseja deletar ${selectedIds.length} fornecedor(es) selecionado(s)?`)) {
      return;
    }

    setIsDeleting(true);
    let successCount = 0;
    let errorOccurred = false;
    const successIds = [];

    for (const id of selectedIds) {
      try {
        await fornecedorService.deleteFornecedor(id);
        successCount += 1;
        successIds.push(id);
      } catch (singleDeleteError) {
        console.error(`Falha ao deletar fornecedor ID ${id}:`, singleDeleteError);
        errorOccurred = true;
      }
    }

    if (successCount > 0) {
      showSuccessToast(`${successCount} fornecedor(es) deletado(s) com sucesso!`);
    }
    if (errorOccurred) {
      showErrorToast('Alguns fornecedores nao puderam ser deletados. Verifique o console.');
    }

    const removedIds = new Set(successIds);
    const newTotalFornecedores = Math.max(0, totalFornecedoresCount - successCount);
    const newTotalPages = Math.ceil(newTotalFornecedores / limitPerPage);

    queryClient.setQueryData(fornecedoresQueryKey, (previous) => {
      const safePrevious = normalizeFornecedoresPayload(previous);
      return {
        items: safePrevious.items.filter((item) => !removedIds.has(item.id)),
        total_items: newTotalFornecedores,
      };
    });

    if (currentPage >= newTotalPages && newTotalPages > 0) {
      setCurrentPage(newTotalPages - 1);
    } else if (newTotalFornecedores === 0) {
      setCurrentPage(0);
    } else {
      await invalidateFornecedores();
    }

    setSelectedIds([]);
    setIsDeleting(false);
  };

  const handleRowClick = (fornecedor) => {
    setEditingFornecedor(fornecedor);
    setIsEditModalOpen(true);
  };

  const handleSelectRow = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
  };

  const handleSelectAllRows = (event) => {
    if (event.target.checked) {
      setSelectedIds(fornecedores.map((fornecedor) => fornecedor.id));
      return;
    }
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
          disabled={loading}
        />
      </div>

      <div className="card">
        <div className="card-header">
          <h3>Lista de Fornecedores</h3>
          <button onClick={() => setIsNewModalOpen(true)} disabled={loading || modalLoading}>
            Novo Fornecedor
          </button>
        </div>

        <FornecedorTable
          fornecedores={fornecedores}
          selectedIds={selectedIds}
          onSelectRow={handleSelectRow}
          onSelectAllRows={handleSelectAllRows}
          onRowClick={handleRowClick}
          isLoading={loading}
        />

        {totalPages > 0 ? (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            isLoading={loading}
          />
        ) : null}

        <div className="table-actions">
          <button
            onClick={handleDeleteSelected}
            disabled={loading || modalLoading || isDeleting || selectedIds.length === 0}
            className="app-danger-btn"
          >
            Deletar Selecionado(s)
          </button>
        </div>
      </div>

      <NewFornecedorModal
        isOpen={isNewModalOpen}
        onClose={() => setIsNewModalOpen(false)}
        onSave={handleSaveNew}
        isLoading={modalLoading}
      />

      <EditFornecedorModal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingFornecedor(null);
        }}
        fornecedorData={editingFornecedor}
        onSave={handleSaveUpdate}
        isLoading={modalLoading}
      />
    </div>
  );
}

export default FornecedoresPage;
