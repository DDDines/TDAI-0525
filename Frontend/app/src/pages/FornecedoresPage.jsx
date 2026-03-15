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

function formatSelectionSummary(selectedIds, selectionScope) {
  if (selectedIds.length <= 0) {
    return '';
  }
  if (selectionScope === 'all') {
    return `${selectedIds.length} fornecedor(es) selecionado(s) em todos os resultados filtrados.`;
  }
  if (selectionScope === 'page') {
    return `${selectedIds.length} fornecedor(es) selecionado(s) na pagina atual.`;
  }
  return `${selectedIds.length} fornecedor(es) selecionado(s) em selecao manual.`;
}

function buildResultsSummary(totalItems, visibleItems, searchTerm) {
  if (!visibleItems && !totalItems) {
    return searchTerm
      ? `Nenhum fornecedor encontrado para "${searchTerm}".`
      : 'Nenhum fornecedor cadastrado na base atual.';
  }

  if (searchTerm) {
    return `Exibindo ${visibleItems} resultado(s) para "${searchTerm}" dentro de uma base com ${totalItems} fornecedor(es).`;
  }

  return `Base com ${totalItems} fornecedor(es) cadastrados e ${visibleItems} visivel(is) na pagina atual.`;
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
  const fornecedoresComSiteNaPagina = fornecedores.filter((item) => String(item?.site_url || '').trim()).length;
  const selectionSummary = formatSelectionSummary(selectedIds, selectionScope);
  const canSelectAllFilteredResults =
    selectedIds.length > 0
    && selectionScope !== 'all'
    && totalFornecedoresCount > selectedIds.length;
  const canReduceSelectionToPage =
    selectionScope === 'all'
    && fornecedores.length > 0;
  const resultsSummary = buildResultsSummary(totalFornecedoresCount, fornecedores.length, termoBusca.trim());

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
      showSuccessToast('Fornecedor criado com sucesso!');
      setIsNewModalOpen(false);
      if (!termoBusca) {
        setCurrentPage(0);
      }
      await invalidateFornecedores();
      clearSelectionState();
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
      clearSelectionState();
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
      showErrorToast(error?.message || 'Falha ao selecionar todos os fornecedores filtrados.');
    }
  };

  const handleSelectCurrentPageOnly = () => {
    if (!fornecedores.length) {
      clearSelectionState();
      return;
    }
    setSelectedIds(fornecedores.map((fornecedor) => fornecedor.id));
    setSelectionScope('page');
  };

  return (
    <div className="app-page-shell ops-page-shell fornecedores-page-shell">
      <div className="app-page-header fornecedores-page-header">
        <h2 className="app-page-heading">Meus Fornecedores</h2>
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

      <section className="ops-card ops-toolbar-card fornecedores-control-card">
        <div className="ops-toolbar-main">
          <div className="ops-toolbar-copy">
            <div className="ops-toolbar-header">
              <span className="ops-inline-eyebrow">Base operacional</span>
              <p>{resultsSummary}</p>
            </div>

            <div className="ops-search-field fornecedores-search-field">
              <label htmlFor="search-forn">Buscar fornecedores</label>
              <div className="ops-search-input-wrap">
                <LuSearch />
                <input
                  type="text"
                  id="search-forn"
                  placeholder="Nome do fornecedor ou dominio do site..."
                  value={termoBusca}
                  onChange={handleSearchChange}
                  disabled={loading}
                />
              </div>
            </div>

            <div className="ops-metrics-row">
              <OperationalStatChip
                icon={<LuBuilding2 />}
                label="Na base"
                value={totalFornecedoresCount}
                tone="neutral"
              />
              <OperationalStatChip
                icon={<LuUsers />}
                label="Visiveis"
                value={fornecedores.length}
                tone="info"
              />
              <OperationalStatChip
                icon={<LuGlobe />}
                label="Com site"
                value={fornecedoresComSiteNaPagina}
                tone="success"
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
          </div>
        </div>
      </section>

      <section className="ops-card ops-table-card fornecedores-table-card">
        <div className="ops-table-head">
          <div>
            <h3>Lista de fornecedores</h3>
            <p>Clique em uma linha para editar e use os checkboxes apenas quando precisar agir em lote.</p>
          </div>
          <div className="ops-table-meta">
            <span>{fornecedores.length} na pagina</span>
            <span>Pagina {Math.min(currentPage + 1, Math.max(totalPages, 1))}</span>
          </div>
        </div>

        {selectionSummary ? (
          <div className="ops-selection-bar fornecedores-selection-bar">
            <div className="ops-selection-copy">
              <p className="ops-selection-summary">{selectionSummary}</p>
              {canSelectAllFilteredResults ? (
                <button
                  type="button"
                  className="ops-selection-inline-action"
                  onClick={() => void handleSelectAllResults(true)}
                >
                  Selecionar todos os {totalFornecedoresCount} resultados
                </button>
              ) : null}
              {canReduceSelectionToPage ? (
                <button
                  type="button"
                  className="ops-selection-inline-action"
                  onClick={handleSelectCurrentPageOnly}
                >
                  Manter apenas os {fornecedores.length} itens desta pagina
                </button>
              ) : null}
            </div>
            <div className="ops-selection-actions">
              <button
                onClick={handleDeleteSelected}
                disabled={loading || modalLoading || isDeleting || selectedIds.length === 0}
                className="btn-danger btn-sm fornecedores-danger-action"
              >
                Deletar selecionado(s)
              </button>
            </div>
          </div>
        ) : null}

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
