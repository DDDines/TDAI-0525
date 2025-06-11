// Frontend/app/src/components/common/PaginationControls.jsx
import React from 'react';
import './PaginationControls.css';

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
    <div className="pagination-controls">
      <button
        onClick={handlePrevious}
        disabled={currentPage === 0 || isLoading}
        className="pagination-button"
      >
        Anterior
      </button>
      <span className="pagination-info">
        Página {currentPage + 1} de {totalPages}
        {typeof totalItems === 'number' && (
          <span className="total-items">({totalItems} itens)</span>
        )}
      </span>
      <button
        onClick={handleNext}
        disabled={currentPage === totalPages - 1 || isLoading}
        className="pagination-button"
      >
        Próxima
      </button>
      {typeof itemsPerPage === 'number' && onItemsPerPageChange && (
        <select
          className="items-per-page-select"
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
