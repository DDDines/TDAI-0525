import React, { useEffect, useRef, useState } from 'react';
import Modal from './Modal.jsx';
import './ColumnMappingModal.css';

const UNIQUE_BASE_FIELDS = new Set([
  'nome_base',
  'sku_original',
  'ean_original',
  'preco_original',
  'marca',
  'categoria_original',
  'auto:sku_nome',
]);

const normalizeMapping = (value) => {
  if (!value || typeof value !== 'object') return {};
  return { ...value };
};

const areMappingsEqual = (left, right) => {
  const a = left || {};
  const b = right || {};
  const aKeys = Object.keys(a);
  const bKeys = Object.keys(b);

  if (aKeys.length !== bKeys.length) return false;
  for (const key of aKeys) {
    if ((a[key] || '') !== (b[key] || '')) return false;
  }
  return true;
};

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
    if (!isOpen) {
      lastSyncedInitialRef.current = null;
      return;
    }

    const normalizedInitial = normalizeMapping(initialMapping);
    const shouldSync =
      lastSyncedInitialRef.current === null ||
      !areMappingsEqual(lastSyncedInitialRef.current, normalizedInitial);

    if (!shouldSync) return;

    setMapping((prev) => (areMappingsEqual(prev, normalizedInitial) ? prev : normalizedInitial));
    lastSyncedInitialRef.current = normalizedInitial;
  }, [isOpen, initialMapping]);

  const handleChange = (header, value) => {
    setMapping((prev) => {
      const next = { ...prev };

      if (value && UNIQUE_BASE_FIELDS.has(value)) {
        Object.keys(next).forEach((key) => {
          if (key !== header && next[key] === value) {
            next[key] = '';
          }
        });
      }

      next[header] = value;
      return next;
    });
  };

  const handleConfirm = () => {
    if (onConfirm) onConfirm(mapping);
  };

  const handleClearMapping = () => {
    setMapping({});
  };

  const isOptionDisabledForHeader = (header, optionValue) => {
    if (!UNIQUE_BASE_FIELDS.has(optionValue)) return false;
    return Object.entries(mapping).some(
      ([mappedHeader, mappedValue]) => mappedHeader !== header && mappedValue === optionValue
    );
  };

  const mappedColumnsCount = Object.values(mapping).filter(Boolean).length;

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Mapear Colunas">
      <div className="column-mapping-header">
        <p className="column-mapping-description">
          Defina para qual campo cada coluna deve ir. Campos únicos (SKU, EAN, Preço, etc.) só podem ser usados uma vez.
        </p>
        <p className="column-mapping-summary">
          Colunas mapeadas: <strong>{mappedColumnsCount}</strong> de <strong>{headers.length}</strong>
        </p>
      </div>

      {productTypes.length > 0 && (
        <div className="column-mapping-product-type">
          <label htmlFor="column-mapping-product-type-select">
            Tipo de Produto:
            <select
              id="column-mapping-product-type-select"
              value={productTypeId || ''}
              onChange={(e) => onProductTypeChange && onProductTypeChange(e.target.value)}
              className="column-mapping-product-type-select"
            >
              <option value="">Selecione...</option>
              {productTypes.map((pt) => {
                const value = pt.id;
                if (value === null || value === undefined) return null;
                const label = pt.friendly_name || pt.nome || pt.name || pt.slug || pt.key_name || value;
                return (
                  <option key={value} value={value}>
                    {label}
                  </option>
                );
              })}
            </select>
          </label>
        </div>
      )}

      <div className="column-mapping-table-wrap">
        <table className="mapping-table">
          <thead>
            <tr>
              <th>Coluna</th>
              <th>Campo</th>
            </tr>
          </thead>
          <tbody>
            {headers.map((header) => (
              <tr key={header}>
                <td>{header}</td>
                <td>
                  <select
                    value={mapping[header] || ''}
                    onChange={(e) => handleChange(header, e.target.value)}
                    aria-label={`Campo para coluna ${header}`}
                  >
                    <option value="">Ignorar</option>
                    {fieldOptions.map((option) => (
                      <option
                        key={option.value}
                        value={option.value}
                        disabled={isOptionDisabledForHeader(header, option.value)}
                      >
                        {option.label}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="column-mapping-tip">
        Dica: você pode mapear mais de uma coluna para <strong>Descrição</strong>. O sistema junta os valores automaticamente.
      </p>

      {rows.length > 0 && (
        <div className="column-mapping-table-wrap">
          <table className="preview-table">
            <thead>
              <tr>
                {headers.map((header) => (
                  <th key={header}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={idx}>
                  {headers.map((header) => {
                    const cell = row?.[header];
                    const display =
                      cell === null || cell === undefined
                        ? ''
                        : typeof cell === 'object'
                          ? JSON.stringify(cell)
                          : cell;
                    return <td key={header}>{display}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="modal-actions">
        <button type="button" onClick={handleClearMapping}>
          Limpar mapeamento
        </button>
        <button type="button" className="btn-primary" onClick={handleConfirm}>
          Confirmar mapeamento
        </button>
      </div>
    </Modal>
  );
}

export default ColumnMappingModal;

