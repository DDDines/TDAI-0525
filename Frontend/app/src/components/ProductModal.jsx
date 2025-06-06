// Frontend/app/src/components/ProductEditModal.jsx (Renomear para ProductModal.jsx)
// REMOVIDO: Conteúdo antigo dos modais separados.
// NOVO: Código unificado para criar e editar produtos.
import React, { useState, useEffect, useCallback } from 'react';
import Modal from './common/Modal';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications';
import productService from '../services/productService';
import fornecedorService from '../services/fornecedorService';
import AttributeField from './produtos/shared/AttributeField';
import { useProductTypes } from '../contexts/ProductTypeContext';
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

// ALTERADO: O nome do componente agora é genérico e recebe um `product` para editar ou nada para criar.
const ProductModal = ({ isOpen, onClose, product, onProductUpdated }) => {
    // ALTERADO: Determina se está em modo de edição baseado na existência do produto e seu ID.
    const isEditing = product && product.id;

    const [formData, setFormData] = useState(initialFormData);
    const [activeTab, setActiveTab] = useState('info');
    const [isLoading, setIsLoading] = useState(false);
    const [isGeneratingIA, setIsGeneratingIA] = useState(false);
    const [isEnrichingWeb, setIsEnrichingWeb] = useState(false);
    const [isSuggestingGemini, setIsSuggestingGemini] = useState(false);
    const [error, setError] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const { productTypes } = useProductTypes();

    const [iaAttributeSuggestions, setIaAttributeSuggestions] = useState({});
    const [selectedIaSuggestions, setSelectedIaSuggestions] = useState({});

    // Carrega fornecedores quando o modal abre
    useEffect(() => {
        const fetchDependencies = async () => {
            if (isOpen) {
                try {
                    const fetchedFornecedores = await fornecedorService.getFornecedores({ skip: 0, limit: 100 });
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

    // Popula o formulário quando o `product` (para edição) muda ou o modal abre.
    useEffect(() => {
        if (isOpen) {
            if (isEditing) {
                const dynamicAttrs = (product.dynamic_attributes && typeof product.dynamic_attributes === 'object') ? product.dynamic_attributes : {};
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
            } else { // Limpa para um novo produto
                setFormData(initialFormData);
                setIaAttributeSuggestions({});
                setSelectedIaSuggestions({});
            }
            // Reseta estados de ação
            setIsEnrichingWeb(false);
            setIsGeneratingIA(false);
            setIsSuggestingGemini(false);
            setActiveTab('info');
            setError(null);
        }
    }, [product, isEditing, isOpen, extractIaSuggestions]);

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

    const addDynamicAttribute = () => {
        const newKey = prompt("Digite a chave do novo atributo (ex: 'cor', 'voltagem'):");
        if (newKey && !formData.dynamic_attributes.hasOwnProperty(newKey)) {
            setFormData(prev => ({
                ...prev,
                dynamic_attributes: {
                    ...prev.dynamic_attributes,
                    [newKey]: '',
                },
            }));
        } else if (newKey) {
            showWarningToast("Atributo com esta chave já existe.");
        }
    };
    
    // Demais handlers (handleIaSuggestionToggle, applySelectedIaSuggestions, handleEnrichWeb, etc.) permanecem os mesmos...
    // ...

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

    // ... todos os outros handlers (handleGenerateTitles, etc) vêm para cá ...
    const handleGenerateTitles = async () => {
        if (!product?.id) { showWarningToast("Salve o produto primeiro para gerar títulos."); return; }
        setIsGeneratingIA(true);
        try {
            await productService.gerarTitulosProduto(product.id);
            showInfoToast("Geração de títulos iniciada. Verifique em breve.");
            setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({ ...prev, nome_chat_api: updatedProduct.nome_chat_api, titulos_sugeridos: updatedProduct.titulos_sugeridos }));
                if (onProductUpdated) onProductUpdated(updatedProduct);
            }, 7000); 
        } catch (err) { showErrorToast(err.response?.data?.detail || "Erro ao gerar títulos."); } 
        finally { setIsGeneratingIA(false); }
    };

    const handleGenerateDescription = async () => {
        if (!product?.id) { showWarningToast("Salve o produto primeiro para gerar descrição."); return; }
        setIsGeneratingIA(true);
        try {
            await productService.gerarDescricaoProduto(product.id);
            showInfoToast("Geração de descrição iniciada. Verifique em breve.");
             setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({...prev, descricao_principal_gerada: updatedProduct.descricao_principal_gerada }));
                if (onProductUpdated) onProductUpdated(updatedProduct);
            }, 7000); 
        } catch (err) { showErrorToast(err.response?.data?.detail || "Erro ao gerar descrição."); } 
        finally { setIsGeneratingIA(false); }
    };
    
    // Lógica para obter os templates de atributos baseados no tipo de produto selecionado
    const selectedProductType = productTypes.find(type => type.id === parseInt(formData.product_type_id));
    const attributeTemplates = selectedProductType ? selectedProductType.attribute_templates : [];

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={isEditing ? `Editar Produto: ${product.nome_base}` : "Criar Novo Produto"}>
            <form onSubmit={handleSubmit}>
                <div className="tab-navigation">
                    <button type="button" className={activeTab === 'info' ? 'active' : ''} onClick={() => setActiveTab('info')}>Info Principais</button>
                    <button type="button" className={activeTab === 'atributos' ? 'active' : ''} onClick={() => setActiveTab('atributos')} disabled={!formData.product_type_id}>Atributos</button>
                    <button type="button" className={activeTab === 'midia' ? 'active' : ''} onClick={() => setActiveTab('midia')}>Mídia</button>
                    <button type="button" className={activeTab === 'conteudo-ia' ? 'active' : ''} onClick={() => setActiveTab('conteudo-ia')}>Conteúdo IA</button>
                    <button type="button" className={activeTab === 'sugestoes-ia' ? 'active' : ''} onClick={() => setActiveTab('sugestoes-ia')}>Sugestões IA</button>
                    <button type="button" className={activeTab === 'log' ? 'active' : ''} onClick={() => setActiveTab('log')}>Log</button>
                </div>

                <div className="tab-content">
                    {/* Renderização do conteúdo de cada aba, baseado em `activeTab` */}
                    {activeTab === 'info' && (
                        <div className="form-section">
                             <label>
                                Tipo de Produto:
                                <select name="product_type_id" value={formData.product_type_id} onChange={handleChange} required>
                                    <option value="">Selecione um tipo</option>
                                    {(productTypes || []).map(type => (
                                        <option key={type.id} value={type.id}>{type.friendly_name}</option>
                                    ))}
                                </select>
                            </label>
                            <label> Nome Base: <input type="text" name="nome_base" value={formData.nome_base} onChange={handleChange} required /> </label>
                            <label> Marca: <input type="text" name="marca" value={formData.marca} onChange={handleChange} /> </label>
                            <label> SKU: <input type="text" name="sku" value={formData.sku} onChange={handleChange} /> </label>
                             <label> Fornecedor:
                                <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange}>
                                    <option value="">Selecione um fornecedor</option>
                                    {fornecedores.map(f => (<option key={f.id} value={f.id}>{f.nome}</option>))}
                                </select>
                            </label>
                        </div>
                    )}
                     {activeTab === 'atributos' && (
                        <div className="form-section">
                             <h3>Atributos Dinâmicos e de Template</h3>
                             {!formData.product_type_id && <p>Selecione um Tipo de Produto na aba "Info Principais".</p>}
                             {attributeTemplates && attributeTemplates.length > 0 && (
                                 <div>
                                     <h4>Atributos do Tipo ({selectedProductType?.friendly_name})</h4>
                                     {attributeTemplates.map(attr => (
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
                    {/* ... outras abas aqui ... */}
                </div>

                <div className="modal-actions">
                    <button type="button" onClick={onClose} disabled={isLoading} className="btn-secondary">Cancelar</button>
                    <button type="submit" disabled={isLoading} className="btn-success">{isLoading ? 'Salvando...' : 'Salvar Produto'}</button>
                </div>
            </form>
        </Modal>
    );
};

export default ProductModal;