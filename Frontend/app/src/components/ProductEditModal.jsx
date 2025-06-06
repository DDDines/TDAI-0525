// Frontend/app/src/components/ProductEditModal.jsx
import React, { useState, useEffect, useCallback } from 'react';
import Modal from './common/Modal';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications';
import productService from '../services/productService';
import fornecedorService from '../services/fornecedorService';
import { uploadProductImage } from '../services/uploadService';
import AttributeField from './produtos/shared/AttributeField';
import { useProductTypes } from '../../contexts/ProductTypeContext';

import './ProductEditModal.css';

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
    imagens: [],
    videos: [],
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
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [error, setError] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const { productTypes } = useProductTypes();

    const [iaAttributeSuggestions, setIaAttributeSuggestions] = useState({});
    const [selectedIaSuggestions, setSelectedIaSuggestions] = useState({});

    const selectedProductType = productTypes.find(type => type.id === parseInt(formData.product_type_id));
    const attributeTemplates = selectedProductType ? selectedProductType.attribute_templates || [] : [];


    useEffect(() => {
        const fetchDependencies = async () => {
            if (isOpen) {
                try {
                    const fetchedFornecedores = await fornecedorService.getFornecedores({ skip: 0, limit: 1000 });
                    setFornecedores(fetchedFornecedores.items || []);
                } catch (err) {
                    console.error("Erro ao carregar fornecedores:", err);
                    showErrorToast("Erro ao carregar lista de fornecedores para o modal.");
                }
            }
        };
        fetchDependencies();
    }, [isOpen]);

    const extractIaSuggestions = useCallback((dadosBrutos) => {
        const extracted = {};
        if (dadosBrutos?.especificacoes_tecnicas_dict && typeof dadosBrutos.especificacoes_tecnicas_dict === 'object') {
            Object.assign(extracted, dadosBrutos.especificacoes_tecnicas_dict);
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
                setFormData({
                    ...initialFormData,
                    ...product,
                    imagens: product.imagens_produto || [],
                    videos: product.videos_produto || [],
                    fornecedor_id: product.fornecedor_id || '',
                    product_type_id: product.product_type_id || '',
                    dynamic_attributes: product.dynamic_attributes || {},
                    dados_brutos: product.dados_brutos || {},
                    titulos_sugeridos: product.titulos_sugeridos || [],
                });
                extractIaSuggestions(product.dados_brutos);
            } else {
                setFormData(initialFormData);
                setIaAttributeSuggestions({});
                setSelectedIaSuggestions({});
            }
            setActiveTab('info');
            setError(null);
            setIsLoading(false);
            setIsGeneratingIA(false);
            setIsEnrichingWeb(false);
            setIsSuggestingGemini(false);
        }
    }, [product, isOpen, extractIaSuggestions]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
    };

    const handleDynamicAttributeChange = (key, value) => {
        setFormData(prev => ({
            ...prev,
            dynamic_attributes: { ...prev.dynamic_attributes, [key]: value },
        }));
    };

    const addDynamicAttribute = () => {
        const newKey = prompt("Digite a chave do novo atributo (ex: 'cor', 'voltagem'):");
        if (newKey && !formData.dynamic_attributes.hasOwnProperty(newKey)) {
            setFormData(prev => ({ ...prev, dynamic_attributes: { ...prev.dynamic_attributes, [newKey]: '' } }));
        } else if (newKey) {
            showWarningToast("Atributo com esta chave já existe.");
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
        if (appliedCount > 0) {
            setFormData(prev => ({ ...prev, dynamic_attributes: { ...prev.dynamic_attributes, ...attributesToApply } }));
            showSuccessToast(`${appliedCount} sugestão(ões) aplicada(s) aos atributos dinâmicos!`);
            setActiveTab('atributos');
        } else {
            showWarningToast("Nenhuma sugestão foi selecionada para aplicar.");
        }
    };

    const handleFileSelect = async (event) => {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        setIsUploading(true);
        setUploadProgress(0);
        const totalFiles = files.length;
        let uploadedCount = 0;

        for (const file of files) {
            try {
                const response = await uploadProductImage(file);
                const newImage = {
                    url: response.url,
                    alt_text: file.name.split('.')[0] || 'Imagem do produto',
                    is_main: formData.imagens.length === 0,
                    mimetype: response.mimetype,
                    size_bytes: response.size_bytes
                };
                setFormData(prev => ({ ...prev, imagens: [...prev.imagens, newImage] }));
            } catch (error) {
                showErrorToast(`Falha no upload da imagem "${file.name}".`);
            } finally {
                uploadedCount++;
                setUploadProgress(Math.round((uploadedCount / totalFiles) * 100));
            }
        }
        setIsUploading(false);
    };

    const handleImageAltChange = (index, newAlt) => {
        setFormData(prev => {
            const newImages = [...prev.imagens];
            newImages[index].alt_text = newAlt;
            return { ...prev, imagens: newImages };
        });
    };

    const handleSetMainImage = (index) => {
        setFormData(prev => ({
            ...prev,
            imagens: prev.imagens.map((img, i) => ({ ...img, is_main: i === index })),
        }));
    };

    const handleRemoveImage = (index) => {
        setFormData(prev => ({
            ...prev,
            imagens: prev.imagens.filter((_, i) => i !== index),
        }));
    };

    const validateForm = () => {
        const errors = [];
        if (!formData.nome_base.trim()) {
            errors.push({ tab: 'info', fieldId: 'nome_base', message: 'O Nome Base é obrigatório.' });
        }
        if (!formData.product_type_id) {
            errors.push({ tab: 'info', fieldId: 'product_type_id', message: 'O Tipo de Produto é obrigatório.' });
        }
        if (attributeTemplates) {
            for (const template of attributeTemplates) {
                if (template.is_required) {
                    const value = formData.dynamic_attributes[template.attribute_key];
                    if (value === undefined || value === null || String(value).trim() === '') {
                        errors.push({ tab: 'atributos', fieldId: `attr-${template.attribute_key}`, message: `O atributo "${template.label}" é obrigatório.` });
                    }
                }
            }
        }
        formData.imagens.forEach((img, index) => {
            if (!img.url) errors.push({ tab: 'media', fieldId: `img-url-${index}`, message: `A URL da imagem ${index + 1} é obrigatória.` });
            if (!img.alt_text || img.alt_text.trim().length < 5) errors.push({ tab: 'media', fieldId: `img-alt-${index}`, message: `O texto alternativo para a imagem ${index + 1} deve ter no mínimo 5 caracteres.` });
        });
        return errors;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const validationErrors = validateForm();
        if (validationErrors.length > 0) {
            const firstError = validationErrors[0];
            showErrorToast(`Verifique o campo: ${firstError.message}`);
            setActiveTab(firstError.tab);
            setTimeout(() => {
                const errorField = document.getElementById(firstError.fieldId);
                if (errorField) {
                    errorField.focus();
                    errorField.classList.add('field-error-highlight');
                    setTimeout(() => errorField.classList.remove('field-error-highlight'), 2000);
                }
            }, 100);
            return;
        }

        setIsLoading(true);
        setError(null);

        const payload = { ...formData, imagens_produto: formData.imagens, videos_produto: formData.videos };
        delete payload.imagens;
        delete payload.videos;

        try {
            let responseProduct;
            if (isNewProduct) {
                responseProduct = await productService.createProduto(payload);
                showSuccessToast("Produto criado com sucesso!");
            } else {
                responseProduct = await productService.updateProduto(product.id, payload);
                showSuccessToast("Produto atualizado com sucesso!");
            }
            if (onProductUpdated) onProductUpdated(responseProduct);
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

    const handleCopyToDescriptionOriginal = (generatedText) => {
        setFormData(prev => ({ ...prev, descricao_original: generatedText }));
        showInfoToast("Descrição gerada copiada para o campo original.");
    };

    const handleCopyToDescriptionCurtaOriginal = (generatedText) => {
        setFormData(prev => ({ ...prev, descricao_curta_orig: generatedText }));
        showInfoToast("Descrição curta gerada copiada para o campo original.");
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={isNewProduct ? "Criar Novo Produto" : `Editar: ${formData.nome_base || 'ID ' + product?.id}`}>
            <form onSubmit={handleSubmit} className="product-modal-form">
                <div className="tab-navigation">
                    <button type="button" className={activeTab === 'info' ? 'active' : ''} onClick={() => setActiveTab('info')}>Info Principais</button>
                    <button type="button" className={activeTab === 'media' ? 'active' : ''} onClick={() => setActiveTab('media')}>Mídia</button>
                    <button type="button" className={activeTab === 'atributos' ? 'active' : ''} onClick={() => setActiveTab('atributos')} disabled={!formData.product_type_id}>Atributos</button>
                    <button type="button" className={activeTab === 'conteudo-ia' ? 'active' : ''} onClick={() => setActiveTab('conteudo-ia')}>Conteúdo IA</button>
                    <button type="button" className={activeTab === 'sugestoes-ia' ? 'active' : ''} onClick={() => setActiveTab('sugestoes-ia')} disabled={isNewProduct}>Sugestões IA</button>
                    <button type="button" className={activeTab === 'log' ? 'active' : ''} onClick={() => setActiveTab('log')}>Log</button>
                </div>

                <div className="tab-content">
                    {activeTab === 'info' && (
                        <div className="form-section form-grid">
                            <label>Tipo de Produto*:
                                <select id="product_type_id" name="product_type_id" value={formData.product_type_id} onChange={handleChange} required>
                                    <option value="">Selecione...</option>
                                    {productTypes.map(type => (<option key={type.id} value={type.id}>{type.friendly_name}</option>))}
                                </select>
                            </label>
                            <label>Nome Base*: <input type="text" id="nome_base" name="nome_base" value={formData.nome_base} onChange={handleChange} required /></label>
                            <label>Marca: <input type="text" name="marca" value={formData.marca} onChange={handleChange} /></label>
                            <label>SKU: <input type="text" name="sku" value={formData.sku} onChange={handleChange} /></label>
                            <label>Fornecedor:
                                <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange}>
                                    <option value="">Selecione...</option>
                                    {fornecedores.map(f => (<option key={f.id} value={f.id}>{f.nome}</option>))}
                                </select>
                            </label>
                        </div>
                    )}

                    {activeTab === 'media' && (
                        <div className="form-section">
                            <h4>Imagens do Produto</h4>
                            <div className="media-upload-area" onClick={() => document.getElementById('productImageInput').click()}>
                                <p>📷 Clique ou Arraste Imagens Aqui</p>
                                <small>(JPG, PNG, WEBP)</small>
                            </div>
                            <input type="file" id="productImageInput" multiple accept="image/*" style={{ display: 'none' }} onChange={handleFileSelect} disabled={isUploading} />
                            {isUploading && (
                                <div id="productImageUploadProgress">
                                    <div className="progress-bar" style={{ width: `${uploadProgress}%` }}>{uploadProgress > 0 ? `${uploadProgress}%` : ''}</div>
                                </div>
                            )}
                            <div className="media-grid">
                                {formData.imagens.map((img, index) => (
                                    <div key={index} className={`media-item ${img.is_main ? 'is-main' : ''}`}>
                                        <img src={img.url} alt={img.alt_text} className="preview" />
                                        <div className="fields">
                                            <input id={`img-alt-${index}`} type="text" value={img.alt_text} onChange={(e) => handleImageAltChange(index, e.target.value)} placeholder="Texto alternativo (alt)*" />
                                        </div>
                                        <div className="actions">
                                            <label className="main-image-radio">
                                                <input type="radio" name="main-image" checked={!!img.is_main} onChange={() => handleSetMainImage(index)} title="Marcar como imagem principal" /> Principal
                                            </label>
                                            <button type="button" className="btn-remove-media" onClick={() => handleRemoveImage(index)} title="Remover Imagem">🗑️</button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {activeTab === 'atributos' && (
                        <div className="form-section">
                            <h3>Atributos Dinâmicos e de Template</h3>
                            {!formData.product_type_id && <p>Selecione um Tipo de Produto na aba "Info".</p>}
                            {attributeTemplates.length > 0 && (
                                <div>
                                    <h4>Atributos de "{selectedProductType?.friendly_name}"</h4>
                                    <div className="form-grid">
                                        {attributeTemplates.map(attr => (
                                            <AttributeField
                                                key={attr.attribute_key}
                                                attributeTemplate={attr}
                                                value={formData.dynamic_attributes[attr.attribute_key]}
                                                onChange={handleDynamicAttributeChange}
                                            />
                                        ))}
                                    </div>
                                </div>
                            )}
                            <h4>Outros Atributos (Manuais)</h4>
                            {Object.entries(formData.dynamic_attributes)
                                .filter(([key]) => !attributeTemplates.some(template => template.attribute_key === key))
                                .map(([key, value]) => (
                                    <div key={key} style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '5px' }}>
                                        <input type="text" value={key} disabled style={{ flex: '1', backgroundColor: '#f0f0f0' }} />
                                        <input type="text" value={value || ''} onChange={(e) => handleDynamicAttributeChange(key, e.target.value)} style={{ flex: '2' }} />
                                        <button type="button" onClick={() => {
                                            const { [key]: _, ...rest } = formData.dynamic_attributes;
                                            setFormData(prev => ({ ...prev, dynamic_attributes: rest }));
                                            showInfoToast(`Atributo manual "${key}" removido.`);
                                        }} title="Remover este atributo manual" style={{ padding: '5px', color: 'red', border: 'none', background: 'transparent', cursor: 'pointer' }}>🗑️</button>
                                    </div>
                                ))}
                            <button type="button" onClick={addDynamicAttribute} style={{ marginTop: '10px' }}>Adicionar Atributo Manual</button>
                        </div>
                    )}
                    
                    {activeTab === 'conteudo-ia' && (
                        <div className="form-section">
                            <h3>Conteúdo Gerado por IA</h3>
                            <div className='ia-generation-box'>
                               <label>Título Gerado (Principal): <input name="nome_chat_api" value={formData.nome_chat_api} onChange={handleChange} /></label>
                               <button type="button" onClick={handleGenerateTitles} disabled={isGeneratingIA || isNewProduct}> {isGeneratingIA ? 'Gerando...' : 'Gerar Títulos com IA'} </button>
                            </div>
                             {formData.titulos_sugeridos && formData.titulos_sugeridos.length > 0 && (
                                <div style={{marginTop: '1rem'}}>
                                    <h4>Outros Títulos Sugeridos:</h4>
                                    <ul className="suggestion-list">{formData.titulos_sugeridos.map((title, index) => (<li key={index}>{title}</li>))}</ul>
                                </div>
                            )}
                            <hr />
                            <div className='ia-generation-box'>
                                <label>Descrição Gerada: <textarea name="descricao_principal_gerada" value={formData.descricao_principal_gerada} onChange={handleChange} rows="8"></textarea></label>
                                <button type="button" onClick={handleGenerateDescription} disabled={isGeneratingIA || isNewProduct}>{isGeneratingIA ? 'Gerando...' : 'Gerar Descrição com IA'}</button>
                            </div>
                        </div>
                    )}

                    {activeTab === 'sugestoes-ia' && (
                        <div className="form-section">
                            <h3>Sugestões de Atributos por IA</h3>
                            <div className="suggestion-action-box">
                                <p>Busque sugestões de atributos e valores usando Gemini, com base nos dados atuais do produto.</p>
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
                                                    <input type="checkbox" checked={!!selectedIaSuggestions[key]} onChange={() => handleIaSuggestionToggle(key)} />
                                                    <div className="suggestion-text"><strong>{key}:</strong> {String(value)}</div>
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                    <button type="button" onClick={applySelectedIaSuggestions} className="btn-apply-suggestions">Aplicar Selecionados</button>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'log' && (
                        <div className="form-section">
                            <h3>Log de Processamento</h3>
                            {formData.log_enriquecimento_web && formData.log_enriquecimento_web.historico_mensagens && formData.log_enriquecimento_web.historico_mensagens.length > 0 ? (
                                <div className="log-container">
                                    {formData.log_enriquecimento_web.historico_mensagens.map((msg, index) => (<p key={index}>{msg}</p>))}
                                </div>
                            ) : (
                                <p>Nenhum log disponível.</p>
                            )}
                        </div>
                    )}
                </div>

                <div className="modal-actions">
                    <button type="button" onClick={onClose} disabled={isLoading} className="btn-secondary">Cancelar</button>
                    <button type="submit" disabled={isLoading} className="btn-success">
                        {isLoading ? 'Salvando...' : 'Salvar Produto'}
                    </button>
                </div>
            </form>
        </Modal>
    );
};

export default ProductEditModal;