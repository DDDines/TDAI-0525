/**
 * Module modal.
 *
 * Defines responsibilities and integration points for components common.
 */

import React, { useId } from 'react';
import './Modal.css';

function Modal({
  isOpen,
  onClose,
  title,
  subtitle = '',
  children,
  size = 'lg',
  className = '',
  bodyClassName = '',
  closeLabel = 'Fechar',
  closeDisabled = false,
}) {
  const headingId = useId();

  if (!isOpen) {
    return null;
  }

  const modalClassName = [
    'modal-content',
    `modal-size-${size}`,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const modalBodyClassName = ['modal-body', bodyClassName].filter(Boolean).join(' ');

  return (
    <div className="modal-overlay">
      <div
        className={modalClassName}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
      >
        <div className="modal-header">
          <div className="modal-header-copy">
            <h2 id={headingId}>{title}</h2>
            {subtitle ? <p className="modal-subtitle">{subtitle}</p> : null}
          </div>
          <button
            type="button"
            className="modal-close-button"
            aria-label={closeLabel}
            onClick={onClose}
            disabled={closeDisabled}
          >
            &times;
          </button>
        </div>
        <div className={modalBodyClassName}>
          {children}
        </div>
      </div>
    </div>
  );
}

export default Modal;
