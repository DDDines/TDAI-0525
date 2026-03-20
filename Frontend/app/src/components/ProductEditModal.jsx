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
import ProductContentWorkspace from './produtos/ProductContentWorkspace.jsx';
import { useProductTypes } from '../contexts/ProductTypeContext';
import {
  buildProductFormState,
  buildInitialDynamicAttributes,
  coerceFormFieldValue,
  handleContentViewNavigation,
  logAsyncPollError,
  resolveProductFormStage,
  resolveServiceErrorDetail,
  resolveShowAiFeatures,
  sanitizeProdutoData
} from './ProductEditModal.helpers.js';
import NewProductTypeModal from './product_types/NewProductTypeModal.jsx';
import './ProductEditModal.css';

// Campos base que não devem aparecer como atributos dinâmicos

const GENERATION_POLL_INTERVAL_MS = 3000;
const GENERATION_MAX_POLLS = 40;
const GENERATION_TERMINAL_STATUSES = new Set([
  'CONCLUIDO',
  'CONCLUIDO_SUCESSO',
  'FALHA',
  'FALHOU',
  'NAO_APLICAVEL',
]);
const ACTIVE_PROCESS_STATUSES = new Set([
  'PENDENTE',
  'EM_PROGRESSO',
]);

function ProductEditModal(

  { isOpen, onClose, product, onProductUpdated, showAiFeatures: showAiFeaturesProp, onOpenContentView }) {
    const isNewProduct = !product?.id;

    const { isAuthenticated: _isAuthenticated } = useAuth();
    const { effectiveMode } = useAppExperience();
    const showAiFeatures = resolveShowAiFeatures(showAiFeaturesProp, effectiveMode);

    const [formData, setFormData] = useState(initialFormData);
    const [activeTab, setActiveTab] = useState('info');
    const [isLoading, setIsLoading] = useState(false);
    const [isGeneratingIA, setIsGeneratingIA] = useState(false);
    const [isEnrichingWeb, setIsEnrichingWeb] = useState(false);
    const [usarIAEnriquecimentoWeb, setUsarIAEnriquecimentoWeb] = useState(false);
    const [usarIAConteudo, setUsarIAConteudo] = useState(false);
    const [isSuggestingGemini, setIsSuggestingGemini] = useState(false);
    const [_error, setError] = useState(null);
    const [fornecedores, setFornecedores] = useState([]);
    const { productTypes } = useProductTypes();
    const safeProductTypes = Array.isArray(productTypes) ? productTypes : [];

    // Para novos produtos, mostramos primeiro a seleção do fornecedor e do tipo
    // Se estiver editando (product fornecido), iniciamos diretamente no formulário
    const [stage, setStage] = useState(product ? 'form' : 'selectFornecedor'); // 'selectFornecedor' | 'selectType' | 'form'

    const [iaAttributeSuggestions, setIaAttributeSuggestions] = useState({});
    const [selectedIaSuggestions, setSelectedIaSuggestions] = useState({});
    const [newAttrKey, setNewAttrKey] = useState('');
    const [isNewTypeModalOpen, setIsNewTypeModalOpen] = useState(false);
    const enrichmentPollRunRef = React.useRef(0);
    const generationPollRunsRef = React.useRef({
      status_titulo_ia: 0,
      status_descricao_ia: 0,
    });
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
        setStage(resolveProductFormStage(product, formData.fornecedor_id, formData.product_type_id));
      }
    }, [isOpen, product, formData.fornecedor_id, formData.product_type_id]);

    useEffect(() => {
      if (isOpen) {
        setUsarIAEnriquecimentoWeb(false);
        setUsarIAConteudo(false);
      }
    }, [isOpen, product?.id]);

    useEffect(() => {
      if (!isOpen) {
        return;
      }
      setActiveTab('info');
      setError(null);
    }, [isOpen, product?.id]);

    useEffect(() => {
      isOpenRef.current = isOpen;
      if (!isOpen) {
        enrichmentPollRunRef.current += 1;
        generationPollRunsRef.current.status_titulo_ia += 1;
        generationPollRunsRef.current.status_descricao_ia += 1;
        setIsEnrichingWeb(false);
      }
      return () => {
        enrichmentPollRunRef.current += 1;
        generationPollRunsRef.current.status_titulo_ia += 1;
        generationPollRunsRef.current.status_descricao_ia += 1;
      };
    }, [isOpen]);

    useEffect(() => {
      if (!showAiFeatures && activeTab === 'sugestoes-ia') {
        setActiveTab('info');
      }
    }, [activeTab, showAiFeatures]);

    const populateFormData = useCallback((prod) => {
      if (!prod) return;
      const nextState = buildProductFormState(
        prod,
        safeProductTypes,
        BASE_PRODUCT_FIELDS,
        initialFormData
      );
      setFormData(nextState.formData);
      setIaAttributeSuggestions(nextState.iaSuggestions);
      setSelectedIaSuggestions(nextState.selectedIaSuggestions);
    }, [safeProductTypes]);

    useEffect(() => {
      const loadDetails = async () => {
        if (!isOpen) return;
        if (product && product.id) {
          populateFormData(product);
          setStage('form');
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
      };
      loadDetails();
    }, [product, isOpen, populateFormData]);

    const handleChange = (e) => {
      const { name, value, type, checked } = e.target;
      if (name === 'product_type_id') {
        setFormData((prev) => ({ ...prev, [name]: value }));
        if (!value) {
          setUsarIAEnriquecimentoWeb(false);
        }
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
      const selectedType = safeProductTypes.find((pt) => pt.id === parseInt(typeId, 10));
      const initialAttrs = buildInitialDynamicAttributes(selectedType, BASE_PRODUCT_FIELDS);
      if (initialAttrs) {
        setFormData((prev) => ({ ...prev, dynamic_attributes: initialAttrs }));
      }
    }, [safeProductTypes]);

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
            onProductUpdated?.(refreshedProduct);
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

    const pollGenerationUntilTerminal = async (produtoId, statusField, runId) => {
      for (let attempt = 1; attempt <= GENERATION_MAX_POLLS; attempt += 1) {
        if (generationPollRunsRef.current[statusField] !== runId) return null;
        try {
          const refreshedProduct = await productService.getProdutoById(produtoId);
          if (generationPollRunsRef.current[statusField] !== runId) return null;

          const currentStatus = String(refreshedProduct?.[statusField] || '').toUpperCase();
          if (currentStatus && GENERATION_TERMINAL_STATUSES.has(currentStatus)) {
            populateFormData(refreshedProduct);
            onProductUpdated?.(refreshedProduct);
            return refreshedProduct;
          }
        } catch {
          if (generationPollRunsRef.current[statusField] !== runId) return null;
          throw new Error(
            statusField === 'status_titulo_ia'
              ? 'Não foi possível atualizar os títulos gerados.'
              : 'Não foi possível atualizar a descrição gerada.'
          );
        }

        if (attempt < GENERATION_MAX_POLLS) {
          await new Promise((resolve) =>
          setTimeout(resolve, GENERATION_POLL_INTERVAL_MS)
          );
        }
      }
      return null;
    };


    const _handleEnrichWeb = async () => {
      const currentStatus = String(formData?.status_enriquecimento_web || '').toUpperCase();
      if (ACTIVE_PROCESS_STATUSES.has(currentStatus)) {
        return;
      }
      if (showAiFeatures && usarIAEnriquecimentoWeb && !formData.product_type_id) {
        showWarningToast('Defina um tipo de produto antes de usar IA no enriquecimento web.');
        return;
      }
      const productId = product.id;
      const runId = Date.now();
      enrichmentPollRunRef.current = runId;
      setIsEnrichingWeb(true);
      setError(null);
      showInfoToast(
        `Processo de enriquecimento web ${showAiFeatures && usarIAEnriquecimentoWeb ? 'com IA' : 'básico'} iniciado. Isso pode levar alguns minutos e atualizar o log e as sugestões.`
      );
      try {
        if (showAiFeatures && usarIAEnriquecimentoWeb) {
          await productService.iniciarEnriquecimentoWebProduto(productId, {
            usarIA: true,
          });
        } else {
          await productService.iniciarEnriquecimentoWebProduto(productId);
        }
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
            const statusFinal = String(refreshed.status_enriquecimento_web).toUpperCase();

            if (statusFinal === 'CONCLUIDO' || statusFinal === 'CONCLUIDO_SUCESSO') {
              showSuccessToast(
                `Enriquecimento finalizado (${statusFinal}). Aplicados: ${appliedTotal}. Ignorados: ${ignoredTotal}.`
              );
            } else if (statusFinal === 'CONCLUIDO_COM_DADOS_PARCIAIS') {
              showWarningToast(
                `Enriquecimento finalizado com pendências (${statusFinal}). Aplicados: ${appliedTotal}. Ignorados: ${ignoredTotal}.`
              );
            } else {
              showWarningToast(`Enriquecimento finalizado com status ${statusFinal}.`);
            }
          } catch (pollErr) {
            logAsyncPollError(
              console.warn,
              enrichmentPollRunRef.current,
              runId,
              'Falha ao acompanhar status de enriquecimento web:',
              pollErr
            );
          }
        })();
      } catch (err) {
        const errorDetail = resolveServiceErrorDetail(err, "Erro ao iniciar enriquecimento web.");
        setError(errorDetail);
        showErrorToast(errorDetail);
      } finally {
        if (enrichmentPollRunRef.current === runId) {
          setIsEnrichingWeb(false);
        }
      }
    };


    const handleFetchGeminiSuggestions = async () => {
      if (!formData.product_type_id) {
        showWarningToast('Defina um tipo de produto para buscar atributos relevantes com IA.');
        return;
      }
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
        const errorDetail = resolveServiceErrorDetail(err, "Falha ao carregar sugestões da IA (Gemini).");
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
        const errorDetail = resolveServiceErrorDetail(err, "Erro ao salvar produto.");
        setError(errorDetail);
        showErrorToast(errorDetail);
      } finally {
        setIsLoading(false);
      }
    };

    const handleGenerateTitles = async () => {
      const currentStatus = String(formData?.status_titulo_ia || '').toUpperCase();
      if (ACTIVE_PROCESS_STATUSES.has(currentStatus)) {
        return;
      }
      const runId = Date.now();
      generationPollRunsRef.current.status_titulo_ia = runId;
      setIsGeneratingIA(true);
      setFormData((prev) => ({
        ...prev,
        status_titulo_ia: 'PENDENTE',
      }));
      try {
        if (showAiFeatures && usarIAConteudo) {
          await productService.gerarTitulosProduto(product.id);
        } else {
          await productService.gerarTitulosProdutoModoBasico(product.id);
        }
        if (generationPollRunsRef.current.status_titulo_ia !== runId) {
          return;
        }
        setFormData((prev) => ({
          ...prev,
          status_titulo_ia: 'EM_PROGRESSO',
        }));
        const updatedProduct = await pollGenerationUntilTerminal(
          product.id,
          'status_titulo_ia',
          runId
        );
        if (generationPollRunsRef.current.status_titulo_ia !== runId || !isMountedRef.current || !isOpenRef.current) {
          return;
        }
        if (!updatedProduct) {
          showWarningToast("A geração de títulos continua em segundo plano. Reabra o produto em instantes.");
        }
      } catch (err) {
        console.error("Erro ao gerar títulos:", err);
        showErrorToast(resolveServiceErrorDetail(err, "Erro ao gerar títulos."));
        setFormData((prev) => ({
          ...prev,
          status_titulo_ia: 'FALHA',
        }));
      } finally {
        setIsGeneratingIA(false);
      }
    };

    const handleOpenContentView = () => {
      handleContentViewNavigation(
        product.id,
        onClose,
        onOpenContentView,
        window.location.assign.bind(window.location)
      );
    };

    const handleGenerateDescription = async () => {
      const currentStatus = String(formData?.status_descricao_ia || '').toUpperCase();
      if (ACTIVE_PROCESS_STATUSES.has(currentStatus)) {
        return;
      }
      const runId = Date.now();
      generationPollRunsRef.current.status_descricao_ia = runId;
      setIsGeneratingIA(true);
      setFormData((prev) => ({
        ...prev,
        status_descricao_ia: 'PENDENTE',
      }));
      try {
        if (showAiFeatures && usarIAConteudo) {
          await productService.gerarDescricaoProduto(product.id);
        } else {
          await productService.gerarDescricaoProdutoModoBasico(product.id);
        }
        if (generationPollRunsRef.current.status_descricao_ia !== runId) {
          return;
        }
        setFormData((prev) => ({
          ...prev,
          status_descricao_ia: 'EM_PROGRESSO',
        }));
        const updatedProduct = await pollGenerationUntilTerminal(
          product.id,
          'status_descricao_ia',
          runId
        );
        if (generationPollRunsRef.current.status_descricao_ia !== runId || !isMountedRef.current || !isOpenRef.current) {
          return;
        }
        if (!updatedProduct) {
          showWarningToast("A geração da descrição continua em segundo plano. Reabra o produto em instantes.");
        }
      } catch (err) {
        console.error("Erro ao gerar descrição:", err);
        showErrorToast(resolveServiceErrorDetail(err, "Erro ao gerar descrição."));
        setFormData((prev) => ({
          ...prev,
          status_descricao_ia: 'FALHA',
        }));
      } finally {
        setIsGeneratingIA(false);
      }
    };

    const selectedProductType = safeProductTypes.find((type) => type.id === parseInt(formData.product_type_id));
    const attributeTemplates = selectedProductType ? selectedProductType.attribute_templates : [];
    const enrichmentSummary = formData?.log_enriquecimento_web?.resumo_aplicacao || {};
    const appliedFields = Array.isArray(enrichmentSummary?.aplicados) ? enrichmentSummary.aplicados : [];
    const ignoredFields = Array.isArray(enrichmentSummary?.ignorados) ? enrichmentSummary.ignorados : [];
    const appliedDetails = Array.isArray(enrichmentSummary?.campos_alterados_detalhe) ?
    enrichmentSummary.campos_alterados_detalhe :
    [];
    const webEnrichmentProcessing =
      isEnrichingWeb || ACTIVE_PROCESS_STATUSES.has(String(formData?.status_enriquecimento_web || '').toUpperCase());
    const titleGenerationProcessing =
      isGeneratingIA || ACTIVE_PROCESS_STATUSES.has(String(formData?.status_titulo_ia || '').toUpperCase());
    const descriptionGenerationProcessing =
      isGeneratingIA || ACTIVE_PROCESS_STATUSES.has(String(formData?.status_descricao_ia || '').toUpperCase());
    const contentGenerationProcessing = titleGenerationProcessing || descriptionGenerationProcessing;

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
                            {safeProductTypes.map((type) =>
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
                                        {safeProductTypes.map((type) =>
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
                                         <button type="button" className="btn-remove-dynamic-attribute" onClick={() => {
                    const { [key]: _, ...rest } = formData.dynamic_attributes;
                    setFormData((prev) => ({ ...prev, dynamic_attributes: rest }));
                    showInfoToast(`Atributo manual "${key}" removido.`);
                  }} title="Remover este atributo manual">🗑️</button>
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
                            <h3>{showAiFeatures ? 'Conteúdo Gerado com IA ou Básico' : 'Conteúdo Gerado'}</h3>
                            <div className="product-edit-content-toolbar">
                              <button type="button" onClick={_handleEnrichWeb} disabled={webEnrichmentProcessing || isNewProduct}>
                                {webEnrichmentProcessing ? 'Enriquecendo Web...' : showAiFeatures && usarIAEnriquecimentoWeb ? 'Enriquecer Web + IA' : 'Enriquecer Web'}
                              </button>
                              {showAiFeatures &&
                                <label className="product-edit-inline-toggle">
                                  <input
                                    type="checkbox"
                                    checked={usarIAEnriquecimentoWeb}
                                    onChange={(event) => {
                                      if (event.target.checked && !formData.product_type_id) {
                                        showWarningToast('Defina um tipo de produto antes de usar IA no enriquecimento web.');
                                        return;
                                      }
                                      setUsarIAEnriquecimentoWeb(event.target.checked);
                                    }}
                                    disabled={webEnrichmentProcessing || isNewProduct}
                                  />
                                  <span>Usar IA no enriquecimento web</span>
                                </label>
                              }
                            </div>
                            {!formData.product_type_id && showAiFeatures ?
                              <p className="warning-text">
                                Defina um tipo de produto para habilitar coleta de atributos relevantes com IA no enriquecimento e nas sugestões.
                              </p> :
                              null}
                            <div className="product-edit-content-toolbar product-edit-content-toolbar--generation">
                              <button
                                type="button"
                                onClick={handleGenerateTitles}
                                disabled={contentGenerationProcessing || isNewProduct}
                              >
                                {titleGenerationProcessing ?
                                  'Gerando...' :
                                  showAiFeatures && usarIAConteudo ?
                                    'Gerar títulos com IA' :
                                    'Gerar títulos no básico'}
                              </button>
                              <button
                                type="button"
                                onClick={handleGenerateDescription}
                                disabled={contentGenerationProcessing || isNewProduct}
                              >
                                {descriptionGenerationProcessing ?
                                  'Gerando...' :
                                  showAiFeatures && usarIAConteudo ?
                                    'Gerar descrição com IA' :
                                    'Gerar descrição no básico'}
                              </button>
                              {showAiFeatures &&
                                <label className="product-edit-inline-toggle">
                                  <input
                                    type="checkbox"
                                    checked={usarIAConteudo}
                                    onChange={(event) => setUsarIAConteudo(event.target.checked)}
                                    disabled={contentGenerationProcessing || isNewProduct}
                                  />
                                  <span>Usar IA</span>
                                </label>
                              }
                              <button
                                type="button"
                                className="btn-secondary"
                                onClick={handleOpenContentView}
                                disabled={isNewProduct}
                              >
                                Abrir tela dedicada
                              </button>
                            </div>
                            <ProductContentWorkspace
                              titles={formData.titulos_sugeridos}
                              description={formData.descricao_chat_api}
                              editable={true}
                              onTitleChange={(index, value) => {
                                setFormData((prev) => {
                                  const nextTitles = Array.isArray(prev.titulos_sugeridos) ? [...prev.titulos_sugeridos] : [];
                                  nextTitles[index] = value;
                                  return { ...prev, titulos_sugeridos: nextTitles };
                                });
                              }}
                              onDescriptionChange={(value) => setFormData((prev) => ({ ...prev, descricao_chat_api: value }))}
                            />
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
                    <button type="button" onClick={onClose} disabled={isLoading || webEnrichmentProcessing || contentGenerationProcessing || isSuggestingGemini} className="btn-secondary">Cancelar</button>
                    <button type="submit" disabled={isLoading || webEnrichmentProcessing || contentGenerationProcessing || isSuggestingGemini} className="btn-success">{isLoading ? 'Salvando...' : 'Salvar Produto'}</button>
                </div>
            </form>
          }
        </Modal>
        <NewProductTypeModal
          isOpen={isNewTypeModalOpen}
          onClose={handleCloseNewTypeModal}
          onCreated={handleNewTypeCreated} />
        
        <LoadingOverlay
          isOpen={isLoading || webEnrichmentProcessing || contentGenerationProcessing || isSuggestingGemini}
          message="Processando..." />
        
        </>);

  }

const BASE_PRODUCT_FIELDS = new Set([
  'nome_base',
  'nome_chat_api',
  'descricao_original',
  'descricao_curta_orig',
  'descricao_chat_api',
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
  'peso_gramas',
  'dimensoes_cm',
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
  descricao_chat_api: '',
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
  peso_gramas: '',
  dimensoes_cm: '',
  imagem_principal_url: '',
  imagens_secundarias_urls: [],
  fornecedor_id: '',
  product_type_id: '',
  dynamic_attributes: {},
  dados_brutos_web: {},
  titulos_sugeridos: [],
  ativo_marketplace: false,
  data_publicacao_marketplace: null,
  log_enriquecimento_web: { historico_mensagens: [] },
  status_enriquecimento_web: null,
  status_titulo_ia: null,
  status_descricao_ia: null,
};

const WEB_ENRICHMENT_POLL_INTERVAL_MS = 3000;
const WEB_ENRICHMENT_MAX_POLLS = 40;
const WEB_ENRICHMENT_TERMINAL_STATUSES = new Set([
  'CONCLUIDO',
  'CONCLUIDO_SUCESSO',
  'CONCLUIDO_COM_DADOS_PARCIAIS',
  'NENHUMA_FONTE_ENCONTRADA',
  'FALHA_API_EXTERNA',
  'FALHA_CONFIGURACAO_API_EXTERNA',
  'FALHA',
  'FALHOU',
  'NAO_APLICAVEL',
]);

export default ProductEditModal;
