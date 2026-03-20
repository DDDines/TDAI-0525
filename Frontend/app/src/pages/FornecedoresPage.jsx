/**
 * Module fornecedores page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LuBuilding2,
  LuGlobe,
  LuPlus,
  LuSearch,
  LuUsers,
} from 'react-icons/lu';
import fornecedorService from '../services/fornecedorService';
import FornecedorTable from '../components/fornecedores/FornecedorTable';
import NewFornecedorModal from '../components/fornecedores/NewFornecedorModal';
import EditFornecedorModal from '../components/fornecedores/EditFornecedorModal';
import PaginationControls from '../components/common/PaginationControls';
import OperationalStatChip from '../components/common/OperationalStatChip.jsx';
import { showErrorToast } from '../utils/notifications';
import { extractErrorMessage } from '../utils/errorDetails';
import { queryKeys } from '../lib/queryKeys.js';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
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

function formatSelectionSummary(selectedIds, selectionScope) {
  if (selectedIds.length <= 0) {
    return '';
  }
  if (selectionScope === 'all') {
    return `${selectedIds.length} fornecedor(es) selecionado(s) em todos os resultados filtrados.`;
  }
  if (selectionScope === 'page') {
    return `${selectedIds.length} fornecedor(es) selecionado(s) na página atual.`;
  }
  return `${selectedIds.length} fornecedor(es) selecionado(s) em seleção manual.`;
}

function FornecedoresPage() {
  const [modalLoading, setModalLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingFornecedor, setEditingFornecedor] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [selectionScope, setSelectionScope] = useState('none');
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
      showErrorToast(
        extractErrorMessage(fornecedoresQuery.error, 'Falha ao buscar fornecedores.')
      );
    }
  }, [fornecedoresQuery.error]);

  const fornecedores = Array.isArray(fornecedoresQuery.data?.items)
    ? fornecedoresQuery.data.items
    : [];
  const totalFornecedoresCount =
    typeof fornecedoresQuery.data?.total_items === 'number' ? fornecedoresQuery.data.total_items : 0;
  const loading = fornecedoresQuery.isLoading;
  const totalPages = Math.ceil(totalFornecedoresCount / limitPerPage);
  const fornecedoresComSiteNaPagina = fornecedores.filter((item) => String(item?.site_url || '').trim()).length;
  const selectionSummary = formatSelectionSummary(selectedIds, selectionScope);
  const loadingInitial = fornecedoresQuery.isLoading;
  const fornecedoresErrorMessage = fornecedoresQuery.isError
    ? extractErrorMessage(fornecedoresQuery.error, 'Falha ao buscar fornecedores.')
    : '';

  const clearSelectionState = () => {
    setSelectedIds([]);
    setSelectionScope('none');
  };

  const handleSearchChange = (event) => {
    setTermoBusca(event.target.value);
    setCurrentPage(0);
    clearSelectionState();
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
    clearSelectionState();
  };

  const invalidateFornecedores = async () => {
    await queryClient.invalidateQueries({ queryKey: ['fornecedores'] });
  };

  const handleSaveNew = async (data) => {
    setModalLoading(true);
    try {
      await fornecedorService.createFornecedor(data);
      setIsNewModalOpen(false);
      if (!termoBusca) {
        setCurrentPage(0);
      }
      await invalidateFornecedores();
      clearSelectionState();
      return Promise.resolve();
    } catch (errThrownByService) {
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
      setIsEditModalOpen(false);
      setEditingFornecedor(null);
      await invalidateFornecedores();
      clearSelectionState();
      return Promise.resolve();
    } catch (errThrownByService) {
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
      } catch {
        errorOccurred = true;
      }
    }

    if (errorOccurred) {
      showErrorToast('Alguns fornecedores não puderam ser deletados. Tente novamente.');
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

    clearSelectionState();
    setIsDeleting(false);
  };

  const handleRowClick = (fornecedor) => {
    setEditingFornecedor(fornecedor);
    setIsEditModalOpen(true);
  };

  const handleSelectRow = (id) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]));
    setSelectionScope('custom');
  };

  const handleSelectAllRows = (isChecked) => {
    if (isChecked) {
      setSelectedIds(fornecedores.map((fornecedor) => fornecedor.id));
      setSelectionScope('page');
      return;
    }
    clearSelectionState();
  };

  const handleSelectAllResults = async (isChecked) => {
    if (!isChecked) {
      clearSelectionState();
      return;
    }
    try {
      const response = await fornecedorService.getFornecedoresIds({
        termo_busca: termoBusca || undefined,
      });
      const ids = Array.isArray(response?.ids) ? response.ids : [];
      setSelectedIds(ids);
      setSelectionScope('all');
    } catch (error) {
      showErrorToast(
        extractErrorMessage(error, 'Falha ao selecionar todos os fornecedores filtrados.')
      );
    }
  };
  const fornecedorSelectionMenuItems = useMemo(() => ([
    {
      key: 'page',
      label: 'Selecionar página atual',
      onClick: () => handleSelectAllRows(true),
      disabled: fornecedores.length === 0,
    },
    {
      key: 'all',
      label: 'Selecionar todos os resultados da pesquisa',
      onClick: () => void handleSelectAllResults(true),
      disabled: totalFornecedoresCount === 0,
    },
    {
      key: 'clear',
      label: 'Limpar seleção',
      onClick: clearSelectionState,
      disabled: selectedIds.length === 0,
    },
  ]), [clearSelectionState, fornecedores.length, selectedIds.length, totalFornecedoresCount]);

  return (
    <div className="app-page-shell ops-page-shell fornecedores-page-shell">
      <section className="ops-card ops-toolbar-card fornecedores-stats-card">
        <div className="fornecedores-stats-header">
          <div className="ops-metrics-row fornecedores-metrics-row">
            <OperationalStatChip
              icon={<LuBuilding2 />}
              label="Na base"
              value={totalFornecedoresCount}
              tone="neutral"
            />
            <OperationalStatChip
              icon={<LuUsers />}
              label="Na página"
              value={fornecedores.length}
              tone="info"
            />
            <OperationalStatChip
              icon={<LuGlobe />}
              label="Com site"
              value={fornecedoresComSiteNaPagina}
              tone={fornecedoresComSiteNaPagina > 0 ? 'success' : 'neutral'}
            />
            {selectedIds.length > 0 ? (
              <OperationalStatChip
                icon={<LuUsers />}
                label="Selecionados"
                value={selectedIds.length}
                tone="warn"
              />
            ) : null}
          </div>
          <button
            type="button"
            className="ops-primary-btn"
            onClick={() => setIsNewModalOpen(true)}
            disabled={loading || modalLoading}
          >
            <LuPlus />
            Novo Fornecedor
          </button>
        </div>
      </section>

      <section className="ops-card ops-table-card fornecedores-table-card">
        <div className="fornecedores-list-toolbar">
          <div className="ops-search-field fornecedores-search-field">
            <div className="ops-search-input-wrap">
              <LuSearch />
              <input
                type="text"
                id="search-forn"
                aria-label="Buscar fornecedores"
                placeholder="Nome do fornecedor ou domínio do site..."
                value={termoBusca}
                onChange={handleSearchChange}
                disabled={loading}
              />
            </div>
          </div>
        </div>

        {selectionSummary ? (
          <div className="ops-selection-bar fornecedores-selection-bar">
            <div className="ops-selection-copy">
              <p className="ops-selection-summary">{selectionSummary}</p>
            </div>
            <div className="ops-selection-actions">
              <button
                onClick={handleDeleteSelected}
                disabled={loading || modalLoading || isDeleting || selectedIds.length === 0}
                className="btn-danger btn-sm fornecedores-danger-action"
              >
                Excluir selecionado(s)
              </button>
            </div>
          </div>
        ) : null}

        {loadingInitial && (!fornecedores || fornecedores.length === 0) ? (
          <LoadingOverlay isOpen={true} message="Carregando fornecedores..." />
        ) : fornecedoresQuery.isError && fornecedores.length === 0 ? (
          <div className="fornecedores-inline-error" role="alert">
            <p>{fornecedoresErrorMessage}</p>
            <button
              type="button"
              className="ops-secondary-btn fornecedores-retry-btn"
              onClick={() => void fornecedoresQuery.refetch()}
            >
              Tentar novamente
            </button>
          </div>
        ) : (
          <FornecedorTable
            fornecedores={fornecedores}
            selectedIds={selectedIds}
            onSelectRow={handleSelectRow}
            onSelectAllRows={handleSelectAllRows}
            selectionMenuItems={fornecedorSelectionMenuItems}
            onRowClick={handleRowClick}
            isLoading={loading}
          />
        )}

        {!loadingInitial && totalPages > 0 ? (
          <PaginationControls
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
            isLoading={loading}
          />
        ) : null}
      </section>

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
