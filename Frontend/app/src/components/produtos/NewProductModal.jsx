// Frontend/app/src/components/produtos/NewProductModal.jsx
import React, { useState, useEffect, useCallback } from 'react';
import productTypeService from '../../services/productTypeService';
import { showErrorToast } from '../../utils/notifications';
import AttributeField from './shared/AttributeField';

const tabStyles = {
  tabContainer: { display: 'flex', borderBottom: '1px solid #ccc', marginBottom: '1rem' },
  tabButton: { padding: '10px 15px', cursor: 'pointer', border: 'none', backgroundColor: 'transparent', borderBottom: '3px solid transparent', marginRight: '5px', fontSize: '0.95rem' },
  activeTabButton: { borderBottom: '3px solid var(--primary)', fontWeight: 'bold', color: 'var(--primary)' },
  tabContent: { padding: '1rem 0', minHeight: '300px' }, // Adicionado min-height
  formGroup: { marginBottom: '1rem' }, 
  label: { display: 'block', marginBottom: '0.3rem', fontWeight: '500', color: '#333', fontSize: '0.9rem' }, 
  input: { width: '100%', padding: '0.6rem 0.75rem', border: '1px solid #d1d5db', borderRadius: 'var(--radius)', fontSize: '0.95rem', boxSizing: 'border-box' }, 
};

