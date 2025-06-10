// Frontend/app/src/components/fornecedores/EditFornecedorModal.jsx
import React, { useState, useEffect } from 'react';
import fornecedorService from '../../services/fornecedorService';
import { showSuccessToast, showErrorToast } from '../../utils/notifications';

function EditFornecedorModal({ isOpen, onClose, fornecedorData, onSave, isLoading }) {
  const [formData, setFormData] = useState({ nome: '', site_url: ''});
  const [activeTab, setActiveTab] = useState('info');
  const [importFile, setImportFile] = useState(null);
  const [importLoading, setImportLoading] = useState(false);

  useEffect(() => {
    if (fornecedorData) {
      setFormData({
        nome: fornecedorData.nome || '',
        site_url: fornecedorData.site_url || '',
      });
      setActiveTab('info');
      setImportFile(null);
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
      alert('Nome é obrigatório.'); 
      return; 
    }
    if (trimmedNome.length < 2) { 
      alert('Nome deve ter pelo menos 2 caracteres.'); 
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
        alert("Erro: ID do fornecedor não encontrado.");
    }
  };

  const handleImport = async () => {
    if (!importFile) {
      alert('Selecione um arquivo para importar.');
      return;
    }
    setImportLoading(true);
    try {
      await fornecedorService.importCatalogo(fornecedorData.id, importFile);
      showSuccessToast('Catálogo importado com sucesso!');
      setImportFile(null);
    } catch (err) {
      const errMsg = err?.detail || err.message || 'Erro ao importar catálogo.';
      showErrorToast(errMsg);
    } finally {
      setImportLoading(false);
    }
  };

  if (!isOpen || !fornecedorData) return null;

  return (
    <div className="modal active" id="edit-forn-modal">
      <div className="modal-content">
        <button
          type="button"
          className="modal-close-button"
          aria-label="Fechar"
          onClick={onClose}
          disabled={isLoading || importLoading}
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
            <p>Envie um arquivo CSV, Excel ou PDF para importar produtos deste fornecedor.</p>
            <input type="file" accept=".csv,.xls,.xlsx,.pdf" onChange={(e) => setImportFile(e.target.files[0])} disabled={importLoading} />
            <button onClick={handleImport} disabled={importLoading || !importFile}>{importLoading ? 'Importando...' : 'Importar'}</button>
          </div>
        )}
      </div>
    </div>
  );
}

export default EditFornecedorModal;
