// Frontend/app/src/components/common/PaginationControls.jsx
import React from 'react';

function PaginationControls({
  currentPage,
  totalPages,
  onPageChange,
  isLoading,
  itemsPerPage,
  onItemsPerPageChange,
  totalItems,
}) {
  if (totalPages <= 1 && !itemsPerPage) {
    // Mantém comportamento antigo se o seletor de itens não for usado
    return null;
  }

  const handlePrevious = () => {
    if (currentPage > 0) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages - 1) {
      onPageChange(currentPage + 1);
    }
  };

  return (
    <div
      className="pagination-controls"
      style={{
        marginTop: '1.5rem',
        marginBottom: '0.5rem',
        textAlign: 'center',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '10px',
        flexWrap: 'wrap',
      }}
    >
      <button
        onClick={handlePrevious}
        disabled={currentPage === 0 || isLoading}
        style={{ padding: '0.5em 1em' }}
      >
        Anterior
      </button>
      <span style={{ margin: '0 10px', fontSize: '0.9em', color: '#555' }}>
        Página {currentPage + 1} de {totalPages}
        {typeof totalItems === 'number' && (
          <span style={{ marginLeft: '0.5rem' }}>({totalItems} itens)</span>
        )}
      </span>
      <button
        onClick={handleNext}
        disabled={currentPage === totalPages - 1 || isLoading}
        style={{ padding: '0.5em 1em' }}
      >
        Próxima
      </button>
      {typeof itemsPerPage === 'number' && onItemsPerPageChange && (
        <select
          style={{ marginLeft: '0.5rem' }}
          value={itemsPerPage}
          onChange={(e) => onItemsPerPageChange(e.target.value)}
        >
          {[5, 10, 25, 50, 100].map((num) => (
            <option key={num} value={num}>
              {num}/página
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

export default PaginationControls;
