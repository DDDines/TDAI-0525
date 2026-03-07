/**
 * Module product edit modal.
 *
 * Defines responsibilities and integration points for components.
 */

// Frontend/app/src/components/ProductEditModal.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useAppExperience } from '../contexts/AppExperienceContext';
import Modal from './common/Modal';
import LoadingOverlay from './common/LoadingOverlay.jsx';
import { showSuccessToast, showErrorToast, showInfoToast, showWarningToast } from '../utils/notifications';
import { normalizeDisplayText } from '../utils/textNormalization';
import productService from '../services/productService';
import fornecedorService from '../services/fornecedorService';
import AttributeField from './produtos/shared/AttributeField';
import { useProductTypes } from '../contexts/ProductTypeContext';
import {
  coerceFormFieldValue,
  extractGeneratedTitles,
  normalizeDynamicAttrsToTemplateKeys
} from './ProductEditModal.helpers.js';
import NewProductTypeModal from './product_types/NewProductTypeModal.jsx';
import './ProductEditModal.css';

// Campos base que não devem aparecer como atributos dinâmicos

function clearRefreshTimeout(timeoutRef) {
  if (!timeoutRef.current) return;
  clearTimeout(timeoutRef.current);
  timeoutRef.current = null;
}

function ProductEditModal(

  { isOpen, onClose, product, onProductUpdated, showAiFeatures: showAiFeaturesProp, onOpenContentView }) {
    const isNewProduct = !product?.id;

    const { isAuthenticated: _isAuthenticated } = useAuth();
    const { effectiveMode } = useAppExperience();
    const showAiFeatures = typeof showAiFeaturesProp === 'boolean' ? showAiFeaturesProp : effectiveMode === 'complete';

    const [formData, setFormData] = useState(initialFormData);
    const [activeTab, setActiveTab] = useState('info');
    const [isLoading, setIsLoading] = useState(false);
    const [isGeneratingIA, setIsGeneratingIA] = useState(false);
    const [isEnrichingWeb, setIsEnrichingWeb] = useState(false);
    const [isSuggestingGemini, setIsSuggestingGemini] = useState(false);
    const [_error, setError] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const { productTypes } = useProductTypes();

    // Para novos produtos, mostramos primeiro a seleção do fornecedor e do tipo
    // Se estiver editando (product fornecido), iniciamos diretamente no formulário
    const [stage, setStage] = useState(product ? 'form' : 'selectFornecedor'); // 'selectFornecedor' | 'selectType' | 'form'

    const [iaAttributeSuggestions, setIaAttributeSuggestions] = useState({});
    const [selectedIaSuggestions, setSelectedIaSuggestions] = useState({});
    const [newAttrKey, setNewAttrKey] = useState('');
    const [isNewTypeModalOpen, setIsNewTypeModalOpen] = useState(false);
    const enrichmentPollRunRef = React.useRef(0);
    const titleRefreshTimeoutRef = React.useRef(null);
    const descriptionRefreshTimeoutRef = React.useRef(null);
    const isMountedRef = React.useRef(false);
    const isOpenRef = React.useRef(isOpen);

    useEffect(() => {
      isMountedRef.current = true;
      return () => {
        isMountedRef.current = false;
      };
    }, []);


    useEffect(() => {
      const fetchDependencies = async () => {
        if (isOpen) {
          try {
            const fetchedFornecedores = await fornecedorService.getFornecedores({ skip: 0, limit: 100 });
            let list = fetchedFornecedores.items || [];

            // Se estiver editando e o fornecedor do produto não estiver na lista, buscamos especificamente
            if (product?.fornecedor_id && !list.some((f) => f.id === product.fornecedor_id)) {
              try {
                const fornecedorCompleto = await fornecedorService.getFornecedorById(product.fornecedor_id);
                if (fornecedorCompleto) {
                  list = [...list, fornecedorCompleto];
                }
              } catch (innerErr) {
                console.error("Erro ao buscar fornecedor pelo ID:", innerErr);
              }
            }

            setFornecedores(list);
          } catch (err) {
            console.error("Erro ao carregar fornecedores:", err);
            showErrorToast("Erro ao carregar lista de fornecedores para o modal.");
          }
        }
      };
      fetchDependencies();
    }, [isOpen, product?.fornecedor_id]);

    // Define o estágio inicial quando o modal é aberto ou quando o produto muda
    useEffect(() => {
      if (isOpen) {
        // Se estivermos editando, já vamos direto para o formulário
        if (product && product.id) {
          setStage('form');
        } else if (!formData.fornecedor_id) {
          setStage('selectFornecedor');
        } else if (!formData.product_type_id) {
          setStage('selectType');
        } else {
          setStage('form');
        }
      }
    }, [isOpen, product, formData.fornecedor_id, formData.product_type_id]);

    useEffect(() => {
      isOpenRef.current = isOpen;
      if (!isOpen) {
        enrichmentPollRunRef.current += 1;
        setIsEnrichingWeb(false);
        clearRefreshTimeout(titleRefreshTimeoutRef);
        clearRefreshTimeout(descriptionRefreshTimeoutRef);
      }
      return () => {
        enrichmentPollRunRef.current += 1;
        clearRefreshTimeout(titleRefreshTimeoutRef);
        clearRefreshTimeout(descriptionRefreshTimeoutRef);
      };
    }, [isOpen]);

    useEffect(() => {
      if (!showAiFeatures && activeTab === 'sugestoes-ia') {
        setActiveTab('info');
      }
    }, [activeTab, showAiFeatures]);

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

    const populateFormData = useCallback((prod) => {
      if (!prod) return;
      const dynamicAttrsRaw = prod.dynamic_attributes && typeof prod.dynamic_attributes === 'object' ? prod.dynamic_attributes : {};
      const productTypeId = Number(prod?.product_type_id || prod?.product_type?.id || 0);
      const fallbackTypeTemplates =
      productTypes.find((type) => Number(type?.id) === productTypeId)?.attribute_templates || [];
      const typeTemplates =
      prod?.product_type?.attribute_templates && Array.isArray(prod.product_type.attribute_templates) ?
      prod.product_type.attribute_templates :
      fallbackTypeTemplates;
      const dynamicAttrsNormalized = normalizeDynamicAttrsToTemplateKeys(dynamicAttrsRaw, typeTemplates);
      const dynamicAttrs = Object.fromEntries(
        Object.entries(dynamicAttrsNormalized).filter(([key]) => !BASE_PRODUCT_FIELDS.has(key))
      );
      const dadosBrutos = prod.dados_brutos_web && typeof prod.dados_brutos_web === 'object' ? prod.dados_brutos_web : {};

      setFormData({
        nome_base: prod.nome_base || '',
        nome_chat_api: prod.nome_chat_api || '',
        descricao_original: prod.descricao_original || '',
        descricao_curta_orig: prod.descricao_curta_orig || '',
        descricao_chat_api: prod.descricao_chat_api || '',
        descricao_curta_gerada: prod.descricao_curta_gerada || '',
        sku: prod.sku || '',
        ean: prod.ean || '',
        ncm: prod.ncm || '',
        marca: prod.marca || '',
        modelo: prod.modelo || '',
        categoria_original: prod.categoria_original || '',
        categoria_mapeada: prod.categoria_mapeada || '',
        preco_custo: prod.preco_custo || '',
        preco_venda: prod.preco_venda || '',
        preco_promocional: prod.preco_promocional || '',
        estoque_disponivel: prod.estoque_disponivel || '',
        peso_gramas: prod.peso_gramas || '',
        dimensoes_cm: prod.dimensoes_cm || '',
        imagem_principal_url: prod.imagem_principal_url || '',
        imagens_secundarias_urls: prod.imagens_secundarias_urls || [],
        fornecedor_id: prod.fornecedor_id || '',
        product_type_id: prod.product_type_id || '',
        dynamic_attributes: dynamicAttrs,
        dados_brutos_web: dadosBrutos,
        titulos_sugeridos: extractGeneratedTitles(prod),
        ativo_marketplace: prod.ativo_marketplace || false,
        data_publicacao_marketplace: prod.data_publicacao_marketplace || null,
        log_enriquecimento_web: prod.log_enriquecimento_web || { historico_mensagens: [] },
        status_enriquecimento_web: prod.status_enriquecimento_web || null,
        status_titulo_ia: prod.status_titulo_ia || null,
        status_descricao_ia: prod.status_descricao_ia || null
      });
      extractIaSuggestions(dadosBrutos);
    }, [extractIaSuggestions, productTypes]);

    useEffect(() => {
      const loadDetails = async () => {
        if (!isOpen) return;
        if (product && product.id) {
          try {
            const fullProduct = await productService.getProdutoById(product.id);
            populateFormData(fullProduct);
          } catch (err) {
            console.error('Erro ao carregar produto:', err);
            showErrorToast('Erro ao carregar dados completos do produto.');
            populateFormData(product);
            showWarningToast('Dados carregados parcialmente.');
          }
          // Garantir que o estágio seja o formulário ao editar
          setStage('form');
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
      };
      loadDetails();
    }, [product, isOpen, populateFormData]);

    const handleChange = (e) => {
      const { name, value, type, checked } = e.target;
      if (name === 'product_type_id') {
        setFormData((prev) => ({ ...prev, [name]: value }));
        if (value) {
          initializeAttributesForType(value);
        }
      } else {
        setFormData((prev) => ({
          ...prev,
          [name]: coerceFormFieldValue(name, value, type, checked)
        }));
      }
    };

    const handleDynamicAttributeChange = (key, value) => {
      setFormData((prev) => ({
        ...prev,
        dynamic_attributes: {
          ...prev.dynamic_attributes,
          [key]: value
        }
      }));
    };

    const initializeAttributesForType = useCallback((typeId) => {
      const selectedType = productTypes.find((pt) => pt.id === parseInt(typeId, 10));
      if (selectedType && selectedType.attribute_templates) {
        const initialAttrs = {};
        selectedType.attribute_templates.
        filter((tpl) => !BASE_PRODUCT_FIELDS.has(tpl.attribute_key)).
        forEach((template) => {
          const typeLower = template.field_type ? template.field_type.toLowerCase() : '';
          if (template.default_value !== null && template.default_value !== undefined) {
            initialAttrs[template.attribute_key] = typeLower === 'boolean' ?
            String(template.default_value).toLowerCase() === 'true' || template.default_value === '1' :
            template.default_value;
          } else {
            initialAttrs[template.attribute_key] = typeLower === 'boolean' ? false : '';
          }
        });
        setFormData((prev) => ({ ...prev, dynamic_attributes: initialAttrs }));
      }
    }, [productTypes]);

    const addDynamicAttribute = () => {
      const newKey = newAttrKey.trim();
      if (newKey && !Object.prototype.hasOwnProperty.call(formData.dynamic_attributes, newKey) && !BASE_PRODUCT_FIELDS.has(newKey)) {
        setFormData((prev) => ({
          ...prev,
          dynamic_attributes: {
            ...prev.dynamic_attributes,
            [newKey]: ''
          }
        }));
        setNewAttrKey('');
      } else if (newKey) {
        showWarningToast("Atributo com esta chave já existe ou é um campo básico.");
      }
    };

    // Helper para sanitizar e converter campos numéricos antes de enviar ao backend
    const sanitizeProdutoData = (data) => {
      const sanitized = { ...data };
      sanitized.preco_custo = data.preco_custo !== '' ? parseFloat(data.preco_custo) : null;
      sanitized.preco_venda = data.preco_venda !== '' ? parseFloat(data.preco_venda) : null;
      sanitized.preco_promocional = data.preco_promocional !== '' ? parseFloat(data.preco_promocional) : null;
      sanitized.estoque_disponivel = data.estoque_disponivel !== '' ? parseInt(data.estoque_disponivel, 10) : null;
      sanitized.peso_gramas = data.peso_gramas !== '' ? parseInt(data.peso_gramas, 10) : null;
      sanitized.fornecedor_id = data.fornecedor_id !== '' ? parseInt(data.fornecedor_id, 10) : null;
      sanitized.product_type_id = data.product_type_id !== '' ? parseInt(data.product_type_id, 10) : null;
      return sanitized;
    };

    const handleIaSuggestionToggle = (key) => {
      setSelectedIaSuggestions((prev) => ({ ...prev, [key]: !prev[key] }));
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
      setFormData((prev) => ({
        ...prev,
        dynamic_attributes: { ...prev.dynamic_attributes, ...attributesToApply }
      }));
      showSuccessToast(`${appliedCount} sugest${appliedCount > 1 ? 'ões' : 'ão'} aplicada${appliedCount > 1 ? 's' : ''} aos atributos dinâmicos!`);
      setActiveTab('atributos');
    };

    const handleOpenNewTypeModal = () => setIsNewTypeModalOpen(true);
    const handleCloseNewTypeModal = () => setIsNewTypeModalOpen(false);
    const handleNewTypeCreated = (newType) => {
      setFormData((prev) => ({ ...prev, product_type_id: newType.id }));
    };

    const resolveErrorDetail = (err, fallback) => {
      if (!err) return fallback;
      if (typeof err?.message === 'string' && err.message.trim()) return err.message;
      if (typeof err?.detail === 'string' && err.detail.trim()) return err.detail;
      if (typeof err?.response?.data?.detail === 'string' && err.response.data.detail.trim()) {
        return err.response.data.detail;
      }
      if (typeof err?.response?.data?.msg === 'string' && err.response.data.msg.trim()) {
        return err.response.data.msg;
      }
      return fallback;
    };

    const pollEnrichmentUntilTerminal = async (produtoId, runId) => {
      for (let attempt = 1; attempt <= WEB_ENRICHMENT_MAX_POLLS; attempt += 1) {
        if (enrichmentPollRunRef.current !== runId) return null;
        try {
          const refreshedProduct = await productService.getProdutoById(produtoId);
          if (enrichmentPollRunRef.current !== runId) return null;

          const currentStatus = String(
            refreshedProduct?.status_enriquecimento_web || ''
          ).toUpperCase();

          if (
          currentStatus &&
          currentStatus !== 'EM_PROGRESSO' &&
          WEB_ENRICHMENT_TERMINAL_STATUSES.has(currentStatus))
          {
            populateFormData(refreshedProduct);
            if (onProductUpdated) onProductUpdated(refreshedProduct);
            return refreshedProduct;
          }
        } catch (pollError) {
          if (enrichmentPollRunRef.current !== runId) return null;
          console.warn('Falha ao consultar status de enriquecimento web:', pollError);
        }

        if (attempt < WEB_ENRICHMENT_MAX_POLLS) {
          await new Promise((resolve) =>
          setTimeout(resolve, WEB_ENRICHMENT_POLL_INTERVAL_MS)
          );
        }
      }
      return null;
    };


    const _handleEnrichWeb = async () => {
      const productId = product.id;
      const runId = Date.now();
      enrichmentPollRunRef.current = runId;
      setIsEnrichingWeb(true);
      setError(null);
      showInfoToast("Processo de enriquecimento web iniciado. Isso pode levar alguns minutos e atualizar o log e as sugestoes.");
      try {
        await productService.iniciarEnriquecimentoWebProduto(productId);
        if (enrichmentPollRunRef.current !== runId) return;

        setFormData((prev) => ({
          ...prev,
          status_enriquecimento_web: 'PENDENTE',
        }));
        showSuccessToast("Comando de enriquecimento enviado. Atualizando status do produto em segundo plano.");

        void (async () => {
          try {
            const refreshed = await pollEnrichmentUntilTerminal(productId, runId);
            if (enrichmentPollRunRef.current !== runId) return;

            if (!refreshed) {
              showWarningToast(
                "O enriquecimento continua em segundo plano. Reabra o produto em instantes para ver o resultado final."
              );
              return;
            }

            const summary = refreshed?.log_enriquecimento_web?.resumo_aplicacao || {};
            const appliedTotal = Number(summary?.aplicados_total || 0);
            const ignoredTotal = Number(summary?.ignorados_total || 0);
            const statusFinal = String(refreshed?.status_enriquecimento_web || '').toUpperCase();

            if (statusFinal === 'CONCLUIDO_SUCESSO' || statusFinal === 'CONCLUIDO_COM_DADOS_PARCIAIS') {
              showSuccessToast(
                `Enriquecimento finalizado (${statusFinal}). Aplicados: ${appliedTotal}. Ignorados: ${ignoredTotal}.`
              );
            } else if (statusFinal) {
              showWarningToast(`Enriquecimento finalizado com status ${statusFinal}.`);
            }
          } catch (pollErr) {
            if (enrichmentPollRunRef.current === runId) {
              console.warn('Falha ao acompanhar status de enriquecimento web:', pollErr);
            }
          }
        })();
      } catch (err) {
        const errorDetail = resolveErrorDetail(err, "Erro ao iniciar enriquecimento web.");
        setError(errorDetail);
        showErrorToast(errorDetail);
      } finally {
        if (enrichmentPollRunRef.current === runId) {
          setIsEnrichingWeb(false);
        }
      }
    };


    const handleFetchGeminiSuggestions = async () => {
      setIsSuggestingGemini(true);
      setError(null);
      showInfoToast("Buscando sugestões de atributos com a IA (Gemini)... Isso pode levar um momento.");

      try {
        const suggestionsData = await productService.getAtributoSuggestions(product.id);
        const sugestoes = Array.isArray(suggestionsData?.sugestoes_atributos) ?
        suggestionsData.sugestoes_atributos :
        [];
        if (sugestoes.length > 0) {
          const newSuggestions = sugestoes.reduce((acc, item) => {
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
        const productDataToSave = sanitizeProdutoData(formData);
        let responseProduct;
        if (isNewProduct) {
          responseProduct = await productService.createProduto(productDataToSave);
          showSuccessToast("Produto criado com sucesso!");
        } else {
          responseProduct = await productService.updateProduto(product.id, productDataToSave);
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
      setIsGeneratingIA(true);
      try {
        if (showAiFeatures) {
          await productService.gerarTitulosProduto(product.id);
          showInfoToast("Geração de títulos iniciada. Verifique em breve.");
        } else {
          await productService.gerarTitulosProdutoModoBasico(product.id);
          showInfoToast("Títulos gerados no modo básico.");
        }
        clearRefreshTimeout(titleRefreshTimeoutRef);
        titleRefreshTimeoutRef.current = setTimeout(() => {
          void (async () => {
            try {
              const updatedProduct = await productService.getProdutoById(product.id);
              if (!isMountedRef.current || !isOpenRef.current) {
                return;
              }
              setFormData((prev) => ({
                ...prev,
                nome_chat_api: updatedProduct.nome_chat_api,
                dados_brutos_web:
                updatedProduct.dados_brutos_web && typeof updatedProduct.dados_brutos_web === 'object' ?
                updatedProduct.dados_brutos_web :
                prev.dados_brutos_web,
                titulos_sugeridos: extractGeneratedTitles(updatedProduct)
              }));
              if (onProductUpdated) onProductUpdated(updatedProduct);
            } catch (refreshErr) {
              if (!isMountedRef.current || !isOpenRef.current) {
                return;
              }
              console.error("Erro ao atualizar títulos gerados:", refreshErr);
              showErrorToast("Nao foi possivel atualizar os titulos gerados.");
            } finally {
              titleRefreshTimeoutRef.current = null;
            }
          })();
        }, 7000);
      } catch (err) {
        console.error("Erro ao gerar títulos:", err);
        showErrorToast(err.response?.data?.detail || "Erro ao gerar títulos.");
      } finally {
        setIsGeneratingIA(false);
      }
    };

    const handleOpenContentView = () => {
      if (typeof onClose === 'function') {
        onClose();
      }
      if (typeof onOpenContentView === 'function') {
        onOpenContentView(product.id);
        return;
      }
      if (typeof window !== 'undefined') {
        window.location.assign(`/produtos/${product.id}/conteudo`);
      }
    };

    const handleGenerateDescription = async () => {
      setIsGeneratingIA(true);
      try {
        if (showAiFeatures) {
          await productService.gerarDescricaoProduto(product.id);
          showInfoToast("Geração de descrição iniciada. Verifique em breve.");
        } else {
          await productService.gerarDescricaoProdutoModoBasico(product.id);
          showInfoToast("Descrição gerada no modo básico.");
        }
        clearRefreshTimeout(descriptionRefreshTimeoutRef);
        descriptionRefreshTimeoutRef.current = setTimeout(() => {
          void (async () => {
            try {
              const updatedProduct = await productService.getProdutoById(product.id);
              if (!isMountedRef.current || !isOpenRef.current) {
                return;
              }
              setFormData((prev) => ({
                ...prev,
                descricao_chat_api: updatedProduct.descricao_chat_api
              }));
              if (onProductUpdated) onProductUpdated(updatedProduct);
            } catch (refreshErr) {
              if (!isMountedRef.current || !isOpenRef.current) {
                return;
              }
              console.error("Erro ao atualizar descrição gerada:", refreshErr);
              showErrorToast("Nao foi possivel atualizar a descricao gerada.");
            } finally {
              descriptionRefreshTimeoutRef.current = null;
            }
          })();
        }, 7000);
      } catch (err) {
        console.error("Erro ao gerar descrição:", err);
        showErrorToast(err.response?.data?.detail || "Erro ao gerar descrição.");
      } finally {
        setIsGeneratingIA(false);
      }
    };

    const selectedProductType = productTypes.find((type) => type.id === parseInt(formData.product_type_id));
    const attributeTemplates = selectedProductType ? selectedProductType.attribute_templates : [];
    const enrichmentSummary = formData?.log_enriquecimento_web?.resumo_aplicacao || {};
    const appliedFields = Array.isArray(enrichmentSummary?.aplicados) ? enrichmentSummary.aplicados : [];
    const ignoredFields = Array.isArray(enrichmentSummary?.ignorados) ? enrichmentSummary.ignorados : [];
    const appliedDetails = Array.isArray(enrichmentSummary?.campos_alterados_detalhe) ?
    enrichmentSummary.campos_alterados_detalhe :
    [];

    return (
      <>
        <Modal isOpen={isOpen} onClose={onClose} title={isNewProduct ? "Criar Novo Produto" : `Editar Produto: ${formData.nome_base || 'ID ' + product?.id}`}>
            {stage === 'selectFornecedor' ?
          <div className="form-section" style={{ padding: '1rem' }}>
                    <label className="full-width">
                        Fornecedor:
                        <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange} required>
                            <option value="">Selecione um fornecedor</option>
                            {fornecedores.map((f) =>
                <option key={f.id} value={f.id}>{f.nome}</option>
                )}
                        </select>
                    </label>
                    <div className="modal-actions" style={{ marginTop: '20px' }}>
                        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
                    </div>
                </div> :
          stage === 'selectType' ?
          <div className="form-section" style={{ padding: '1rem' }}>
                    <label className="full-width">
                        Fornecedor:
                        <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange} required>
                            <option value="">Selecione um fornecedor</option>
                            {fornecedores.map((f) =>
                <option key={f.id} value={f.id}>{f.nome}</option>
                )}
                        </select>
                    </label>
                    <label className="full-width">
                        Tipo de Produto:
                        <select name="product_type_id" value={formData.product_type_id} onChange={handleChange} required>
                            <option value="">Selecione um tipo</option>
                            {(productTypes || []).map((type) =>
                <option key={type.id} value={type.id}>{type.friendly_name}</option>
                )}
                        </select>
                    </label>
                    <button type="button" className="btn-small" onClick={handleOpenNewTypeModal} style={{ marginTop: '8px' }}>+ Novo Tipo</button>
                    <div className="modal-actions" style={{ marginTop: '20px' }}>
                        <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
                    </div>
                </div> :

          <form onSubmit={handleSubmit}>
                <div className="tab-navigation">
                    <button type="button" className={activeTab === 'info' ? 'active' : ''} onClick={() => setActiveTab('info')}>Info Principais</button>
                    <button type="button" className={activeTab === 'atributos' ? 'active' : ''} onClick={() => setActiveTab('atributos')} disabled={!formData.fornecedor_id || !formData.product_type_id}>Atributos</button>
                    <button type="button" className={activeTab === 'midia' ? 'active' : ''} onClick={() => setActiveTab('midia')} disabled={!formData.fornecedor_id || !formData.product_type_id}>Mídia</button>
                    <button type="button" className={activeTab === 'conteudo-ia' ? 'active' : ''} onClick={() => setActiveTab('conteudo-ia')} disabled={!formData.fornecedor_id || !formData.product_type_id}>
                          {showAiFeatures ? 'Conteúdo IA' : 'Conteúdo'}
                        </button>
                    {showAiFeatures &&
                    <>
                        <button type="button" className={activeTab === 'sugestoes-ia' ? 'active' : ''} onClick={() => setActiveTab('sugestoes-ia')} disabled={!formData.fornecedor_id || !formData.product_type_id}>Sugestões IA</button>
                      </>
                    }
                    <button type="button" className={activeTab === 'log' ? 'active' : ''} onClick={() => setActiveTab('log')} disabled={!formData.fornecedor_id || !formData.product_type_id}>Log</button>
                </div>

                <div className="tab-content">
                    {activeTab === 'info' &&
              <div className="form-section form-grid">
                            <label className="full-width">
                                Fornecedor:
                                <select name="fornecedor_id" value={formData.fornecedor_id} onChange={handleChange} required>
                                    <option value="">Selecione um fornecedor</option>
                                    {fornecedores.map((f) =>
                    <option key={f.id} value={f.id}>{f.nome}</option>
                    )}
                                </select>
                            </label>
                            {formData.fornecedor_id &&
                <label className="full-width">
                                    Tipo de Produto:
                                    <select name="product_type_id" value={formData.product_type_id} onChange={handleChange} required>
                                        <option value="">Selecione um tipo</option>
                                        {(productTypes || []).map((type) =>
                    <option key={type.id} value={type.id}>{type.friendly_name}</option>
                    )}
                                    </select>
                                </label>
                }
                            {formData.fornecedor_id && formData.product_type_id &&
                <>
                                    <label> Nome Base: <input type="text" name="nome_base" value={formData.nome_base} onChange={handleChange} required /> </label>
                                    <label> Marca: <input type="text" name="marca" value={formData.marca} onChange={handleChange} /> </label>
                                    <label> SKU: <input type="text" name="sku" value={formData.sku} onChange={handleChange} /> </label>
                                </>
                }
                        </div>
              }
                    {activeTab === 'atributos' &&
              <div className="form-section">
                             <h3>Atributos Dinâmicos e de Template</h3>
                             {!formData.product_type_id && <p>Selecione um Tipo de Produto na aba "Info Principais".</p>}
                             {attributeTemplates && attributeTemplates.length > 0 &&
                <div>
                                     <h4>Atributos do Tipo ({selectedProductType?.friendly_name})</h4>
                                     {attributeTemplates.filter((attr) => !BASE_PRODUCT_FIELDS.has(attr.attribute_key)).map((attr) =>
                  <AttributeField
                    key={attr.attribute_key}
                    attributeTemplate={attr}
                    value={formData.dynamic_attributes?.[attr.attribute_key] ?? ''}
                    onChange={handleDynamicAttributeChange} />

                  )}
                                </div>
                }
                             <h4>Outros Atributos (Manuais)</h4>
                             {Object.entries(formData.dynamic_attributes).
                filter(([key]) => !attributeTemplates.some((template) => template.attribute_key === key)).
                filter(([key]) => !BASE_PRODUCT_FIELDS.has(key)).
                map(([key, value]) =>
                <div key={key} style={{ display: 'flex', gap: '10px', alignItems: 'center', marginBottom: '5px' }}>
                                         <input type="text" value={key} disabled style={{ flex: '1', backgroundColor: '#f0f0f0' }} />
                                         <input type="text" value={value || ''} onChange={(e) => handleDynamicAttributeChange(key, e.target.value)} style={{ flex: '2' }} />
                                         <button type="button" onClick={() => {
                    const { [key]: _, ...rest } = formData.dynamic_attributes;
                    setFormData((prev) => ({ ...prev, dynamic_attributes: rest }));
                    showInfoToast(`Atributo manual "${key}" removido.`);
                  }} title="Remover este atributo manual" style={{ padding: '5px', color: 'red', border: 'none', background: 'transparent', cursor: 'pointer' }}>🗑️</button>
                                     </div>
                )}
                              <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                                  <input type="text" placeholder="Nova chave" value={newAttrKey} onChange={(e) => setNewAttrKey(e.target.value)} style={{ flex: '1' }} />
                                  <button type="button" onClick={addDynamicAttribute}>Adicionar Atributo Manual</button>
                              </div>
                        </div>
              }
                    {activeTab === 'midia' &&
              <div className="form-section">
                             <h3>Mídia do Produto</h3>
                             <label> URL Imagem Principal: <input type="url" name="imagem_principal_url" value={formData.imagem_principal_url} onChange={handleChange} /> </label>
                             <div className="image-previews">
                                 {formData.imagem_principal_url && <img src={formData.imagem_principal_url} alt="Principal" style={{ maxWidth: '100px', maxHeight: '100px', margin: '5px', border: '2px solid var(--primary)' }} />}
                             </div>
                         </div>
              }
                    {activeTab === 'conteudo-ia' &&
              <div className="form-section">
                            <h3>{showAiFeatures ? 'Conteúdo Gerado por IA' : 'Conteúdo Gerado'}</h3>
                            <button type="button" onClick={handleOpenContentView} disabled={isNewProduct}>
                              Ver 5 Títulos + Descrição em Tela Dedicada
                            </button>
                            <button type="button" onClick={_handleEnrichWeb} disabled={isEnrichingWeb || isNewProduct}>
                              {isEnrichingWeb ? 'Enriquecendo Web...' : 'Enriquecer Web'}
                            </button>
                            <hr />
                            <button type="button" onClick={handleGenerateTitles} disabled={isGeneratingIA || isNewProduct}>
                              {isGeneratingIA ? 'Gerando Títulos...' : showAiFeatures ? 'Gerar Títulos (OpenAI)' : 'Gerar Títulos (Básico)'}
                            </button>
                            {formData.titulos_sugeridos && formData.titulos_sugeridos.length > 0 && <div> <h4>Títulos Sugeridos:</h4> <ul> {formData.titulos_sugeridos.map((title, index) => <li key={index}>{title}</li>)} </ul> </div>}
                            <hr />
                            <button type="button" onClick={handleGenerateDescription} disabled={isGeneratingIA || isNewProduct}>
                              {isGeneratingIA ? 'Gerando Descrição...' : showAiFeatures ? 'Gerar Descrição (OpenAI)' : 'Gerar Descrição (Básico)'}
                            </button>
                            {formData.descricao_chat_api && <div style={{ marginTop: '10px' }}> <h4>Descrição Principal Gerada:</h4> <textarea value={formData.descricao_chat_api} readOnly rows="10" style={{ width: '100%', backgroundColor: '#f9f9f9' }} /> </div>}
                        </div>
              }
                    {showAiFeatures && activeTab === 'sugestoes-ia' &&
              <div className="form-section">
                            <h3>Sugestões de Atributos por IA</h3>
                            <div className="suggestion-action-box">
                                <p>Busque sugestões rápidas de atributos usando Gemini com os dados atuais do produto.</p>
                                <button type="button" onClick={handleFetchGeminiSuggestions} disabled={isSuggestingGemini || isNewProduct}>
                                    {isSuggestingGemini ? 'Buscando...' : 'Buscar Sugestões (Gemini)'}
                                </button>
                            </div>
                            {Object.keys(iaAttributeSuggestions).length > 0 &&
                <div className="ia-suggestions-container">
                                    <h4>Sugestões Encontradas:</h4>
                                    <div className="ia-suggestions-grid">
                                        {Object.entries(iaAttributeSuggestions).map(([key, value]) =>
                    <div key={key} className={`ia-suggestion-item ${selectedIaSuggestions[key] ? 'selected' : ''}`}>
                                                <label>
                                                    <input type="checkbox" checked={!!selectedIaSuggestions[key]} onChange={() => handleIaSuggestionToggle(key)} />
                                                    <div><strong>{key}:</strong> {String(value)}</div>
                                                </label>
                                            </div>
                    )}
                                    </div>
                                    <button type="button" onClick={applySelectedIaSuggestions} className="btn-apply-suggestions">
                                        Aplicar Selecionados
                                    </button>
                                </div>
                }
                        </div>
              }
                    {activeTab === 'log' &&
              <div className="form-section">
                             <h3>Log de Processamento</h3>
                             {(appliedFields.length > 0 || ignoredFields.length > 0) &&
                <div style={{ marginBottom: '12px' }}>
                                     {appliedFields.length > 0 &&
                  <div>
                                             <strong>Campos aplicados:</strong> {appliedFields.join(', ')}
                                         </div>
                  }
                                     {ignoredFields.length > 0 &&
                  <div>
                                             <strong>Campos ignorados:</strong> {ignoredFields.join(', ')}
                                         </div>
                  }
                                     {appliedDetails.length > 0 &&
                  <div style={{ marginTop: '8px' }}>
                                             <strong>Alterações aplicadas:</strong>
                                             <ul style={{ margin: '6px 0 0 18px' }}>
                                                 {appliedDetails.map((item, idx) =>
                      <li key={`${item}-${idx}`}>{normalizeDisplayText(item)}</li>
                      )}
                                             </ul>
                                         </div>
                  }
                                 </div>
                }
                             {formData.log_enriquecimento_web && formData.log_enriquecimento_web.historico_mensagens && formData.log_enriquecimento_web.historico_mensagens.length > 0 ?
                <div className="log-container">
                                     {formData.log_enriquecimento_web.historico_mensagens.map((msg, index) =>
                  <p key={index}>{normalizeDisplayText(msg)}</p>
                  )}
                                 </div> :

                <p>Nenhum log disponível.</p>
                }
                        </div>
              }
                </div>

                <div className="modal-actions">
                    <button type="button" onClick={onClose} disabled={isLoading || isEnrichingWeb || isGeneratingIA || isSuggestingGemini} className="btn-secondary">Cancelar</button>
                    <button type="submit" disabled={isLoading || isEnrichingWeb || isGeneratingIA || isSuggestingGemini} className="btn-success">{isLoading ? 'Salvando...' : 'Salvar Produto'}</button>
                </div>
            </form>
          }
        </Modal>
        <NewProductTypeModal
          isOpen={isNewTypeModalOpen}
          onClose={handleCloseNewTypeModal}
          onCreated={handleNewTypeCreated} />
        
        <LoadingOverlay
          isOpen={isLoading || isEnrichingWeb || isGeneratingIA || isSuggestingGemini}
          message="Processando..." />
        
        </>);

  }
const BASE_PRODUCT_FIELDS = new Set(['nome_base', 'nome_chat_api', 'descricao_original', 'descricao_curta_orig', 'descricao_chat_api', 'descricao_curta_gerada', 'sku', 'ean', 'ncm', 'marca', 'modelo', 'categoria_original', 'categoria_mapeada', 'preco_custo', 'preco_venda', 'preco_promocional', 'estoque_disponivel', 'peso_gramas', 'dimensoes_cm', 'imagem_principal_url', 'imagens_secundarias_urls', 'fornecedor_id', 'product_type_id', 'ativo_marketplace', 'data_publicacao_marketplace', 'status_enriquecimento_web', 'status_titulo_ia', 'status_descricao_ia', 'log_enriquecimento_web', 'titulos_sugeridos']);const initialFormData = { nome_base: '', nome_chat_api: '', descricao_original: '', descricao_curta_orig: '', descricao_chat_api: '', descricao_curta_gerada: '', sku: '', ean: '', ncm: '', marca: '', modelo: '', categoria_original: '', categoria_mapeada: '', preco_custo: '', preco_venda: '', preco_promocional: '', estoque_disponivel: '', peso_gramas: '', dimensoes_cm: '', imagem_principal_url: '', imagens_secundarias_urls: [], fornecedor_id: '', product_type_id: '', dynamic_attributes: {}, dados_brutos_web: {}, titulos_sugeridos: [], ativo_marketplace: false, data_publicacao_marketplace: null, log_enriquecimento_web: { historico_mensagens: [] }, status_enriquecimento_web: null, status_titulo_ia: null, status_descricao_ia: null };const WEB_ENRICHMENT_POLL_INTERVAL_MS = 3000;const WEB_ENRICHMENT_MAX_POLLS = 40;const WEB_ENRICHMENT_TERMINAL_STATUSES = new Set(['CONCLUIDO', 'CONCLUIDO_SUCESSO', 'CONCLUIDO_COM_DADOS_PARCIAIS', 'NENHUMA_FONTE_ENCONTRADA', 'FALHA_API_EXTERNA', 'FALHA_CONFIGURACAO_API_EXTERNA', 'FALHA', 'FALHOU', 'NAO_APLICAVEL']);export default ProductEditModal;
