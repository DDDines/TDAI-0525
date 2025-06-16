import React, { useState, useEffect } from 'react';
import Modal from './Modal.jsx';

function ColumnMappingModal({
  isOpen,
  onClose,
  headers = [],
  rows = [],
  fieldOptions = [],
  onConfirm,
}) {
  const [mapping, setMapping] = useState({});

  useEffect(() => {
    if (isOpen) setMapping({});
  }, [isOpen]);

  const handleChange = (header, value) => {
    setMapping((prev) => ({ ...prev, [header]: value }));
  };

  const handleConfirm = () => {
    if (onConfirm) onConfirm(mapping);
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Mapear Colunas">
      <table className="mapping-table">
        <thead>
          <tr>
            <th>Coluna</th>
            <th>Campo</th>
          </tr>
        </thead>
        <tbody>
          {headers.map((h) => (
            <tr key={h}>
              <td>{h}</td>
              <td>
                <select
                  value={mapping[h] || ''}
                  onChange={(e) => handleChange(h, e.target.value)}
                >
                  <option value="">Ignorar</option>
                  {fieldOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 0 && (
        <table className="preview-table">
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={idx}>
                {headers.map((h) => (
                  <td key={h}>{row[h]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="modal-actions">
        <button onClick={handleConfirm}>Confirmar mapeamento</button>
      </div>
    </Modal>
  );
}

export default ColumnMappingModal;
