// Frontend/app/src/components/fornecedores/NewFornecedorModal.jsx
import React, { useState, useEffect } from 'react';
import { showWarningToast } from '../../utils/notifications';
import '../common/Modal.css';

function NewFornecedorModal({ isOpen, onClose, onSave, isLoading }) {
  const [nome, setNome] = useState('');
  const [siteUrl, setSiteUrl] = useState('');

  const clearForm = () => { 
    setNome(''); 
    setSiteUrl('');
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
    };

    let finalSiteUrl = null; // Definido como null por padrão
    const trimmedSiteUrlInput = siteUrl.trim();

    if (trimmedSiteUrlInput !== "") {
      if (!trimmedSiteUrlInput.startsWith('http://') && !trimmedSiteUrlInput.startsWith('https://')) {
        finalSiteUrl = 'http://' + trimmedSiteUrlInput;
      } else {
        finalSiteUrl = trimmedSiteUrlInput;
      }
      payload.site_url = finalSiteUrl; 
    } else {
      payload.site_url = null; // Garante que null seja enviado se o input estiver vazio
    }
    
    onSave(payload).then(() => {
        clearForm();
    }).catch(err => {
      console.error("Falha ao salvar novo fornecedor (do modal NewFornecedorModal):", err);
    });
  };

  useEffect(() => { 
    if (!isOpen) {
      clearForm(); 
    }
  }, [isOpen]);
  
  if (!isOpen) return null;

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
            onChange={e => setNome(e.target.value)}
            disabled={isLoading}
          />
        </div>
        <div className="form-section">
          <label htmlFor="new-forn-siteurl">Site URL</label>
          <input
            id="new-forn-siteurl"
            type="text"
            value={siteUrl}
            onChange={e => setSiteUrl(e.target.value)}
            placeholder="www.exemplo.com"
            disabled={isLoading}
          />
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
