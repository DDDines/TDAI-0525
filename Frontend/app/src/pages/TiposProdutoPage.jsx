// Frontend/app/src/pages/TiposProdutoPage.jsx
import React, { useState, useEffect } from 'react';
import { useProductTypes } from '../contexts/ProductTypeContext';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import productTypeService from '../services/productTypeService';

import AttributeTemplateList from '../components/product_types/AttributeTemplateList';
import AttributeTemplateModal from '../components/product_types/AttributeTemplateModal';

import './TiposProdutoPage.css';

function TiposProdutoPage() {
  const { productTypes, isLoading, error, refreshProductTypes, addProductType, removeProductType } = useProductTypes();
  
  const [selectedProductType, setSelectedProductType] = useState(null);
  const [isAttributeModalOpen, setIsAttributeModalOpen] = useState(false);
  const [editingAttribute, setEditingAttribute] = useState(null);

  const [isNewTypeModalOpen, setIsNewTypeModalOpen] = useState(false);
  const [newTypeKeyName, setNewTypeKeyName] = useState('');
  const [newTypeFriendlyName, setNewTypeFriendlyName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (selectedProductType) {
      const updatedType = productTypes.find(pt => pt.id === selectedProductType.id);
      setSelectedProductType(updatedType || null);
    }
  }, [productTypes, selectedProductType]);

  const handleOpenNewTypeModal = () => {
    setNewTypeKeyName('');
    setNewTypeFriendlyName('');
    setIsNewTypeModalOpen(true);
  };
  const handleCloseNewTypeModal = () => setIsNewTypeModalOpen(false);

  const handleSaveNewType = async () => {
    if (!newTypeKeyName.trim() || !newTypeFriendlyName.trim()) {
      showErrorToast("Chave e Nome Amigável são obrigatórios.");
      return;
    }
    setIsSubmitting(true);
    try {
      await addProductType({
        key_name: newTypeKeyName.trim(),
        friendly_name: newTypeFriendlyName.trim(),
        attribute_templates: []
      });
      showSuccessToast("Tipo de Produto criado com sucesso!");
      handleCloseNewTypeModal();
    } catch (err) {
      showErrorToast(err.response?.data?.detail || err.message || "Falha ao criar Tipo de Produto.");
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleDeleteType = async (typeId, typeName) => {
    if (window.confirm(`Tem certeza que deseja deletar o tipo de produto "${typeName}"? Isso não poderá ser desfeito.`)) {
      try {
        await removeProductType(typeId);
        if (selectedProductType && selectedProductType.id === typeId) {
          setSelectedProductType(null);
        }
        showSuccessToast(`Tipo de produto "${typeName}" deletado com sucesso.`);
      } catch (err) {
        showErrorToast(err.response?.data?.detail || `Falha ao deletar o tipo "${typeName}". Verifique se ele não está em uso.`);
      }
    }
  };

  const handleSelectType = (type) => {
    setSelectedProductType(type);
  };
  
  const handleOpenAttributeModal = (attribute = null) => {
    setEditingAttribute(attribute);
    setIsAttributeModalOpen(true);
  };

  const handleCloseAttributeModal = () => {
    setIsAttributeModalOpen(false);
    setEditingAttribute(null);
  };

  const handleSaveAttribute = async (attributeData) => {
    if (!selectedProductType) {
      showErrorToast("Nenhum tipo de produto selecionado.");
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingAttribute) {
        await productTypeService.updateAttributeInType(selectedProductType.id, editingAttribute.id, attributeData);
        showSuccessToast("Atributo atualizado com sucesso!");
      } else {
        await productTypeService.addAttributeToType(selectedProductType.id, attributeData);
        showSuccessToast("Atributo adicionado com sucesso!");
      }
      refreshProductTypes();
      handleCloseAttributeModal();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || "Falha ao salvar o atributo.";
      showErrorToast(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteAttribute = async (attributeId) => {
     if (!selectedProductType) return;
     if (window.confirm(`Tem certeza que deseja remover este atributo do template?`)) {
       try {
         await productTypeService.removeAttributeFromType(selectedProductType.id, attributeId);
         showSuccessToast("Atributo removido com sucesso.");
         refreshProductTypes();
       } catch (err) {
         const errorMsg = err.response?.data?.detail || "Falha ao remover o atributo.";
         showErrorToast(errorMsg);
       }
     }
  };

  // --- NOVA FUNÇÃO ADICIONADA PARA REORDENAR ---
  const handleReorderAttribute = async (attributeId, direction) => {
    if (!selectedProductType) return;
    
    try {
      // Chama o serviço para reordenar
      await productTypeService.reorderAttributeInType(selectedProductType.id, attributeId, direction);
      showSuccessToast("Ordem do atributo atualizada.");
      // Força o recarregamento dos dados para refletir a nova ordem na UI
      refreshProductTypes();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || "Falha ao reordenar o atributo.";
      showErrorToast(errorMsg);
    }
  };
  // --- FIM DA NOVA FUNÇÃO ---

  if (isLoading && productTypes.length === 0) {
    return <div className="loading-message">Carregando tipos de produto...</div>;
  }

  if (error) {
    return <div className="error-message">Erro ao carregar tipos de produto: {error.message || error.detail}</div>;
  }

  return (
    <div className="tipos-produto-container">
      <div className="tipos-produto-header">
        <h1>Gerenciar Tipos de Produto</h1>
        <button onClick={handleOpenNewTypeModal} className="tipos-produto-button">
          + Novo Tipo de Produto
        </button>
      </div>
      
      <div className="type-management-container">
        <div className="type-list-panel">
          <h4>Tipos Cadastrados</h4>
          {productTypes.length === 0 && !isLoading ? (
            <p>Nenhum tipo cadastrado.</p>
          ) : (
            <ul>
              {productTypes.map(type => (
                <li 
                  key={type.id} 
                  onClick={() => handleSelectType(type)}
                  className={selectedProductType?.id === type.id ? 'selected' : ''}
                >
                  <span>{type.friendly_name} <span className="usage-count">({type.attribute_templates?.length || 0} attrs)</span></span>
                  <button onClick={(e) => { e.stopPropagation(); handleDeleteType(type.id, type.friendly_name); }} title="Deletar Tipo" className="btn-icon">
                    🗑️
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="type-detail-panel">
          {selectedProductType ? (
            <>
              <div className="panel-header">
                <h5>Atributos para: {selectedProductType.friendly_name}</h5>
                <button className="btn-small btn-primary" onClick={() => handleOpenAttributeModal(null)}>+ Novo Atributo</button>
              </div>
              {/* --- ALTERAÇÃO AQUI PARA PASSAR A NOVA PROP --- */}
              <AttributeTemplateList
                attributes={selectedProductType.attribute_templates}
                onEdit={handleOpenAttributeModal}
                onDelete={handleDeleteAttribute}
                onReorder={handleReorderAttribute}
              />
            </>
          ) : (
            <p style={{ textAlign: 'center', color: 'var(--text-color-light)', paddingTop: '2rem' }}>
              Selecione um tipo de produto da lista para ver e gerenciar seus atributos.
            </p>
          )}
        </div>
      </div>

      {isNewTypeModalOpen && (
        <div className="tipos-produto-modal">
          <div className="tipos-produto-modal-content">
            <div className="tipos-produto-modal-header">
                <h2 className="tipos-produto-modal-header h2">Novo Tipo de Produto</h2>
                <button onClick={handleCloseNewTypeModal} className="tipos-produto-modal-close-button">×</button>
            </div>
            <div className="tipos-produto-form-group">
              <label htmlFor="type-key-name" className="tipos-produto-form-group label">Chave (Identificador Único)*:</label>
              <input type="text" id="type-key-name" value={newTypeKeyName} onChange={(e) => setNewTypeKeyName(e.target.value)} className="tipos-produto-form-group input" placeholder="Ex: eletronicos, vestuario_camisetas" disabled={isSubmitting} />
            </div>
            <div className="tipos-produto-form-group">
              <label htmlFor="type-friendly-name" className="tipos-produto-form-group label">Nome Amigável*:</label>
              <input type="text" id="type-friendly-name" value={newTypeFriendlyName} onChange={(e) => setNewTypeFriendlyName(e.target.value)} className="tipos-produto-form-group input" placeholder="Ex: Eletrônicos, Camisetas (Vestuário)" disabled={isSubmitting} />
            </div>
            <div className="tipos-produto-modal-actions">
              <button onClick={handleCloseNewTypeModal} className="tipos-produto-modal-button cancel" disabled={isSubmitting}>Cancelar</button>
              <button onClick={handleSaveNewType} className="tipos-produto-modal-button save" disabled={isSubmitting}>{isSubmitting ? 'Salvando...' : 'Salvar Tipo'}</button>
            </div>
          </div>
        </div>
      )}

      {isAttributeModalOpen && (
        <AttributeTemplateModal
          isOpen={isAttributeModalOpen}
          onClose={handleCloseAttributeModal}
          attribute={editingAttribute}
          onSave={handleSaveAttribute}
          isSubmitting={isSubmitting}
        />
      )}
    </div>
  );
}

export default TiposProdutoPage;