// Frontend/app/src/components/fornecedores/EditFornecedorModal.jsx
import React, { useState, useEffect } from 'react';
import { showErrorToast, showWarningToast } from '../../utils/notifications';
import ImportCatalogWizard from './ImportCatalogWizard.jsx';
import CatalogFileList from './CatalogFileList.jsx';
import fornecedorService from '../../services/fornecedorService';

function EditFornecedorModal({ isOpen, onClose, fornecedorData, onSave, isLoading }) {
  const [formData, setFormData] = useState({ nome: '', site_url: ''});
  const [activeTab, setActiveTab] = useState('info'); // 'info' | 'import' | 'files'
  const [isImportWizardOpen, setIsImportWizardOpen] = useState(false);
  const [catalogFiles, setCatalogFiles] = useState([]);
  const [loadingFiles, setLoadingFiles] = useState(false);

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

  const fetchFiles = async () => {
    if (!fornecedorData?.id) return;
    setLoadingFiles(true);
    try {
      const data = await fornecedorService.getCatalogImportFiles({
        fornecedor_id: fornecedorData.id,
      });
      setCatalogFiles(data.items || data);
    } catch (err) {
      console.error('Erro ao carregar arquivos de catálogo:', err);
    } finally {
      setLoadingFiles(false);
    }
  };

  useEffect(() => {
    if (isOpen && activeTab === 'files') {
      fetchFiles();
    }
  }, [isOpen, activeTab, fornecedorData]);

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

  const handleReprocessFile = async (fileId) => {
    try {
      await fornecedorService.reprocessCatalogFile(fileId);
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
          <button type="button" className={activeTab === 'files' ? 'active' : ''} onClick={() => setActiveTab('files')}>Arquivos</button>
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

        {activeTab === 'files' && (
          <div className="form-section" style={{ marginTop: '1em' }}>
            <button
              type="button"
              onClick={() => setIsImportWizardOpen(true)}
              style={{ marginBottom: '0.5em' }}
            >
              Adicionar Arquivo
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
        )}
        <ImportCatalogWizard
          fornecedor={fornecedorData}
          onClose={() => setIsImportWizardOpen(false)}
        />
      </div>
    </div>
  );
}

export default EditFornecedorModal;
