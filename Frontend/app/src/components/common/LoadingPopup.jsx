/**
 * Module loading popup.
 *
 * Defines responsibilities and integration points for components common.
 */

import LogoImg from '../../assets/Logo.png';
import './LoadingPopup.css';

function LoadingPopup({ isOpen, title = 'Processando', message = 'Aguarde...' }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content loading-popup-content">
        <img src={LogoImg} alt="CommerceFolio" className="loading-popup-logo" />
        <div className="loading-spinner" />
        <h3 className="loading-popup-title">{title}</h3>
        {message && <p className="loading-popup-message">{message}</p>}
      </div>
    </div>
  );
}

export default LoadingPopup;
