// Frontend/app/src/components/fornecedores/NewFornecedorModal.jsx
import React, { useState, useEffect } from 'react';

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
    <div className="modal active" id="new-forn-modal">
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} disabled={isLoading}>×</button>
        <h3>Novo Fornecedor</h3>
        <div>
            <label htmlFor="new-forn-nome">Nome*</label>
            <input id="new-forn-nome" type="text" value={nome} onChange={e => setNome(e.target.value)} disabled={isLoading} />
        </div>
        <div>
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
        <button onClick={handleSubmit} disabled={isLoading}>{isLoading ? 'Salvando...' : 'Salvar'}</button>
      </div>
    </div>
  );
}

export default NewFornecedorModal;
