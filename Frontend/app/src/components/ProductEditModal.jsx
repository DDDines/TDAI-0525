// Frontend/app/src/components/ProductEditModal.jsx
import React, { useState, useEffect, useCallback } from 'react';
import Modal from './common/Modal'; // Supondo que você tem um componente Modal
// ALTERAÇÃO: Importar as funções de toast específicas
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications'; 
import * as productService from '../services/productService'; 
import * as fornecedorService from '../services/fornecedorService'; 
import * as productTypeService from '../services/productTypeService'; 
import AttributeField from './produtos/shared/AttributeField';
import { useProductTypes } from '../contexts/ProductTypeContext'; 

const ProductEditModal = ({ isOpen, onClose, product, onProductUpdated }) => {
    const isNewProduct = !product?.id;

    const [formData, setFormData] = useState({
        nome_base: product?.nome_base || '',
        nome_chat_api: product?.nome_chat_api || '',
        descricao_original: product?.descricao_original || '',
        descricao_curta_orig: product?.descricao_curta_orig || '',
        descricao_principal_gerada: product?.descricao_principal_gerada || '',
        descricao_curta_gerada: product?.descricao_curta_gerada || '',
        sku: product?.sku || '',
        ean: product?.ean || '',
        ncm: product?.ncm || '',
        marca: product?.marca || '',
        modelo: product?.modelo || '',
        categoria_original: product?.categoria_original || '',
        categoria_mapeada: product?.categoria_mapeada || '',
        preco_custo: product?.preco_custo || '',
        preco_venda: product?.preco_venda || '',
        preco_promocional: product?.preco_promocional || '',
        estoque_disponivel: product?.estoque_disponivel || '',
        peso_kg: product?.peso_kg || '',
        altura_cm: product?.altura_cm || '',
        largura_cm: product?.largura_cm || '',
        profundidade_cm: product?.profundidade_cm || '',
        imagem_principal_url: product?.imagem_principal_url || '',
        imagens_secundarias_urls: product?.imagens_secundarias_urls || [],
        fornecedor_id: product?.fornecedor_id || '',
        product_type_id: product?.product_type_id || '',
        dynamic_attributes: product?.dynamic_attributes || {},
        dados_brutos: product?.dados_brutos || {},
        titulos_sugeridos: product?.titulos_sugeridos || [],
        ativo_marketplace: product?.ativo_marketplace || false,
        data_publicacao_marketplace: product?.data_publicacao_marketplace || null,
        log_enriquecimento_web: product?.log_enriquecimento_web || { historico_mensagens: [] },
        status_enriquecimento_web: product?.status_enriquecimento_web || null,
        status_titulo_ia: product?.status_titulo_ia || null,
        status_descricao_ia: product?.status_descricao_ia || null,
    });

    const [activeTab, setActiveTab] = useState('info'); 
    const [isLoading, setIsLoading] = useState(false);
    const [isGeneratingIA, setIsGeneratingIA] = useState(false); 
    const [isEnrichingWeb, setIsEnrichingWeb] = useState(false); 
    const [error, setError] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const { productTypes } = useProductTypes(); 

    const [iaAttributeSuggestions, setIaAttributeSuggestions] = useState({});
    const [selectedIaSuggestions, setSelectedIaSuggestions] = useState({});

    useEffect(() => {
        const fetchDependencies = async () => {
            try {
                const fetchedFornecedores = await fornecedorService.getFornecedores(1, 100); 
                setFornecedores(fetchedFornecedores.items);
            } catch (err) {
                console.error("Erro ao carregar fornecedores:", err);
                showErrorToast("Erro ao carregar fornecedores."); // ALTERAÇÃO
            }
        };
        fetchDependencies();
    }, []);

    useEffect(() => {
        if (product) {
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
                dynamic_attributes: product.dynamic_attributes || {},
                dados_brutos: product.dados_brutos || {},
                titulos_sugeridos: product.titulos_sugeridos || [],
                ativo_marketplace: product.ativo_marketplace || false,
                data_publicacao_marketplace: product.data_publicacao_marketplace || null,
                log_enriquecimento_web: product.log_enriquecimento_web || { historico_mensagens: [] },
                status_enriquecimento_web: product.status_enriquecimento_web || null,
                status_titulo_ia: product.status_titulo_ia || null,
                status_descricao_ia: product.status_descricao_ia || null,
            });
            extractIaSuggestions(product.dados_brutos);
        } else {
            setFormData({
                nome_base: '', nome_chat_api: '', descricao_original: '', descricao_curta_orig: '',
                descricao_principal_gerada: '', descricao_curta_gerada: '', sku: '', ean: '', ncm: '',
                marca: '', modelo: '', categoria_original: '', categoria_mapeada: '',
                preco_custo: '', preco_venda: '', preco_promocional: '', estoque_disponivel: '',
                peso_kg: '', altura_cm: '', largura_cm: '', profundidade_cm: '',
                imagem_principal_url: '', imagens_secundarias_urls: [],
                fornecedor_id: '', product_type_id: '', dynamic_attributes: {}, dados_brutos: {},
                titulos_sugeridos: [], ativo_marketplace: false, data_publicacao_marketplace: null,
                log_enriquecimento_web: { historico_mensagens: [] },
                status_enriquecimento_web: null, status_titulo_ia: null, status_descricao_ia: null,
            });
            setIaAttributeSuggestions({});
            setSelectedIaSuggestions({});
            setActiveTab('info');
        }
    }, [product]);

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
                    [newKey]: '', 
                    ...prev.dynamic_attributes, 
                },
            }));
        } else if (newKey) {
            showWarningToast("Atributo com esta chave já existe."); // ALTERAÇÃO
        }
    };

    const handleIaSuggestionToggle = (key) => {
        setSelectedIaSuggestions(prev => ({
            ...prev,
            [key]: !prev[key],
        }));
    };

    const applySelectedIaSuggestions = () => {
        setFormData(prev => {
            const newDynamicAttributes = { ...prev.dynamic_attributes };
            for (const key in selectedIaSuggestions) {
                if (selectedIaSuggestions[key]) {
                    newDynamicAttributes[key] = iaAttributeSuggestions[key];
                }
            }
            return { ...prev, dynamic_attributes: newDynamicAttributes };
        });
        showSuccessToast("Sugestões aplicadas aos atributos dinâmicos."); // ALTERAÇÃO
    };

    const handleEnrichWeb = async () => {
        if (!product?.id) {
            showWarningToast("Salve o produto primeiro antes de enriquecer a web."); // ALTERAÇÃO
            return;
        }
        setIsEnrichingWeb(true);
        setError(null);
        try {
            await productService.iniciarEnriquecimentoWebProduto(product.id); // ALTERAÇÃO: Renomeado para iniciarEnriquecimentoWebProduto
            showInfoToast("Processo de enriquecimento web iniciado. Pode levar alguns minutos."); // ALTERAÇÃO

            setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({
                    ...prev,
                    dados_brutos: updatedProduct.dados_brutos,
                    log_enriquecimento_web: updatedProduct.log_enriquecimento_web,
                    status_enriquecimento_web: updatedProduct.status_enriquecimento_web, 
                }));
                extractIaSuggestions(updatedProduct.dados_brutos); 
                showSuccessToast("Enriquecimento web concluído (verifique o log e sugestões IA)."); // ALTERAÇÃO
                onProductUpdated(updatedProduct); 
            }, 10000); 
            
        } catch (err) {
            console.error("Erro ao iniciar enriquecimento web:", err);
            setError(err.response?.data?.detail || "Erro ao iniciar enriquecimento web.");
            showErrorToast(err.response?.data?.detail || "Erro ao iniciar enriquecimento web."); // ALTERAÇÃO
        } finally {
            setIsEnrichingWeb(false);
        }
    };


    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        if (!formData.nome_base) {
            setError("O nome base do produto é obrigatório.");
            showErrorToast("O nome base do produto é obrigatório."); // ALTERAÇÃO
            setIsLoading(false);
            return;
        }
        if (!formData.product_type_id && !isNewProduct) { 
             setError("O tipo de produto é obrigatório.");
             showErrorToast("O tipo de produto é obrigatório."); // ALTERAÇÃO
             setIsLoading(false);
             return;
        }

        try {
            const productData = { ...formData };
            for (const key in productData) {
                if (productData[key] === '' || productData[key] === null || (Array.isArray(productData[key]) && productData[key].length === 0)) {
                    if (typeof productData[key] === 'boolean') continue;
                    if (typeof productData[key] === 'number' && (productData[key] === 0 || productData[key] === null)) continue;
                    
                    delete productData[key];
                }
            }
            if (Object.keys(productData.dynamic_attributes || {}).length === 0) {
                productData.dynamic_attributes = {};
            }
            if (Object.keys(productData.dados_brutos || {}).length === 0) {
                productData.dados_brutos = {};
            }
            if (productData.data_publicacao_marketplace instanceof Date) {
                productData.data_publicacao_marketplace = productData.data_publicacao_marketplace.toISOString();
            } else if (!productData.data_publicacao_marketplace) {
                productData.data_publicacao_marketplace = null;
            }

            let responseProduct;
            if (isNewProduct) {
                responseProduct = await productService.createProduto(productData);
                showSuccessToast("Produto criado com sucesso!"); // ALTERAÇÃO
            } else {
                responseProduct = await productService.updateProduto(product.id, productData);
                showSuccessToast("Produto atualizado com sucesso!"); // ALTERAÇÃO
            }
            onProductUpdated(responseProduct); 
            onClose(); 
        } catch (err) {
            console.error("Erro ao salvar produto:", err);
            setError(err.response?.data?.detail || "Erro ao salvar produto.");
            showErrorToast(err.response?.data?.detail || "Erro ao salvar produto."); // ALTERAÇÃO
        } finally {
            setIsLoading(false);
        }
    };

    const selectedProductType = productTypes.find(type => type.id === formData.product_type_id);
    const attributeTemplates = selectedProductType ? selectedProductType.attribute_templates : [];

    const handleGenerateTitles = async () => {
        if (!product?.id) {
            showWarningToast("Salve o produto primeiro para gerar títulos."); // ALTERAÇÃO
            return;
        }
        setIsGeneratingIA(true);
        try {
            await productService.gerarTitulosProduto(product.id, { max_sugestoes: 3 }); // ALTERAÇÃO: Renomeado para gerarTitulosProduto
            showInfoToast("Geração de títulos iniciada. Verifique em breve."); // ALTERAÇÃO
            setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({ ...prev, titulos_sugeridos: updatedProduct.titulos_sugeridos }));
                onProductUpdated(updatedProduct);
            }, 5000); 
        } catch (err) {
            console.error("Erro ao gerar títulos:", err);
            showErrorToast(err.response?.data?.detail || "Erro ao gerar títulos.", "error"); // ALTERAÇÃO
        } finally {
            setIsGeneratingIA(false);
        }
    };

    const handleGenerateDescription = async () => {
        if (!product?.id) {
            showWarningToast("Salve o produto primeiro para gerar descrição."); // ALTERAÇÃO
            return;
        }
        setIsGeneratingIA(true);
        try {
            await productService.gerarDescricaoProduto(product.id, { max_palavras: 300 }); // ALTERAÇÃO: Renomeado para gerarDescricaoProduto
            showInfoToast("Geração de descrição iniciada. Verifique em breve."); // ALTERAÇÃO
            setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({
                    ...prev,
                    descricao_principal_gerada: updatedProduct.descricao_principal_gerada,
                    descricao_curta_gerada: updatedProduct.descricao_curta_gerada
                }));
                onProductUpdated(updatedProduct);
            }, 5000); 
        } catch (err) {
            console.error("Erro ao gerar descrição:", err);
            showErrorToast(err.response?.data?.detail || "Erro ao gerar descrição.", "error"); // ALTERAÇÃO
        } finally {
            setIsGeneratingIA(false);
        }
    };

    const handleCopyToDescriptionOriginal = (generatedText) => {
        setFormData(prev => ({ ...prev, descricao_original: generatedText }));
        showInfoToast("Descrição gerada copiada para o campo original."); // ALTERAÇÃO
    };

    const handleCopyToDescriptionCurtaOriginal = (generatedText) => {
        setFormData(prev => ({ ...prev, descricao_curta_orig: generatedText }));
        showInfoToast("Descrição curta gerada copiada para o campo original."); // ALTERAÇÃO
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={isNewProduct ? "Criar Novo Produto" : `Editar Produto: ${product?.nome_base}`}>
            <form onSubmit={handleSubmit}>
                <div className="tab-navigation">
                    <button type="button" className={activeTab === 'info' ? 'active' : ''} onClick={() => setActiveTab('info')}>Info Principais</button>
                    <button type="button" className={activeTab === 'atributos' ? 'active' : ''} onClick={() => setActiveTab('atributos')}>Atributos</button>
                    <button type="button" className={activeTab === 'midia' ? 'active' : ''} onClick={() => setActiveTab('midia')}>Mídia</button>
                    <button type="button" className={activeTab === 'conteudo-ia' ? 'active' : ''} onClick={() => setActiveTab('conteudo-ia')}>Conteúdo IA</button>
                    <button type="button" className={activeTab === 'sugestoes-ia' ? 'active' : ''} onClick={() => setActiveTab('sugestoes-ia')}>Sugestões IA</button> 
                    <button type="button" className={activeTab === 'log' ? 'active' : ''} onClick={() => setActiveTab('log')}>Log de Processamento</button>
                </div>

                <div className="tab-content">
                    {activeTab === 'info' && (
                        <div className="form-section">
                            <label>
                                Nome Base:
                                <input type="text" name="nome_base" value={formData.nome_base} onChange={handleChange} required />
                            </label>
                            <label>
                                Nome Chat API:
                                <input type="text" name="nome_chat_api" value={formData.nome_chat_api} onChange={handleChange} />
                            </label>
                            <label>
                                Descrição Original:
                                <textarea name="descricao_original" value={formData.descricao_original} onChange={handleChange} />
                            </label>
                             <label>
                                Descrição Curta Original:
                                <input type="text" name="descricao_curta_orig" value={formData.descricao_curta_orig} onChange={handleChange} />
                            </label>
                            <label>
                                SKU:
                                <input type="text" name="sku" value={formData.sku} onChange={handleChange} />
                            </label>
                            <label>
                                EAN:
                                <input type="text" name="ean" value={formData.ean} onChange={handleChange} />
                            </label>
                            <label>
                                NCM:
                                <input type="text" name="ncm" value={formData.ncm} onChange={handleChange} />
                            </label>
                            <label>
                                Marca:
                                <input type="text" name="marca" value={formData.marca} onChange={handleChange} />
                            </label>
                             <label>
                                Modelo:
                                <input type="text" name="modelo" value={formData.modelo} onChange={handleChange} />
                            </label>
                            <label>
                                Categoria Original:
                                <input type="text" name="categoria_original" value={formData.categoria_original} onChange={handleChange} />
                            </label>
                            <label>
                                Categoria Mapeada:
                                <input type="text" name="categoria_mapeada" value={formData.categoria_mapeada} onChange={handleChange} />
                            </label>
                            <label>
                                Preço Custo:
                                <input type="number" name="preco_custo" value={formData.preco_custo} onChange={handleChange} step="0.01" />
                            </label>
                            <label>
                                Preço Venda:
                                <input type="number" name="preco_venda" value={formData.preco_venda} onChange={handleChange} step="0.01" />
                            </label>
                            <label>
                                Preço Promocional:
                                <input type="number" name="preco_promocional" value={formData.preco_promocional} onChange={handleChange} step="0.01" />
                            </label>
                            <label>
                                Estoque Disponível:
                                <input type="number" name="estoque_disponivel" value={formData.estoque_disponivel} onChange={handleChange} />
                            </label>
                            <label>
                                Peso (kg):
                                <input type="number" name="peso_kg" value={formData.peso_kg} onChange={handleChange} step="0.01" />
                            </label>
                            <label>
                                Altura (cm):
                                <input type="number" name="altura_cm" value={formData.altura_cm} onChange={handleChange} step="0.01" />
                            </label>
                            <label>
                                Largura (cm):
                                <input type="number" name="largura_cm" value={formData.largura_cm} onChange={handleChange} step="0.01" />
                            </label>
                            <label>
                                Profundidade (cm):
                                <input type="number" name="profundidade_cm" value={formData.profundidade_cm} onChange={handleChange} step="0.01" />
                            </label>
                            <label>
                                Ativo no Marketplace:
                                <input type="checkbox" name="ativo_marketplace" checked={formData.ativo_marketplace} onChange={handleChange} />
                            </label>
                            <label>
                                Data Publicação Marketplace:
                                <input type="date" name="data_publicacao_marketplace" 
                                       value={formData.data_publicacao_marketplace ? new Date(formData.data_publicacao_marketplace).toISOString().split('T')[0] : ''}
                                       onChange={handleChange} />
                            </label>
                            <label>
                                Fornecedor:
                                <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange}>
                                    <option value="">Selecione um fornecedor</option>
                                    {fornecedores.map(f => (
                                        <option key={f.id} value={f.id}>{f.nome}</option>
                                    ))}
                                </select>
                            </label>
                            <label>
                                Tipo de Produto:
                                <select name="product_type_id" value={formData.product_type_id} onChange={handleChange}>
                                    <option value="">Selecione um tipo de produto</option>
                                    {productTypes.map(type => (
                                        <option key={type.id} value={type.id}>{type.friendly_name}</option>
                                    ))}
                                </select>
                            </label>
                        </div>
                    )}

                    {activeTab === 'atributos' && (
                        <div className="form-section">
                            <h3>Atributos Dinâmicos e de Template</h3>
                            {attributeTemplates.length > 0 && (
                                <div>
                                    <h4>Atributos do Tipo de Produto ({selectedProductType?.friendly_name})</h4>
                                    {attributeTemplates.map(attr => (
                                        <AttributeField
                                            key={attr.id}
                                            attribute={attr}
                                            value={formData.dynamic_attributes[attr.attribute_key] || ''}
                                            onChange={handleDynamicAttributeChange}
                                        />
                                    ))}
                                </div>
                            )}

                            <h4>Outros Atributos Dinâmicos</h4>
                            {Object.entries(formData.dynamic_attributes).map(([key, value]) => {
                                const isTemplateAttribute = attributeTemplates.some(template => template.attribute_key === key);
                                if (!isTemplateAttribute) {
                                    return (
                                        <label key={key}>
                                            {key}:
                                            <input
                                                type="text"
                                                value={value || ''}
                                                onChange={(e) => handleDynamicAttributeChange(key, e.target.value)}
                                            />
                                        </label>
                                    );
                                }
                                return null;
                            })}
                             <button type="button" onClick={addDynamicAttribute}>Adicionar Atributo Manual</button>
                        </div>
                    )}

                    {activeTab === 'midia' && (
                        <div className="form-section">
                            <h3>Mídia do Produto</h3>
                            <label>
                                URL Imagem Principal:
                                <input type="url" name="imagem_principal_url" value={formData.imagem_principal_url} onChange={handleChange} />
                            </label>
                            <label>
                                URLs Imagens Secundárias (separadas por vírgula):
                                <textarea
                                    name="imagens_secundarias_urls"
                                    value={formData.imagens_secundarias_urls.join(', ')}
                                    onChange={handleChange}
                                />
                            </label>
                            <div className="image-previews">
                                {formData.imagem_principal_url && (
                                    <img src={formData.imagem_principal_url} alt="Principal" style={{ maxWidth: '100px', maxHeight: '100px', margin: '5px' }} />
                                )}
                                {formData.imagens_secundarias_urls && formData.imagens_secundarias_urls.map((url, index) => (
                                    <img key={index} src={url} alt={`Secundária ${index + 1}`} style={{ maxWidth: '100px', maxHeight: '100px', margin: '5px' }} />
                                ))}
                            </div>
                        </div>
                    )}

                    {activeTab === 'conteudo-ia' && (
                        <div className="form-section">
                            <h3>Conteúdo Gerado por IA</h3>
                            <button type="button" onClick={handleGenerateTitles} disabled={isGeneratingIA}>
                                {isGeneratingIA ? 'Gerando Títulos...' : 'Gerar Títulos por IA'}
                            </button>
                            {formData.titulos_sugeridos && formData.titulos_sugeridos.length > 0 && (
                                <div>
                                    <h4>Títulos Sugeridos:</h4>
                                    <ul>
                                        {formData.titulos_sugeridos.map((title, index) => (
                                            <li key={index}>{title}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <hr />

                            <button type="button" onClick={handleGenerateDescription} disabled={isGeneratingIA}>
                                {isGeneratingIA ? 'Gerando Descrição...' : 'Gerar Descrição por IA'}
                            </button>
                            {formData.descricao_principal_gerada && (
                                <div style={{ marginTop: '10px' }}>
                                    <h4>Descrição Principal Gerada:</h4>
                                    <textarea
                                        value={formData.descricao_principal_gerada}
                                        onChange={(e) => setFormData(prev => ({ ...prev, descricao_principal_gerada: e.target.value }))}
                                        rows="10"
                                        style={{ width: '100%' }}
                                    />
                                    <button type="button" onClick={() => handleCopyToDescriptionOriginal(formData.descricao_principal_gerada)}>
                                        Copiar para Descrição Original
                                    </button>
                                </div>
                            )}
                            {formData.descricao_curta_gerada && (
                                <div style={{ marginTop: '10px' }}>
                                    <h4>Descrição Curta Gerada:</h4>
                                    <textarea
                                        value={formData.descricao_curta_gerada}
                                        onChange={(e) => setFormData(prev => ({ ...prev, descricao_curta_gerada: e.target.value }))}
                                        rows="3"
                                        style={{ width: '100%' }}
                                    />
                                    <button type="button" onClick={() => handleCopyToDescriptionCurtaOriginal(formData.descricao_curta_gerada)}>
                                        Copiar para Descrição Curta Original
                                    </button>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'sugestoes-ia' && (
                        <div className="form-section">
                            <h3>Sugestões de Atributos por IA</h3>
                            <p>Clique no botão abaixo para iniciar o processo de busca e sugestão de atributos com base em informações da web e IA. Este processo ocorre em segundo plano.</p>
                            
                            <button type="button" onClick={handleEnrichWeb} disabled={isEnrichingWeb || isNewProduct}>
                                {isEnrichingWeb ? 'Buscando Sugestões...' : 'Buscar Sugestões de Atributos'}
                            </button>
                            {!product?.id && <p className="warning-text">Salve o produto primeiro para buscar sugestões de atributos.</p>}

                            {Object.keys(iaAttributeSuggestions).length > 0 && (
                                <div style={{ marginTop: '20px' }}>
                                    <h4>Sugestões Encontradas:</h4>
                                    <p>Selecione os atributos que deseja adicionar ou atualizar nos "Atributos Dinâmicos".</p>
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                                        {Object.entries(iaAttributeSuggestions).map(([key, value]) => (
                                            <div key={key} style={{ border: '1px solid #ddd', padding: '10px', borderRadius: '5px' }}>
                                                <label>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedIaSuggestions[key] || false}
                                                        onChange={() => handleIaSuggestionToggle(key)}
                                                    />
                                                    <strong>{key}:</strong> {String(value)}
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                    <button type="button" onClick={applySelectedIaSuggestions} style={{ marginTop: '15px' }}>
                                        Aplicar Selecionados aos Atributos Dinâmicos
                                    </button>
                                </div>
                            )}
                            {Object.keys(iaAttributeSuggestions).length === 0 && !isEnrichingWeb && product?.id && (
                                <p style={{ marginTop: '20px', color: '#666' }}>Nenhuma sugestão de atributo encontrada ainda. Clique em "Buscar Sugestões de Atributos" para iniciar.</p>
                            )}
                        </div>
                    )}

                    {activeTab === 'log' && (
                        <div className="form-section">
                            <h3>Log de Processamento Web</h3>
                            {formData.log_enriquecimento_web && formData.log_enriquecimento_web.historico_mensagens && (
                                <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #ccc', padding: '10px', backgroundColor: '#f9f9f9' }}>
                                    {formData.log_enriquecimento_web.historico_mensagens.map((msg, index) => (
                                        <p key={index} style={{ fontSize: '0.9em', margin: '2px 0' }}>{msg}</p>
                                    ))}
                                </div>
                            )}
                            {(!formData.log_enriquecimento_web || !formData.log_enriquecimento_web.historico_mensagens || formData.log_enriquecimento_web.historico_mensagens.length === 0) && (
                                <p>Nenhum log de processamento web disponível para este produto.</p>
                            )}
                        </div>
                    )}
                </div>

                {error && <p className="error-message">{error}</p>}

                <div className="modal-actions">
                    <button type="submit" disabled={isLoading}>
                        {isLoading ? 'Salvando...' : 'Salvar Produto'}
                    </button>
                    <button type="button" onClick={onClose} disabled={isLoading}>
                        Cancelar
                    </button>
                </div>
            </form>
        </Modal>
    );
};

export default ProductEditModal;