// Frontend/app/src/components/ProductEditModal.jsx
import React, { useState, useEffect, useCallback } from 'react';
import Modal from './common/Modal';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications'; 
import productService from '../services/productService'; 
import fornecedorService from '../services/fornecedorService'; 
import AttributeField from './produtos/shared/AttributeField';
import { useProductTypes } from '../contexts/ProductTypeContext';
import './ProductEditModal.css';

// Campos base que não devem aparecer como atributos dinâmicos
const BASE_PRODUCT_FIELDS = new Set([
    'nome_base',
    'nome_chat_api',
    'descricao_original',
    'descricao_curta_orig',
    'descricao_principal_gerada',
    'descricao_curta_gerada',
    'sku',
    'ean',
    'ncm',
    'marca',
    'modelo',
    'categoria_original',
    'categoria_mapeada',
    'preco_custo',
    'preco_venda',
    'preco_promocional',
    'estoque_disponivel',
    'peso_kg',
    'altura_cm',
    'largura_cm',
    'profundidade_cm',
    'imagem_principal_url',
    'imagens_secundarias_urls',
    'fornecedor_id',
    'product_type_id',
    'ativo_marketplace',
    'data_publicacao_marketplace',
    'status_enriquecimento_web',
    'status_titulo_ia',
    'status_descricao_ia',
    'log_enriquecimento_web',
    'titulos_sugeridos',
]);

const initialFormData = {
    nome_base: '',
    nome_chat_api: '',
    descricao_original: '',
    descricao_curta_orig: '',
    descricao_principal_gerada: '',
    descricao_curta_gerada: '',
    sku: '',
    ean: '',
    ncm: '',
    marca: '',
    modelo: '',
    categoria_original: '',
    categoria_mapeada: '',
    preco_custo: '',
    preco_venda: '',
    preco_promocional: '',
    estoque_disponivel: '',
    peso_kg: '',
    altura_cm: '',
    largura_cm: '',
    profundidade_cm: '',
    imagem_principal_url: '',
    imagens_secundarias_urls: [],
    fornecedor_id: '',
    product_type_id: '',
    dynamic_attributes: {},
    dados_brutos: {},
    titulos_sugeridos: [],
    ativo_marketplace: false,
    data_publicacao_marketplace: null,
    log_enriquecimento_web: { historico_mensagens: [] },
    status_enriquecimento_web: null,
    status_titulo_ia: null,
    status_descricao_ia: null,
};

