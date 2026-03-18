/**
 * Module import review page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { LuCircleCheck, LuCircleX, LuTriangleAlert, LuArrowLeft, LuThumbsUp } from 'react-icons/lu';
import apiClient from '../services/apiClient';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import './ImportReviewPage.css';

// ── helpers ──────────────────────────────────────────────────────────────────

function ScoreBadge({ score }) {
  if (score == null) return <span className="ir-badge ir-badge--none">—</span>;
  const pct = Math.round(score);
  if (pct >= 75) return <span className="ir-badge ir-badge--high">{pct}%</span>;
  if (pct >= 45) return <span className="ir-badge ir-badge--mid">{pct}%</span>;
  return <span className="ir-badge ir-badge--low">{pct}%</span>;
}

function FieldRow({ label, value, conf }) {
  const confClass =
    conf == null ? '' : conf >= 0.75 ? 'ir-conf--high' : conf >= 0.45 ? 'ir-conf--mid' : 'ir-conf--low';
  return (
    <tr>
      <td className="ir-field-label">{label}</td>
      <td className="ir-field-value">{value != null && value !== '' ? String(value) : <em className="ir-null">null</em>}</td>
      {conf != null && (
        <td className={`ir-field-conf ${confClass}`}>{(conf * 100).toFixed(0)}%</td>
      )}
    </tr>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export default function ImportReviewPage() {
  const { fileId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [selectedIndex, setSelectedIndex] = useState(0);
  const [remember, setRemember] = useState(false);
  const [batchThreshold, setBatchThreshold] = useState(75);

  // ── fetch quarantined items ──────────────────────────────────────────────
  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ['quarentena', fileId],
    queryFn: () =>
      apiClient.get(`/importacoes/${fileId}/quarentena`).then((r) => r.data),
    refetchOnWindowFocus: false,
  });

  // ── approve single item ──────────────────────────────────────────────────
  const approveMutation = useMutation({
    mutationFn: ({ index, rememberRule }) =>
      apiClient.post(`/importacoes/${fileId}/quarentena/${index}/aprovar`, {
        remember: rememberRule,
        min_quality_score: null,
      }),
    onSuccess: () => {
      showSuccessToast('Produto aprovado com sucesso!');
      queryClient.invalidateQueries({ queryKey: ['quarentena', fileId] });
      setSelectedIndex(0);
    },
    onError: (err) => showErrorToast(err.response?.data?.detail || 'Erro ao aprovar produto'),
  });

  // ── batch approve ────────────────────────────────────────────────────────
  const batchMutation = useMutation({
    mutationFn: () =>
      apiClient.post(`/importacoes/${fileId}/quarentena/aprovar-lote`, {
        min_quality_score: batchThreshold,
        remember,
      }),
    onSuccess: (res) => {
      showSuccessToast(`${res.data.aprovados} produto(s) aprovado(s)!`);
      queryClient.invalidateQueries({ queryKey: ['quarentena', fileId] });
      setSelectedIndex(0);
    },
    onError: (err) => showErrorToast(err.response?.data?.detail || 'Erro ao aprovar em lote'),
  });

  // ── render ───────────────────────────────────────────────────────────────
  if (isLoading) return <LoadingOverlay isOpen message="Carregando itens em quarentena..." />;
  if (isError)
    return (
      <div className="ir-error">
        <LuCircleX /> Erro ao carregar itens de quarentena.
      </div>
    );

  const selected = items[selectedIndex] ?? null;
  const rawData = selected?.raw_data ?? {};

  const DISPLAY_FIELDS = [
    { key: 'nome_base', label: 'Nome Base' },
    { key: 'sku_original', label: 'SKU' },
    { key: 'ean_original', label: 'EAN' },
    { key: 'descricao_original', label: 'Descrição' },
    { key: 'marca', label: 'Marca' },
    { key: 'categoria_original', label: 'Categoria' },
    { key: 'preco_original', label: 'Preço' },
  ];

  return (
    <div className="ir-page">
      {/* ── header ── */}
      <div className="ir-header">
        <button className="ir-back-btn" onClick={() => navigate('/fornecedores')}>
          <LuArrowLeft /> Voltar
        </button>
        <h1 className="ir-title">
          Revisão de Importação
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
              onChange={(e) => setBatchThreshold(Number(e.target.value))}
              className="ir-threshold-input"
            />
            %
          </label>
          <label className="ir-remember-label">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
            />
            Lembrar para este fornecedor
          </label>
          <button
            className="ir-btn ir-btn--primary"
            onClick={() => batchMutation.mutate()}
            disabled={batchMutation.isPending || items.length === 0}
          >
            <LuThumbsUp /> Aprovar em Lote
          </button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="ir-empty">
          <LuCircleCheck className="ir-empty-icon" />
          <p>Nenhum produto na fila de quarentena.</p>
          <button className="ir-btn ir-btn--secondary" onClick={() => navigate('/fornecedores')}>
            Voltar aos Fornecedores
          </button>
        </div>
      ) : (
        <div className="ir-body">
          {/* ── list panel ── */}
          <ul className="ir-list">
            {items.map((item, idx) => (
              <li
                key={idx}
                className={`ir-list-item ${idx === selectedIndex ? 'ir-list-item--active' : ''}`}
                onClick={() => setSelectedIndex(idx)}
              >
                <ScoreBadge score={item.quality_score} />
                <span className="ir-list-name">{item.nome_base || item.sku || `Produto #${idx + 1}`}</span>
              </li>
            ))}
          </ul>

          {/* ── detail panel ── */}
          {selected && (
            <div className="ir-detail">
              <div className="ir-detail-header">
                <span className="ir-detail-name">{selected.nome_base || selected.sku || `Produto #${selectedIndex + 1}`}</span>
                <ScoreBadge score={selected.quality_score} />
                {selected.reason && (
                  <span className="ir-detail-reason">
                    <LuTriangleAlert /> {selected.reason}
                  </span>
                )}
              </div>

              <table className="ir-fields-table">
                <thead>
                  <tr>
                    <th>Campo</th>
                    <th>Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {DISPLAY_FIELDS.map(({ key, label }) => (
                    <FieldRow key={key} label={label} value={rawData[key]} conf={null} />
                  ))}
                </tbody>
              </table>

              <div className="ir-detail-actions">
                <label className="ir-remember-label">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                  />
                  Lembrar para este fornecedor
                </label>
                <button
                  className="ir-btn ir-btn--primary"
                  onClick={() => approveMutation.mutate({ index: selectedIndex, rememberRule: remember })}
                  disabled={approveMutation.isPending}
                >
                  <LuCircleCheck /> Aprovar
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
