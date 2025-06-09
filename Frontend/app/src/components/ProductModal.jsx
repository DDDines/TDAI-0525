// Frontend/app/src/components/produtos/ProductModal.jsx
// ARQUIVO UNIFICADO para Criar e Editar Produtos

import React, { useState, useEffect, useCallback } from 'react';
import Modal from '../common/Modal';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../../utils/notifications';
import productService from '../../services/productService';
import fornecedorService from '../../services/fornecedorService';
// Ajuste do caminho para o componente de atributo
import AttributeField from '../components/produtos/shared/AttributeField';
import { useProductTypes } from '../../contexts/ProductTypeContext';
import '../ProductEditModal.css';

// Estado inicial do formulário, com todos os campos do seu modelo.
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
    status_enriquecimento_web: 'NAO_INICIADO',
    status_titulo_ia: 'NAO_INICIADO',
    status_descricao_ia: 'NAO_INICIADO',
};

const ProductModal = ({ isOpen, onClose, product, onProductUpdated }) => {
    const isEditing = product && product.id;

    const [formData, setFormData] = useState(initialFormData);
    const [activeTab, setActiveTab] = useState('info');
    const [isLoading, setIsLoading] = useState(false);
    const [isGeneratingIA, setIsGeneratingIA] = useState(false);
    const [isSuggestingGemini, setIsSuggestingGemini] = useState(false);
    const [error, setError] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const { productTypes } = useProductTypes();

    // NOVO: Estado para armazenar as sugestões da Gemini.
    const [geminiSuggestions, setGeminiSuggestions] = useState([]);
    const [selectedGeminiSuggestions, setSelectedGeminiSuggestions] = useState({});

    // Carrega fornecedores quando o modal abre.
    useEffect(() => {
        const fetchDependencies = async () => {
            if (isOpen) {
                try {
                    const fetchedFornecedores = await fornecedorService.getFornecedores({ skip: 0, limit: 1000 });
                    setFornecedores(fetchedFornecedores.items || []);
                } catch (err) {
                    console.error("Erro ao carregar fornecedores:", err);
                    showErrorToast("Erro ao carregar lista de fornecedores.");
                }
            }
        };
        fetchDependencies();
    }, [isOpen]);

    // Popula o formulário com dados do produto para edição, ou reseta para criação.
    useEffect(() => {
        if (isOpen) {
            if (isEditing) {
                setFormData({
                    ...initialFormData, // Garante que todos os campos estão presentes
                    ...product,         // Sobrescreve com os dados do produto
                    // Garante que os campos relacionais e de objeto/array sejam válidos
                    fornecedor_id: product.fornecedor_id || '',
                    product_type_id: product.product_type_id || '',
                    dynamic_attributes: product.dynamic_attributes && typeof product.dynamic_attributes === 'object' ? product.dynamic_attributes : {},
                    dados_brutos: product.dados_brutos && typeof product.dados_brutos === 'object' ? product.dados_brutos : {},
                    imagens_secundarias_urls: product.imagens_secundarias_urls || [],
                    titulos_sugeridos: product.titulos_sugeridos || [],
                });
            } else {
                setFormData(initialFormData);
            }
            // Reseta estados de ação
            setActiveTab('info');
            setError(null);
            setIsGeneratingIA(false);
            setIsSuggestingGemini(false);
            setGeminiSuggestions([]);
            setSelectedGeminiSuggestions({});
        }
    }, [product, isEditing, isOpen]);

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
    
    // NOVO: Handler para buscar sugestões de atributos com a Gemini.
    const handleFetchGeminiSuggestions = async () => {
        if (!isEditing) {
            showWarningToast("Por favor, salve o produto antes de buscar sugestões.");
            return;
        }
        setIsSuggestingGemini(true);
        showInfoToast("Buscando sugestões com a API Gemini...");
        try {
            const response = await productService.sugerirAtributosGemini(product.id);
            if (response && response.sugestoes_atributos && response.sugestoes_atributos.length > 0) {
                setGeminiSuggestions(response.sugestoes_atributos);
                // Pré-marca todas as sugestões para facilitar a aplicação
                const initialSelections = response.sugestoes_atributos.reduce((acc, sug) => {
                    acc[sug.chave_atributo] = true;
                    return acc;
                }, {});
                setSelectedGeminiSuggestions(initialSelections);
                showSuccessToast(`${response.sugestoes_atributos.length} sugestões encontradas!`);
                setActiveTab('sugestoes-ia');
            } else {
                showWarningToast("Nenhuma sugestão de atributo foi retornada pela IA.");
                setGeminiSuggestions([]);
            }
        } catch (err) {
            showErrorToast(err.response?.data?.detail || "Falha ao buscar sugestões da IA.");
        } finally {
            setIsSuggestingGemini(false);
        }
    };
    
    // NOVO: Handler para selecionar/deselecionar uma sugestão.
    const handleSuggestionToggle = (key) => {
        setSelectedGeminiSuggestions(prev => ({ ...prev, [key]: !prev[key] }));
    };

    // NOVO: Handler para aplicar as sugestões selecionadas.
    const applySelectedSuggestions = () => {
        const newDynamicAttributes = { ...formData.dynamic_attributes };
        let appliedCount = 0;
        geminiSuggestions.forEach(suggestion => {
            if (selectedGeminiSuggestions[suggestion.chave_atributo]) {
                newDynamicAttributes[suggestion.chave_atributo] = suggestion.valor_sugerido;
                appliedCount++;
            }
        });

        if (appliedCount > 0) {
            setFormData(prev => ({ ...prev, dynamic_attributes: newDynamicAttributes }));
            showSuccessToast(`${appliedCount} sugestão(ões) aplicada(s) com sucesso!`);
            setActiveTab('atributos'); // Muda para a aba de atributos para ver o resultado
        } else {
            showWarningToast("Nenhuma sugestão foi selecionada para aplicar.");
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
            if (isEditing) {
                responseProduct = await productService.updateProduto(product.id, productDataToSave);
                showSuccessToast("Produto atualizado com sucesso!");
            } else {
                responseProduct = await productService.createProduto(productDataToSave);
                showSuccessToast("Produto criado com sucesso!");
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
    
    // ATUALIZADO: Chama o endpoint Gemini para títulos.
    const handleGenerateTitles = async () => {
        if (!isEditing) { showWarningToast("Salve o produto primeiro."); return; }
        setIsGeneratingIA(true);
        try {
            // Assumindo que o productService foi atualizado para ter essa função
            await productService.gerarTitulosGemini(product.id);
            showInfoToast("Geração de títulos com Gemini iniciada. O resultado aparecerá em breve.");
            // Opcional: Implementar um polling ou WebSocket para atualizar automaticamente.
            // Por simplicidade, o usuário pode reabrir para ver as atualizações.
        } catch (err) { 
            showErrorToast(err.response?.data?.detail || "Erro ao agendar geração de títulos.");
        } finally {
            setIsGeneratingIA(false);
        }
    };

    // ATUALIZADO: Chama o endpoint Gemini para descrição.
    const handleGenerateDescription = async () => {
        if (!isEditing) { showWarningToast("Salve o produto primeiro."); return; }
        setIsGeneratingIA(true);
        try {
             // Assumindo que o productService foi atualizado
            await productService.gerarDescricaoGemini(product.id);
            showInfoToast("Geração de descrição com Gemini iniciada. O resultado aparecerá em breve.");
        } catch (err) { 
            showErrorToast(err.response?.data?.detail || "Erro ao agendar geração de descrição.");
        } finally {
            setIsGeneratingIA(false);
        }
    };
    
    const selectedProductType = productTypes.find(type => type.id === parseInt(formData.product_type_id));
    const attributeTemplates = selectedProductType ? selectedProductType.attribute_templates : [];

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={isEditing ? `Editar Produto: ${product.nome_base}` : "Criar Novo Produto"}>
            <form onSubmit={handleSubmit} className="product-modal-form">
                <div className="tab-navigation">
                    <button type="button" className={activeTab === 'info' ? 'active' : ''} onClick={() => setActiveTab('info')}>Info</button>
                    <button type="button" className={activeTab === 'atributos' ? 'active' : ''} onClick={() => setActiveTab('atributos')}>Atributos</button>
                    <button type="button" className={activeTab === 'conteudo' ? 'active' : ''} onClick={() => setActiveTab('conteudo')}>Conteúdo</button>
                    <button type="button" className={activeTab === 'sugestoes-ia' ? 'active' : ''} onClick={() => setActiveTab('sugestoes-ia')} disabled={!isEditing}>Sugestões IA</button>
                </div>

                <div className="tab-content">
                    {activeTab === 'info' && (
                        <div className="form-grid">
                            <label>Nome Base*<input name="nome_base" value={formData.nome_base} onChange={handleChange} required /></label>
                            <label>Marca<input name="marca" value={formData.marca} onChange={handleChange} /></label>
                            <label>SKU<input name="sku" value={formData.sku} onChange={handleChange} /></label>
                            <label>EAN<input name="ean" value={formData.ean} onChange={handleChange} /></label>
                            <label>Tipo de Produto*
                                <select name="product_type_id" value={formData.product_type_id} onChange={handleChange} required>
                                    <option value="">Selecione...</option>
                                    {(productTypes || []).map(type => (<option key={type.id} value={type.id}>{type.friendly_name}</option>))}
                                </select>
                            </label>
                            <label>Fornecedor
                                <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange}>
                                    <option value="">Selecione...</option>
                                    {fornecedores.map(f => (<option key={f.id} value={f.id}>{f.nome}</option>))}
                                </select>
                            </label>
                        </div>
                    )}
                    {activeTab === 'atributos' && (
                        <div className="form-section">
                           {!formData.product_type_id && <p className="info-text">Selecione um Tipo de Produto na aba "Info" para ver os atributos.</p>}
                           {attributeTemplates.length > 0 && <h4>Atributos de "{selectedProductType?.friendly_name}"</h4>}
                           <div className="form-grid">
                            {attributeTemplates.map(attr => (
                                <AttributeField key={attr.id} attributeTemplate={attr} value={formData.dynamic_attributes[attr.attribute_key]} onChange={handleDynamicAttributeChange} />
                            ))}
                           </div>
                        </div>
                    )}
                    {activeTab === 'conteudo' && (
                        <div className="form-section">
                            <h4>Conteúdo Original</h4>
                            <label>Descrição Original <textarea name="descricao_original" value={formData.descricao_original} onChange={handleChange} rows="5"></textarea></label>
                            
                            <hr />

                            <h4>Conteúdo Gerado por IA</h4>
                            <div className='ia-generation-box'>
                               <label>Título Gerado <input name="nome_chat_api" value={formData.nome_chat_api} onChange={handleChange} /></label>
                               <button type="button" onClick={handleGenerateTitles} disabled={isGeneratingIA || !isEditing}>Gerar Títulos com IA</button>
                            </div>
                            <div className='ia-generation-box'>
                                <label>Descrição Gerada <textarea name="descricao_principal_gerada" value={formData.descricao_principal_gerada} onChange={handleChange} rows="5"></textarea></label>
                                <button type="button" onClick={handleGenerateDescription} disabled={isGeneratingIA || !isEditing}>Gerar Descrição com IA</button>
                            </div>
                        </div>
                    )}
                     {activeTab === 'sugestoes-ia' && (
                        <div className="form-section">
                            <div className="suggestion-action-box">
                                <p>Clique no botão para usar a Gemini para analisar os dados do produto e sugerir valores para os atributos.</p>
                                <button type="button" onClick={handleFetchGeminiSuggestions} disabled={isSuggestingGemini}>
                                    {isSuggestingGemini ? 'Analisando...' : 'Buscar Sugestões com Gemini'}
                                </button>
                            </div>
                            {geminiSuggestions.length > 0 && (
                                <div className="ia-suggestions-container">
                                    <h4>Sugestões Encontradas:</h4>
                                    <div className="ia-suggestions-grid">
                                        {geminiSuggestions.map((sug) => (
                                            <div key={sug.chave_atributo} className={`ia-suggestion-item ${selectedGeminiSuggestions[sug.chave_atributo] ? 'selected' : ''}`}>
                                                <label>
                                                    <input
                                                        type="checkbox"
                                                        checked={!!selectedGeminiSuggestions[sug.chave_atributo]}
                                                        onChange={() => handleSuggestionToggle(sug.chave_atributo)}
                                                    />
                                                    <div className="suggestion-text">
                                                        <strong>{sug.chave_atributo}:</strong>
                                                        <span>{sug.valor_sugerido}</span>
                                                    </div>
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                    <button type="button" onClick={applySelectedSuggestions} className="btn-apply-suggestions">Aplicar Selecionados</button>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="modal-actions">
                    <button type="button" onClick={onClose} disabled={isLoading} className="btn-secondary">Cancelar</button>
                    <button type="submit" disabled={isLoading || isGeneratingIA || isSuggestingGemini} className="btn-primary">
                        {isLoading ? 'Salvando...' : 'Salvar Produto'}
                    </button>
                </div>
            </form>
        </Modal>
    );
};

export default ProductModal;

