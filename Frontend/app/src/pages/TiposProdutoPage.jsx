/**
 * Module tipos produto page.
 *
 * Defines responsibilities and integration points for pages.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { LuBoxes, LuPlus, LuSearch, LuSparkles, LuTag } from 'react-icons/lu';
import { useProductTypes } from '../contexts/ProductTypeContext';
import { showErrorToast, showSuccessToast } from '../utils/notifications';
import productTypeService from '../services/productTypeService';
import EditProductTypeModal from '../components/product_types/EditProductTypeModal.jsx';
import NewProductTypeModal from '../components/product_types/NewProductTypeModal.jsx';
import AttributeTemplateList from '../components/product_types/AttributeTemplateList';
import AttributeTemplateModal from '../components/product_types/AttributeTemplateModal';
import LoadingOverlay from '../components/common/LoadingOverlay.jsx';
import OperationalStatChip from '../components/common/OperationalStatChip.jsx';
import './TiposProdutoPage.css';

function countAllAttributes(productTypes) {
  return productTypes.reduce(
    (total, type) => total + (Array.isArray(type?.attribute_templates) ? type.attribute_templates.length : 0),
    0
  );
}

function countAiAttributes(productTypes) {
  return productTypes.reduce((total, type) => (
    total + (Array.isArray(type?.attribute_templates)
      ? type.attribute_templates.filter((attribute) => attribute?.collect_in_ai !== false).length
      : 0)
  ), 0);
}

function countRequiredAttributes(attributes) {
  return Array.isArray(attributes)
    ? attributes.filter((attribute) => Boolean(attribute?.is_required)).length
    : 0;
}

function countSelectedAiAttributes(attributes) {
  return Array.isArray(attributes)
    ? attributes.filter((attribute) => attribute?.collect_in_ai !== false).length
    : 0;
}

function getSelectedMetricLabel(selectedProductType) {
  return selectedProductType ? 'No tipo' : 'Sem selecao';
}

function normalizeTypeIdentity(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '');
}

function shouldShowTypeKeyName(friendlyName, keyName) {
  if (!String(keyName || '').trim()) {
    return false;
  }
  return normalizeTypeIdentity(friendlyName) !== normalizeTypeIdentity(keyName);
}

function findMatchingProductType(productTypes, identity) {
  if (!identity) {
    return null;
  }

  return productTypes.find((productType) => (
    String(productType?.id) === String(identity.id)
    || (
      String(productType?.key_name || '').trim()
      && String(productType?.key_name || '').trim() === String(identity.key_name || '').trim()
    )
    || normalizeTypeIdentity(productType?.friendly_name) === normalizeTypeIdentity(identity.friendly_name)
  )) || null;
}

function TiposProdutoPage() {
  const { productTypes, isLoading, error, refreshProductTypes, updateProductType } = useProductTypes();

  const [selectedProductType, setSelectedProductType] = useState(null);
  const [pendingSelectedTypeIdentity, setPendingSelectedTypeIdentity] = useState(null);
  const [typeSearchTerm, setTypeSearchTerm] = useState('');
  const [isAttributeModalOpen, setIsAttributeModalOpen] = useState(false);
  const [editingAttribute, setEditingAttribute] = useState(null);
  const [isNewTypeModalOpen, setIsNewTypeModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isEditTypeModalOpen, setIsEditTypeModalOpen] = useState(false);
  const [editingType, setEditingType] = useState(null);
  const hasAutoSelectedInitialTypeRef = useRef(false);

  const allAttributesCount = useMemo(() => countAllAttributes(productTypes), [productTypes]);
  const aiAttributesCount = useMemo(() => countAiAttributes(productTypes), [productTypes]);

  const filteredProductTypes = useMemo(() => {
    const normalizedSearch = typeSearchTerm.trim().toLowerCase();
    if (!normalizedSearch) {
      return productTypes;
    }

    return productTypes.filter((type) => {
      const friendlyName = String(type?.friendly_name || '').toLowerCase();
      const keyName = String(type?.key_name || '').toLowerCase();
      const description = String(type?.description || '').toLowerCase();
      return friendlyName.includes(normalizedSearch)
        || keyName.includes(normalizedSearch)
        || description.includes(normalizedSearch);
    });
  }, [productTypes, typeSearchTerm]);

  useEffect(() => {
    if (pendingSelectedTypeIdentity) {
      const matchedType = findMatchingProductType(productTypes, pendingSelectedTypeIdentity);
      if (matchedType) {
        setSelectedProductType(matchedType);
        setPendingSelectedTypeIdentity(null);
      }
      return;
    }

    if (!selectedProductType) {
      return;
    }

    const updatedType = productTypes.find(
      (productType) => String(productType.id) === String(selectedProductType.id)
    );

    if (updatedType) {
      setSelectedProductType(updatedType);
    }
  }, [pendingSelectedTypeIdentity, productTypes, selectedProductType]);

  useEffect(() => {
    if (filteredProductTypes.length === 0) {
      if (selectedProductType) {
        setSelectedProductType(null);
      }
      return;
    }

    if (pendingSelectedTypeIdentity) {
      return;
    }

    if (!selectedProductType) {
      if (!hasAutoSelectedInitialTypeRef.current) {
        hasAutoSelectedInitialTypeRef.current = true;
        setSelectedProductType(filteredProductTypes[0]);
      }
      return;
    }

    const isSelectedTypeVisible = filteredProductTypes.some(
      (productType) => productType.id === selectedProductType.id
    );

    if (!isSelectedTypeVisible) {
      setSelectedProductType(filteredProductTypes[0]);
    }
  }, [filteredProductTypes, pendingSelectedTypeIdentity, selectedProductType]);

  const selectedAttributes = Array.isArray(selectedProductType?.attribute_templates)
    ? selectedProductType.attribute_templates
    : [];
  const selectedRequiredCount = countRequiredAttributes(selectedAttributes);
  const selectedAiCount = countSelectedAiAttributes(selectedAttributes);
  const showSelectedKeyName = selectedProductType
    ? shouldShowTypeKeyName(selectedProductType.friendly_name, selectedProductType.key_name)
    : false;

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
    setPendingSelectedTypeIdentity({
      id: newType?.id,
      key_name: newType?.key_name,
      friendly_name: newType?.friendly_name,
    });
    refreshProductTypes();
    setSelectedProductType(newType);
  };

  const handleDeleteType = async (typeId, typeName) => {
    if (window.confirm(`Tem certeza que deseja deletar o tipo de produto "${typeName}"? Isso nao podera ser desfeito.`)) {
      try {
        await productTypeService.deleteProductType(typeId);
        if (selectedProductType && selectedProductType.id === typeId) {
          setSelectedProductType(null);
        }
        showSuccessToast(`Tipo de produto "${typeName}" deletado com sucesso.`);
        refreshProductTypes();
      } catch (err) {
        showErrorToast(
          err.response?.data?.detail || `Falha ao deletar o tipo "${typeName}". Verifique se ele nao esta em uso.`
        );
      }
    }
  };

  const handleSelectType = (type) => {
    setSelectedProductType(type);
  };

  const handleOpenAttributeModal = (attribute) => {
    setEditingAttribute(attribute ?? null);
    setIsAttributeModalOpen(true);
  };

  const handleCloseAttributeModal = () => {
    setIsAttributeModalOpen(false);
    setEditingAttribute(null);
  };

  const handleSaveEditedType = async (payload) => {
    setIsSubmitting(true);
    try {
      await updateProductType(editingType.id, payload);
      refreshProductTypes();
      handleCloseEditTypeModal();
    } catch {
      // toasts tratados no contexto
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveAttribute = async (attributeData) => {
    if (!selectedProductType) {
      showErrorToast('Nenhum tipo de produto selecionado.');
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingAttribute) {
        await productTypeService.updateAttributeInType(
          selectedProductType.id,
          editingAttribute.id,
          attributeData
        );
        showSuccessToast('Atributo atualizado com sucesso!');
      } else {
        await productTypeService.addAttributeToType(selectedProductType.id, attributeData);
        showSuccessToast('Atributo adicionado com sucesso!');
      }
      refreshProductTypes();
      handleCloseAttributeModal();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Falha ao salvar o atributo.';
      showErrorToast(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteAttribute = async (attributeId) => {
    if (window.confirm('Tem certeza que deseja remover este atributo do template?')) {
      try {
        await productTypeService.removeAttributeFromType(selectedProductType.id, attributeId);
        showSuccessToast('Atributo removido com sucesso.');
        refreshProductTypes();
      } catch (err) {
        const errorMsg = err.response?.data?.detail || 'Falha ao remover o atributo.';
        showErrorToast(errorMsg);
      }
    }
  };

  const handleReorderAttribute = async (attributeId, direction) => {
    try {
      await productTypeService.reorderAttributeInType(selectedProductType.id, attributeId, direction);
      showSuccessToast('Ordem do atributo atualizada.');
      refreshProductTypes();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Falha ao reordenar o atributo.';
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
    <div className="app-page-shell ops-page-shell tipos-produto-page-shell">
      <section className="ops-card ops-toolbar-card tipos-produto-stats-card">
        <div className="tipos-produto-stats-header">
          <div className="ops-metrics-row tipos-produto-metrics-row">
            <OperationalStatChip
              icon={<LuBoxes />}
              label="Tipos"
              value={productTypes.length}
              tone="neutral"
            />
            <OperationalStatChip
              icon={<LuTag />}
              label="Atributos"
              value={allAttributesCount}
              tone="info"
            />
            <OperationalStatChip
              icon={<LuSparkles />}
              label="Usados pela IA"
              value={aiAttributesCount}
              tone={aiAttributesCount > 0 ? 'success' : 'neutral'}
            />
            <OperationalStatChip
              icon={<LuTag />}
              label={getSelectedMetricLabel(selectedProductType)}
              value={selectedProductType ? selectedAttributes.length : '--'}
              tone={selectedProductType ? 'info' : 'neutral'}
            />
          </div>
          <button type="button" onClick={handleOpenNewTypeModal} className="ops-primary-btn">
            <LuPlus />
            Novo Tipo
          </button>
        </div>
      </section>

      <section className="ops-card tipos-produto-workspace-card">
        <aside className="tipos-produto-sidebar">
              <div className="tipos-produto-panel-heading">
                <div>
                  <h3>Tipos</h3>
                  <p>Escolha um tipo para editar atributos, regras e sinais usados pela IA.</p>
                </div>
              </div>

          <div className="ops-search-field tipos-produto-search-field">
            <div className="ops-search-input-wrap">
              <LuSearch />
              <input
                id="tipos-produto-search"
                type="text"
                aria-label="Buscar tipos de produto"
                placeholder="Buscar por nome, chave ou descricao..."
                value={typeSearchTerm}
                onChange={(event) => setTypeSearchTerm(event.target.value)}
              />
            </div>
          </div>

          <div className="tipos-produto-type-list">
            {filteredProductTypes.length > 0 ? (
              <ul className="tipos-produto-list">
                {filteredProductTypes.map((type) => {
                  const attributes = Array.isArray(type.attribute_templates) ? type.attribute_templates : [];
                  const aiCount = countSelectedAiAttributes(attributes);
                  const isSelected = selectedProductType?.id === type.id;
                  const showKeyName = shouldShowTypeKeyName(type.friendly_name, type.key_name);

                  return (
                    <li
                      key={type.id}
                      onClick={() => handleSelectType(type)}
                      className={`tipos-produto-list-item${isSelected ? ' is-selected' : ''}`}
                    >
                      <div className="tipos-produto-list-item-copy">
                        <strong>{type.friendly_name}</strong>
                        {showKeyName ? (
                          <span className="tipos-produto-list-item-key">{type.key_name}</span>
                        ) : null}
                        <div className="tipos-produto-list-item-meta">
                          <span>{attributes.length} atribut{attributes.length === 1 ? 'o' : 'os'}</span>
                          <span>{aiCount} usado(s) pela IA</span>
                        </div>
                      </div>
                      <div className="tipos-produto-list-item-actions">
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleOpenEditTypeModal(type);
                          }}
                          title="Editar tipo"
                          className="btn-icon"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            handleDeleteType(type.id, type.friendly_name);
                          }}
                          title="Deletar tipo"
                          className="btn-icon danger"
                        >
                          Excluir
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className="tipos-produto-empty-list">
                {typeSearchTerm.trim()
                  ? 'Nenhum tipo encontrado para a busca atual.'
                  : 'Nenhum tipo cadastrado.'}
              </div>
            )}
          </div>
        </aside>

        <div className="tipos-produto-detail-panel">
          {selectedProductType ? (
            <>
              <div className="tipos-produto-detail-header">
                <div className="tipos-produto-detail-copy">
                  <div className="tipos-produto-detail-title-row">
                    <h3>{selectedProductType.friendly_name}</h3>
                    {showSelectedKeyName ? (
                      <span className="tipos-produto-key-badge">{selectedProductType.key_name}</span>
                    ) : null}
                  </div>
                  <p>
                    {selectedProductType.description
                      ? selectedProductType.description
                      : 'Sem descricao cadastrada para este tipo de produto.'}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn-secondary btn-sm tipos-produto-attribute-action"
                  onClick={() => handleOpenAttributeModal(null)}
                >
                  <LuPlus />
                  Novo Atributo
                </button>
              </div>

              <div className="tipos-produto-detail-metrics">
                <OperationalStatChip
                  icon={<LuTag />}
                  label="Atributos"
                  value={selectedAttributes.length}
                  tone="info"
                />
                <OperationalStatChip
                  icon={<LuSparkles />}
                  label="Usados pela IA"
                  value={selectedAiCount}
                  tone={selectedAiCount > 0 ? 'success' : 'neutral'}
                />
                <OperationalStatChip
                  icon={<LuTag />}
                  label="Obrigatorios"
                  value={selectedRequiredCount}
                  tone={selectedRequiredCount > 0 ? 'warn' : 'neutral'}
                />
              </div>

              <AttributeTemplateList
                attributes={selectedAttributes}
                onEdit={handleOpenAttributeModal}
                onDelete={handleDeleteAttribute}
                onReorder={handleReorderAttribute}
              />
            </>
          ) : (
            <div className="tipos-produto-empty-state">
              <strong>Nenhum tipo disponivel</strong>
              <p>
                {typeSearchTerm.trim()
                  ? 'A busca atual nao encontrou tipos de produto.'
                  : 'Cadastre um tipo novo para comecar a definir atributos e regras da IA.'}
              </p>
            </div>
          )}
        </div>
      </section>

      <NewProductTypeModal
        isOpen={isNewTypeModalOpen}
        onClose={handleCloseNewTypeModal}
        onCreated={handleNewTypeCreated}
      />

      {isEditTypeModalOpen ? (
        <EditProductTypeModal
          isOpen={isEditTypeModalOpen}
          onClose={handleCloseEditTypeModal}
          type={editingType}
          onSave={handleSaveEditedType}
          isSubmitting={isSubmitting}
        />
      ) : null}

      {isAttributeModalOpen ? (
        <AttributeTemplateModal
          isOpen={isAttributeModalOpen}
          onClose={handleCloseAttributeModal}
          attribute={editingAttribute}
          onSave={handleSaveAttribute}
          isSubmitting={isSubmitting}
        />
      ) : null}
    </div>
  );
}

export default TiposProdutoPage;
