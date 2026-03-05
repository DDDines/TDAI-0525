/**
 * Module loading popup.
 *
 * Defines responsibilities and integration points for components common.
 */

import React from 'react';
import './LoadingPopup.css';
import LogoImg from '../../assets/Logo.png';

function LoadingPopup(

  {
    isOpen,
    title = 'Processando',
    message = 'Carregando...',
    details = [],
    progressPercent = null,
    progressLabel = '',
    chips = []
  }) {
    if (!isOpen) return null;

    const detailsList = Array.isArray(details) ? details.filter(Boolean) : [];
    const infoChips = Array.isArray(chips) ?
    chips.
    filter((chip) => chip && chip.label && chip.value !== null && chip.value !== undefined && String(chip.value).trim() !== '') :
    [];
    const hasProgress = typeof progressPercent === 'number' && Number.isFinite(progressPercent);
    const normalizedProgress = hasProgress ? Math.max(0, Math.min(100, Math.round(progressPercent))) : null;

    return (
      <div className="modal-overlay">
      <div className="modal-content loading-popup-content">
        <div className="loading-popup-header">
          {LogoImg ? <img src={LogoImg} alt="CatalogAI" className="loading-popup-logo" /> : null}
          <div className="loading-popup-header-copy">
            <h3 className="loading-popup-title">{title}</h3>
            <p className="loading-popup-message">{message}</p>
          </div>
          <div className="loading-spinner" />
        </div>

        {hasProgress &&
          <div className="loading-popup-progress-block">
            <div className="loading-popup-progress-meta">
              <span>Progresso</span>
              <strong>{normalizedProgress}%</strong>
            </div>
            <div className="loading-popup-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={normalizedProgress}>
              <div className="loading-popup-progress-fill" style={{ width: `${normalizedProgress}%` }} />
            </div>
            {progressLabel ? <p className="loading-popup-progress-label">{progressLabel}</p> : null}
          </div>
        }

        {infoChips.length > 0 &&
          <ul className="loading-popup-chips">
            {infoChips.map((chip, index) =>
            <li key={`${chip.label}-${index}`} className="loading-popup-chip">
                <span className="loading-popup-chip-label">{chip.label}</span>
                <strong className="loading-popup-chip-value">{chip.value}</strong>
              </li>
            )}
          </ul>
        }

        {detailsList.length > 0 &&
          <div className="loading-popup-details-panel">
            <p className="loading-popup-details-title">Atualizações em tempo real</p>
            <ul className="loading-popup-details">
              {detailsList.map((line, index) =>
              <li key={`${line}-${index}`}>{line}</li>
              )}
            </ul>
          </div>
          }
      </div>
    </div>);

  }
export default LoadingPopup;
