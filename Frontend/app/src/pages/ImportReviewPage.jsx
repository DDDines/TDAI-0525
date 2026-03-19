/**
 * Import review page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LuArrowLeft,
  LuCircleCheck,
  LuCircleX,
  LuThumbsUp,
  LuTriangleAlert,
} from 'react-icons/lu';
import apiClient from '../services/apiClient';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import { extractErrorMessage } from '../utils/errorDetails';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import './ImportReviewPage.css';

function ScoreBadge({ score }) {
  if (score == null) {
    return <span className="ir-badge ir-badge--none">—</span>;
  }

  const pct = Math.round(score);
  if (pct >= 75) {
    return <span className="ir-badge ir-badge--high">{pct}%</span>;
  }
  if (pct >= 45) {
    return <span className="ir-badge ir-badge--mid">{pct}%</span>;
  }
  return <span className="ir-badge ir-badge--low">{pct}%</span>;
}

function FieldRow({ label, value, conf }) {
  const confClass =
    conf == null ? '' : conf >= 0.75 ? 'ir-conf--high' : conf >= 0.45 ? 'ir-conf--mid' : 'ir-conf--low';

  return (
    <tr>
      <td className="ir-field-label">{label}</td>
      <td className="ir-field-value">
        {value != null && value !== '' ? String(value) : <em className="ir-null">null</em>}
      </td>
      {conf != null ? (
        <td className={`ir-field-conf ${confClass}`}>{(conf * 100).toFixed(0)}%</td>
      ) : null}
    </tr>
  );
}

export default function ImportReviewPage() {
  const { fileId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [remember, setRemember] = useState(false);
  const [batchThreshold, setBatchThreshold] = useState(75);

  const reviewQuery = useQuery({
    queryKey: ['quarentena', fileId],
    queryFn: async () => {
      const response = await apiClient.get(`/importacoes/${fileId}/quarentena`);
      return Array.isArray(response.data) ? response.data : [];
    },
    refetchOnWindowFocus: false,
  });

  const items = useMemo(
    () => (Array.isArray(reviewQuery.data) ? reviewQuery.data : []),
    [reviewQuery.data]
  );

  useEffect(() => {
    if (selectedIndex >= items.length) {
      setSelectedIndex(items.length > 0 ? items.length - 1 : 0);
    }
  }, [items.length, selectedIndex]);

  const approveMutation = useMutation({
    mutationFn: ({ index, rememberRule }) =>
      apiClient.post(`/importacoes/${fileId}/quarentena/${index}/aprovar`, {
        remember: rememberRule,
        min_quality_score: null,
      }),
    onSuccess: () => {
      showSuccessToast('Produto aprovado com sucesso.');
      void queryClient.invalidateQueries({ queryKey: ['quarentena', fileId] });
      setSelectedIndex(0);
    },
    onError: (error) => {
      showErrorToast(extractErrorMessage(error, 'Erro ao aprovar produto.'));
    },
  });

  const batchMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`/importacoes/${fileId}/quarentena/aprovar-lote`, {
        min_quality_score: batchThreshold,
        remember,
      }),
    onSuccess: (response) => {
      showSuccessToast(`${response.data.aprovados} produto(s) aprovado(s).`);
      void queryClient.invalidateQueries({ queryKey: ['quarentena', fileId] });
      setSelectedIndex(0);
    },
    onError: (error) => {
      showErrorToast(extractErrorMessage(error, 'Erro ao aprovar em lote.'));
    },
  });

  if (reviewQuery.isLoading) {
    return <LoadingOverlay isOpen message="Carregando itens em quarentena..." />;
  }

  if (reviewQuery.isError) {
    return (
      <div className="ir-error" role="alert">
        <LuCircleX />
        <div className="ir-error-copy">
          <p>{extractErrorMessage(reviewQuery.error, 'Erro ao carregar itens de quarentena.')}</p>
          <button
            type="button"
            className="ir-btn ir-btn--secondary"
            onClick={() => void reviewQuery.refetch()}
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  const selected = items[selectedIndex] ?? null;
  const rawData = selected?.raw_data ?? {};
  const displayFields = [
    { key: 'nome_base', label: 'Nome base' },
    { key: 'sku_original', label: 'SKU' },
    { key: 'ean_original', label: 'EAN' },
    { key: 'descricao_original', label: 'Descrição' },
    { key: 'marca', label: 'Marca' },
    { key: 'categoria_original', label: 'Categoria' },
    { key: 'preco_original', label: 'Preço' },
  ];

  return (
    <div className="ir-page">
      <div className="ir-header">
        <button type="button" className="ir-back-btn" onClick={() => navigate('/fornecedores')}>
          <LuArrowLeft />
          Voltar
        </button>
        <h1 className="ir-title">
          Revisão de importação
          <span className="ir-subtitle"> — {items.length} produto(s) aguardando revisão</span>
        </h1>

        <div className="ir-batch-controls">
          <label className="ir-threshold-label">
            Aprovar todos com score ≥
            <input
              type="number"
              min={0}
              max={100}
              value={batchThreshold}
              onChange={(event) => setBatchThreshold(Number(event.target.value))}
              className="ir-threshold-input"
            />
            %
          </label>
          <label className="ir-remember-label">
            <input
              type="checkbox"
              checked={remember}
              onChange={(event) => setRemember(event.target.checked)}
            />
            Lembrar para este fornecedor
          </label>
          <button
            type="button"
            className="ir-btn ir-btn--primary"
            onClick={() => batchMutation.mutate()}
            disabled={batchMutation.isPending || items.length === 0}
          >
            <LuThumbsUp />
            Aprovar em lote
          </button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="ir-empty">
          <LuCircleCheck className="ir-empty-icon" />
          <p>Nenhum produto na fila de quarentena.</p>
          <button className="ir-btn ir-btn--secondary" onClick={() => navigate('/fornecedores')}>
            Voltar aos fornecedores
          </button>
        </div>
      ) : (
        <div className="ir-body">
          <ul className="ir-list">
            {items.map((item, index) => (
              <li
                key={`${item?.sku || item?.nome_base || index}`}
                className={`ir-list-item ${index === selectedIndex ? 'ir-list-item--active' : ''}`}
                onClick={() => setSelectedIndex(index)}
              >
                <ScoreBadge score={item.quality_score} />
                <span className="ir-list-name">{item.nome_base || item.sku || `Produto #${index + 1}`}</span>
              </li>
            ))}
          </ul>

          {selected ? (
            <div className="ir-detail">
              <div className="ir-detail-header">
                <span className="ir-detail-name">
                  {selected.nome_base || selected.sku || `Produto #${selectedIndex + 1}`}
                </span>
                <ScoreBadge score={selected.quality_score} />
                {selected.reason ? (
                  <span className="ir-detail-reason">
                    <LuTriangleAlert />
                    {selected.reason}
                  </span>
                ) : null}
              </div>

              <table className="ir-fields-table">
                <thead>
                  <tr>
                    <th>Campo</th>
                    <th>Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {displayFields.map(({ key, label }) => (
                    <FieldRow key={key} label={label} value={rawData[key]} conf={null} />
                  ))}
                </tbody>
              </table>

              <div className="ir-detail-actions">
                <label className="ir-remember-label">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(event) => setRemember(event.target.checked)}
                  />
                  Lembrar para este fornecedor
                </label>
                <button
                  type="button"
                  className="ir-btn ir-btn--primary"
                  onClick={() =>
                    approveMutation.mutate({ index: selectedIndex, rememberRule: remember })
                  }
                  disabled={approveMutation.isPending}
                >
                  <LuCircleCheck />
                  Aprovar
                </button>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
