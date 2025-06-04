// Frontend/app/src/components/produtos/NewProductModal.jsx
import React, { useState, useEffect, useCallback } from 'react';
import productTypeService from '../../services/productTypeService';
import { showErrorToast } from '../../utils/notifications'; // Removido showSuccessToast se não usado aqui
import AttributeField from './shared/AttributeField';

// Nomes das Abas
const TAB_INFO_PRINCIPAIS = 'INFO_PRINCIPAIS';
const TAB_ATRIBUTOS = 'ATRIBUTOS';
// const TAB_MIDIA = 'MIDIA'; 
// const TAB_CONTEUDO_IA = 'CONTEUDO_IA'; 

// Estilos para as abas
const tabStyles = {
  tabContainer: { display: 'flex', borderBottom: '1px solid #ccc', marginBottom: '1rem' },
  tabButton: { padding: '10px 15px', cursor: 'pointer', border: 'none', backgroundColor: 'transparent', borderBottom: '3px solid transparent', marginRight: '5px', fontSize: '0.95rem' },
  activeTabButton: { borderBottom: '3px solid var(--primary)', fontWeight: 'bold', color: 'var(--primary)' },
  tabContent: { padding: '1rem 0' },
  formGroup: { marginBottom: '1rem' }, 
  label: { display: 'block', marginBottom: '0.3rem', fontWeight: '500', color: '#333', fontSize: '0.9rem' }, 
  input: { width: '100%', padding: '0.6rem 0.75rem', border: '1px solid #d1d5db', borderRadius: 'var(--radius)', fontSize: '0.95rem', boxSizing: 'border-box' }, 
};

