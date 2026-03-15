/**
 * Module edit fornecedor modal.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { showErrorToast, showWarningToast } from '../../utils/notifications';
import ImportCatalogWizard from './ImportCatalogWizard.jsx';
import CatalogFileList from './CatalogFileList.jsx';
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

function EditFornecedorModal({ isOpen, onClose, fornecedorData, onSave, isLoading }) {
  const [formData, setFormData] = useState({ nome: '', site_url: '', logo_url: '' });
  const [activeTab, setActiveTab] = useState('info');
  const [isImportWizardOpen, setIsImportWizardOpen] = useState(false);
  const [catalogFiles, setCatalogFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [isResolvingLogo, setIsResolvingLogo] = useState(false);
  const [logoSource, setLogoSource] = useState('');

  useEffect(() => {
    if (fornecedorData) {
      setFormData({
        nome: fornecedorData.nome || '',
        site_url: fornecedorData.site_url || '',
        logo_url: fornecedorData.logo_url || '',
      });
      setLogoSource(fornecedorData.logo_url ? 'manual' : '');
      setActiveTab('info');
      return;
    }
    setFormData({ nome: '', site_url: '', logo_url: '' });
    setLogoSource('');
  }, [fornecedorData]);

  const fetchFiles = useCallback(async () => {
    if (!fornecedorData?.id) {
      return;
    }
    setLoadingFiles(true);
    try {
      const data = await fornecedorService.getCatalogImportFiles({
        fornecedor_id: fornecedorData.id,
      });
      setCatalogFiles(data.items || data);
    } catch (err) {
      console.error('Erro ao carregar arquivos de catalogo:', err);
    } finally {
      setLoadingFiles(false);
    }
  }, [fornecedorData?.id]);

  useEffect(() => {
    if (isOpen && activeTab === 'files') {
      fetchFiles();
    }
  }, [activeTab, fetchFiles, isOpen]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (name === 'logo_url') {
      setLogoSource(value.trim() ? 'manual' : '');
    }
  };

  const handleResolveLogo = async () => {
    const siteUrl = normalizeOptionalUrl(formData.site_url);
    if (!siteUrl) {
      showWarningToast('Informe o site do fornecedor antes de buscar o logo.');
      return;
    }

    setIsResolvingLogo(true);
    try {
      const resolved = await fornecedorService.resolveFornecedorLogo(siteUrl);
      setFormData((prev) => ({
        ...prev,
        site_url: resolved?.resolved_site_url || siteUrl,
        logo_url: resolved?.logo_url || '',
      }));
      setLogoSource(resolved?.source || '');
    } catch (error) {
      console.error('Erro ao buscar logo do fornecedor:', error);
      showErrorToast(error?.detail || error?.message || 'Falha ao buscar o logo do site.');
    } finally {
      setIsResolvingLogo(false);
    }
  };

  const handleSubmit = () => {
    const trimmedNome = formData.nome?.trim();
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
      site_url: normalizeOptionalUrl(formData.site_url),
      logo_url: normalizeOptionalUrl(formData.logo_url),
    };

    if (fornecedorData?.id) {
      onSave(fornecedorData.id, payload);
      return;
    }

    console.error('ID do fornecedor nao encontrado para atualizacao.');
    showErrorToast('Erro: ID do fornecedor nao encontrado.');
  };

  const handleReprocessFile = async (fileId) => {
    try {
      await fornecedorService.reprocessCatalogFile(fileId, {
        fornecedor_id: fornecedorData?.id,
      });
      await fetchFiles();
    } catch (err) {
      console.error('Erro ao reprocessar arquivo:', err);
    }
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await fornecedorService.deleteCatalogFile(fileId);
      await fetchFiles();
    } catch (err) {
      console.error('Erro ao excluir arquivo:', err);
    }
  };

  if (!isOpen || !fornecedorData) {
    return null;
  }

  return (
    <div className="modal-overlay" id="edit-forn-modal">
      <div className="modal-content">
        <button
          type="button"
          className="modal-close-button"
          aria-label="Fechar"
          onClick={onClose}
          disabled={isLoading}
        >
          &times;
        </button>
        <h3>Editar fornecedor: {fornecedorData.nome}</h3>

        <div className="tab-navigation">
          <button
            type="button"
            className={activeTab === 'info' ? 'active' : ''}
            onClick={() => setActiveTab('info')}
          >
            Info
          </button>
          <button
            type="button"
            className={activeTab === 'import' ? 'active' : ''}
            onClick={() => setActiveTab('import')}
          >
            Importar Catalogo
          </button>
          <button
            type="button"
            className={activeTab === 'files' ? 'active' : ''}
            onClick={() => setActiveTab('files')}
          >
            Arquivos
          </button>
        </div>

        {activeTab === 'info' ? (
          <div className="form-section">
            <div>
              <label htmlFor="edit-forn-nome">Nome*</label>
              <input
                id="edit-forn-nome"
                name="nome"
                type="text"
                value={formData.nome || ''}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
            <div>
              <label htmlFor="edit-forn-siteurl">Site URL</label>
              <input
                id="edit-forn-siteurl"
                name="site_url"
                type="text"
                value={formData.site_url || ''}
                onChange={handleChange}
                placeholder="www.exemplo.com"
                disabled={isLoading || isResolvingLogo}
              />
            </div>
            <div className="fornecedor-logo-panel">
              <div className="fornecedor-logo-preview-column">
                <div className="fornecedor-logo-preview">
                  {formData.logo_url ? (
                    <img
                      src={formData.logo_url}
                      alt={`Logo de ${formData.nome || 'fornecedor'}`}
                    />
                  ) : (
                    <span>{buildInitials(formData.nome)}</span>
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
                    <label htmlFor="edit-forn-logourl">Logo URL</label>
                    <input
                      id="edit-forn-logourl"
                      name="logo_url"
                      type="text"
                      value={formData.logo_url || ''}
                      onChange={handleChange}
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
            <button onClick={handleSubmit} disabled={isLoading}>
              {isLoading ? 'Salvando...' : 'Salvar alteracoes'}
            </button>
          </div>
        ) : null}

        {activeTab === 'import' ? (
          <div className="form-section">
            <p>Use o assistente abaixo para importar produtos deste fornecedor.</p>
            <button type="button" onClick={() => setIsImportWizardOpen(true)}>
              Importar Catalogo
            </button>
          </div>
        ) : null}

        {activeTab === 'files' ? (
          <div className="form-section catalog-files-section">
            <button
              type="button"
              className="catalog-files-add-btn"
              onClick={() => setIsImportWizardOpen(true)}
            >
              Adicionar arquivo
            </button>
            {loadingFiles ? (
              <p>Carregando...</p>
            ) : (
              <CatalogFileList
                files={catalogFiles}
                onReprocess={handleReprocessFile}
                onDelete={handleDeleteFile}
              />
            )}
          </div>
        ) : null}

        <ImportCatalogWizard
          fornecedor={fornecedorData}
          onClose={() => setIsImportWizardOpen(false)}
          isOpen={isImportWizardOpen}
        />
      </div>
    </div>
  );
}

export default EditFornecedorModal;
