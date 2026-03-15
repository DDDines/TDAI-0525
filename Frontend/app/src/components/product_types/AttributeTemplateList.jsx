/**
 * Module attribute template list.
 *
 * Defines responsibilities and integration points for components product types.
 */

import React from 'react';
import '../../pages/TiposProdutoPage.css';

function AttributeTemplateList({ attributes, onEdit, onDelete, onReorder }) {
  if (!attributes || attributes.length === 0) {
    return (
      <p style={{ textAlign: 'center', color: 'var(--text-color-light)', padding: '2rem 0' }}>
        Nenhum atributo definido para este tipo de produto.
      </p>
    );
  }

  const sortedAttributes = [...attributes].sort((a, b) => a.display_order - b.display_order);

  return (
    <div>
      {sortedAttributes.map((attr, index) => (
        <div key={attr.id} className="attribute-template-card">
          <div className="main-info">
            <strong>{attr.label}</strong>
            <div className="details">
              <span className="detail-item" title={attr.attribute_key}>
                <strong>Chave:</strong> {attr.attribute_key}
              </span>
              <span className="detail-item">
                <strong>Tipo:</strong> {attr.field_type}
              </span>
              {attr.is_required ? (
                <span className="detail-item">
                  <strong style={{ color: 'var(--danger)' }}>Obrigatório</strong>
                </span>
              ) : null}
              {attr.collect_in_ai !== false ? (
                <span className="detail-item">
                  <strong style={{ color: 'var(--success)' }}>Usado pela IA</strong>
                </span>
              ) : null}
            </div>
            {attr.options ? (
              <div className="details" style={{ marginTop: '5px' }}>
                <span className="detail-item">
                  <strong>Opções:</strong>{' '}
                  {Array.isArray(attr.options) ? attr.options.join(', ') : attr.options}
                </span>
              </div>
            ) : null}
          </div>
          <div className="attr-controls">
            <div className="attr-order-icons">
              <button
                onClick={() => onReorder(attr.id, 'up')}
                disabled={index === 0}
                title="Mover para Cima"
                className="btn-icon btn-small"
              >
                ^
              </button>
              <button
                onClick={() => onReorder(attr.id, 'down')}
                disabled={index === sortedAttributes.length - 1}
                title="Mover para Baixo"
                className="btn-icon btn-small"
              >
                v
              </button>
            </div>
            <div className="attr-actions">
              <button
                className="btn-small"
                style={{ backgroundColor: 'var(--info)' }}
                onClick={() => onEdit(attr)}
              >
                Editar
              </button>
              <button className="btn-small btn-danger" onClick={() => onDelete(attr.id)}>
                Excluir
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default AttributeTemplateList;
