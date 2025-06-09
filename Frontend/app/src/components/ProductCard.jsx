import React from 'react';

const styles = {
  card: {
    border: '1px solid #e5e7eb',
    borderRadius: 'var(--radius)',
    padding: '1rem',
    marginBottom: '1rem',
    backgroundColor: '#fff',
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
  },
  title: { margin: '0 0 0.5rem 0' },
  actions: { marginTop: '0.5rem', display: 'flex', gap: '0.5rem' },
  btn: {
    padding: '0.25rem 0.6rem',
    cursor: 'pointer',
    borderRadius: 'var(--radius)',
    border: '1px solid #d1d5db',
    background: '#f9fafb'
  },
  deleteBtn: {
    background: '#fee2e2',
    borderColor: '#fecaca',
    color: '#b91c1c'
  }
};

function ProductCard({ produto, onEdit, onDelete }) {
  if (!produto) return null;

  return (
    <div className="product-card" style={styles.card}>
      <h3 style={styles.title}>{produto.nome_base || `Produto ${produto.id}`}</h3>
      <p><strong>SKU:</strong> {produto.sku || '--'}</p>
      <p><strong>Fornecedor:</strong> {produto.fornecedor_id || '--'}</p>
      <div style={styles.actions}>
        {onEdit && (
          <button onClick={() => onEdit(produto)} style={styles.btn} title="Editar Produto">✏️</button>
        )}
        {onDelete && (
          <button onClick={() => onDelete(produto.id)} style={{...styles.btn, ...styles.deleteBtn}} title="Excluir Produto">🗑️</button>
        )}
      </div>
    </div>
  );
}

export default ProductCard;
