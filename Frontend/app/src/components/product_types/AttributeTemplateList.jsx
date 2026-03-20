/**
 * Module attribute template list.
 *
 * Defines responsibilities and integration points for components product types.
 */

import React from 'react';
import { LuArrowDown, LuArrowUp, LuPencil, LuSparkles, LuTrash2 } from 'react-icons/lu';
import '../../pages/TiposProdutoPage.css';

function formatFieldTypeLabel(fieldType) {
  const normalizedType = String(fieldType || '').toLowerCase();
  const labels = {
    text: 'texto',
    textarea: 'texto longo',
    number: 'numero',
    boolean: 'sim/nao',
    select: 'selecao unica',
    multiselect: 'selecao multipla',
    date: 'data',
  };
  return labels[normalizedType] || normalizedType || '--';
}

function AttributeTemplateList({ attributes, onEdit, onDelete, onReorder }) {
  if (!attributes || attributes.length === 0) {
    return (
      <div className="tipos-produto-empty-state tipos-produto-empty-state--compact">
        <span className="tipos-produto-empty-icon">
          <LuSparkles />
        </span>
        <strong>Nenhum atributo definido ainda</strong>
        <p>Adicione campos para orientar o enrichment e a geracao com mais precisao.</p>
      </div>
    );
  }

  const sortedAttributes = [...attributes].sort((a, b) => a.display_order - b.display_order);

  return (
    <div className="attribute-template-list">
      {sortedAttributes.map((attribute, index) => (
        <article key={attribute.id} className="attribute-template-card">
          <div className="attribute-template-main">
            <div className="attribute-template-title-row">
              <strong>{attribute.label}</strong>
              <span className="attribute-template-badge">{formatFieldTypeLabel(attribute.field_type)}</span>
              {attribute.is_required ? (
                <span className="attribute-template-badge required">Obrigatorio</span>
              ) : null}
              {attribute.collect_in_ai !== false ? (
                <span className="attribute-template-badge ai">Usado pela IA</span>
              ) : null}
            </div>

            <div className="attribute-template-meta">
              <span title={attribute.attribute_key}>
                <strong>Chave:</strong> {attribute.attribute_key}
              </span>
              <span>
                <strong>Ordem:</strong> {attribute.display_order}
              </span>
              {attribute.tooltip_text ? (
                <span>
                  <strong>Ajuda:</strong> {attribute.tooltip_text}
                </span>
              ) : null}
            </div>

            {attribute.options ? (
              <div className="attribute-template-options">
                <strong>Opcoes:</strong>{' '}
                {Array.isArray(attribute.options) ? attribute.options.join(', ') : attribute.options}
              </div>
            ) : null}
          </div>

          <div className="attribute-template-controls">
            <div className="attribute-template-reorder">
              <button
                type="button"
                className="attribute-template-icon-button"
                onClick={() => onReorder(attribute.id, 'up')}
                disabled={index === 0}
                title="Mover para cima"
              >
                <LuArrowUp />
              </button>
              <button
                type="button"
                className="attribute-template-icon-button"
                onClick={() => onReorder(attribute.id, 'down')}
                disabled={index === sortedAttributes.length - 1}
                title="Mover para baixo"
              >
                <LuArrowDown />
              </button>
            </div>
            <div className="attribute-template-actions">
              <button
                type="button"
                className="attribute-template-action-button edit"
                onClick={() => onEdit(attribute)}
              >
                <LuPencil />
                Editar
              </button>
              <button
                type="button"
                className="attribute-template-action-button delete"
                onClick={() => onDelete(attribute.id)}
              >
                <LuTrash2 />
                Excluir
              </button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

export default AttributeTemplateList;
