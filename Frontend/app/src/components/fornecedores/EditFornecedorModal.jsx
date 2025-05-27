// Frontend/app/src/components/fornecedores/EditFornecedorModal.jsx
import React, { useState, useEffect } from 'react';

function EditFornecedorModal({ isOpen, onClose, fornecedorData, onSave, isLoading }) {
  const [formData, setFormData] = useState({ nome: '', site_url: ''});

  useEffect(() => {
    if (fornecedorData) {
      setFormData({ 
        nome: fornecedorData.nome || '', 
        site_url: fornecedorData.site_url || '',
      });
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

  if (!isOpen || !fornecedorData) return null;

  return (
    <div className="modal active" id="edit-forn-modal">
      <div className="modal-content">
        <button className="modal-close" onClick={onClose} disabled={isLoading}>×</button>
        <h3>Editar Fornecedor: {fornecedorData.nome}</h3>
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
    </div>
  );
}

export default EditFornecedorModal;