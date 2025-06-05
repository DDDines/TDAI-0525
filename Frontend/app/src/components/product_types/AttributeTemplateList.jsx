// Frontend/app/src/components/product_types/AttributeTemplateList.jsx

import React from 'react';
// Importa o CSS da página pai para reutilizar os estilos
import '../../pages/TiposProdutoPage.css'; // <-- CAMINHO CORRIGIDO

const AttributeTemplateList = ({ attributes, onEdit, onDelete }) => {
  if (!attributes || attributes.length === 0) {
    return <p style={{ textAlign: 'center', color: 'var(--text-color-light)', padding: '2rem 0' }}>Nenhum atributo definido para este tipo de produto.</p>;
  }

  // Ordena os atributos pela propriedade 'display_order' antes de renderizar
  const sortedAttributes = [...attributes].sort((a, b) => a.display_order - b.display_order);

  return (
    <div>
      {sortedAttributes.map((attr) => (
        <div key={attr.id} className="attribute-template-card">
          <div className="main-info">
            <strong>{attr.label}</strong>
            <div className="details">
              <span className="detail-item" title={attr.attribute_key}><strong>Chave:</strong> {attr.attribute_key}</span>
              <span className="detail-item"><strong>Tipo:</strong> {attr.field_type}</span>
              {attr.is_required && <span className="detail-item"><strong style={{color: 'var(--danger)'}}>Obrigatório</strong></span>}
            </div>
            {attr.options && (
                 <div className="details" style={{marginTop: '5px'}}>
                    <span className="detail-item"><strong>Opções:</strong> {Array.isArray(attr.options) ? attr.options.join(', ') : attr.options}</span>
                 </div>
            )}
          </div>
          <div className="attr-controls">
            <div className="attr-actions">
              <button className="btn-small" style={{backgroundColor: 'var(--info)'}} onClick={() => onEdit(attr)}>Editar</button>
              <button className="btn-small btn-danger" onClick={() => onDelete(attr.id)}>Excluir</button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default AttributeTemplateList;