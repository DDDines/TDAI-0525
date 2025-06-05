// Frontend/app/src/components/ProductEditModal.jsx
import React, { useState, useEffect, useCallback } from 'react';
import Modal from './common/Modal';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications'; 
import * as productService from '../services/productService'; 
import * as fornecedorService from '../services/fornecedorService'; 
// import * as productTypeService from '../services/productTypeService'; // Removido, pois usamos o contexto
import AttributeField from './produtos/shared/AttributeField';
import { useProductTypes } from '../contexts/ProductTypeContext'; 

const ProductEditModal = ({ isOpen, onClose, product, onProductUpdated }) => {
    const isNewProduct = !product?.id;

    // SEU ESTADO INICIAL - MANTIDO
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

    const [formData, setFormData] = useState(initialFormData);
    const [activeTab, setActiveTab] = useState('info'); 
    const [isLoading, setIsLoading] = useState(false); // Para o submit principal
    const [isGeneratingIA, setIsGeneratingIA] = useState(false); // Para gerar títulos/descrições
    const [isEnrichingWeb, setIsEnrichingWeb] = useState(false); // Para o botão "Buscar Sugestões de Atributos" (Web)
    const [error, setError] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const { productTypes } = useProductTypes(); 

    // --- ESTADOS PARA SUGESTÕES IA (JÁ EXISTIAM NO SEU CÓDIGO) ---
    const [iaAttributeSuggestions, setIaAttributeSuggestions] = useState({});
    const [selectedIaSuggestions, setSelectedIaSuggestions] = useState({});
    // --- NOVO ESTADO ESPECÍFICO PARA O BOTÃO GEMINI ---
    const [isSuggestingGemini, setIsSuggestingGemini] = useState(false);


    useEffect(() => {
        const fetchDependencies = async () => {
            if (isOpen) {
                try {
                    // SEU CÓDIGO ORIGINAL PARA BUSCAR FORNECEDORES
                    const fetchedFornecedores = await fornecedorService.getFornecedores({page: 1, limit: 100}); // Passando page e limit
                    setFornecedores(fetchedFornecedores.items || []);
                } catch (err) {
                    console.error("Erro ao carregar fornecedores:", err);
                    showErrorToast("Erro ao carregar fornecedores.");
                }
            }
        };
        fetchDependencies();
    }, [isOpen]);

    useEffect(() => {
        if (isOpen) {
            if (product) {
                setFormData({
                    nome_base: product.nome_base || '',
                    nome_chat_api: product.nome_chat_api || '',
                    descricao_original: product.descricao_original || '',
                    descricao_curta_orig: product.descricao_curta_orig || '',
                    descricao_principal_gerada: product.descricao_principal_gerada || '', // Mantido como no seu código
                    descricao_curta_gerada: product.descricao_curta_gerada || '', // Mantido como no seu código
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
                extractIaSuggestions(product.dados_brutos); // Chamada existente mantida
            } else { // Novo produto
                setFormData(initialFormData);
                setIaAttributeSuggestions({});
                setSelectedIaSuggestions({});
                setIsEnrichingWeb(false); // Resetar estados de loading
                setIsGeneratingIA(false);
                setIsSuggestingGemini(false); // Resetar novo estado
            }
            setActiveTab('info'); // Sempre começa na aba info
            setError(null); // Limpa erros anteriores
        }
    }, [product, isOpen, initialFormData]); // Adicionado initialFormData para garantir reset correto

    // SUA FUNÇÃO extractIaSuggestions - MANTIDA
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

    // SUA FUNÇÃO handleChange - MANTIDA
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

    // SUA FUNÇÃO handleDynamicAttributeChange - MANTIDA
    const handleDynamicAttributeChange = (key, value) => {
        setFormData(prev => ({
            ...prev,
            dynamic_attributes: {
                ...prev.dynamic_attributes,
                [key]: value,
            },
        }));
    };

    // SUA FUNÇÃO addDynamicAttribute - MANTIDA E MELHORADA A ATUALIZAÇÃO DO ESTADO
    const addDynamicAttribute = () => {
        const newKey = prompt("Digite a chave do novo atributo (ex: 'cor', 'voltagem'):");
        if (newKey && !formData.dynamic_attributes.hasOwnProperty(newKey)) {
            setFormData(prev => ({
                ...prev,
                dynamic_attributes: {
                    ...prev.dynamic_attributes, // Mantém os atributos existentes
                    [newKey]: '', // Adiciona o novo atributo
                },
            }));
        } else if (newKey) {
            showWarningToast("Atributo com esta chave já existe.");
        }
    };

    // SUAS FUNÇÕES handleIaSuggestionToggle e applySelectedIaSuggestions - MANTIDAS
    const handleIaSuggestionToggle = (key) => {
        setSelectedIaSuggestions(prev => ({
            ...prev,
            [key]: !prev[key],
        }));
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
            dynamic_attributes: {
                ...prev.dynamic_attributes,
                ...attributesToApply
            }
        }));
        showSuccessToast(`${appliedCount} sugest${appliedCount > 1 ? 'ões' : 'ão'} aplicada${appliedCount > 1 ? 's' : ''} aos atributos dinâmicos!`);
        setActiveTab('atributos');
    };

    // SUA FUNÇÃO handleEnrichWeb - MANTIDA
    const handleEnrichWeb = async () => {
        if (!product?.id) {
            showWarningToast("Salve o produto primeiro antes de enriquecer a web.");
            return;
        }
        setIsEnrichingWeb(true);
        setError(null);
        showInfoToast("Processo de enriquecimento web iniciado. Isso pode levar alguns minutos e atualizará o log e as sugestões.");
        try {
            // A chamada original no seu código:
            await productService.iniciarEnriquecimentoWebProduto(product.id); 
            // Após iniciar, o backend processa. Não há retorno imediato das sugestões aqui.
            // O usuário deve verificar o log ou a aba de sugestões após um tempo.
            // A lógica de setTimeout para buscar o produto atualizado pode ser mantida
            // ou substituída por um refresh manual ou WebSocket no futuro.
            showSuccessToast("Comando de enriquecimento enviado. O produto será atualizado em segundo plano.");
            // Opcional: agendar uma atualização dos dados do produto no modal após algum tempo
            // setTimeout(async () => {
            // try {
            // const updatedProduct = await productService.getProdutoById(product.id);
            // onProductUpdated(updatedProduct); // Atualiza na lista da página
            // setFormData(prev => ({ ...prev, ...updatedProduct })); // Atualiza no modal
            // extractIaSuggestions(updatedProduct.dados_brutos);
            // showInfoToast("Dados do produto atualizados após enriquecimento.");
            // } catch (fetchErr) {
            // console.error("Erro ao buscar produto atualizado:", fetchErr);
            // }
            // }, 15000); // Exemplo: 15 segundos

        } catch (err) {
            console.error("Erro ao iniciar enriquecimento web:", err);
            const errorDetail = err.response?.data?.detail || "Erro ao iniciar enriquecimento web.";
            setError(errorDetail);
            showErrorToast(errorDetail);
        } finally {
            setIsEnrichingWeb(false);
        }
    };

    // --- NOVA FUNÇÃO PARA BUSCAR SUGESTÕES COM GEMINI ---
    const handleFetchGeminiSuggestions = async () => {
        if (!product?.id) {
            showWarningToast("É preciso salvar o produto antes de buscar sugestões com Gemini.");
            return;
        }
        setIsSuggestingGemini(true); // Novo estado de loading
        setError(null);
        showInfoToast("Buscando sugestões de atributos com a IA (Gemini)... Isso pode levar um momento.");

        try {
            const suggestionsData = await productService.getAtributoSugestions(product.id); // Chama a nova função do service
            
            if (suggestionsData && suggestionsData.sugestoes_atributos && suggestionsData.sugestoes_atributos.length > 0) {
                const newSuggestions = suggestionsData.sugestoes_atributos.reduce((acc, item) => {
                    acc[item.chave_atributo] = item.valor_sugerido;
                    return acc;
                }, {});
                setIaAttributeSuggestions(newSuggestions); // Atualiza o mesmo estado usado pelo handleEnrichWeb
                
                // Reseta a seleção de checkboxes para as novas sugestões
                const initialSelections = Object.keys(newSuggestions).reduce((acc, key) => {
                    acc[key] = false;
                    return acc;
                }, {});
                setSelectedIaSuggestions(initialSelections);
                showSuccessToast("Sugestões da IA (Gemini) carregadas!");
            } else {
                setIaAttributeSuggestions({}); // Limpa sugestões antigas se a resposta for vazia
                setSelectedIaSuggestions({});
                showInfoToast("Nenhuma sugestão de atributo específica retornada pela IA (Gemini).");
            }
        } catch (err) {
            console.error("Erro ao buscar sugestões Gemini:", err);
            const errorDetail = err.response?.data?.detail || err.message || "Falha ao carregar sugestões da IA (Gemini).";
            setError(errorDetail);
            showErrorToast(errorDetail);
            setIaAttributeSuggestions({}); // Limpa em caso de erro
            setSelectedIaSuggestions({});
        } finally {
            setIsSuggestingGemini(false);
        }
    };
    // --- FIM DA NOVA FUNÇÃO ---

    // SUA FUNÇÃO handleSubmit - MANTIDA com pequenas melhorias na validação
    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        if (!formData.nome_base) {
            setError("O nome base do produto é obrigatório.");
            showErrorToast("O nome base do produto é obrigatório.");
            setActiveTab('info');
            setIsLoading(false);
            return;
        }
        // A validação do product_type_id é importante para um produto existente
        // Para um novo, pode ser selecionado na primeira aba e salvo.
        if (!isNewProduct && !formData.product_type_id) { 
             setError("O tipo de produto é obrigatório para editar.");
             showErrorToast("O tipo de produto é obrigatório para editar.");
             setActiveTab('info');
             setIsLoading(false);
             return;
        }
        // Se for novo produto e não selecionou tipo, o backend pode não permitir
        // ou pode criar sem tipo. Idealmente, para novo, a aba "info" já deve ter o product_type_id.
        if (isNewProduct && !formData.product_type_id) {
            showWarningToast("É recomendado selecionar um Tipo de Produto.");
            // Pode-se optar por não bloquear o save aqui e deixar o backend decidir
            // ou adicionar uma validação mais estrita.
        }


        try {
            const productDataToSave = { ...formData };
            
            // Limpeza de campos que não devem ser enviados se vazios/nulos
            // (exceto booleanos e números que podem ser 0)
            Object.keys(productDataToSave).forEach(key => {
                const value = productDataToSave[key];
                if (value === '' || value === null) {
                    if (typeof value === 'boolean' || typeof value === 'number') {
                        // Não deletar booleanos false ou números 0
                    } else {
                        delete productDataToSave[key];
                    }
                } else if (Array.isArray(value) && value.length === 0) {
                    delete productDataToSave[key];
                } else if (typeof value === 'object' && value !== null && Object.keys(value).length === 0 && !(value instanceof Date) ) {
                     // Deleta objetos vazios (exceto Date)
                    delete productDataToSave[key];
                }
            });
            
            // Garante que objetos JSON vazios sejam enviados como {} se necessário pelo backend,
            // ou omitidos se o backend os trata como opcionais.
            // A lógica acima já remove objetos vazios. Se o backend *precisar* de um objeto vazio,
            // a lógica de delete teria que ser mais específica.
            // if (!productDataToSave.dynamic_attributes) productDataToSave.dynamic_attributes = {};
            // if (!productDataToSave.dados_brutos) productDataToSave.dados_brutos = {};


            if (productDataToSave.data_publicacao_marketplace && productDataToSave.data_publicacao_marketplace instanceof Date) {
                productDataToSave.data_publicacao_marketplace = productDataToSave.data_publicacao_marketplace.toISOString();
            } else if (!productDataToSave.data_publicacao_marketplace) {
                 delete productDataToSave.data_publicacao_marketplace; // Ou null se o backend preferir
            }


            let responseProduct;
            if (isNewProduct) {
                responseProduct = await productService.createProduto(productDataToSave);
                showSuccessToast("Produto criado com sucesso!");
            } else {
                responseProduct = await productService.updateProduto(product.id, productDataToSave);
                showSuccessToast("Produto atualizado com sucesso!");
            }
            onProductUpdated(responseProduct); 
            onClose(); 
        } catch (err) {
            console.error("Erro ao salvar produto:", err);
            const errorDetail = err.response?.data?.detail || err.message || "Erro ao salvar produto.";
            setError(errorDetail);
            showErrorToast(errorDetail);
        } finally {
            setIsLoading(false);
        }
    };

    // SUAS FUNÇÕES handleGenerateTitles, handleGenerateDescription, etc. - MANTIDAS
    const handleGenerateTitles = async () => {
        if (!product?.id) {
            showWarningToast("Salve o produto primeiro para gerar títulos.");
            return;
        }
        setIsGeneratingIA(true);
        try {
            // A API do backend pode esperar parâmetros adicionais em um objeto no corpo
            await productService.gerarTitulosProduto(product.id); // Removido {max_sugestoes:3} a menos que o backend suporte
            showInfoToast("Geração de títulos iniciada. Verifique em breve.");
            // Simular atualização ou usar um mecanismo de polling/WebSockets
            setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({ ...prev, nome_chat_api: updatedProduct.nome_chat_api, titulos_sugeridos: updatedProduct.titulos_sugeridos }));
                onProductUpdated(updatedProduct); // Para atualizar na lista principal
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
            await productService.gerarDescricaoProduto(product.id); // Removido {max_palavras:300} a menos que o backend suporte
            showInfoToast("Geração de descrição iniciada. Verifique em breve.");
             setTimeout(async () => {
                const updatedProduct = await productService.getProdutoById(product.id);
                setFormData(prev => ({
                    ...prev,
                    descricao_chat_api: updatedProduct.descricao_chat_api, // Assumindo que o backend retorna 'descricao_chat_api'
                    // descricao_principal_gerada: updatedProduct.descricao_principal_gerada, // Se estes campos são diferentes
                    // descricao_curta_gerada: updatedProduct.descricao_curta_gerada
                }));
                onProductUpdated(updatedProduct);
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
            <form onSubmit={handleSubmit}>
                <div className="tab-navigation">
                    <button type="button" className={activeTab === 'info' ? 'active' : ''} onClick={() => setActiveTab('info')}>Info Principais</button>
                    <button type="button" className={activeTab === 'atributos' ? 'active' : ''} onClick={() => setActiveTab('atributos')} disabled={!formData.product_type_id && isNewProduct}>Atributos</button>
                    <button type="button" className={activeTab === 'midia' ? 'active' : ''} onClick={() => setActiveTab('midia')}>Mídia</button>
                    <button type="button" className={activeTab === 'conteudo-ia' ? 'active' : ''} onClick={() => setActiveTab('conteudo-ia')}>Conteúdo IA</button>
                    <button type="button" className={activeTab === 'sugestoes-ia' ? 'active' : ''} onClick={() => setActiveTab('sugestoes-ia')}>Sugestões IA</button> 
                    <button type="button" className={activeTab === 'log' ? 'active' : ''} onClick={() => setActiveTab('log')}>Log</button>
                </div>

                <div className="tab-content" style={{minHeight: '350px', padding:'15px 0'}}>
                    {activeTab === 'info' && (
                        <div className="form-section">
                            {/* SEUS CAMPOS DA ABA INFO PRINCIPAIS - MANTIDOS */}
                            <label>
                                Tipo de Produto:
                                <select name="product_type_id" value={formData.product_type_id} onChange={handleChange} required={!isNewProduct}>
                                    <option value="">Selecione um tipo</option>
                                    {productTypes.map(type => (
                                        <option key={type.id} value={type.id}>{type.friendly_name}</option>
                                    ))}
                                </select>
                            </label>
                            <label> Nome Base: <input type="text" name="nome_base" value={formData.nome_base} onChange={handleChange} required /> </label>
                            <label> Nome Chat API: <input type="text" name="nome_chat_api" value={formData.nome_chat_api} onChange={handleChange} /> </label>
                            <label> Descrição Original: <textarea name="descricao_original" value={formData.descricao_original} onChange={handleChange} /> </label>
                            <label> Descrição Curta Original: <input type="text" name="descricao_curta_orig" value={formData.descricao_curta_orig} onChange={handleChange} /> </label>
                            <label> SKU: <input type="text" name="sku" value={formData.sku} onChange={handleChange} /> </label>
                            <label> EAN: <input type="text" name="ean" value={formData.ean} onChange={handleChange} /> </label>
                            <label> NCM: <input type="text" name="ncm" value={formData.ncm} onChange={handleChange} /> </label>
                            <label> Marca: <input type="text" name="marca" value={formData.marca} onChange={handleChange} /> </label>
                            <label> Modelo: <input type="text" name="modelo" value={formData.modelo} onChange={handleChange} /> </label>
                            <label> Categoria Original: <input type="text" name="categoria_original" value={formData.categoria_original} onChange={handleChange} /> </label>
                            <label> Categoria Mapeada: <input type="text" name="categoria_mapeada" value={formData.categoria_mapeada} onChange={handleChange} /> </label>
                            <label> Preço Custo: <input type="number" name="preco_custo" value={formData.preco_custo} onChange={handleChange} step="0.01" /> </label>
                            <label> Preço Venda: <input type="number" name="preco_venda" value={formData.preco_venda} onChange={handleChange} step="0.01" /> </label>
                            <label> Preço Promocional: <input type="number" name="preco_promocional" value={formData.preco_promocional} onChange={handleChange} step="0.01" /> </label>
                            <label> Estoque Disponível: <input type="number" name="estoque_disponivel" value={formData.estoque_disponivel} onChange={handleChange} /> </label>
                            <label> Peso (kg): <input type="number" name="peso_kg" value={formData.peso_kg} onChange={handleChange} step="0.01" /> </label>
                            <label> Altura (cm): <input type="number" name="altura_cm" value={formData.altura_cm} onChange={handleChange} step="0.01" /> </label>
                            <label> Largura (cm): <input type="number" name="largura_cm" value={formData.largura_cm} onChange={handleChange} step="0.01" /> </label>
                            <label> Profundidade (cm): <input type="number" name="profundidade_cm" value={formData.profundidade_cm} onChange={handleChange} step="0.01" /> </label>
                            <label> Ativo no Marketplace: <input type="checkbox" name="ativo_marketplace" checked={formData.ativo_marketplace} onChange={handleChange} /> </label>
                            <label> Data Publicação Marketplace: <input type="date" name="data_publicacao_marketplace" value={formData.data_publicacao_marketplace ? new Date(formData.data_publicacao_marketplace).toISOString().split('T')[0] : ''} onChange={handleChange} /> </label>
                            <label>
                                Fornecedor:
                                <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange}>
                                    <option value="">Selecione um fornecedor</option>
                                    {fornecedores.map(f => (<option key={f.id} value={f.id}>{f.nome}</option>))}
                                </select>
                            </label>
                        </div>
                    )}

                    {activeTab === 'atributos' && (
                        <div className="form-section">
                            {/* SEU JSX PARA ATRIBUTOS - MANTIDO */}
                             <h3>Atributos Dinâmicos e de Template</h3>
                             {!formData.product_type_id && <p>Selecione um Tipo de Produto na aba "Info Principais" para ver os atributos do template.</p>}
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
                             <h4>Outros Atributos Dinâmicos (Manuais)</h4>
                             {Object.entries(formData.dynamic_attributes)
                                 .filter(([key]) => !attributeTemplates.some(template => template.attribute_key === key))
                                 .map(([key, value]) => (
                                     <div key={key} style={{display: 'flex', gap: '10px', alignItems: 'center', marginBottom:'5px'}}>
                                         <input type="text" value={key} disabled style={{flex:'1', backgroundColor:'#f0f0f0'}} />
                                         <input
                                             type="text"
                                             value={value || ''}
                                             onChange={(e) => handleDynamicAttributeChange(key, e.target.value)}
                                             style={{flex:'2'}}
                                         />
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
                            {/* SEU JSX PARA MÍDIA - MANTIDO */}
                             <h3>Mídia do Produto</h3>
                             <label> URL Imagem Principal: <input type="url" name="imagem_principal_url" value={formData.imagem_principal_url} onChange={handleChange} /> </label>
                             <label> URLs Imagens Secundárias (separadas por vírgula): <textarea name="imagens_secundarias_urls" value={Array.isArray(formData.imagens_secundarias_urls) ? formData.imagens_secundarias_urls.join(', ') : ''} onChange={handleChange} /> </label>
                             <div className="image-previews">
                                 {formData.imagem_principal_url && ( <img src={formData.imagem_principal_url} alt="Principal" style={{ maxWidth: '100px', maxHeight: '100px', margin: '5px', border:'1px solid #ddd' }} /> )}
                                 {Array.isArray(formData.imagens_secundarias_urls) && formData.imagens_secundarias_urls.map((url, index) => ( url && <img key={index} src={url} alt={`Secundária ${index + 1}`} style={{ maxWidth: '100px', maxHeight: '100px', margin: '5px', border:'1px solid #ddd' }} /> ))}
                             </div>
                         </div>
                    )}

                    {activeTab === 'conteudo-ia' && (
                         <div className="form-section">
                            {/* SEU JSX PARA CONTEÚDO IA - MANTIDO */}
                             <h3>Conteúdo Gerado por IA</h3>
                             <button type="button" onClick={handleGenerateTitles} disabled={isGeneratingIA || isNewProduct}> {isGeneratingIA ? 'Gerando Títulos...' : 'Gerar Títulos (OpenAI)'} </button>
                             {formData.titulos_sugeridos && formData.titulos_sugeridos.length > 0 && ( <div> <h4>Títulos Sugeridos:</h4> <ul> {formData.titulos_sugeridos.map((title, index) => ( <li key={index}>{title}</li> ))} </ul> </div> )}
                             <hr />
                             <button type="button" onClick={handleGenerateDescription} disabled={isGeneratingIA || isNewProduct}> {isGeneratingIA ? 'Gerando Descrição...' : 'Gerar Descrição (OpenAI)'} </button>
                             {formData.descricao_principal_gerada && ( <div style={{ marginTop: '10px' }}> <h4>Descrição Principal Gerada:</h4> <textarea value={formData.descricao_principal_gerada} onChange={(e) => setFormData(prev => ({ ...prev, descricao_principal_gerada: e.target.value }))} rows="10" style={{ width: '100%' }} /> <button type="button" onClick={() => handleCopyToDescriptionOriginal(formData.descricao_principal_gerada)}> Copiar para Descrição Original </button> </div> )}
                             {formData.descricao_curta_gerada && ( <div style={{ marginTop: '10px' }}> <h4>Descrição Curta Gerada:</h4> <textarea value={formData.descricao_curta_gerada} onChange={(e) => setFormData(prev => ({ ...prev, descricao_curta_gerada: e.target.value }))} rows="3" style={{ width: '100%' }} /> <button type="button" onClick={() => handleCopyToDescriptionCurtaOriginal(formData.descricao_curta_gerada)}> Copiar para Descrição Curta Original </button> </div> )}
                         </div>
                    )}

                    {activeTab === 'sugestoes-ia' && (
                        <div className="form-section">
                            <h3>Sugestões de Atributos por IA</h3>
                            
                            <div style={{marginBottom: '20px'}}>
                                <p>Use o botão abaixo para que a IA (Web Scraping + Gemini) analise o produto e sugira valores para os atributos. Este processo pode demorar e ocorre em segundo plano.</p>
                                <button type="button" onClick={handleEnrichWeb} disabled={isEnrichingWeb || isNewProduct}>
                                    {isEnrichingWeb ? 'Enriquecendo Web...' : 'Iniciar Enriquecimento Web (Sugestões via Web)'}
                                </button>
                                {isNewProduct && <p className="warning-text">Salve o produto primeiro para esta funcionalidade.</p>}
                            </div>
                            
                            <hr style={{margin: "20px 0"}}/>

                            <div>
                                <p>Clique no botão abaixo para uma busca rápida de sugestões de atributos usando a IA (Gemini) com os dados atuais do produto.</p>
                                <button type="button" onClick={handleFetchGeminiSuggestions} disabled={isSuggestingGemini || isNewProduct}>
                                    {isSuggestingGemini ? 'Buscando com Gemini...' : 'Buscar Sugestões (Gemini Direto)'}
                                </button>
                                {isNewProduct && <p className="warning-text">Salve o produto primeiro para esta funcionalidade.</p>}
                            </div>

                            {Object.keys(iaAttributeSuggestions).length > 0 && (
                                <div style={{ marginTop: '20px' }}>
                                    <h4>Sugestões de Atributos Encontradas:</h4>
                                    <p>Selecione os atributos que deseja aplicar aos "Atributos Dinâmicos".</p>
                                    <div className="ia-suggestions-grid" style={{display:'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap:'10px'}}>
                                        {Object.entries(iaAttributeSuggestions).map(([key, value]) => (
                                            <div key={key} className="ia-suggestion-item" style={{border:'1px solid #eee', padding:'10px', borderRadius:'5px', backgroundColor: selectedIaSuggestions[key] ? '#e6f7ff' : 'transparent'}}>
                                                <label style={{display:'flex', alignItems:'center', cursor:'pointer', width:'100%'}}>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedIaSuggestions[key] || false}
                                                        onChange={() => handleIaSuggestionToggle(key)}
                                                        style={{marginRight:'8px'}}
                                                    />
                                                    <div>
                                                        <strong>{key}:</strong> {String(value)}
                                                    </div>
                                                </label>
                                            </div>
                                        ))}
                                    </div>
                                    <button type="button" onClick={applySelectedIaSuggestions} style={{ marginTop: '15px' }} className="btn-success">
                                        Aplicar Atributos Selecionados
                                    </button>
                                </div>
                            )}
                            {Object.keys(iaAttributeSuggestions).length === 0 && !isEnrichingWeb && !isSuggestingGemini && product?.id && (
                                <p style={{ marginTop: '20px', color: '#666' }}>Nenhuma sugestão de atributo encontrada ainda. Clique em um dos botões acima para iniciar.</p>
                            )}
                        </div>
                    )}

                    {activeTab === 'log' && (
                         <div className="form-section">
                            {/* SEU JSX PARA LOG - MANTIDO */}
                             <h3>Log de Processamento</h3>
                             {formData.log_enriquecimento_web && formData.log_enriquecimento_web.historico_mensagens && formData.log_enriquecimento_web.historico_mensagens.length > 0 ? (
                                 <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid #ccc', padding: '10px', backgroundColor: '#f9f9f9', fontSize:'0.9em' }}>
                                     {formData.log_enriquecimento_web.historico_mensagens.map((msg, index) => (
                                         <p key={index} style={{ margin: '2px 0', whiteSpace:'pre-wrap' }}>{msg}</p>
                                     ))}
                                 </div>
                             ) : (
                                 <p>Nenhum log disponível.</p>
                             )}
                         </div>
                    )}
                </div>

                {error && <p className="error-message" style={{color: 'red', marginTop:'10px', textAlign:'center'}}>{error}</p>}

                <div className="modal-actions" style={{marginTop:'20px', paddingTop:'15px', borderTop:'1px solid #eee', display:'flex', justifyContent:'flex-end', gap:'10px'}}>
                    <button type="button" onClick={onClose} disabled={isLoading || isGeneratingIA || isSuggestingGemini || isEnrichingWeb} style={{backgroundColor: '#6c757d'}}>
                        Cancelar
                    </button>
                    <button type="submit" disabled={isLoading || isGeneratingIA || isSuggestingGemini || isEnrichingWeb} style={{backgroundColor:'var(--success)'}}>
                        {isLoading ? 'Salvando...' : 'Salvar Alterações'}
                    </button>
                </div>
            </form>
        </Modal>
    );
};

export default ProductEditModal;