function NewProductModal({
  isOpen,
  onClose,
  onSave,
  isLoading: propIsLoading,
  productTypes,
  loadingProductTypes
}) {
  const [activeTab, setActiveTab] = useState('INFO_PRINCIPAIS');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [nomeBase, setNomeBase] = useState('');
  const [marca, setMarca] = useState('');
  const [categoriaOriginal, setCategoriaOriginal] = useState('');
  const [skuOriginal, setSkuOriginal] = useState('');
  const [selectedProductTypeId, setSelectedProductTypeId] = useState('');

  const [dynamicAttributes, setDynamicAttributes] = useState({});
  const [currentAttributeTemplates, setCurrentAttributeTemplates] = useState([]);
  const [loadingTemplate, setLoadingTemplate] = useState(false);

  const [manualAttributes, setManualAttributes] = useState([]);
  const [newManualAttributeKey, setNewManualAttributeKey] = useState('');
  const [newManualAttributeValue, setNewManualAttributeValue] = useState('');

  const isLoading = propIsLoading || loadingTemplate;

  const clearForm = useCallback(() => {
    setNomeBase('');
    setMarca('');
    setCategoriaOriginal('');
    setSkuOriginal('');
    setSelectedProductTypeId('');
    setDynamicAttributes({});
    setCurrentAttributeTemplates([]);
    setManualAttributes([]);
    setNewManualAttributeKey('');
    setNewManualAttributeValue('');
    setActiveTab('INFO_PRINCIPAIS');
  }, []);

  useEffect(() => {
    if (isOpen) {
        clearForm();
        setIsSubmitting(false);
    }
  }, [isOpen, clearForm]);

  useEffect(() => {
    if (selectedProductTypeId) {
      const selectedType = Array.isArray(productTypes) 
        ? productTypes.find(pt => pt.id === parseInt(selectedProductTypeId, 10))
        : null;
      
      let templatesToUse = [];

      const initializeAttributes = (templates) => {
        const initialAttrs = {};
        templates.forEach(template => {
          if (template.default_value !== null && template.default_value !== undefined) {
            initialAttrs[template.attribute_key] = template.field_type === 'boolean'
              ? (String(template.default_value).toLowerCase() === 'true' || template.default_value === '1')
              : template.default_value;
          } else {
            initialAttrs[template.attribute_key] = template.field_type === 'boolean' ? false : '';
          }
        });
        setDynamicAttributes(initialAttrs);
        setManualAttributes([]);
      };

      if (selectedType?.attribute_templates?.length) {
        templatesToUse = selectedType.attribute_templates;
        setCurrentAttributeTemplates(templatesToUse);
        initializeAttributes(templatesToUse);
      } else if (selectedType) {
        const fetchDetails = async () => {
          setLoadingTemplate(true);
          setDynamicAttributes({});
          setManualAttributes([]);
          try {
            const details = await productTypeService.getProductTypeDetails(selectedProductTypeId);
            templatesToUse = details?.attribute_templates || [];
            setCurrentAttributeTemplates(templatesToUse);
            initializeAttributes(templatesToUse);
          } catch (error) {
            const errorMsg = error.response?.data?.detail || error.message || "Erro desconhecido ao buscar detalhes."
            showErrorToast(`Falha ao carregar atributos para o tipo: ${errorMsg}`);
            setCurrentAttributeTemplates([]);
            setDynamicAttributes({});
          } finally {
            setLoadingTemplate(false);
          }
        };
        fetchDetails();
      }
    } else {
      setCurrentAttributeTemplates([]);
      setDynamicAttributes({});
      setManualAttributes([]);
    }
  }, [selectedProductTypeId, productTypes]);

  const handleDynamicAttributeChange = (key, value) => {
    setDynamicAttributes(prev => ({ ...prev, [key]: value }));
  };

  const handleAddManualAttribute = () => {
    if (!newManualAttributeKey.trim()) {
      showErrorToast("A chave do atributo manual não pode ser vazia.");
      return;
    }
    const keyToTrim = newManualAttributeKey.trim();
    const keyExistsInTemplate = currentAttributeTemplates.some(attr => attr.attribute_key === keyToTrim);
    const keyExistsInManual = manualAttributes.some(attr => attr.key === keyToTrim);

    if (keyExistsInTemplate || keyExistsInManual) {
      showErrorToast(`O atributo "${keyToTrim}" já existe.`);
      return;
    }

    setManualAttributes(prev => [...prev, { key: keyToTrim, value: newManualAttributeValue.trim() }]);
    setNewManualAttributeKey('');
    setNewManualAttributeValue('');
  };

  const handleManualAttributeChange = (index, field, value) => {
    setManualAttributes(prev =>
      prev.map((attr, i) => (i === index ? { ...attr, [field]: value } : attr))
    );
  };

  const handleRemoveManualAttribute = (index) => {
    setManualAttributes(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!nomeBase.trim()) {
      setActiveTab('INFO_PRINCIPAIS');
      showErrorToast('Nome base é obrigatório.');
      return;
    }
    if (!selectedProductTypeId) {
      showErrorToast('Por favor, selecione um Tipo de Produto.');
      return;
    }
    for (const template of currentAttributeTemplates) {
      if (template.is_required) {
        const value = dynamicAttributes[template.attribute_key];
        if (value === undefined || value === null || String(value).trim() === '') {
          setActiveTab('ATRIBUTOS');
          showErrorToast(`O atributo "${template.label}" é obrigatório.`);
          return;
        }
      }
    }

    const finalDynamicAttributes = { ...dynamicAttributes };
    manualAttributes.forEach(attr => {
      if (attr.key.trim()) {
        finalDynamicAttributes[attr.key.trim()] = attr.value.trim();
      }
    });

    const produtoData = {
      nome_base: nomeBase.trim(),
      marca: marca.trim() || null,
      categoria_original: categoriaOriginal.trim() || null,
      dados_brutos: skuOriginal.trim() ? { sku_original: skuOriginal.trim() } : {}, 
      product_type_id: parseInt(selectedProductTypeId, 10),
      dynamic_attributes: Object.keys(finalDynamicAttributes).length > 0 ? JSON.stringify(finalDynamicAttributes) : null,
    };

    setIsSubmitting(true);
    try {
      await onSave(produtoData);
      clearForm();
      onClose();
    } catch (err) {
      console.error("Falha ao salvar novo produto (capturado no NewProductModal):", err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={`modal active`} id="new-prod-modal">
      <div className="modal-content" style={{maxWidth: '750px', width: '90%'}}>
        <button className="modal-close" onClick={onClose} disabled={isSubmitting || isLoading}>×</button>
        <h3>Criar Novo Produto</h3>

        {/* --- INÍCIO DA LÓGICA CONDICIONAL --- */}

        <div style={tabStyles.formGroup}>
          <label htmlFor="p-product_type" style={tabStyles.label}>Passo 1: Selecione o Tipo de Produto*</label>
          <select
            id="p-product_type"
            name="product_type_id"
            value={selectedProductTypeId}
            onChange={e => setSelectedProductTypeId(e.target.value)}
            disabled={isSubmitting || loadingProductTypes || isLoading}
            style={tabStyles.input}
            required
          >
            <option value="">
              {loadingProductTypes ? 'Carregando tipos...' : '-- Selecione um Tipo --'}
            </option>
            {productTypes && productTypes.map(pt => (
              <option key={pt.id} value={pt.id}>
                {pt.friendly_name}
              </option>
            ))}
          </select>
        </div>
        
        {/* O resto do formulário só aparece DEPOIS que um tipo é selecionado */}
        {selectedProductTypeId && (
          <>
            <div style={tabStyles.tabContainer}>
              <button style={{...tabStyles.tabButton, ...(activeTab === 'INFO_PRINCIPAIS' ? tabStyles.activeTabButton : {})}} onClick={() => setActiveTab('INFO_PRINCIPAIS')} disabled={isSubmitting || isLoading}>Info Principais</button>
              <button style={{...tabStyles.tabButton, ...(activeTab === 'ATRIBUTOS' ? tabStyles.activeTabButton : {})}} onClick={() => setActiveTab('ATRIBUTOS')} disabled={isSubmitting || isLoading}>Atributos</button>
              <button style={{...tabStyles.tabButton, opacity: 0.5}} disabled>Mídia (Em breve)</button>
              <button style={{...tabStyles.tabButton, opacity: 0.5}} disabled>Conteúdo IA (Em breve)</button>
            </div>

            <div style={tabStyles.tabContent}>
              {activeTab === 'INFO_PRINCIPAIS' && (
                <>
                  <div style={tabStyles.formGroup}>
                    <label htmlFor="p-nome_base" style={tabStyles.label}>Nome Base*</label>
                    <input id="p-nome_base" name="nome_base" type="text" value={nomeBase} onChange={e => setNomeBase(e.target.value)} placeholder="Nome principal do produto" style={tabStyles.input} disabled={isSubmitting || isLoading} required />
                  </div>
                  <div style={tabStyles.formGroup}>
                    <label htmlFor="p-marca" style={tabStyles.label}>Marca</label>
                    <input id="p-marca" name="marca" type="text" value={marca} onChange={e => setMarca(e.target.value)} placeholder="Marca do produto" style={tabStyles.input} disabled={isSubmitting || isLoading} />
                  </div>
                  <div style={tabStyles.formGroup}>
                    <label htmlFor="p-categoria_original" style={tabStyles.label}>Categoria Original</label>
                    <input id="p-categoria_original" name="categoria_original" type="text" value={categoriaOriginal} onChange={e => setCategoriaOriginal(e.target.value)} placeholder="Categoria original do produto" style={tabStyles.input} disabled={isSubmitting || isLoading} />
                  </div>
                  <div style={tabStyles.formGroup}>
                    <label htmlFor="p-sku_original" style={tabStyles.label}>SKU Original (em dados_brutos)</label>
                    <input id="p-sku_original" name="sku_original" type="text" value={skuOriginal} onChange={e => setSkuOriginal(e.target.value)} placeholder="SKU original do fornecedor" style={tabStyles.input} disabled={isSubmitting || isLoading} />
                  </div>
                </>
              )}

              {activeTab === 'ATRIBUTOS' && (
                 <>
                    {loadingTemplate ? (
                        <p>Carregando template de atributos...</p>
                    ) : (
                        <>
                            <h4>Atributos para "{productTypes.find(pt => pt.id === parseInt(selectedProductTypeId))?.friendly_name}"</h4>
                            {currentAttributeTemplates.length > 0 ? currentAttributeTemplates.sort((a,b) => a.display_order - b.display_order).map(attrTemplate => (
                            <AttributeField
                                key={attrTemplate.attribute_key}
                                attributeTemplate={attrTemplate}
                                value={dynamicAttributes[attrTemplate.attribute_key]}
                                onChange={handleDynamicAttributeChange}
                                disabled={isSubmitting || isLoading}
                            />
                            )) : <p>Nenhum atributo definido no template para este tipo de produto.</p>}
                            
                            <hr style={{ margin: '20px 0', borderColor: '#eee' }} />
                            
                            <h4>Atributos Manuais Adicionais</h4>
                            {manualAttributes.map((attr, index) => (
                                <div key={index} style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'center' }}>
                                    <input type="text" placeholder="Chave do Atributo" value={attr.key} onChange={(e) => handleManualAttributeChange(index, 'key', e.target.value)} style={{ ...tabStyles.input, flexGrow: 1 }} disabled={isSubmitting || isLoading}/>
                                    <input type="text" placeholder="Valor do Atributo" value={attr.value} onChange={(e) => handleManualAttributeChange(index, 'value', e.target.value)} style={{ ...tabStyles.input, flexGrow: 2 }} disabled={isSubmitting || isLoading}/>
                                    <button type="button" onClick={() => handleRemoveManualAttribute(index)} disabled={isSubmitting || isLoading} title="Remover Atributo Manual" style={{padding: '0.4rem 0.6rem', backgroundColor: 'transparent', color:'var(--danger)', border:'1px solid var(--danger-light)', borderRadius:'var(--radius)', cursor: 'pointer'}}>🗑️</button>
                                </div>
                            ))}
                            <div style={{ display: 'flex', gap: '10px', marginTop: '10px', borderTop: '1px solid #eee', paddingTop: '15px' }}>
                                <input type="text" placeholder="Nova Chave Manual" value={newManualAttributeKey} onChange={(e) => setNewManualAttributeKey(e.target.value)} style={{ ...tabStyles.input, flexGrow: 1 }} disabled={isSubmitting || isLoading}/>
                                <input type="text" placeholder="Novo Valor Manual" value={newManualAttributeValue} onChange={(e) => setNewManualAttributeValue(e.target.value)} style={{ ...tabStyles.input, flexGrow: 2 }} disabled={isSubmitting || isLoading}/>
                                <button type="button" onClick={handleAddManualAttribute} disabled={isSubmitting || isLoading}>Adicionar Manual</button>
                            </div>
                        </>
                    )}
                </>
              )}
            </div>
            
            <button type="button" onClick={handleSubmit} disabled={isSubmitting || isLoading} style={{ marginTop: '20px', padding: '12px', backgroundColor: (isSubmitting || isLoading) ? '#ccc' : 'var(--success)', color: 'white', border: 'none', borderRadius: 'var(--radius)', width: '100%', fontSize: '1rem', cursor: (isSubmitting || isLoading) ? 'not-allowed' : 'pointer' }}>
              {isSubmitting ? 'Salvando...' : 'Salvar Produto'}
            </button>
          </>
        )}
        {/* --- FIM DA LÓGICA CONDICIONAL --- */}
      </div>
    </div>
  );
}

export default NewProductModal;
