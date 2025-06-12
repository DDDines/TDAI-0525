import React from 'react';
import './LoadingPopup.css';

function LoadingPopup({ isOpen, message = 'Carregando...' }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content loading-popup-content">
        <div className="loading-spinner" />
        <p>{message}</p>
      </div>
    </div>
  );
}

export default LoadingPopup;
