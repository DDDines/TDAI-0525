/**
 * Module import review.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useEffect, useState } from 'react';
import Modal from '../common/Modal';
import LoadingPopup from '../common/LoadingPopup';
import PaginationControls from '../common/PaginationControls';
import fornecedorService from '../../services/fornecedorService';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';
import { extractErrorMessage } from '../../utils/errorDetails';

function formatCellValue(value) {
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function normalizeReviewData(data) {
  if (Array.isArray(data?.items)) {
    return {
      items: data.items,
      totalItems: data.total_items ?? data.items.length,
    };
  }

  if (Array.isArray(data)) {
    return {
      items: data,
      totalItems: data.length,
    };
  }

  return {
    items: [],
    totalItems: typeof data?.total_items === 'number' ? data.total_items : 0,
  };
}

function ImportReview({ jobId, isOpen, onClose }) {
  const [items, setItems] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [page, setPage] = useState(0);
  const [limit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);

  useEffect(() => {
    if (!isOpen || !jobId) {
      return;
    }

    let cancelled = false;

    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await fornecedorService.getReviewData(jobId, {
          skip: page * limit,
          limit,
        });
        if (cancelled) {
          return;
        }
        const normalized = normalizeReviewData(data);
        setItems(normalized.items);
        setTotalItems(normalized.totalItems);
      } catch (error) {
        if (!cancelled) {
          showErrorToast(extractErrorMessage(error, 'Falha ao carregar dados.'));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchData();

    return () => {
      cancelled = true;
    };
  }, [jobId, page, limit, isOpen]);

  const headers = items.length > 0 ? Object.keys(items[0]) : [];
  const totalPages = totalItems > 0 ? Math.ceil(totalItems / limit) : 1;

  const handleCommit = async () => {
    setCommitting(true);
    try {
      await fornecedorService.commitImport(jobId);
      showSuccessToast('Importação confirmada com sucesso!');
      onClose?.();
    } catch (error) {
      showErrorToast(extractErrorMessage(error, 'Falha ao confirmar importação.'));
    } finally {
      setCommitting(false);
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Revisar importação">
      <LoadingPopup isOpen={loading} message="Carregando revisão..." />
      <p>Serão criados {totalItems} produtos.</p>
      <div className="table-responsive">
        <table className="fornecedor-review-table">
          <thead>
            <tr>
              {headers.map((header) => (
                <th key={header}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((row, index) => (
              <tr key={index}>
                {headers.map((header) => (
                  <td key={header}>{formatCellValue(row[header])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <PaginationControls
        currentPage={page}
        totalPages={totalPages}
        onPageChange={setPage}
        isLoading={loading}
      />

      <div style={{ marginTop: '1rem' }}>
        <button type="button" onClick={onClose} disabled={loading || committing}>
          Fechar
        </button>
        <button
          type="button"
          onClick={handleCommit}
          disabled={loading || committing}
          style={{ marginLeft: '0.5em' }}
        >
          {committing ? 'Salvando...' : 'Confirmar e salvar tudo'}
        </button>
      </div>
    </Modal>
  );
}

export default ImportReview;
