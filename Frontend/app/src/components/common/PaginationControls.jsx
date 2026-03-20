/**
 * Module pagination controls.
 *
 * Defines responsibilities and integration points for components common.
 */

import React, { useEffect, useRef, useState } from 'react';
import { LuCheck, LuChevronDown } from 'react-icons/lu';
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
  const [isSizeMenuOpen, setIsSizeMenuOpen] = useState(false);
  const sizeMenuRef = useRef(null);

  useEffect(() => {
    if (!isSizeMenuOpen) {
      return undefined;
    }

    const handlePointerDown = (event) => {
      if (sizeMenuRef.current && !sizeMenuRef.current.contains(event.target)) {
        setIsSizeMenuOpen(false);
      }
    };

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsSizeMenuOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isSizeMenuOpen]);

  if (totalPages <= 1 && !itemsPerPage) {
    // Mantem comportamento antigo se o seletor de itens nao for usado.
    return null;
  }

  const handlePrevious = () => {
    onPageChange(currentPage - 1);
  };

  const handleNext = () => {
    onPageChange(currentPage + 1);
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
        {'P\u00E1gina'} {currentPage + 1} de {totalPages}
        {typeof totalItems === 'number' ? (
          <span className="total-items">({totalItems} itens)</span>
        ) : null}
      </span>

      <button
        onClick={handleNext}
        disabled={currentPage === totalPages - 1 || isLoading}
        className="pagination-button"
      >
        {'Pr\u00F3xima'}
      </button>

      {typeof itemsPerPage === 'number' && onItemsPerPageChange ? (
        <div className="items-per-page-field" ref={sizeMenuRef}>
          <button
            type="button"
            className={`items-per-page-trigger${isSizeMenuOpen ? ' is-open' : ''}`}
            aria-label={'Itens por p\u00E1gina'}
            aria-haspopup="menu"
            aria-expanded={isSizeMenuOpen}
            disabled={isLoading}
            onClick={() => setIsSizeMenuOpen((current) => !current)}
          >
            <span>{`${itemsPerPage}/página`}</span>
            <LuChevronDown className="items-per-page-icon" aria-hidden="true" />
          </button>

          {isSizeMenuOpen ? (
            <div className="items-per-page-dropdown" role="menu" aria-label="Opções de itens por página">
              {[5, 10, 25, 50, 100].map((num) => {
                const isActive = Number(itemsPerPage) === num;
                return (
                  <button
                    key={num}
                    type="button"
                    role="menuitemradio"
                    aria-checked={isActive}
                    className={`items-per-page-option${isActive ? ' is-active' : ''}`}
                    onClick={() => {
                      setIsSizeMenuOpen(false);
                      onItemsPerPageChange(String(num));
                    }}
                  >
                    <span>{`${num}/página`}</span>
                    {isActive ? <LuCheck aria-hidden="true" /> : null}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export default PaginationControls;
