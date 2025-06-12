// Frontend/app/src/pages/TiposProdutoPage.jsx
import React, { useState, useEffect } from 'react';
import { useProductTypes } from '../contexts/ProductTypeContext';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import productTypeService from '../services/productTypeService';
import EditProductTypeModal from '../components/product_types/EditProductTypeModal.jsx';
import NewProductTypeModal from '../components/product_types/NewProductTypeModal.jsx';

import AttributeTemplateList from '../components/product_types/AttributeTemplateList';
import AttributeTemplateModal from '../components/product_types/AttributeTemplateModal';

import './TiposProdutoPage.css';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';

function TiposProdutoPage() {
  const { productTypes, isLoading, error, refreshProductTypes, updateProductType } = useProductTypes();
  
  const [selectedProductType, setSelectedProductType] = useState(null);
  const [isAttributeModalOpen, setIsAttributeModalOpen] = useState(false);
  const [editingAttribute, setEditingAttribute] = useState(null);

  const [isNewTypeModalOpen, setIsNewTypeModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isEditTypeModalOpen, setIsEditTypeModalOpen] = useState(false);
  const [editingType, setEditingType] = useState(null);

  // Atualiza os detalhes do tipo selecionado se a lista geral for atualizada
  useEffect(() => {
    if (selectedProductType) {
      const updatedType = productTypes.find(pt => pt.id === selectedProductType.id);
      setSelectedProductType(updatedType || null);
    }
  }, [productTypes, selectedProductType]);

  const handleOpenNewTypeModal = () => {
    setIsNewTypeModalOpen(true);
  };

  const handleCloseNewTypeModal = () => setIsNewTypeModalOpen(false);

  const handleOpenEditTypeModal = (type) => {
    setEditingType(type);
    setIsEditTypeModalOpen(true);
  };

  const handleCloseEditTypeModal = () => {
    setIsEditTypeModalOpen(false);
    setEditingType(null);
  };

  const handleNewTypeCreated = (newType) => {
    refreshProductTypes();
    setSelectedProductType(newType);
  };

  
  const handleDeleteType = async (typeId, typeName) => {
    if (window.confirm(`Tem certeza que deseja deletar o tipo de produto "${typeName}"? Isso não poderá ser desfeito.`)) {
      try {
        await productTypeService.deleteProductType(typeId);
        if (selectedProductType && selectedProductType.id === typeId) {
          setSelectedProductType(null);
        }
        showSuccessToast(`Tipo de produto "${typeName}" deletado com sucesso.`);
        refreshProductTypes();
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

  const handleSaveEditedType = async (payload) => {
    if (!editingType) return;
    setIsSubmitting(true);
    try {
      await updateProductType(editingType.id, payload);
      refreshProductTypes();
      handleCloseEditTypeModal();
    } catch (err) {
      // Toasts são tratados no contexto
    } finally {
      setIsSubmitting(false);
    }
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

  const handleReorderAttribute = async (attributeId, direction) => {
    if (!selectedProductType) return;
    try {
      await productTypeService.reorderAttributeInType(selectedProductType.id, attributeId, direction);
      showSuccessToast("Ordem do atributo atualizada.");
      refreshProductTypes();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || "Falha ao reordenar o atributo.";
      showErrorToast(errorMsg);
    }
  };

  if (isLoading && productTypes.length === 0) {
    return <LoadingOverlay isOpen={true} message="Carregando tipos de produto..." />;
  }

  if (error) {
    return <div className="error-message">Erro ao carregar tipos de produto: {error}</div>;
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
                  <span className="type-actions">
                    <button onClick={(e) => { e.stopPropagation(); handleOpenEditTypeModal(type); }} title="Editar Tipo" className="btn-icon">✏️</button>
                    <button onClick={(e) => { e.stopPropagation(); handleDeleteType(type.id, type.friendly_name); }} title="Deletar Tipo" className="btn-icon">🗑️</button>
                  </span>
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

      <NewProductTypeModal
        isOpen={isNewTypeModalOpen}
        onClose={handleCloseNewTypeModal}
        onCreated={handleNewTypeCreated}
      />

      {isEditTypeModalOpen && (
        <EditProductTypeModal
          isOpen={isEditTypeModalOpen}
          onClose={handleCloseEditTypeModal}
          type={editingType}
          onSave={handleSaveEditedType}
          isSubmitting={isSubmitting}
        />
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
