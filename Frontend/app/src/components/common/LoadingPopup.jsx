import React from 'react';
import './LoadingPopup.css';
import LogoImg from '../../assets/Logo.png';

function LoadingPopup({ isOpen, message = 'Carregando...', details = [] }) {
  if (!isOpen) return null;

  const detailsList = Array.isArray(details) ? details.filter(Boolean) : [];

  return (
    <div className="modal-overlay">
      <div className="modal-content loading-popup-content">
        {LogoImg ? <img src={LogoImg} alt="CatalogAI" className="loading-popup-logo" /> : null}
        <div className="loading-spinner" />
        <p className="loading-popup-message">{message}</p>
        {detailsList.length > 0 && (
          <ul className="loading-popup-details">
            {detailsList.map((line, index) => (
              <li key={`${line}-${index}`}>{line}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default LoadingPopup;
