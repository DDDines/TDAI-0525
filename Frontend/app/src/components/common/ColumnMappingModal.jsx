/**
 * Module column mapping modal.
 */

import { useEffect, useRef, useState } from 'react';
import Modal from './Modal.jsx';
import './ColumnMappingModal.css';

const UNIQUE_BASE_FIELDS = new Set([
  'nome_base', 'sku_original', 'ean_original', 'preco_original',
  'marca', 'categoria_original', 'auto:sku_nome',
]);

function normalizeMapping(value) {
  if (!value || typeof value !== 'object') return {};
  return { ...value };
}

function normalizeMappingValue(value) {
  if (value === null || value === undefined) return '';
  return String(value);
}

function areMappingsEqual(left, right) {
  const a = normalizeMapping(left);
  const b = normalizeMapping(right);
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);
  if (aKeys.length !== bKeys.length) return false;
  for (const key of aKeys) {
    if (normalizeMappingValue(a[key]) !== normalizeMappingValue(b[key])) return false;
  }
  return true;
}

function ColumnMappingModal({
  isOpen,
  onClose,
  headers = [],
  rows = [],
  fieldOptions = [],
  productTypes = [],
  productTypeId = '',
  onProductTypeChange,
  initialMapping = null,
  onConfirm,
}) {
  const [mapping, setMapping] = useState({});
  const lastSyncedInitialRef = useRef(null);

  useEffect(() => {
    if (!isOpen) { lastSyncedInitialRef.current = null; return; }
    const normalizedInitial = normalizeMapping(initialMapping);
    const shouldSync =
      lastSyncedInitialRef.current === null ||
      !areMappingsEqual(lastSyncedInitialRef.current, normalizedInitial);
    if (!shouldSync) return;
    setMapping((prev) => areMappingsEqual(prev, normalizedInitial) ? prev : normalizedInitial);
    lastSyncedInitialRef.current = normalizedInitial;
  }, [isOpen, initialMapping]);

  const handleChange = (header, value) => {
    setMapping((prev) => {
      const next = { ...prev };
      if (value && UNIQUE_BASE_FIELDS.has(value)) {
        Object.keys(next).forEach((key) => {
          if (key !== header && next[key] === value) next[key] = '';
        });
      }
      next[header] = value;
      return next;
    });
  };

  const mappedColumnsCount = Object.values(mapping).filter(Boolean).length;

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Mapear Colunas" size="fullscreen" bodyClassName="cmm-modal-body">
      {/* Top bar */}
      <div className="cmm-topbar">
        {productTypes.length > 0 && (
          <div className="cmm-product-type-row">
            <label htmlFor="cmm-product-type">Tipo de Produto:</label>
            <select
              id="cmm-product-type"
              value={productTypeId || ''}
              onChange={(e) => onProductTypeChange && onProductTypeChange(e.target.value)}
              className="cmm-product-type-select"
            >
              <option value="">Selecione...</option>
              {productTypes.map((pt) => {
                const val = pt.id;
                if (val === null || val === undefined) return null;
                const label = pt.friendly_name || pt.nome || pt.name || pt.slug || pt.key_name || val;
                return <option key={val} value={val}>{label}</option>;
              })}
            </select>
          </div>
        )}
        <span className="cmm-badge">{mappedColumnsCount} / {headers.length} mapeadas</span>
      </div>

      {/* Split layout */}
      <div className="cmm-split">
        {/* Left: mapping list */}
        <div className="cmm-left">
          <p className="cmm-panel-label">Mapeamento</p>
          <div className="cmm-list">
            {headers.map((header) => {
              const value = mapping[header] || '';
              const isMapped = Boolean(value);
              return (
                <div key={header} className={`cmm-row${isMapped ? ' cmm-row--mapped' : ''}`}>
                  <span className="cmm-col-badge">{header}</span>
                  <select
                    className="cmm-row-select"
                    value={value}
                    onChange={(e) => handleChange(header, e.target.value)}
                    aria-label={`Campo para coluna ${header}`}
                  >
                    <option value="">Ignorar</option>
                    {fieldOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>
          <p className="cmm-tip">
            Dica: mapeie mais de uma coluna para <strong>Descrição</strong> — os valores são concatenados.
          </p>
        </div>

        {/* Right: preview table */}
        {rows.length > 0 && (
          <div className="cmm-right">
            <p className="cmm-panel-label">Dados extraídos ({rows.length} linhas)</p>
            <div className="cmm-preview-scroll">
              <table className="cmm-preview-table">
                <thead>
                  <tr>
                    {headers.map((h) => {
                      const mapped = mapping[h];
                      const fieldLabel = mapped
                        ? (fieldOptions.find(o => o.value === mapped)?.label || mapped)
                        : null;
                      return (
                        <th key={h} className={mapped ? 'cmm-th--mapped' : ''}>
                          {h}
                          {fieldLabel && <span className="cmm-th-field"><br />{fieldLabel}</span>}
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, idx) => (
                    <tr key={idx}>
                      {headers.map((h) => {
                        const cell = row?.[h];
                        const display = cell === null || cell === undefined
                          ? '' : typeof cell === 'object' ? JSON.stringify(cell) : cell;
                        return (
                          <td key={h} className={mapping[h] ? 'cmm-td--mapped' : ''}>
                            {display}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="cmm-actions">
        <button type="button" className="cmm-btn-secondary" onClick={() => setMapping({})}>
          Limpar mapeamento
        </button>
        <button type="button" className="cmm-btn-primary" onClick={() => onConfirm && onConfirm(mapping)}>
          Confirmar mapeamento
        </button>
      </div>
    </Modal>
  );
}

export default ColumnMappingModal;
