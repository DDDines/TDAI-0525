// Frontend/app/src/components/common/PaginationControls.jsx
import React from 'react';

function PaginationControls({ currentPage, totalPages, onPageChange, isLoading }) {
  if (totalPages <= 1) {
    return null; // Não mostra controlos se houver apenas uma página ou nenhuma
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
    <div className="pagination-controls" style={{ marginTop: '1.5rem', marginBottom: '0.5rem', textAlign: 'center', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '10px' }}>
      <button 
        onClick={handlePrevious} 
        disabled={currentPage === 0 || isLoading}
        style={{ padding: '0.5em 1em' }}
      >
        Anterior
      </button>
      <span style={{ margin: '0 10px', fontSize: '0.9em', color: '#555' }}>
        Página {currentPage + 1} de {totalPages}
      </span>
      <button 
        onClick={handleNext} 
        disabled={currentPage === totalPages - 1 || isLoading}
        style={{ padding: '0.5em 1em' }}
      >
        Próxima
      </button>
    </div>
  );
}

export default PaginationControls;