function NewProductModal({
  isOpen,
  onClose,
  onSave, // Esta é a função handleSaveProdutoCallback de ProdutosPage.jsx
  isLoading: propIsLoading, // Renomeado para evitar conflito com isLoading interno
  productTypes, // Já vem do context, não precisa ser initialProductTypes
  loadingProductTypes
}) {
  const [activeTab, setActiveTab] = useState(TAB_INFO_PRINCIPAIS);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [nomeBase, setNomeBase] = useState('');
  const [marca, setMarca] = useState('');
  const [categoriaOriginal, setCategoriaOriginal] = useState('');
  const [skuOriginal, setSkuOriginal] = useState(''); // Este será parte de dados_brutos
  const [selectedProductTypeId, setSelectedProductTypeId] = useState('');

  const [dynamicAttributes, setDynamicAttributes] = useState({});
  const [currentAttributeTemplates, setCurrentAttributeTemplates] = useState([]);
  const [loadingTemplate, setLoadingTemplate] = useState(false);

  const [manualAttributes, setManualAttributes] = useState([]);
  const [newManualAttributeKey, setNewManualAttributeKey] = useState('');
  const [newManualAttributeValue, setNewManualAttributeValue] = useState('');

  //isLoading para o componente, considerando o loading da prop e o loading interno do template
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
    setActiveTab(TAB_INFO_PRINCIPAIS);
    // setIsSubmitting(false); // Não resetar isSubmitting aqui, pois pode ser chamado no useEffect de isOpen
  }, []);

  useEffect(() => {
    if (isOpen) { // Limpa o formulário e reseta isSubmitting quando o modal é aberto
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
        setManualAttributes([]); // Limpa atributos manuais ao mudar o tipo
      };

      if (selectedType?.attribute_templates?.length) {
        console.log("NewProductModal: Usando templates pré-carregados do tipo:", selectedType.attribute_templates);
        templatesToUse = selectedType.attribute_templates;
        setCurrentAttributeTemplates(templatesToUse);
        initializeAttributes(templatesToUse);
      } else if (selectedType) {
        console.log("NewProductModal: Buscando detalhes e templates para o tipo ID:", selectedProductTypeId);
        const fetchDetails = async () => {
          setLoadingTemplate(true);
          setDynamicAttributes({}); // Limpa atributos enquanto carrega novos
          setManualAttributes([]);
          try {
            const details = await productTypeService.getProductTypeDetails(selectedProductTypeId);
            templatesToUse = details?.attribute_templates || [];
            setCurrentAttributeTemplates(templatesToUse);
            initializeAttributes(templatesToUse);
            if (!templatesToUse.length) {
                console.log("NewProductModal: Tipo de produto não possui atributos pré-definidos.");
            }
          } catch (error) {
            const errorMsg = error.response?.data?.detail || error.message || "Erro desconhecido ao buscar detalhes."
            showErrorToast(`Falha ao carregar atributos para o tipo: ${errorMsg}`);
            console.error("NewProductModal: Erro em fetchDetails:", error)
            setCurrentAttributeTemplates([]);
            setDynamicAttributes({});
          } finally {
            setLoadingTemplate(false);
          }
        };
        fetchDetails();
      }
    } else { // Se nenhum tipo de produto estiver selecionado
      setCurrentAttributeTemplates([]);
      setDynamicAttributes({});
      setManualAttributes([]);
    }
  }, [selectedProductTypeId, productTypes]); // Removido fetchDetails daqui pois está sendo chamado condicionalmente

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

    if (keyExistsInTemplate) {
      showErrorToast(`A chave "${keyToTrim}" já existe no template. Edite o valor lá, se aplicável.`);
      return;
    }
    if (keyExistsInManual) {
      showErrorToast(`O atributo manual com a chave "${keyToTrim}" já foi adicionado.`);
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

  const handleSubmit = async () => { // Removido 'e' do parâmetro se não usado
    if (!nomeBase.trim()) {
      setActiveTab(TAB_INFO_PRINCIPAIS);
      showErrorToast('Nome base é obrigatório.');
      return;
    }
    if (!selectedProductTypeId) {
      setActiveTab(TAB_INFO_PRINCIPAIS);
      showErrorToast('Por favor, selecione um Tipo de Produto.');
      return;
    }

    for (const template of currentAttributeTemplates) {
      if (template.is_required) {
        const value = dynamicAttributes[template.attribute_key];
        if (value === undefined || value === null || String(value).trim() === '') {
          setActiveTab(TAB_ATRIBUTOS);
          showErrorToast(`O atributo "${template.label}" é obrigatório.`);
          return;
        }
      }
    }
    for (const manualAttr of manualAttributes) {
        if (!manualAttr.key.trim() && manualAttr.value.trim()) {
            setActiveTab(TAB_ATRIBUTOS);
            showErrorToast('Um atributo manual tem um valor mas não tem uma chave. Por favor, defina a chave ou remova o atributo.');
            return;
        }
    }

    const finalDynamicAttributes = { ...dynamicAttributes };
    manualAttributes.forEach(attr => {
      if (attr.key.trim()) { // Só adiciona se a chave não for vazia
        finalDynamicAttributes[attr.key.trim()] = attr.value.trim(); // Garante que o valor também seja trimado
      }
    });

    const produtoData = {
      nome_base: nomeBase.trim(),
      marca: marca.trim() || null, // Envia null se vazio
      categoria_original: categoriaOriginal.trim() || null, // Envia null se vazio
      // Monta dados_brutos corretamente
      dados_brutos: skuOriginal.trim() ? { sku_original: skuOriginal.trim() } : {}, 
      product_type_id: parseInt(selectedProductTypeId, 10),
      // --- ALTERAÇÃO PARA ENVIAR dynamic_attributes COMO STRING JSON ---
      dynamic_attributes: Object.keys(finalDynamicAttributes).length > 0 ? JSON.stringify(finalDynamicAttributes) : null,
      // Adicione outros campos que seu backend espera no ProdutoCreate, como:
      // sku: skuOriginal.trim() || null, // Se sku é um campo direto e não em dados_brutos
      // ean: ean.trim() || null,
      // modelo: modelo.trim() || null,
      // preco_custo: preco_custo ? parseFloat(preco_custo) : null,
      // preco_venda: preco_venda ? parseFloat(preco_venda) : null,
      // descricao_original: descricao_original.trim() || null,
    };
    
    // --- LOG PARA VER O PAYLOAD ANTES DE ENVIAR ---
    console.log("PAYLOAD PARA CRIAR PRODUTO (NewProductModal):", JSON.stringify(produtoData, null, 2));

    setIsSubmitting(true);
    try {
      await onSave(produtoData); // onSave é handleSaveProdutoCallback de ProdutosPage.jsx
      // showSuccessToast("Produto salvo com sucesso!"); // ProdutosPage.jsx já mostra essa mensagem
      clearForm(); // Limpa o formulário
      onClose();   // Fecha o modal
    } catch (err) {
      // O erro já deve ser logado e notificado por handleSaveProdutoCallback em ProdutosPage
      console.error("Falha ao salvar novo produto (capturado no NewProductModal):", err);
      // showErrorToast já deve ser chamado por handleSaveProdutoCallback
    } finally {
      setIsSubmitting(false);
    }
  };


  if (!isOpen) return null;

  const renderTabContent = () => {
    switch (activeTab) {
      case TAB_INFO_PRINCIPAIS:
        return (
          <>
            <div style={tabStyles.formGroup}>
              <label htmlFor="p-product_type" style={tabStyles.label}>Tipo de Produto*</label>
              <select
                id="p-product_type"
                name="product_type_id"
                value={selectedProductTypeId}
                onChange={e => setSelectedProductTypeId(e.target.value)}
                disabled={isSubmitting || loadingProductTypes || isLoading}
                style={tabStyles.input}
                required // Adicionado required
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
            {/* Adicionar outros campos básicos aqui se necessário, como EAN, Modelo, Preços, Descrição */}
          </>
        );
      case TAB_ATRIBUTOS:
        if (!selectedProductTypeId) {
          return <p>Por favor, selecione um Tipo de Produto na aba "Informações Principais" para ver os atributos.</p>;
        }
        if (loadingTemplate) {
          return <p>Carregando template de atributos...</p>;
        }
        return (
          <>
            <h4>Atributos para "{productTypes.find(pt => pt.id === parseInt(selectedProductTypeId))?.friendly_name}"</h4>
            {currentAttributeTemplates.length > 0 ? currentAttributeTemplates.sort((a,b) => a.display_order - b.display_order).map(attrTemplate => (
              <AttributeField
                key={attrTemplate.attribute_key}
                attributeTemplate={attrTemplate} // Passando o template completo
                value={dynamicAttributes[attrTemplate.attribute_key]}
                onChange={handleDynamicAttributeChange}
                disabled={isSubmitting || isLoading}
              />
            )) : <p>Nenhum atributo definido no template para este tipo de produto.</p>}

            <hr style={{ margin: '20px 0', borderColor: '#eee' }} />
            <h4>Atributos Manuais Adicionais</h4>
            {manualAttributes.map((attr, index) => (
              <div key={index} style={{ display: 'flex', gap: '10px', marginBottom: '10px', alignItems: 'center' }}>
                <input
                  type="text"
                  placeholder="Chave do Atributo"
                  value={attr.key}
                  onChange={(e) => handleManualAttributeChange(index, 'key', e.target.value)}
                  style={{ ...tabStyles.input, flexGrow: 1 }}
                  disabled={isSubmitting || isLoading}
                />
                <input
                  type="text"
                  placeholder="Valor do Atributo"
                  value={attr.value}
                  onChange={(e) => handleManualAttributeChange(index, 'value', e.target.value)}
                  style={{ ...tabStyles.input, flexGrow: 2 }}
                  disabled={isSubmitting || isLoading}
                />
                <button
                  type="button" // importante para não submeter o form principal
                  onClick={() => handleRemoveManualAttribute(index)}
                  disabled={isSubmitting || isLoading}
                  title="Remover Atributo Manual"
                  style={{padding: '0.4rem 0.6rem', backgroundColor: 'transparent', color:'var(--danger)', border:'1px solid var(--danger-light)', borderRadius:'var(--radius)', cursor: 'pointer'}}
                >
                  🗑️
                </button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: '10px', marginTop: '10px', borderTop: '1px solid #eee', paddingTop: '15px' }}>
              <input
                type="text"
                placeholder="Nova Chave Manual"
                value={newManualAttributeKey}
                onChange={(e) => setNewManualAttributeKey(e.target.value)}
                style={{ ...tabStyles.input, flexGrow: 1 }}
                disabled={isSubmitting || isLoading}
              />
              <input
                type="text"
                placeholder="Novo Valor Manual"
                value={newManualAttributeValue}
                onChange={(e) => setNewManualAttributeValue(e.target.value)}
                style={{ ...tabStyles.input, flexGrow: 2 }}
                disabled={isSubmitting || isLoading}
              />
              <button
                type="button" // importante
                onClick={handleAddManualAttribute}
                disabled={isSubmitting || isLoading}
                style={{padding: '0.6rem 1rem', backgroundColor: 'var(--primary-lightest)', color: 'var(--primary)', border: '1px solid var(--primary-light)', borderRadius:'var(--radius)', cursor: 'pointer'}}
              >
                Adicionar Manual
              </button>
            </div>
          </>
        );
      default:
        return <p>Aba '{activeTab}' ainda não implementada.</p>;
    }
  };

  return (
    <div className={`modal ${isOpen ? 'active' : ''}`} id="new-prod-modal"> {/* Usa a classe 'active' para controlar visibilidade via CSS */}
      <div className="modal-content" style={{maxWidth: '750px', width: '90%'}}>
        <button className="modal-close" onClick={onClose} disabled={isSubmitting || isLoading}>×</button>
        <h3>Novo Produto</h3>

        <div style={tabStyles.tabContainer}>
          <button style={{...tabStyles.tabButton, ...(activeTab === TAB_INFO_PRINCIPAIS ? tabStyles.activeTabButton : {})}} onClick={() => setActiveTab(TAB_INFO_PRINCIPAIS)} disabled={isSubmitting || isLoading}>Info Principais</button>
          <button style={{...tabStyles.tabButton, ...(activeTab === TAB_ATRIBUTOS ? tabStyles.activeTabButton : {})}} onClick={() => setActiveTab(TAB_ATRIBUTOS)} disabled={!selectedProductTypeId || isSubmitting || isLoading}>Atributos</button>
          <button style={{...tabStyles.tabButton, opacity: 0.5}} disabled>Mídia (Em breve)</button>
          <button style={{...tabStyles.tabButton, opacity: 0.5}} disabled>Conteúdo IA (Em breve)</button>
        </div>

        <div style={tabStyles.tabContent}>
          {renderTabContent()}
        </div>

        <button
            type="button" // Alterado para type="button" para ser chamado por handleSubmit
            onClick={handleSubmit} // Chama a função de submit que tem validações
            disabled={isSubmitting || loadingProductTypes || isLoading || loadingTemplate}
            style={{
                marginTop: '20px',
                padding: '12px',
                backgroundColor: (isSubmitting || loadingProductTypes || isLoading || loadingTemplate) ? 'var(--disabled-bg)' : 'var(--success)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--radius)',
                width: '100%',
                fontSize: '1rem',
                cursor: (isSubmitting || loadingProductTypes || isLoading || loadingTemplate) ? 'not-allowed' : 'pointer'
            }}
        >
          {isSubmitting ? 'Salvando...' : 'Salvar Produto'}
        </button>
      </div>
    </div>
  );
}

// Removido PropTypes se não estiver usando extensivamente para simplificar
// NewProductModal.propTypes = { ... };

export default NewProductModal;