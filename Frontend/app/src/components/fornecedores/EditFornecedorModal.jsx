// Frontend/app/src/components/fornecedores/EditFornecedorModal.jsx
import React, { useState, useEffect } from 'react';
import { showErrorToast, showWarningToast } from '../../utils/notifications';
import ImportCatalogWizard from './ImportCatalogWizard.jsx';

function EditFornecedorModal({ isOpen, onClose, fornecedorData, onSave, isLoading }) {
  const [formData, setFormData] = useState({ nome: '', site_url: ''});
  const [activeTab, setActiveTab] = useState('info');
  const [isImportWizardOpen, setIsImportWizardOpen] = useState(false);

  useEffect(() => {
    if (fornecedorData) {
      setFormData({
        nome: fornecedorData.nome || '',
        site_url: fornecedorData.site_url || '',
      });
      setActiveTab('info');
    } else {
      setFormData({ nome: '', site_url: ''});
    }
  }, [fornecedorData]);

  const handleChange = e => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  
  const handleSubmit = () => {
    const trimmedNome = formData.nome?.trim();
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
    };

    let finalSiteUrl = null;
    const trimmedSiteUrlInput = formData.site_url?.trim();

    if (trimmedSiteUrlInput && trimmedSiteUrlInput !== "") {
      if (!trimmedSiteUrlInput.startsWith('http://') && !trimmedSiteUrlInput.startsWith('https://')) {
        finalSiteUrl = 'http://' + trimmedSiteUrlInput;
      } else {
        finalSiteUrl = trimmedSiteUrlInput;
      }
      payload.site_url = finalSiteUrl;
    } else {
        payload.site_url = null;
    }

    if (fornecedorData && fornecedorData.id) {
        onSave(fornecedorData.id, payload);
    } else {
        console.error("ID do fornecedor não encontrado para atualização.");
        showErrorToast("Erro: ID do fornecedor não encontrado.");
    }
  };


  if (!isOpen || !fornecedorData) return null;

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
          ×
        </button>
        <h3>Editar Fornecedor: {fornecedorData.nome}</h3>
        <div className="tab-navigation">
          <button type="button" className={activeTab === 'info' ? 'active' : ''} onClick={() => setActiveTab('info')}>Info</button>
          <button type="button" className={activeTab === 'import' ? 'active' : ''} onClick={() => setActiveTab('import')}>Importar Catálogo</button>
        </div>

        {activeTab === 'info' && (
          <div className="form-section">
            <div>
              <label htmlFor="edit-forn-nome">Nome*</label>
              <input id="edit-forn-nome" name="nome" type="text" value={formData.nome || ''} onChange={handleChange} disabled={isLoading} />
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
                disabled={isLoading}
              />
            </div>
            <button onClick={handleSubmit} disabled={isLoading}>{isLoading ? 'Salvando...' : 'Salvar Alterações'}</button>
          </div>
        )}

        {activeTab === 'import' && (
          <div className="form-section">
            <p>Use o assistente abaixo para importar produtos deste fornecedor.</p>
            <button onClick={() => setIsImportWizardOpen(true)}>
              Importar Catálogo
            </button>
          </div>
        )}
        <ImportCatalogWizard
          isOpen={isImportWizardOpen}
          onClose={() => setIsImportWizardOpen(false)}
          fornecedorId={fornecedorData.id}
        />
      </div>
    </div>
  );
}

export default EditFornecedorModal;
