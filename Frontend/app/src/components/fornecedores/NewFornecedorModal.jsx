/**
 * Module new fornecedor modal.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useEffect, useState } from 'react';
import { showErrorToast, showWarningToast } from '../../utils/notifications';
import fornecedorService from '../../services/fornecedorService';
import Modal from '../common/Modal.jsx';
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
      return 'Ícone do site';
    case 'favicon-default':
      return 'Favicon padrão do domínio';
    case 'manual':
      return 'URL definida manualmente';
    default:
      return 'Logo ainda não definida';
  }
}

function getLogoSourceHint(source) {
  switch (source) {
    case 'css-logo':
    case 'inline-logo':
    case 'img-logo':
      return 'A marca foi localizada no próprio layout do fornecedor. Ajuste manualmente apenas se quiser trocar.';
    case 'meta-image':
      return 'O site não expôs uma logo clara no HTML; usamos a imagem institucional mais confiável encontrada.';
    case 'link-icon':
    case 'favicon-default':
      return 'O site não forneceu uma logo melhor. Se quiser, troque manualmente por uma imagem oficial da marca.';
    case 'manual':
      return 'Essa logo foi informada manualmente e será usada na lista e nos detalhes do fornecedor.';
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
      showWarningToast('Nome é obrigatório.');
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
      showWarningToast('Informe o site do fornecedor antes de buscar a logo.');
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
      showErrorToast(error?.detail || error?.message || 'Falha ao buscar a logo do site.');
    } finally {
      setIsResolvingLogo(false);
    }
  };

  useEffect(() => {
    if (!isOpen) {
      clearForm();
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      closeDisabled={isLoading}
      title="Novo Fornecedor"
      subtitle="Cadastre a base do fornecedor e prepare o site e a identidade visual para o restante da operação."
      size="lg"
      className="fornecedor-modal-shell"
      bodyClassName="fornecedor-modal-body"
    >
      <div className="modal-workspace">
        <section className="modal-section-card fornecedor-modal-section-card fornecedor-modal-section-card--fields">
          <div className="modal-section-head">
            <div className="modal-section-copy">
              <h3>Informações básicas</h3>
              <p>Preencha os dados principais e, se quiser, deixe o sistema buscar a logo automaticamente no site.</p>
            </div>
          </div>

          <div className="fornecedor-modal-field-grid">
            <div className="fornecedor-modal-field">
              <label htmlFor="new-forn-nome">Nome*</label>
              <input
                id="new-forn-nome"
                type="text"
                value={nome}
                onChange={(event) => setNome(event.target.value)}
                disabled={isLoading}
              />
            </div>
            <div className="fornecedor-modal-field">
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
          </div>

          <div className="fornecedor-logo-panel">
            <div className="fornecedor-logo-preview-column">
              <div className="fornecedor-logo-preview">
                {logoUrl ? (
                  <img src={logoUrl} alt={`Logo de ${nome || 'fornecedor'}`} />
                ) : (
                  <span>{buildInitials(nome)}</span>
                )}
              </div>
              <span className="fornecedor-logo-preview-caption">
                Visual usado na lista de fornecedores
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
        </section>

        <div className="modal-actions fornecedor-modal-footer">
          <button type="button" onClick={onClose} disabled={isLoading}>
            Cancelar
          </button>
          <button type="button" className="btn-primary" onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default NewFornecedorModal;
