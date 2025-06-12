import React from 'react';
import './LoadingOverlay.css';
import LogoImg from '../../assets/Logo.png';

function LoadingOverlay({ isOpen, message = 'Carregando...' }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay loading-overlay">
      <div className="loading-overlay-content">
        <img src={LogoImg} alt="CatalogAI logo" className="loading-logo" />
        <div className="loading-spinner" />
        <p className="loading-text">Loading...</p>
        <p>{message}</p>
      </div>
    </div>
  );
}

export default LoadingOverlay;