const ProductEditModal = ({ isOpen, onClose, product, onProductUpdated }) => {
    const isNewProduct = !product?.id;

    const [formData, setFormData] = useState(initialFormData);
    const [activeTab, setActiveTab] = useState('info'); 
    const [isLoading, setIsLoading] = useState(false);
    const [isGeneratingIA, setIsGeneratingIA] = useState(false);
    const [isEnrichingWeb, setIsEnrichingWeb] = useState(false);
    const [isSuggestingGemini, setIsSuggestingGemini] = useState(false);
    const [error, setError] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const { productTypes } = useProductTypes();

    // Para novos produtos, mostramos primeiro a seleção do tipo
    const [stage, setStage] = useState('form'); // 'selectType' ou 'form'

    const [iaAttributeSuggestions, setIaAttributeSuggestions] = useState({});
    const [selectedIaSuggestions, setSelectedIaSuggestions] = useState({});


    useEffect(() => {
        const fetchDependencies = async () => {
            if (isOpen) {
                try {
                    const fetchedFornecedores = await fornecedorService.getFornecedores({skip: 0, limit: 100});
                    setFornecedores(fetchedFornecedores.items || []);
                } catch (err) {
                    console.error("Erro ao carregar fornecedores:", err);
                    showErrorToast("Erro ao carregar lista de fornecedores para o modal.");
                }
            }
        };
        fetchDependencies();
    }, [isOpen]);

    // Define o estágio inicial quando o modal é aberto
    useEffect(() => {
        if (isOpen) {
            if (isNewProduct) {
                setStage(formData.product_type_id ? 'form' : 'selectType');
            } else {
                setStage('form');
            }
        }
    }, [isOpen, isNewProduct, formData.product_type_id]);

    const extractIaSuggestions = useCallback((dadosBrutos) => {
        const extracted = {};
        if (dadosBrutos) {
            if (dadosBrutos.especificacoes_tecnicas_dict && typeof dadosBrutos.especificacoes_tecnicas_dict === 'object') {
                for (const key in dadosBrutos.especificacoes_tecnicas_dict) {
                    if (Object.prototype.hasOwnProperty.call(dadosBrutos.especificacoes_tecnicas_dict, key)) {
                        extracted[key] = dadosBrutos.especificacoes_tecnicas_dict[key];
                    }
                }
            }
        }
        setIaAttributeSuggestions(extracted);
        const initialSelections = {};
        for (const key in extracted) {
            initialSelections[key] = false;
        }
        setSelectedIaSuggestions(initialSelections);
    }, []);

    useEffect(() => {
        if (isOpen) {
            if (product) {
                const dynamicAttrsRaw = (product.dynamic_attributes && typeof product.dynamic_attributes === 'object') ? product.dynamic_attributes : {};
                const dynamicAttrs = Object.fromEntries(
                    Object.entries(dynamicAttrsRaw).filter(([key]) => !BASE_PRODUCT_FIELDS.has(key))
                );
                const dadosBrutos = (product.dados_brutos && typeof product.dados_brutos === 'object') ? product.dados_brutos : {};

                setFormData({
                    nome_base: product.nome_base || '',
                    nome_chat_api: product.nome_chat_api || '',
                    descricao_original: product.descricao_original || '',
                    descricao_curta_orig: product.descricao_curta_orig || '',
                    descricao_principal_gerada: product.descricao_principal_gerada || '',
                    descricao_curta_gerada: product.descricao_curta_gerada || '',
                    sku: product.sku || '',
                    ean: product.ean || '',
                    ncm: product.ncm || '',
                    marca: product.marca || '',
                    modelo: product.modelo || '',
                    categoria_original: product.categoria_original || '',
                    categoria_mapeada: product.categoria_mapeada || '',
                    preco_custo: product.preco_custo || '',
                    preco_venda: product.preco_venda || '',
                    preco_promocional: product.preco_promocional || '',
                    estoque_disponivel: product.estoque_disponivel || '',
                    peso_kg: product.peso_kg || '',
                    altura_cm: product.altura_cm || '',
                    largura_cm: product.largura_cm || '',
                    profundidade_cm: product.profundidade_cm || '',
                    imagem_principal_url: product.imagem_principal_url || '',
                    imagens_secundarias_urls: product.imagens_secundarias_urls || [],
                    fornecedor_id: product.fornecedor_id || '',
                    product_type_id: product.product_type_id || '',
                    dynamic_attributes: dynamicAttrs,
                    dados_brutos: dadosBrutos,
                    titulos_sugeridos: product.titulos_sugeridos || [],
                    ativo_marketplace: product.ativo_marketplace || false,
                    data_publicacao_marketplace: product.data_publicacao_marketplace || null,
                    log_enriquecimento_web: product.log_enriquecimento_web || { historico_mensagens: [] },
                    status_enriquecimento_web: product.status_enriquecimento_web || null,
                    status_titulo_ia: product.status_titulo_ia || null,
                    status_descricao_ia: product.status_descricao_ia || null,
                });
                extractIaSuggestions(dadosBrutos);
            } else {
                setFormData(initialFormData);
                setIaAttributeSuggestions({});
                setSelectedIaSuggestions({});
                setIsEnrichingWeb(false);
                setIsGeneratingIA(false);
                setIsSuggestingGemini(false);
            }
            setActiveTab('info');
            setError(null);
        }
    }, [product, isOpen, extractIaSuggestions]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        if (name === 'imagens_secundarias_urls') {
            const urls = value.split(',').map(url => url.trim()).filter(url => url);
            setFormData(prev => ({ ...prev, [name]: urls }));
        } else if (type === 'checkbox') {
            setFormData(prev => ({ ...prev, [name]: checked }));
        } else {
            setFormData(prev => ({ ...prev, [name]: value }));
        }
    };

    const handleDynamicAttributeChange = (key, value) => {
        setFormData(prev => ({
            ...prev,
            dynamic_attributes: {
                ...prev.dynamic_attributes,
                [key]: value,
            },
        }));
    };

    const initializeAttributesForType = useCallback((typeId) => {
        const selectedType = productTypes.find(pt => pt.id === parseInt(typeId, 10));
        if (selectedType && selectedType.attribute_templates) {
            const initialAttrs = {};
            selectedType.attribute_templates
                .filter(tpl => !BASE_PRODUCT_FIELDS.has(tpl.attribute_key))
                .forEach(template => {
                    if (template.default_value !== null && template.default_value !== undefined) {
                        initialAttrs[template.attribute_key] = template.field_type === 'boolean'
                            ? (String(template.default_value).toLowerCase() === 'true' || template.default_value === '1')
                            : template.default_value;
                    } else {
                        initialAttrs[template.attribute_key] = template.field_type === 'boolean' ? false : '';
                    }
                });
            setFormData(prev => ({ ...prev, dynamic_attributes: initialAttrs }));
        }
    }, [productTypes]);

    const addDynamicAttribute = () => {
        const newKey = prompt("Digite a chave do novo atributo (ex: 'cor', 'voltagem'):");
        if (newKey && !formData.dynamic_attributes.hasOwnProperty(newKey) && !BASE_PRODUCT_FIELDS.has(newKey)) {
            setFormData(prev => ({
                ...prev,
                dynamic_attributes: {
                    ...prev.dynamic_attributes,
                    [newKey]: '',
                },
            }));
        } else if (newKey) {
            showWarningToast("Atributo com esta chave já existe ou é um campo básico.");
        }
    };

    const handleIaSuggestionToggle = (key) => {
        setSelectedIaSuggestions(prev => ({ ...prev, [key]: !prev[key] }));
    };

    const applySelectedIaSuggestions = () => {
        const attributesToApply = {};
        let appliedCount = 0;
        for (const key in selectedIaSuggestions) {
            if (selectedIaSuggestions[key] && iaAttributeSuggestions[key] !== undefined) {
                attributesToApply[key] = iaAttributeSuggestions[key];
                appliedCount++;
            }
        }
        if (appliedCount === 0) {
            showWarningToast("Nenhuma sugestão selecionada para aplicar.");
            return;
        }
        setFormData(prev => ({
            ...prev,
            dynamic_attributes: { ...prev.dynamic_attributes, ...attributesToApply }
        }));
        showSuccessToast(`${appliedCount} sugest${appliedCount > 1 ? 'ões' : 'ão'} aplicada${appliedCount > 1 ? 's' : ''} aos atributos dinâmicos!`);
        setActiveTab('atributos');
    };

    const handleContinueAfterTypeSelect = () => {
        if (formData.product_type_id) {
            initializeAttributesForType(formData.product_type_id);
            setStage('form');
        } else {
            showWarningToast('Selecione um Tipo de Produto para continuar.');
        }
    };

    const handleEnrichWeb = async () => {
        if (!product?.id) {
            showWarningToast("Salve o produto primeiro antes de enriquecer a web.");
            return;
        }
        setIsEnrichingWeb(true);
        setError(null);
        showInfoToast("Processo de enriquecimento web iniciado. Isso pode levar alguns minutos e atualizará o log e as sugestões.");
        try {
            await productService.iniciarEnriquecimentoWebProduto(product.id); 
            showSuccessToast("Comando de enriquecimento enviado. O produto será atualizado em segundo plano.");
        } catch (err) {
            const errorDetail = err.response?.data?.detail || "Erro ao iniciar enriquecimento web.";
            setError(errorDetail);
            showErrorToast(errorDetail);
        } finally {
            setIsEnrichingWeb(false);
        }
    };

    const handleFetchGeminiSuggestions = async () => {
        if (!product?.id) {
            showWarningToast("É preciso salvar o produto antes de buscar sugestões com Gemini.");
            return;
        }
        setIsSuggestingGemini(true);
        setError(null);
        showInfoToast("Buscando sugestões de atributos com a IA (Gemini)... Isso pode levar um momento.");

        try {
            const suggestionsData = await productService.getAtributoSugestions(product.id);
            if (suggestionsData && suggestionsData.sugestoes_atributos && suggestionsData.sugestoes_atributos.length > 0) {
                const newSuggestions = suggestionsData.sugestoes_atributos.reduce((acc, item) => {
                    acc[item.chave_atributo] = item.valor_sugerido;
                    return acc;
                }, {});
                setIaAttributeSuggestions(newSuggestions);
                const initialSelections = Object.keys(newSuggestions).reduce((acc, key) => {
                    acc[key] = false;
                    return acc;
                }, {});
                setSelectedIaSuggestions(initialSelections);
                showSuccessToast("Sugestões da IA (Gemini) carregadas!");
            } else {
                setIaAttributeSuggestions({});
                setSelectedIaSuggestions({});
                showInfoToast("Nenhuma sugestão de atributo específica retornada pela IA (Gemini).");
            }
        } catch (err) {
            console.error("Erro ao buscar sugestões Gemini:", err);
            const errorDetail = err.response?.data?.detail || err.message || "Falha ao carregar sugestões da IA (Gemini).";
            setError(errorDetail);
            showErrorToast(errorDetail);
            setIaAttributeSuggestions({});
            setSelectedIaSuggestions({});
        } finally {
            setIsSuggestingGemini(false);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        if (!formData.nome_base) {
            showErrorToast("O nome base do produto é obrigatório.");
            setActiveTab('info');
            setIsLoading(false);
            return;
        }
        
        try {
            const productDataToSave = { ...formData };
            let responseProduct;
            if (isNewProduct) {
                responseProduct = await productService.createProduto(productDataToSave);
                showSuccessToast("Produto criado com sucesso!");
            } else {
                responseProduct = await productService.updateProduto(product.id, productDataToSave);
                showSuccessToast("Produto atualizado com sucesso!");
            }
            if(onProductUpdated) onProductUpdated(responseProduct);
            onClose(); 
        } catch (err) {
            const errorDetail = err.response?.data?.detail || err.message || "Erro ao salvar produto.";
            setError(errorDetail);
            showErrorToast(errorDetail);
        } finally {
            setIsLoading(false);
        }
    };

    const handleGenerateTitles = async () => {
        if (!product?.id) {
            showWarningToast("Salve o produto primeiro para gerar títulos.");
            return;
        }
        setIsGeneratingIA(true);
        try {
            await productService.gerarTitulosProduto(product.id);
            showInfoToast("Geração de títulos iniciada. Verifique em breve.");
            setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({ ...prev, nome_chat_api: updatedProduct.nome_chat_api, titulos_sugeridos: updatedProduct.titulos_sugeridos }));
                if (onProductUpdated) onProductUpdated(updatedProduct);
            }, 7000); 
        } catch (err) {
            console.error("Erro ao gerar títulos:", err);
            showErrorToast(err.response?.data?.detail || "Erro ao gerar títulos.");
        } finally {
            setIsGeneratingIA(false);
        }
    };

    const handleGenerateDescription = async () => {
        if (!product?.id) {
            showWarningToast("Salve o produto primeiro para gerar descrição.");
            return;
        }
        setIsGeneratingIA(true);
        try {
            await productService.gerarDescricaoProduto(product.id);
            showInfoToast("Geração de descrição iniciada. Verifique em breve.");
             setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({
                    ...prev,
                    descricao_principal_gerada: updatedProduct.descricao_principal_gerada,
                }));
                if (onProductUpdated) onProductUpdated(updatedProduct);
            }, 7000); 
        } catch (err) {
            console.error("Erro ao gerar descrição:", err);
            showErrorToast(err.response?.data?.detail || "Erro ao gerar descrição.");
        } finally {
            setIsGeneratingIA(false);
        }
    };

    const handleCopyToDescriptionOriginal = (generatedText) => {
        setFormData(prev => ({ ...prev, descricao_original: generatedText }));
        showInfoToast("Descrição gerada copiada para o campo original.");
    };

    const handleCopyToDescriptionCurtaOriginal = (generatedText) => {
        setFormData(prev => ({ ...prev, descricao_curta_orig: generatedText }));
        showInfoToast("Descrição curta gerada copiada para o campo original.");
    };

    const selectedProductType = productTypes.find(type => type.id === parseInt(formData.product_type_id));
    const attributeTemplates = selectedProductType ? selectedProductType.attribute_templates : [];

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={isNewProduct ? "Criar Novo Produto" : `Editar Produto: ${formData.nome_base || 'ID ' + product?.id}`}>
            {stage === 'selectType' ? (
                <div className="form-section" style={{padding:'1rem'}}>
                    <label>
                        Tipo de Produto:
                        <select name="product_type_id" value={formData.product_type_id} onChange={handleChange} required>
                            <option value="">Selecione um tipo</option>
                            {(productTypes || []).map(type => (
                                <option key={type.id} value={type.id}>{type.friendly_name}</option>
                            ))}
                        </select>
                    </label>
                    <div className="modal-actions" style={{marginTop:'20px'}}>
                        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
                        <button type="button" onClick={handleContinueAfterTypeSelect} className="btn-primary" disabled={!formData.product_type_id}>Continuar</button>
                    </div>
                </div>
            ) : (
            <form onSubmit={handleSubmit}>
                <div className="tab-navigation">
                    <button type="button" className={activeTab === 'info' ? 'active' : ''} onClick={() => setActiveTab('info')}>Info Principais</button>
                    <button type="button" className={activeTab === 'atributos' ? 'active' : ''} onClick={() => setActiveTab('atributos')} disabled={!formData.product_type_id}>Atributos</button>
                    <button type="button" className={activeTab === 'midia' ? 'active' : ''} onClick={() => setActiveTab('midia')} disabled={!formData.product_type_id}>Mídia</button>
                    <button type="button" className={activeTab === 'conteudo-ia' ? 'active' : ''} onClick={() => setActiveTab('conteudo-ia')} disabled={!formData.product_type_id}>Conteúdo IA</button>
                    <button type="button" className={activeTab === 'sugestoes-ia' ? 'active' : ''} onClick={() => setActiveTab('sugestoes-ia')} disabled={!formData.product_type_id}>Sugestões IA</button>
                    <button type="button" className={activeTab === 'log' ? 'active' : ''} onClick={() => setActiveTab('log')} disabled={!formData.product_type_id}>Log</button>
                </div>

                <div className="tab-content">
                    {activeTab === 'info' && (
                        <div className="form-section form-grid">
                            <label>
                                Tipo de Produto:
                                <select name="product_type_id" value={formData.product_type_id} onChange={handleChange} required>
                                    <option value="">Selecione um tipo</option>
                                    {(productTypes || []).map(type => (
                                        <option key={type.id} value={type.id}>{type.friendly_name}</option>
                                    ))}
                                </select>
                            </label>
                            {formData.product_type_id && (
                                <>
                                    <label> Nome Base: <input type="text" name="nome_base" value={formData.nome_base} onChange={handleChange} required /> </label>
                                    <label> Marca: <input type="text" name="marca" value={formData.marca} onChange={handleChange} /> </label>
                                    <label> SKU: <input type="text" name="sku" value={formData.sku} onChange={handleChange} /> </label>
                                    <label> Fornecedor:
                                        <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange}>
                                            <option value="">Selecione um fornecedor</option>
                                            {fornecedores.map(f => (<option key={f.id} value={f.id}>{f.nome}</option>))}
                                        </select>
                                    </label>
                                </>
                            )}
                        </div>
                    )}
                    {activeTab === 'atributos' && (
                        <div className="form-section">
                             <h3>Atributos Dinâmicos e de Template</h3>
                             {!formData.product_type_id && <p>Selecione um Tipo de Produto na aba "Info Principais".</p>}
                             {attributeTemplates && attributeTemplates.length > 0 && (
                                 <div>
                                     <h4>Atributos do Tipo ({selectedProductType?.friendly_name})</h4>
                                     {attributeTemplates.filter(attr => !BASE_PRODUCT_FIELDS.has(attr.attribute_key)).map(attr => (
                                         <AttributeField
                                             key={attr.attribute_key}
                                             attributeTemplate={attr}
                                             value={formData.dynamic_attributes[attr.attribute_key]}
                                             onChange={handleDynamicAttributeChange}
                                         />
                                     ))}
                                 </div>
                             )}
                             <h4>Outros Atributos (Manuais)</h4>
                             {Object.entries(formData.dynamic_attributes)
                                 .filter(([key]) => !attributeTemplates.some(template => template.attribute_key === key))
                                 .filter(([key]) => !BASE_PRODUCT_FIELDS.has(key))
                                 .map(([key, value]) => (
                                     <div key={key} style={{display: 'flex', gap: '10px', alignItems: 'center', marginBottom:'5px'}}>
                                         <input type="text" value={key} disabled style={{flex:'1', backgroundColor:'#f0f0f0'}} />
                                         <input type="text" value={value || ''} onChange={(e) => handleDynamicAttributeChange(key, e.target.value)} style={{flex:'2'}} />
                                         <button type="button" onClick={() => {
                                             const {[key]: _, ...rest} = formData.dynamic_attributes;
                                             setFormData(prev => ({...prev, dynamic_attributes: rest}));
                                             showInfoToast(`Atributo manual "${key}" removido.`);
                                         }} title="Remover este atributo manual" style={{padding:'5px', color:'red', border:'none', background:'transparent', cursor:'pointer'}}>🗑️</button>
                                     </div>
                             ))}
                              <button type="button" onClick={addDynamicAttribute} style={{marginTop:'10px'}}>Adicionar Atributo Manual</button>
                        </div>
                    )}
                    {activeTab === 'midia' && (
                         <div className="form-section">
                             <h3>Mídia do Produto</h3>
                             <label> URL Imagem Principal: <input type="url" name="imagem_principal_url" value={formData.imagem_principal_url} onChange={handleChange} /> </label>
                             <div className="image-previews">
                                 {formData.imagem_principal_url && ( <img src={formData.imagem_principal_url} alt="Principal" style={{ maxWidth: '100px', maxHeight: '100px', margin: '5px', border:'2px solid var(--primary)' }} /> )}
                             </div>
                         </div>
                    )}
                    {activeTab === 'conteudo-ia' && (
                        <div className="form-section">
                            <h3>Conteúdo Gerado por IA</h3>
                            <button type="button" onClick={handleGenerateTitles} disabled={isGeneratingIA || isNewProduct}> {isGeneratingIA ? 'Gerando Títulos...' : 'Gerar Títulos (OpenAI)'} </button>
                            {formData.titulos_sugeridos && formData.titulos_sugeridos.length > 0 && ( <div> <h4>Títulos Sugeridos:</h4> <ul> {formData.titulos_sugeridos.map((title, index) => ( <li key={index}>{title}</li> ))} </ul> </div> )}
                            <hr />
                            <button type="button" onClick={handleGenerateDescription} disabled={isGeneratingIA || isNewProduct}> {isGeneratingIA ? 'Gerando Descrição...' : 'Gerar Descrição (OpenAI)'} </button>
                            {formData.descricao_principal_gerada && ( <div style={{ marginTop: '10px' }}> <h4>Descrição Principal Gerada:</h4> <textarea value={formData.descricao_principal_gerada} readOnly rows="10" style={{ width: '100%', backgroundColor: '#f9f9f9' }} /> </div> )}
                        </div>
                    )}
                    {activeTab === 'sugestoes-ia' && (
                        <div className="form-section">
                            <h3>Sugestões de Atributos por IA</h3>
                            <div className="suggestion-action-box">
                                <p>Busque sugestões rápidas de atributos usando Gemini com os dados atuais do produto.</p>
                                <button type="button" onClick={handleFetchGeminiSuggestions} disabled={isSuggestingGemini || isNewProduct}>
                                    {isSuggestingGemini ? 'Buscando...' : 'Buscar Sugestões (Gemini)'}
                                </button>
                            </div>
                            {Object.keys(iaAttributeSuggestions).length > 0 && (
                                <div className="ia-suggestions-container">
                                    <h4>Sugestões Encontradas:</h4>
                                    <div className="ia-suggestions-grid">
                                        {Object.entries(iaAttributeSuggestions).map(([key, value]) => (
                                            <div key={key} className={`ia-suggestion-item ${selectedIaSuggestions[key] ? 'selected' : ''}`}>
                                                <label>
                                                    <input type="checkbox" checked={!!selectedIaSuggestions[key]} onChange={() => handleIaSuggestionToggle(key)}/>
                                                    <div><strong>{key}:</strong> {String(value)}</div>
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                    <button type="button" onClick={applySelectedIaSuggestions} className="btn-apply-suggestions">
                                        Aplicar Selecionados
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                    {activeTab === 'log' && (
                        <div className="form-section">
                             <h3>Log de Processamento</h3>
                             {formData.log_enriquecimento_web && formData.log_enriquecimento_web.historico_mensagens && formData.log_enriquecimento_web.historico_mensagens.length > 0 ? (
                                 <div className="log-container">
                                     {formData.log_enriquecimento_web.historico_mensagens.map((msg, index) => (
                                         <p key={index}>{msg}</p>
                                     ))}
                                 </div>
                             ) : (
                                 <p>Nenhum log disponível.</p>
                             )}
                        </div>
                    )}
                </div>

                <div className="modal-actions">
                    <button type="button" onClick={onClose} disabled={isLoading || isEnrichingWeb || isGeneratingIA || isSuggestingGemini} className="btn-secondary">Cancelar</button>
                    <button type="submit" disabled={isLoading || isEnrichingWeb || isGeneratingIA || isSuggestingGemini} className="btn-success">{isLoading ? 'Salvando...' : 'Salvar Produto'}</button>
                </div>
            </form>
            )}
        </Modal>
    );
};

export default ProductEditModal;

