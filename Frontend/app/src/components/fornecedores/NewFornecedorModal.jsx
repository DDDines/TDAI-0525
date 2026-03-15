/**
 * Module new fornecedor modal.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useEffect, useState } from 'react';
import { showErrorToast, showWarningToast } from '../../utils/notifications';
import fornecedorService from '../../services/fornecedorService';
import '../common/Modal.css';
import './FornecedorModal.css';

function normalizeOptionalUrl(value) {
  const raw = String(value || '').trim();
  if (!raw) {
    return null;
  }
  if (raw.startsWith('http://') || raw.startsWith('https://')) {
    return raw;
  }
  return `http://${raw}`;
}

function buildInitials(name) {
  const safeName = String(name || '').trim();
  if (!safeName) {
    return 'F';
  }
  return safeName
    .split(/\s+/)
    .slice(0, 2)
    .map((chunk) => chunk.charAt(0).toUpperCase())
    .join('');
}

function getLogoSourceLabel(source) {
  switch (source) {
    case 'css-logo':
      return 'Logo detectada no layout do site';
    case 'inline-logo':
      return 'Logo detectada em bloco visual do site';
    case 'img-logo':
      return 'Logo detectada em imagem do site';
    case 'meta-image':
      return 'Imagem institucional do site';
    case 'link-icon':
      return 'Icone do site';
    case 'favicon-default':
      return 'Favicon padrao do dominio';
    case 'manual':
      return 'URL definida manualmente';
    default:
      return 'Logo ainda nao definida';
  }
}

function getLogoSourceHint(source) {
  switch (source) {
    case 'css-logo':
    case 'inline-logo':
    case 'img-logo':
      return 'A marca foi localizada no proprio layout do fornecedor. Ajuste manualmente apenas se quiser trocar.';
    case 'meta-image':
      return 'O site nao expôs uma logo clara no HTML; usamos a imagem institucional mais confiavel encontrada.';
    case 'link-icon':
    case 'favicon-default':
      return 'O site nao forneceu uma logo melhor. Se quiser, troque manualmente por uma imagem oficial da marca.';
    case 'manual':
      return 'Essa logo foi informada manualmente e sera usada na lista e nos detalhes do fornecedor.';
    default:
      return 'Busque a marca oficial no site ou informe uma URL manualmente.';
  }
}

function NewFornecedorModal({ isOpen, onClose, onSave, isLoading }) {
  const [nome, setNome] = useState('');
  const [siteUrl, setSiteUrl] = useState('');
  const [logoUrl, setLogoUrl] = useState('');
  const [isResolvingLogo, setIsResolvingLogo] = useState(false);
  const [logoSource, setLogoSource] = useState('');

  const clearForm = () => {
    setNome('');
    setSiteUrl('');
    setLogoUrl('');
    setLogoSource('');
  };

  const handleSubmit = () => {
    const trimmedNome = nome.trim();
    if (!trimmedNome) {
      showWarningToast('Nome e obrigatorio.');
      return;
    }
    if (trimmedNome.length < 2) {
      showWarningToast('Nome deve ter pelo menos 2 caracteres.');
      return;
    }

    const payload = {
      nome: trimmedNome,
      site_url: normalizeOptionalUrl(siteUrl),
      logo_url: normalizeOptionalUrl(logoUrl),
    };

    onSave(payload)
      .then(() => {
        clearForm();
      })
      .catch((err) => {
        console.error('Falha ao salvar novo fornecedor:', err);
      });
  };

  const handleResolveLogo = async () => {
    const normalizedSiteUrl = normalizeOptionalUrl(siteUrl);
    if (!normalizedSiteUrl) {
      showWarningToast('Informe o site do fornecedor antes de buscar o logo.');
      return;
    }

    setIsResolvingLogo(true);
    try {
      const resolved = await fornecedorService.resolveFornecedorLogo(normalizedSiteUrl);
      setSiteUrl(resolved?.resolved_site_url || normalizedSiteUrl);
      setLogoUrl(resolved?.logo_url || '');
      setLogoSource(resolved?.source || '');
    } catch (error) {
      console.error('Falha ao resolver logo do fornecedor:', error);
      showErrorToast(error?.detail || error?.message || 'Falha ao buscar o logo do site.');
    } finally {
      setIsResolvingLogo(false);
    }
  };

  useEffect(() => {
    if (!isOpen) {
      clearForm();
    }
  }, [isOpen]);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="modal-overlay" id="new-forn-modal">
      <div className="modal-content">
        <button
          type="button"
          className="modal-close-button"
          aria-label="Fechar"
          onClick={onClose}
          disabled={isLoading}
        >
          ×
        </button>
        <h3>Novo Fornecedor</h3>
        <div className="form-section">
          <label htmlFor="new-forn-nome">Nome*</label>
          <input
            id="new-forn-nome"
            type="text"
            value={nome}
            onChange={(event) => setNome(event.target.value)}
            disabled={isLoading}
          />
        </div>
        <div className="form-section">
          <label htmlFor="new-forn-siteurl">Site URL</label>
          <input
            id="new-forn-siteurl"
            type="text"
            value={siteUrl}
            onChange={(event) => setSiteUrl(event.target.value)}
            placeholder="www.exemplo.com"
            disabled={isLoading || isResolvingLogo}
          />
        </div>
        <div className="form-section fornecedor-logo-panel">
          <div className="fornecedor-logo-preview-column">
            <div className="fornecedor-logo-preview">
              {logoUrl ? (
                <img src={logoUrl} alt={`Logo de ${nome || 'fornecedor'}`} />
              ) : (
                <span>{buildInitials(nome)}</span>
              )}
            </div>
            <span className="fornecedor-logo-preview-caption">
              {getLogoSourceLabel(logoSource)}
            </span>
          </div>
          <div className="fornecedor-logo-controls">
            <div className="fornecedor-logo-meta-head">
              <div>
                <h4>Identidade visual</h4>
                <p>
                  Tente localizar a marca oficial no site do fornecedor. Se precisar,
                  ajuste a URL manualmente.
                </p>
              </div>
              {logoSource ? (
                <span className={`fornecedor-logo-source fornecedor-logo-source--${logoSource}`}>
                  {getLogoSourceLabel(logoSource)}
                </span>
              ) : null}
            </div>
            <div className="fornecedor-logo-field-row">
              <div className="fornecedor-logo-url-group">
                <label htmlFor="new-forn-logourl">Logo URL</label>
                <input
                  id="new-forn-logourl"
                  type="text"
                  value={logoUrl}
                  onChange={(event) => {
                    setLogoUrl(event.target.value);
                    setLogoSource(event.target.value.trim() ? 'manual' : '');
                  }}
                  placeholder="https://site.com/logo.png"
                  disabled={isLoading || isResolvingLogo}
                />
              </div>
              <button
                type="button"
                className="fornecedor-logo-action"
                onClick={handleResolveLogo}
                disabled={isLoading || isResolvingLogo}
              >
                {isResolvingLogo ? 'Buscando logo...' : 'Buscar do site'}
              </button>
            </div>
            <p className="fornecedor-logo-helper">{getLogoSourceHint(logoSource)}</p>
          </div>
        </div>
        <div className="modal-actions">
          <button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default NewFornecedorModal;
