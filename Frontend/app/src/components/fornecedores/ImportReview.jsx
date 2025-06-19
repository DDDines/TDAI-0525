import React, { useEffect, useState } from 'react';
import Modal from '../common/Modal';
import LoadingPopup from '../common/LoadingPopup';
import PaginationControls from '../common/PaginationControls';
import fornecedorService from '../../services/fornecedorService';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';

const ImportReview = ({ jobId, isOpen, onClose }) => {
  const [items, setItems] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [page, setPage] = useState(0);
  const [limit, setLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [committing, setCommitting] = useState(false);

  useEffect(() => {
    if (!isOpen || !jobId) return;
    const fetchData = async () => {
      setLoading(true);
      try {
        const data = await fornecedorService.getReviewData(jobId, {
          skip: page * limit,
          limit,
        });
        if (data.items) {
          setItems(data.items);
          setTotalItems(data.total_items ?? data.items.length);
        } else {
          setItems(data);
          setTotalItems(Array.isArray(data) ? data.length : 0);
        }
      } catch (err) {
        console.error('Erro ao obter dados de revisão:', err);
        const msg = err?.detail || err.message || 'Falha ao carregar dados.';
        showErrorToast(msg);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [jobId, page, limit, isOpen]);

  const headers = items.length > 0 ? Object.keys(items[0]) : [];
  const totalPages = totalItems > 0 ? Math.ceil(totalItems / limit) : 1;

  const handleCommit = async () => {
    setCommitting(true);
    try {
      await fornecedorService.commitImport(jobId);
      showSuccessToast('Importação confirmada com sucesso!');
      if (onClose) onClose();
    } catch (err) {
      console.error('Erro ao confirmar importação:', err);
      const msg = err?.detail || err.message || 'Falha ao confirmar importação.';
      showErrorToast(msg);
    } finally {
      setCommitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Revisar Importação">
      <LoadingPopup isOpen={loading} message="Carregando revisão..." />
      <p>Serão criados {totalItems} produtos.</p>
      <div className="table-responsive">
        <table className="fornecedor-review-table">
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((row, idx) => (
              <tr key={idx}>
                {headers.map((h) => (
                  <td key={h}>{row[h]}</td>
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
        <button onClick={onClose} disabled={loading || committing}>Fechar</button>
        <button
          onClick={handleCommit}
          disabled={loading || committing}
          style={{ marginLeft: '0.5em' }}
        >
          {committing ? 'Salvando...' : 'Confirmar e Salvar Tudo'}
        </button>
      </div>
    </Modal>
  );
};

export default ImportReview;
