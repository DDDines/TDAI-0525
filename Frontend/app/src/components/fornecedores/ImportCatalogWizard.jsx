/**
 * Module import catalog wizard.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as fornecedorService from '../../services/fornecedorService';
import productTypeService from '../../services/productTypeService';
import { normalizeDisplayText } from '../../utils/textNormalization';
import { extractErrorMessage } from '../../utils/errorDetails';
import {
  appendUniqueTimelineEntry,
  buildAttributeOption,
  buildImportStartPayload,
  buildTimelineLines,
  buildWizardResetKey,
  buildWizardViewModel,
  cloneFornecedorMapping,
  extractProductTypeAttributes,
  extractProductTypesCollection,
  formatCellValue,
  getPreviewImageSrc,
  getProductTypeOptionLabel,
  formatElapsed,
  normalizeImportStatus,
  normalizePreviewPayload,
  normalizePayloadStrings,
  resolveMappingEditorState,
  resolveManualMappingPreview,
  resolvePreviewImageIndex,
  resolveWizardPage,
  sanitizePositivePageInput,
} from './ImportCatalogWizard.helpers.js';
import LoadingPopup from '../common/LoadingPopup';
import ColumnMappingModal from '../common/ColumnMappingModal.jsx';
import PdfRegionSelector from '../common/PdfRegionSelector.jsx';
import Modal from '../common/Modal.jsx';
import LogoImg from '../../assets/Logo.png';
import './ImportCatalogWizard.css';

function timestamp() {return (

      new Date().toLocaleTimeString('pt-BR'));}

const DEFAULT_EXTRACTION_MODE = 'vision';

function ImportCatalogWizard(

  {
    fornecedor,
    productTypeId: initialProductTypeId,
    onClose,
    isOpen,
    onShowInfo,
    onShowFiles,
    shellTitle,
    shellSubtitle,
    embedded = false,
  }) {
    const defaultFornecedorMapping = useMemo(
      () => cloneFornecedorMapping(fornecedor?.default_column_mapping),
      [fornecedor?.default_column_mapping]
    );

    const [step, setStep] = useState('upload');
    const [selectedFile, setSelectedFile] = useState(null);
    const [fileId, setFileId] = useState(null);
    const [previewData, setPreviewData] = useState(null);
    const [previewError, setPreviewError] = useState('');
    const [startPage, setStartPage] = useState(1);
    const [pageCount, setPageCount] = useState(15);
    const [isLoading, setIsLoading] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState('');
    const [mapping, setMapping] = useState(defaultFornecedorMapping);
    const [showMappingModal, setShowMappingModal] = useState(false);
    const [showRegionModal, setShowRegionModal] = useState(false);
    const [pdfBytes, setPdfBytes] = useState(null);
    const [selectedBbox, setSelectedBbox] = useState(null);
    const [selectedBboxNorm, setSelectedBboxNorm] = useState(null);
    const [selectedPageForRegion, setSelectedPageForRegion] = useState(null);
    const [applyAllPages, setApplyAllPages] = useState(false);
    const [regionPreview, setRegionPreview] = useState(null);
    const [manualMappingRows, setManualMappingRows] = useState([]);
    const [showPagePicker, setShowPagePicker] = useState(false);
    const [selectedPreviewIndex, setSelectedPreviewIndex] = useState(null);
    const [productTypes, setProductTypes] = useState([]);
    const [productTypeId, setProductTypeId] = useState(initialProductTypeId || '');
    const [extractionMode, setExtractionMode] = useState(DEFAULT_EXTRACTION_MODE);
    const [fieldOptions, setFieldOptions] = useState(BASE_FIELD_OPTIONS);
    const [statusData, setStatusData] = useState(null);
    const [resultData, setResultData] = useState(null);
    const [error, setError] = useState('');
    const [regionError, setRegionError] = useState('');
    const [statusTimeline, setStatusTimeline] = useState([]);
    const [expectedPages, setExpectedPages] = useState(0);
    const [processingStartedAt, setProcessingStartedAt] = useState(null);
    const fileInputRef = useRef(null);
    const pollRunRef = useRef(0);
    const pollLoopActiveRef = useRef(false);
    const timelineSeenRef = useRef(new Set());
    const lastStatusSnapshotRef = useRef('');
    const terminalStatusAnnouncedRef = useRef(false);
    const openResetKeyRef = useRef(null);
    const navigate = useNavigate();

    const appendTimeline = useCallback((message) => {
      setStatusTimeline((prev) => {
        const nextState = appendUniqueTimelineEntry(prev, message, timestamp());
        if (nextState.appended) {
          timelineSeenRef.current.add(nextState.dedupeKey);
        }
        return nextState.entries;
      });
    }, []);

    useEffect(() => {
      if (!isOpen) {
        openResetKeyRef.current = null;
        return;
      }
      const resetKey = buildWizardResetKey(fornecedor?.id, initialProductTypeId);
      if (openResetKeyRef.current === resetKey) return;
      openResetKeyRef.current = resetKey;

      setStep('upload');
      setSelectedFile(null);
      setFileId(null);
      setPreviewData(null);
      setPreviewError('');
      setStartPage(1);
      setPageCount(15);
      setShowRegionModal(false);
      setPdfBytes(null);
      setSelectedBbox(null);
      setSelectedBboxNorm(null);
      setSelectedPageForRegion(null);
      setApplyAllPages(false);
      setRegionPreview(null);
      setManualMappingRows([]);
      setShowPagePicker(false);
      setSelectedPreviewIndex(null);
      setMapping({ ...defaultFornecedorMapping });
      setProductTypeId(initialProductTypeId || '');
      setExtractionMode(DEFAULT_EXTRACTION_MODE);
      setStatusData(null);
      setResultData(null);
      setError('');
      setRegionError('');
      setStatusTimeline([]);
      timelineSeenRef.current = new Set();
      lastStatusSnapshotRef.current = '';
      terminalStatusAnnouncedRef.current = false;
    }, [isOpen, fornecedor?.id, initialProductTypeId, defaultFornecedorMapping]);

    useEffect(() => {
      if (!isOpen) return;
      const loadProductTypes = async () => {
        try {
          const data = await productTypeService.getProductTypes({ limit: 100 });
          setProductTypes(extractProductTypesCollection(data));
        } catch (err) {
          console.error('Erro ao carregar tipos de produto:', err);
          setProductTypes([]);
        }
      };
      loadProductTypes();
    }, [isOpen]);

    useEffect(() => {
      if (!isOpen) {
        pollRunRef.current += 1;
        pollLoopActiveRef.current = false;
        timelineSeenRef.current = new Set();
        lastStatusSnapshotRef.current = '';
        terminalStatusAnnouncedRef.current = false;
      }
    }, [isOpen]);

    useEffect(() => {
      const refreshFieldOptionsByProductType = async () => {
        const base = [...BASE_FIELD_OPTIONS];
        if (!productTypeId) {
          setFieldOptions(base);
          return;
        }
        try {
          const details = await productTypeService.getProductTypeDetails(productTypeId);
          const attrs = extractProductTypeAttributes(details);
          const attrOptions = attrs.map((attribute) => buildAttributeOption(attribute));
          setFieldOptions([...base, ...attrOptions]);
        } catch (err) {
          console.warn('Falha ao carregar atributos do tipo de produto:', err);
          setFieldOptions(base);
        }
      };
      refreshFieldOptionsByProductType();
    }, [productTypeId]);

    const previewImages = useMemo(() => previewData?.previewImages || [], [previewData]);
    const sampleRows = useMemo(
      () => Array.isArray(previewData?.sampleRows) ? previewData.sampleRows : [],
      [previewData]
    );

    const handleProductTypeChange = (nextValue) => {
      setProductTypeId(nextValue);
    };

    const handleFileChange = (event) => {
      const file = event.target.files?.[0];
      if (!file) return;
      setSelectedFile(file);
      setPreviewData(null);
      setPreviewError('');
      setStep('upload');
      setStatusTimeline([]);
    };

    const handleOpenFilePicker = () => {
      fileInputRef.current?.click();
    };

    const handlePreview = async () => {
      setIsLoading(true);
      setLoadingMessage('Gerando preview...');
      setPreviewError('');
      appendTimeline('Iniciando geração de preview do arquivo.');
      try {
        const previewRaw = await fornecedorService.previewCatalogo(
          selectedFile,
          pageCount,
          startPage,
          fornecedor.id
        );
        const preview = normalizePreviewPayload(previewRaw);
        if (preview.error) {
          setPreviewError(preview.error);
          setPreviewData(null);
          appendTimeline(`Falha no preview: ${preview.error}`);
          return;
        }
        setFileId(preview.fileId);
        setPreviewData(preview);
        setStep('preview');
        setSelectedPageForRegion(startPage);
        setSelectedPreviewIndex(null);
        appendTimeline(
          `Preview gerado com sucesso. File ID ${preview.fileId}. ${preview.numPages} páginas detectadas.`
        );
        if (preview.previewImages.length > 1) {
          setShowPagePicker(true);
        }
      } catch (err) {
        const detail = extractErrorMessage(err, 'Falha ao gerar preview.');
        setPreviewError(detail);
        appendTimeline(`Erro ao gerar preview: ${detail}`);
      } finally {
        setIsLoading(false);
        setLoadingMessage('');
      }
    };

    const launchRegionSelector = async (pageToUse) => {
      const buffer = await selectedFile.arrayBuffer();
      setPdfBytes(new Uint8Array(buffer));
      setSelectedPageForRegion(pageToUse);
      const previewIndex = resolvePreviewImageIndex(previewImages.length, pageToUse, startPage);
      if (previewIndex !== null) {
        setSelectedPreviewIndex(previewIndex);
      }
      setSelectedBbox(null);
      setRegionPreview(null);
      setShowRegionModal(true);
      appendTimeline(`Abrindo seletor de região para a página ${pageToUse}.`);
    };

    const handleOpenRegionSelector = async () => {
      if (previewImages.length > 1) {
        setShowPagePicker(true);
        return;
      }
      await launchRegionSelector(resolveWizardPage(selectedPageForRegion, startPage));
    };

    const handleRegionSelect = async ({
      page,
      bbox,
      bboxNorm,
      canvasWidth,
      canvasHeight,
      applyAllPages: applyAll
    }) => {
      setSelectedPageForRegion(page);
      setSelectedBbox(bbox);
      setSelectedBboxNorm(bboxNorm);
      setApplyAllPages(Boolean(applyAll));
      setShowRegionModal(false);
      setShowPagePicker(false);
      setIsLoading(true);
      setLoadingMessage('Extraindo região selecionada...');
      appendTimeline(`Região selecionada na página ${page}. Iniciando extração de dados.`);
      try {
        const data = await fornecedorService.selecionarRegiaoProduto({
          fileId,
          pageNumber: page,
          bbox,
          bboxNorm,
          canvasWidth,
          canvasHeight
        });
        const produtosArr = Array.isArray(data?.produtos) ? data.produtos : [];
        const previewHeaders = data?.preview_headers || [];
        const previewRows = data?.preview_rows || [];

        if (previewHeaders.length > 0 && previewRows.length > 0) {
          setRegionPreview({ headers: previewHeaders, rows: previewRows });
          setManualMappingRows(previewRows);
          setShowMappingModal(true);
          appendTimeline(`Extração concluída: ${previewRows.length} linhas de preview prontas para mapeamento.`);
          return;
        }

        if (produtosArr.length > 0) {
          const headers = Object.keys(produtosArr[0]);
          const rows = produtosArr.slice(0, 5);
          setRegionPreview({ headers, rows });
          setManualMappingRows(rows);
          setShowMappingModal(true);
          appendTimeline(`Extração concluída: ${produtosArr.length} itens detectados na região.`);
          return;
        }

        setRegionPreview({ headers: FALLBACK_HEADERS, rows: [] });
        setManualMappingRows([]);
        setPreviewError('Nenhum dado extraído da região selecionada.');
        appendTimeline('Nenhum dado útil encontrado na região selecionada.');
      } catch (err) {
        const detail = extractErrorMessage(err, 'Falha ao extrair região.');
        setRegionError(detail);
        appendTimeline(`Erro ao extrair região: ${detail}`);
      } finally {
        setIsLoading(false);
        setLoadingMessage('');
      }
    };

    const openManualMapping = () => {
      const { headers, rows } = resolveMappingEditorState({
        regionPreview,
        manualMappingRows,
        fallbackHeaders: FALLBACK_HEADERS,
      });
      setRegionPreview({ headers, rows });
      setShowMappingModal(true);
      appendTimeline('Abrindo mapeamento manual de colunas.');
    };

    const handleConfirmMapping = async (map) => {
      const nextMapping = cloneFornecedorMapping(map);
      setMapping(nextMapping);
      appendTimeline(`Mapeamento atualizado com ${Object.keys(nextMapping).length} coluna(s).`);
      try {
        if (fornecedor?.id) {
          await fornecedorService.setFornecedorMapping(fornecedor.id, nextMapping);
          appendTimeline('Mapeamento salvo no fornecedor com sucesso.');
        }
      } catch (err) {
        console.warn('Falha ao salvar mapeamento no fornecedor:', err);
        appendTimeline('Falha ao salvar mapeamento padrão no fornecedor.');
      }
      setShowMappingModal(false);
    };

    const pollStatus = async (id, runId) => {
      pollLoopActiveRef.current = true;

      let keepPolling = true;
      let lastProgressAt = Date.now();
      let terminalDetectedAt = null;
      let terminalAttempts = 0;
      let terminalStableCount = 0;
      let lastTerminalSnapshot = '';
      let lastObservedStatus = '';
      let lastObservedPagesProcessed = 0;
      let lastObservedPagesTotal = 0;
      try {
        while (keepPolling && pollRunRef.current === runId) {
          const noProgressElapsedMs = Date.now() - lastProgressAt;
          if (noProgressElapsedMs >= MAX_ABSOLUTE_POLL_MS) {
            const hardTimeoutMessage =
            'Monitoramento encerrado por inatividade de progresso. O processamento pode continuar no backend; atualize em instantes para obter o resultado final.';
            setError(hardTimeoutMessage);
            appendTimeline(hardTimeoutMessage);
            break;
          }

          try {
            const statusRaw = await fornecedorService.getImportacaoStatus(id);
            const status = normalizeImportStatus(statusRaw, expectedPages);
            setStatusData(status);

            const pagesProcessed = status.pages_processed;
            const pagesTotal = status.total_pages;
            const hasStatusChanged = status.status !== lastObservedStatus;
            const hasPagesAdvanced = pagesProcessed > lastObservedPagesProcessed;
            const hasPageTotalChanged = pagesTotal !== lastObservedPagesTotal;
            if (hasStatusChanged || hasPagesAdvanced || hasPageTotalChanged) {
              lastProgressAt = Date.now();
            }
            lastObservedStatus = status.status;
            lastObservedPagesProcessed = pagesProcessed;
            lastObservedPagesTotal = pagesTotal;

            const terminalStatuses = new Set(['IMPORTED', 'DONE', 'FAILED', 'PARTIAL']);
            const isTerminal = Boolean(status?.status && terminalStatuses.has(status.status));
            if (!isTerminal) {
              const statusSnapshot = `${status.status}|${pagesProcessed}|${pagesTotal}`;
              if (statusSnapshot !== lastStatusSnapshotRef.current) {
                appendTimeline(`Status: ${status.status} | Páginas: ${pagesProcessed}/${pagesTotal}`);
                lastStatusSnapshotRef.current = statusSnapshot;
              }
            } else if (!terminalStatusAnnouncedRef.current) {
              appendTimeline(`Status: ${status.status} | Páginas: ${pagesProcessed}/${pagesTotal}`);
              terminalStatusAnnouncedRef.current = true;
            }

            if (status?.status && terminalStatuses.has(status.status)) {
              const terminalSnapshot = `${status.status}|${pagesProcessed}|${pagesTotal}`;
              if (terminalSnapshot === lastTerminalSnapshot) {
                terminalStableCount += 1;
              } else {
                lastTerminalSnapshot = terminalSnapshot;
                terminalStableCount = 1;
              }

              if (!terminalDetectedAt) {
                terminalDetectedAt = Date.now();
                appendTimeline(
                  `Processamento finalizado com status ${status.status}. Buscando resultado final...`
                );
              }
              terminalAttempts += 1;

              const elapsedWaitingMs = Date.now() - terminalDetectedAt;
              const statusSignalsReady = Boolean(status?.result_ready);
              const timeoutExceeded =
              elapsedWaitingMs >= MAX_RESULT_WAIT_MS ||
              terminalAttempts >= MAX_RESULT_ATTEMPTS ||
              terminalStableCount >= MAX_RESULT_ATTEMPTS;

              let shouldFetchResult = true;
              const probeResultWhenNotReady = terminalAttempts % 5 === 0;
              if (!statusSignalsReady && !timeoutExceeded && !probeResultWhenNotReady) {
                shouldFetchResult = false;
              }

              if (!statusSignalsReady && timeoutExceeded) {
                const timeoutMessage =
                'Processamento concluído, mas o resultado final ainda não ficou disponível. Tente atualizar em instantes.';
                setError(timeoutMessage);
                appendTimeline(timeoutMessage);
                keepPolling = false;
                shouldFetchResult = false;
              }

              if (shouldFetchResult && keepPolling) {
                try {
                  const res = await fornecedorService.getImportacaoResult(id);
                  if (res?.ready === false) {
                    if (timeoutExceeded) {
                      const timeoutMessage =
                      'Resultado ainda pendente após o tempo limite de espera. Tente atualizar em instantes.';
                      setError(timeoutMessage);
                      appendTimeline(timeoutMessage);
                      keepPolling = false;
                    } else {
                      appendTimeline('Resultado final ainda não disponível. Continuando monitoramento...');
                      keepPolling = true;
                    }
                  } else {
                    const normalizedRes = normalizePayloadStrings(res);
                    setResultData(normalizedRes);
                    appendTimeline('Resultado final carregado.');
                    keepPolling = false;
                    if ((normalizedRes?.quarantine_non_critical?.length ?? 0) > 0) {
                      navigate(`/importacoes/${id}/quarentena`);
                    }
                  }
                } catch (err) {
                  const detail = normalizeDisplayText(
                    extractErrorMessage(err, 'Falha ao obter resultado final da importação.')
                  );
                  const waitingResult =
                  /ainda n[aã]o dispon[ií]vel|not available|still processing/i.test(detail);
                  if (waitingResult && !timeoutExceeded) {
                    appendTimeline('Resultado final ainda não disponível. Continuando monitoramento...');
                    keepPolling = true;
                  } else {
                    console.error('Erro ao obter resultado final:', err);
                    setError(detail);
                    appendTimeline(`Erro ao obter resultado final: ${detail}`);
                    keepPolling = false;
                  }
                }
              }
            }
          } catch (err) {
            console.error('Erro ao consultar status:', err);
            const detail = extractErrorMessage(err, 'Falha ao consultar status da importação.');
            setError(detail);
            appendTimeline(`Erro de monitoramento: ${detail}`);
            keepPolling = false;
          }

          if (keepPolling && pollRunRef.current === runId) {
            await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
          }
        }
      } finally {
        if (pollRunRef.current === runId) {
          pollLoopActiveRef.current = false;
        }
      }
    };

    const handleQuickStart = async () => {
      setIsLoading(true);
      setLoadingMessage('Carregando arquivo...');
      setPreviewError('');
      appendTimeline('Carregando arquivo para processamento direto.');
      let uploadedFileId;
      try {
        const previewRaw = await fornecedorService.previewCatalogo(
          selectedFile,
          pageCount,
          startPage,
          fornecedor.id
        );
        const preview = normalizePreviewPayload(previewRaw);
        if (preview.error) {
          setPreviewError(preview.error);
          appendTimeline(`Falha ao carregar arquivo: ${preview.error}`);
          return;
        }
        uploadedFileId = preview.fileId;
        setFileId(preview.fileId);
        setPreviewData(preview);
        appendTimeline(`Arquivo carregado. File ID ${preview.fileId}. Iniciando processamento...`);
      } catch (err) {
        const detail = extractErrorMessage(err, 'Falha ao carregar arquivo.');
        setPreviewError(detail);
        appendTimeline(`Erro ao carregar arquivo: ${detail}`);
        return;
      } finally {
        setIsLoading(false);
        setLoadingMessage('');
      }
      await startImport(uploadedFileId);
    };

    const startImport = async (fileIdOverride) => {
      const effectiveFileId = fileIdOverride ?? fileId;
      setIsLoading(true);
      setLoadingMessage('Iniciando processamento...');
      setError('');
      setStatusData(null);
      setResultData(null);
      setStatusTimeline([]);
      timelineSeenRef.current = new Set();
      lastStatusSnapshotRef.current = '';
      terminalStatusAnnouncedRef.current = false;
      pollLoopActiveRef.current = false;
      appendTimeline('Solicitação de processamento enviada para o backend.');
      try {
        const { estimatedTotal, payload } = buildImportStartPayload({
          fileId: effectiveFileId,
          productTypeId,
          fornecedorId: fornecedor.id,
          mapping,
          selectedPageForRegion,
          startPage,
          applyAllPages,
          previewData,
          selectedBboxNorm,
          selectedBbox,
          extractionMode,
        });
        setExpectedPages(estimatedTotal);
        setProcessingStartedAt(Date.now());
        setStatusData((prev) => ({
          status: 'PROCESSING',
          pages_processed: 0,
          total_pages: prev?.total_pages || estimatedTotal
        }));
        setStep('processing');
        appendTimeline('Importação iniciada. Acompanhando progresso em tempo real.');

        const runId = Date.now();
        pollRunRef.current = runId;
        pollStatus(fileId, runId);

        await fornecedorService.finalizarImportacaoCatalogo(payload);
      } catch (err) {
        pollRunRef.current += 1;
        setStep('preview');
        const detail = normalizeDisplayText(
          extractErrorMessage(err, 'Falha ao iniciar processamento.')
        );
        setError(detail);
        appendTimeline(`Erro ao iniciar processamento: ${detail}`);
      } finally {
        setIsLoading(false);
        setLoadingMessage('');
      }
    };

    if (!isOpen) return null;

    const { headers: mappedHeaders, rows: mappedRows } = resolveManualMappingPreview({
      regionPreview,
      previewData,
      manualMappingRows,
      fallbackHeaders: FALLBACK_HEADERS,
    });
    const currentStepIndex = Math.max(0, STEP_FLOW.indexOf(step));
    const liveTimelineLines = buildTimelineLines(statusTimeline);
    const {
      acceptedQualityAvg,
      canStartWithMapping,
      criticalErrorsCount,
      createdCount,
      discardedNonCritical,
      elapsedSec,
      etaLabel,
      failedMessage,
      hasPrimaryMapping,
      loadingPopupMessage,
      pagesProcessed,
      pagesTotalLabel,
      processingActive,
      processingStatusLabel,
      previewFileIdLabel,
      progressPct,
      quarantineCount,
      quarantineQualityAvg,
      regionSelectionPage,
      resultPagesProcessed,
      resultPagesTotal,
      resultOutputHeadline,
      resultOutputLabel,
      resultOutputPages,
      resultTopReasons,
      selectedScopeLabel,
      showLoadingPopup,
      showFailedResultMessage,
      showPartialWarning,
      showResultStats,
      updatedCount,
      formatExt,
    } = buildWizardViewModel({
      resultData,
      statusData,
      expectedPages,
      step,
      error,
      processingStartedAt,
      isLoading,
      loadingMessage,
      applyAllPages,
      selectedPageForRegion,
      startPage,
      fileId,
      mapping,
      productTypeId,
      selectedFile,
    });

    if (!isOpen) {
      return null;
    }

    const fornecedorNome = String(fornecedor?.nome || 'Fornecedor').trim() || 'Fornecedor';
    const fornecedorSite = normalizeDisplayText(fornecedor?.site_url || '');
    const modalTitle = shellTitle || 'Importar Catálogo';
    const modalSubtitle = shellSubtitle ||
      (fornecedorSite
        ? `${fornecedorNome} conectado em ${fornecedorSite}. Revise o preview, mapeie colunas e acompanhe o processamento sem sair do fluxo.`
        : `${fornecedorNome}. Revise o preview, mapeie colunas e acompanhe o processamento sem sair do fluxo.`);
    const showFornecedorTabs = Boolean(onShowInfo || onShowFiles);

    const wizardBody = (
      <div className={`wizard-container ${embedded ? 'wizard-container--embedded' : ''}`.trim()} aria-live="polite">
      {showFornecedorTabs && !embedded ? (
        <div className="tab-navigation fornecedor-modal-tabs wizard-provider-tabs">
          <button type="button" onClick={onShowInfo}>
            Info
          </button>
          <button type="button" className="active">
            Importar Catálogo
          </button>
          <button type="button" onClick={onShowFiles}>
            Arquivos
          </button>
        </div>
      ) : null}
      <div className="wizard-stepper" role="list" aria-label="Etapas da importa\u00e7\u00e3o">
        {STEP_FLOW.map((stepKey, index) => {
            const isCurrent = step === stepKey;
            const isDone = currentStepIndex > index;
            return (
              <div
                key={stepKey}
                role="listitem"
                className={`wizard-step-item ${isCurrent ? 'is-current' : ''} ${isDone ? 'is-done' : ''}`}>
                
              <span className="wizard-step-index">{index + 1}</span>
              <span className="wizard-step-label">{STEP_LABELS[stepKey]}</span>
            </div>);

          })}
      </div>

      {error &&
        <p className="wizard-error-banner">{error}</p>
        }

      {step === 'upload' &&
        <section className="wizard-panel">
          <header className="wizard-panel-header">
            <h3>Passo 1: Enviar catálogo</h3>
            <p>Selecione o arquivo do catálogo para começar.</p>
          </header>

          <div className="wizard-upload-block">
            <label htmlFor="wizard-file-input" className="wizard-file-label">
              Arquivo do catálogo (PDF, XLSX ou CSV)
            </label>
            <input
              ref={fileInputRef}
              id="wizard-file-input"
              type="file"
              accept=".pdf,.xlsx,.xls,.csv"
              onChange={handleFileChange}
              aria-label="Arquivo de catálogo"
              className="wizard-file-input-hidden"
            />
            <div className="wizard-file-picker">
              <button type="button" className="wizard-file-trigger" onClick={handleOpenFilePicker}>
                Escolher arquivo
              </button>
              <span className={`wizard-file-name ${selectedFile ? 'is-selected' : ''}`}>
                {selectedFile ? selectedFile.name : 'Nenhum arquivo selecionado'}
              </span>
            </div>
          </div>

          {selectedFile && (() => {
            const isPdf = selectedFile.name.toLowerCase().endsWith('.pdf');
            const isDirectMode = extractionMode === 'vision' || extractionMode === 'ia';
            return (
              <>
                {isPdf ? (
                  <>
                    <div className="wizard-mode-selector">
                      <p className="wizard-mode-selector-label">Como o sistema vai ler o PDF?</p>
                      <p className="wizard-mode-selector-hint">
                        Escolha o método de extração. O modo <strong>Visão IA</strong> funciona com qualquer PDF — catálogos com fotos, tabelas, texto ou documentos escaneados.
                      </p>
                      <div className="wizard-mode-cards">
                        {[
                          {
                            value: 'vision',
                            icon: '✦',
                            title: 'Visão IA — GPT-4o',
                            desc: 'Analisa cada página como imagem com IA avançada.',
                            hint: 'Qualquer PDF — fotos, tabelas mistas, layouts visuais ou documentos escaneados.',
                            recommended: true,
                            costLabel: '~$0,01/pág',
                            isFree: false,
                          },
                          {
                            value: 'table',
                            icon: '⊞',
                            title: 'Tabela',
                            desc: 'Extrai tabelas estruturadas diretamente do texto do PDF.',
                            hint: 'PDFs gerados por software com tabelas bem definidas, como exportações de ERP.',
                            recommended: false,
                            costLabel: null,
                            isFree: true,
                          },
                          {
                            value: 'ocr',
                            icon: '⊙',
                            title: 'OCR',
                            desc: 'Reconhece texto em PDFs sem camada de texto, sem enviar dados para a internet.',
                            hint: 'Documentos físicos digitalizados (escaneados) onde o texto não é selecionável.',
                            recommended: false,
                            costLabel: null,
                            isFree: true,
                          },
                          {
                            value: 'ia',
                            icon: '⚡',
                            title: 'IA Local',
                            desc: 'Usa modelo de linguagem local para interpretar o conteúdo.',
                            hint: 'Quando prefere processar sem enviar dados para fora ou não há conexão.',
                            recommended: false,
                            costLabel: 'Consome créditos de IA',
                            isFree: false,
                          },
                        ].map((mode) => (
                          <button
                            key={mode.value}
                            type="button"
                            className={[
                              'wizard-mode-card',
                              extractionMode === mode.value ? 'is-selected' : '',
                            ].filter(Boolean).join(' ')}
                            onClick={() => setExtractionMode(mode.value)}
                            aria-pressed={extractionMode === mode.value}
                          >
                            <div className="wizard-mode-card-head">
                              <span className="wizard-mode-card-icon" aria-hidden="true">{mode.icon}</span>
                              <span className="wizard-mode-card-title">{mode.title}</span>
                              {mode.recommended ? (
                                <span className="wizard-mode-badge">Recomendado</span>
                              ) : null}
                              {mode.isFree ? (
                                <span className="wizard-mode-badge wizard-mode-badge--free">Gratuito</span>
                              ) : null}
                            </div>
                            <p className="wizard-mode-card-desc">{mode.desc}</p>
                            <p className="wizard-mode-card-hint">Ideal para: {mode.hint}</p>
                            {mode.costLabel ? (
                              <p className="wizard-mode-card-cost">{mode.costLabel}</p>
                            ) : null}
                          </button>
                        ))}
                      </div>
                    </div>

                    {isDirectMode ? (
                      <div className="wizard-inline-fields wizard-quick-type-row">
                        <label htmlFor="wizard-upload-product-type">
                          Tipo de Produto
                          <select
                            id="wizard-upload-product-type"
                            value={productTypeId}
                            onChange={(e) => handleProductTypeChange(e.target.value)}
                            className="wizard-inline-select">
                            <option value="">Selecione...</option>
                            {productTypes.map((pt) => {
                              const value = pt.id;
                              if (value === null || value === undefined) return null;
                              return (
                                <option key={value} value={value}>
                                  {getProductTypeOptionLabel(pt)}
                                </option>
                              );
                            })}
                          </select>
                        </label>
                      </div>
                    ) : (
                      <div className="wizard-inline-fields">
                        <label htmlFor="wizard-start-page">
                          Página inicial
                          <input
                            id="wizard-start-page"
                            type="number"
                            min="1"
                            value={startPage}
                            onChange={(e) => setStartPage(sanitizePositivePageInput(e.target.value))}
                            className="wizard-small-number-input" />
                        </label>
                        <label htmlFor="wizard-page-count">
                          Quantidade de páginas para o preview
                          <input
                            id="wizard-page-count"
                            type="number"
                            min="1"
                            value={pageCount}
                            onChange={(e) => setPageCount(sanitizePositivePageInput(e.target.value))}
                            className="wizard-small-number-input" />
                        </label>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="wizard-file-type-hint">
                    Planilha detectada — o sistema vai gerar uma prévia das colunas para você confirmar o mapeamento antes de importar.
                  </p>
                )}

                <div className="wizard-actions-row">
                  {isPdf && isDirectMode ? (
                    <button
                      onClick={handleQuickStart}
                      disabled={!productTypeId || isLoading}
                      type="button"
                    >
                      Iniciar Importação
                    </button>
                  ) : (
                    <button onClick={handlePreview} disabled={isLoading} type="button">
                      Gerar Preview
                    </button>
                  )}
                </div>
                {isPdf && isDirectMode && !productTypeId && (
                  <p className="wizard-warning-text">Selecione o tipo de produto para iniciar a importação.</p>
                )}
              </>
            );
          })()}

          {previewError && <p className="wizard-error-text">{previewError}</p>}
        </section>
        }

      {step === 'preview' && previewData &&
        <section className="wizard-panel">
          <header className="wizard-panel-header">
            <div className="wp2-header-row">
              <div>
                <h3>Revisar e mapear dados</h3>
                <p>Arquivo #{previewFileIdLabel} &middot; {previewData.numPages} página(s)</p>
              </div>
              <span className="wp2-scope-badge">Escopo atual: {selectedScopeLabel}</span>
            </div>
          </header>

          {!previewData.headers && !previewImages.length &&
            <p className="wizard-warning-text">Nenhum preview disponível. Verifique se o arquivo é suportado.</p>
          }

          <div className="wp2-body">

            {/* ── Full-width: columns table ── */}
            {previewData.headers && sampleRows.length > 0 &&
              <div className="wp2-preview-section">
                <p className="wp2-section-label">Colunas detectadas</p>
                <div className="wizard-table-wrap">
                  <table className="preview-table">
                    <thead>
                      <tr>{previewData.headers.map((h) => <th key={h}>{h}</th>)}</tr>
                    </thead>
                    <tbody>
                      {sampleRows.slice(0, 5).map((row, idx) =>
                        <tr key={idx}>{previewData.headers.map((h) => <td key={h}>{formatCellValue(row?.[h])}</td>)}</tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            }

            {/* ── Image + config side by side ── */}
            <div className="wp2-img-config-row">

              {previewImages.length > 0 &&
                <div className="wp2-img-col">
                  <p className="wp2-section-label">
                    Prévia de páginas
                    <span className="wp2-count-pill">
                      {selectedPreviewIndex != null ? 1 : previewImages.length} pág.
                    </span>
                  </p>
                  <div className="wp2-doc-grid">
                    {(selectedPreviewIndex != null ? [previewImages[selectedPreviewIndex]] : previewImages).map((img, idx) => {
                      const absoluteIdx = selectedPreviewIndex != null ? selectedPreviewIndex : idx;
                      const pageNumber = startPage + absoluteIdx;
                      const src = getPreviewImageSrc(img);
                      if (!src) return null;
                      return (
                        <div key={`${pageNumber}-${idx}`} className="wp2-doc-card">
                          <div className="wp2-doc-img-wrap">
                            <img src={src} alt={`Página ${pageNumber}`} className="wp2-doc-img" />
                            <span className="wp2-doc-page-badge">pág. {pageNumber}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              }

              {/* ── Config column ── */}
              <div className="wp2-config-col">

              <div className="wp2-config-card">
                <p className="wp2-card-title">Extração e Mapeamento</p>
                <p className="wp2-card-desc">Ajuste a região da tabela e o mapeamento de colunas.</p>
                <div className="wp2-btn-stack">
                  <button type="button" className="wp2-tool-btn" onClick={() => setShowMappingModal(true)}>
                    <svg className="wp2-btn-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M3 5h14M3 10h10M3 15h6" strokeLinecap="round"/>
                      <path d="M15 13l2 2 2-2M17 11v4" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    Definir mapeamento
                  </button>
                  <button type="button" className="wp2-tool-btn" onClick={handleOpenRegionSelector} disabled={!fileId}>
                    <svg className="wp2-btn-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <rect x="3" y="3" width="14" height="14" rx="2"/>
                      <path d="M7 7h6v6H7z" fill="currentColor" opacity="0.25"/>
                      <path d="M7 7h6v6H7z" strokeLinecap="round"/>
                    </svg>
                    Selecionar região
                  </button>
                  <button type="button" className="wp2-tool-btn wp2-tool-btn--ghost" onClick={openManualMapping}>
                    <svg className="wp2-btn-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8">
                      <path d="M4 13.5V16h2.5l7-7L11 6.5l-7 7z" strokeLinejoin="round"/>
                      <path d="M13.5 4l2.5 2.5" strokeLinecap="round"/>
                    </svg>
                    Mapear manualmente
                  </button>
                </div>
              </div>

              <div className="wp2-config-card wp2-config-card--primary">
                <p className="wp2-card-title">Configuração da Importação</p>

                <div className="wp2-inline-row">
                  <div className="wp2-field wp2-field--small">
                    <label className="wp2-field-label" htmlFor="wizard-page-select">Página para seleção</label>
                    <input
                      id="wizard-page-select"
                      type="number"
                      min="1"
                      value={regionSelectionPage}
                      onChange={(e) => {
                        const val = sanitizePositivePageInput(e.target.value);
                        setSelectedPageForRegion(val);
                      }}
                      className="wp2-num-input" />
                  </div>
                  <div className="wp2-field wp2-field--grow">
                    <label className="wp2-field-label" htmlFor="wizard-product-type">Tipo de Produto</label>
                    <select
                      id="wizard-product-type"
                      value={productTypeId}
                      onChange={(e) => handleProductTypeChange(e.target.value)}
                      className="wp2-select">
                      <option value="">Selecione...</option>
                      {productTypes.map((pt) => {
                        const value = pt.id;
                        if (value === null || value === undefined) return null;
                        const label = getProductTypeOptionLabel(pt);
                        return <option key={value} value={value}>{label}</option>;
                      })}
                    </select>
                  </div>
                </div>

                <label className="wp2-checkbox-row" htmlFor="wizard-apply-all">
                  <input
                    id="wizard-apply-all"
                    type="checkbox"
                    checked={applyAllPages}
                    onChange={(e) => setApplyAllPages(e.target.checked)}
                    className="wizard-inline-checkbox" />
                  Aplicar região em todas as páginas
                </label>

                <button type="button" className="wp2-start-btn" onClick={() => startImport()} disabled={!canStartWithMapping}>
                  Iniciar Processamento
                </button>

                {!productTypeId &&
                  <p className="wizard-warning-text">Selecione o tipo de produto para habilitar a importação.</p>
                }
                {productTypeId && !hasPrimaryMapping &&
                  <p className="wizard-warning-text">
                    Defina ao menos uma coluna como <strong>SKU + Nome (Auto)</strong>, <strong>Nome Base</strong> ou <strong>SKU</strong>.
                  </p>
                }
              </div>

            </div>{/* end wp2-config-col */}
          </div>{/* end wp2-img-config-row */}

          {/* ── Full-width: region preview ── */}
          {regionPreview?.headers &&
            <div className="wp2-preview-section">
              <p className="wp2-section-label">Prévia da região selecionada</p>
              <div className="wizard-table-wrap">
                <table className="preview-table">
                  <thead>
                    <tr>{regionPreview.headers.map((h) => <th key={h}>{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {regionPreview.rows.map((row, idx) =>
                      <tr key={idx}>{regionPreview.headers.map((h) => <td key={h}>{formatCellValue(row?.[h])}</td>)}</tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          }

          {regionError && <p className="wizard-error-text">{regionError}</p>}

          </div>{/* end wp2-body */}

          <ColumnMappingModal
            isOpen={showMappingModal}
            onClose={() => setShowMappingModal(false)}
            headers={mappedHeaders}
            rows={mappedRows}
            fieldOptions={fieldOptions}
            productTypes={productTypes}
            productTypeId={productTypeId}
            onProductTypeChange={handleProductTypeChange}
            initialMapping={mapping}
            onConfirm={handleConfirmMapping} />

        </section>
        }

      {step === 'processing' &&
        <section className="wizard-panel">
          <header className="wizard-panel-header">
            <h3>Passo 3: Processando importação</h3>
            <p>Acompanhe o status em tempo real e revise o resumo final ao concluir.</p>
          </header>

          <div className="wizard-processing-card">
            <div className="wizard-processing-header">
              <img src={LogoImg} alt="CatalogAI" className="wizard-processing-logo" />
              <div>
                <strong>Status:</strong> {processingStatusLabel}
                <div>{`Páginas: ${pagesProcessed}/${pagesTotalLabel}`}</div>
                <div>{`Tempo decorrido: ${elapsedSec}s`}</div>
              </div>
              {processingActive ? <div className="wizard-processing-spinner" /> : <div className="wizard-processing-done">OK</div>}
            </div>

            <div className="wizard-progress-track" role="progressbar" aria-valuenow={progressPct} aria-valuemin={0} aria-valuemax={100}>
              <div className="wizard-progress-fill" style={{ width: `${progressPct}%` }} />
            </div>
            <small>{progressPct}% concluído</small>

            <div className="wizard-live-log" aria-live="polite">
              <h4>Atualizações em tempo real</h4>
              <ul>
                  {liveTimelineLines.map((line, idx) =>
                <li key={`${line}-${idx}`}>{line}</li>
                )}
                </ul>
            </div>
          </div>

          {resultData &&
          <div className="wizard-result-block">
              <h4>Resultado</h4>
              {resultOutputLabel &&
            <p><strong>{resultOutputLabel}</strong></p>
            }
              {resultOutputHeadline &&
            <p>{resultOutputHeadline}</p>
            }
              {showFailedResultMessage &&
            <p className="wizard-result-error">
                  Falha: {failedMessage}
                </p>
            }
              {showPartialWarning &&
            <p className="wizard-result-warning">
                  Importação concluída com alertas: há erros críticos que exigem revisão.
                </p>
            }
              {showResultStats &&
            <ul className="wizard-result-list">
                  <li>Criados: {createdCount}</li>
                  <li>Atualizados: {updatedCount}</li>
                  <li>Erros críticos: {criticalErrorsCount}</li>
                  <li>Descartes não críticos: {discardedNonCritical}</li>
                  <li>Quarentena (não importados): {quarantineCount}</li>
                  <li>
                    Páginas: {resultPagesProcessed}/{resultPagesTotal}
                  </li>
                  {typeof resultOutputPages?.progress_pct === 'number' &&
              <li>Progresso final: {resultOutputPages.progress_pct}%</li>
              }
                  <li>Formato: {formatExt}</li>
                  {acceptedQualityAvg != null &&
              <li>Qualidade média (aceitos): {acceptedQualityAvg}</li>
              }
                  {quarantineQualityAvg != null &&
              <li>Qualidade média (quarentena): {quarantineQualityAvg}</li>
              }
                </ul>
            }
              {resultTopReasons.length > 0 &&
            <details>
                  <summary>Top motivos de erro</summary>
                  <ul className="wizard-result-list">
                    {resultTopReasons.map((item, idx) =>
                <li key={`reason-${idx}`}>
                        {item.reason} ({item.count})
                      </li>
                )}
                  </ul>
                </details>
            }
              {resultData.errors?.length > 0 &&
            <details>
                  <summary>Erros</summary>
                  <pre className="wizard-result-pre">{JSON.stringify(resultData.errors, null, 2)}</pre>
                </details>
            }
              {resultData.log?.length > 0 &&
            <details>
                  <summary>Log</summary>
                  <pre className="wizard-result-pre">{resultData.log.map((line) => normalizeDisplayText(line)).join('\n')}</pre>
                </details>
            }
              {resultData.quarantine_non_critical?.length > 0 &&
            <details>
                  <summary>Linhas em quarentena</summary>
                  <pre className="wizard-result-pre">
                    {JSON.stringify(resultData.quarantine_non_critical.slice(0, 100), null, 2)}
                  </pre>
                </details>
            }
            </div>
          }
        </section>
        }

      <Modal isOpen={showRegionModal} onClose={() => setShowRegionModal(false)} title="Selecione a região da tabela">
        {pdfBytes &&
          <PdfRegionSelector
            key={`pdf-region-${regionSelectionPage}`}
            file={pdfBytes}
            onSelect={handleRegionSelect}
            initialPage={regionSelectionPage}
            initialApplyAll={applyAllPages}
            onApplyAllChange={setApplyAllPages} />

          }
      </Modal>

      <Modal
          isOpen={showPagePicker}
          onClose={() => setShowPagePicker(false)}
          title="Escolha a página para selecionar a região"
          size="xl">
          
        <div className="wizard-page-picker-grid">
          {previewImages.map((img, idx) => {
              const src = getPreviewImageSrc(img);
              if (!src) return null;
              const pageNumber = startPage + idx;
              return (
                <button
                  key={`preview-page-${idx}`}
                  type="button"
                  onClick={() => {
                    setShowPagePicker(false);
                    setSelectedPreviewIndex(idx);
                    setTimeout(() => launchRegionSelector(pageNumber), 0);
                  }}
                  className="wizard-page-picker-item">
                  
                <div className="wizard-page-picker-label">Página {pageNumber}</div>
                <img
                    src={src}
                    alt={`Página ${pageNumber}`}
                    className="wizard-page-picker-image" />
                  
              </button>);

            })}
        </div>
      </Modal>

    </div>
    );

    return (
      <>
      {showLoadingPopup &&
        <LoadingPopup
          title="Importação de catálogo em andamento"
          message={loadingPopupMessage}
          isOpen={showLoadingPopup}
          progressPercent={progressPct}
          progressLabel={`${pagesProcessed}/${pagesTotalLabel} páginas processadas`}
          chips={[
          { label: 'Status', value: statusData?.status || 'PROCESSING' },
          { label: 'Arquivo', value: fileId ? `#${fileId}` : '-' },
          { label: 'Tempo', value: formatElapsed(elapsedSec) },
          { label: 'ETA', value: etaLabel }]}
          details={statusTimeline.slice(-5)} />

        }
      {embedded ? (
        wizardBody
      ) : (
        <Modal
          isOpen={isOpen}
          onClose={onClose}
          title={modalTitle}
          subtitle={modalSubtitle}
          size="xl"
          className="wizard-modal-shell"
          bodyClassName="wizard-modal-body"
        >
          {wizardBody}
        </Modal>
      )}
    </>);

  }
const BASE_FIELD_OPTIONS = [
  { value: 'nome_base', label: 'Nome Base' },
  { value: 'sku_original', label: 'SKU' },
  { value: 'auto:sku_nome', label: 'SKU + Nome (Auto)' },
  { value: 'ean_original', label: 'Código de Barras (EAN-13)' },
  { value: 'preco_original', label: 'Preço' },
  { value: 'descricao_original', label: 'Descrição' },
  { value: 'marca', label: 'Marca' },
  { value: 'categoria_original', label: 'Categoria' },
  { value: 'attr:codigo_original', label: 'Atributo: Código Original' },
  { value: 'attr:aplicacao', label: 'Atributo: Aplicação' },
  { value: 'attr:material', label: 'Atributo: Material' },
];

const FALLBACK_HEADERS = ['col_0', 'col_1', 'col_2', 'col_3', 'col_4'];
const STEP_FLOW = ['upload', 'preview', 'processing'];
const POLL_INTERVAL_MS = 2000;
const MAX_RESULT_WAIT_MS = 60000;
const MAX_RESULT_ATTEMPTS = 30;
const MAX_ABSOLUTE_POLL_MS = 5 * 60 * 1000;
const STEP_LABELS = {
  upload: 'Upload',
  preview: 'Preview e Mapeamento',
  processing: 'Processamento',
};

export default ImportCatalogWizard;
