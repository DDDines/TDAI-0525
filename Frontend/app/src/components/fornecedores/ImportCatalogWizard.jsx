/**
 * Module import catalog wizard.
 *
 * Defines responsibilities and integration points for components fornecedores.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as fornecedorService from '../../services/fornecedorService';
import productTypeService from '../../services/productTypeService';
import LoadingPopup from '../common/LoadingPopup';
import ColumnMappingModal from '../common/ColumnMappingModal.jsx';
import PdfRegionSelector from '../common/PdfRegionSelector.jsx';
import Modal from '../common/Modal.jsx';
import LogoImg from '../../assets/Logo.png';
import './ImportCatalogWizard.css';

function formatCellValue(


  value) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

function getPreviewImageSrc(

  img) {
    if (typeof img === 'string') {
      if (!img.trim()) return null;
      return img.startsWith('data:image') ? img : `data:image/png;base64,${img}`;
    }
    if (img && typeof img === 'object' && img.image) return img.image;
    return null;
  }

function toErrorDetail(

  err, fallback) {
    if (!err) return fallback;
    if (typeof err?.detail === 'string') return err.detail;
    if (typeof err?.message === 'string') return err.message;
    if (err?.detail && typeof err.detail === 'object') return JSON.stringify(err.detail);
    return fallback;
  }

function timestamp() {return (

      new Date().toLocaleTimeString('pt-BR'));}

function formatElapsed(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '0s';
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

function normalizeDisplayText(

  value) {
    if (value === null || value === undefined) return '';
    let text = String(value);
    const markerCount = (candidate) => (candidate.match(/[\u00c3\u00c2\u00e2\u0192\ufffd]/g) || []).length;
    const hasMarkers = (candidate) => markerCount(candidate) > 0 || /[?]{2,}/.test(candidate);
    const decodeMaybe = (candidate, source) => {
      try {
        return new TextDecoder('utf-8', { fatal: false }).decode(
          Uint8Array.from(Array.from(candidate).map((ch) => ch.charCodeAt(0) & 0xff))
        );
      } catch {
        return source;
      }
    };

    for (let i = 0; i < 5 && hasMarkers(text); i += 1) {
      let improved = text;
      const decoded = decodeMaybe(text, text);
      if (decoded && decoded !== text && markerCount(decoded) <= markerCount(improved)) {
        improved = decoded;
      }
      if (improved === text) break;
      text = improved;
    }

    text = text.replaceAll('ÃƒÆ’Ã‚', 'Ãƒ').replaceAll('Ã‚', '');

    const replacements = [
    ['n??o', 'n\u00e3o'],
    ['n?o', 'n\u00e3o'],
    ['n\u00c3\u00a3o', 'n\u00e3o'],
    ['p??gina', 'p\u00e1gina'],
    ['p?gina', 'p\u00e1gina'],
    ['P??gina', 'P\u00e1gina'],
    ['P?gina', 'P\u00e1gina'],
    ['P\u00c3\u00a1gina', 'P\u00e1gina'],
    ['p\u00c3\u00a1gina', 'p\u00e1gina'],
    ['extra??do', 'extra\u00eddo'],
    ['extra?do', 'extra\u00eddo'],
    ['extra??vel', 'extra\u00edvel'],
    ['extra?vel', 'extra\u00edvel'],
    ['cat??logo', 'cat\u00e1logo'],
    ['cat?logo', 'cat\u00e1logo'],
    ['conte??do', 'conte\u00fado'],
    ['conte?do', 'conte\u00fado'],
    ['poss??vel', 'poss\u00edvel'],
    ['poss?vel', 'poss\u00edvel'],
    ['cr??tico', 'cr\u00edtico'],
    ['cr?tico', 'cr\u00edtico'],
    ['cr??tica', 'cr\u00edtica'],
    ['cr?tica', 'cr\u00edtica'],
    ['Importa??o', 'Importa\u00e7\u00e3o'],
    ['importa??o', 'importa\u00e7\u00e3o'],
    ['Relat?rio', 'Relat\u00f3rio'],
    ['relat?rio', 'relat\u00f3rio'],
    ['n?o cr?ticos', 'n\u00e3o cr\u00edticos'],
    ['n?o dispon?veis', 'n\u00e3o dispon\u00edveis'],
    ['pÃƒÆ’Ã‚Â´de', 'p\u00f4de'],
    ['PÃƒÆ’Ã‚Â¡gina', 'P\u00e1gina'],
    ['pÃƒÆ’Ã‚Â¡gina', 'p\u00e1gina'],
    ['extraÃƒÆ’Ã‚Â§ÃƒÆ’Ã‚Â£o', 'extra\u00e7\u00e3o'],
    ['regiÃƒÆ’Ã‚Â£o', 'regi\u00e3o'],
    ['nÃƒÆ’Ã‚Â£o', 'n\u00e3o']];

    replacements.forEach(([src, dst]) => {
      text = text.replaceAll(src, dst);
    });

    return text.replace(/\s+/g, ' ').trim();
  }

function normalizePayloadStrings(

  payload) {
    if (Array.isArray(payload)) return payload.map((item) => normalizePayloadStrings(item));
    if (payload && typeof payload === 'object') {
      return Object.fromEntries(
        Object.entries(payload).map(([k, v]) => [k, normalizePayloadStrings(v)])
      );
    }
    if (typeof payload === 'string') return normalizeDisplayText(payload);
    return payload;
  }

function ImportCatalogWizard(

  { fornecedor, productTypeId: initialProductTypeId, onClose, isOpen }) {
    const defaultFornecedorMappingJson = useMemo(
      () => JSON.stringify(fornecedor?.default_column_mapping || {}),
      [fornecedor?.default_column_mapping]
    );
    const defaultFornecedorMapping = useMemo(() => {
      try {
        return JSON.parse(defaultFornecedorMappingJson);
      } catch {
        return {};
      }
    }, [defaultFornecedorMappingJson]);

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
    const [extractionMode, setExtractionMode] = useState('ocr');
    const [fieldOptions, setFieldOptions] = useState(BASE_FIELD_OPTIONS);
    const [statusData, setStatusData] = useState(null);
    const [resultData, setResultData] = useState(null);
    const [error, setError] = useState('');
    const [regionError, setRegionError] = useState('');
    const [statusTimeline, setStatusTimeline] = useState([]);
    const [expectedPages, setExpectedPages] = useState(0);
    const [processingStartedAt, setProcessingStartedAt] = useState(null);
    const pollRunRef = useRef(0);
    const pollLoopActiveRef = useRef(false);
    const timelineSeenRef = useRef(new Set());
    const lastStatusSnapshotRef = useRef('');
    const terminalStatusAnnouncedRef = useRef(false);
    const openResetKeyRef = useRef(null);

    const appendTimeline = useCallback((message) => {
      if (!message) return;
      const safeMessage = normalizeDisplayText(message);
      if (!safeMessage) return;
      const dedupeKey = safeMessage.
      replace(/[\u200B-\u200D\uFEFF]/g, '').
      replace(/\s+/g, ' ').
      trim().
      toLowerCase();
      if (!dedupeKey) return;
      if (timelineSeenRef.current.has(dedupeKey)) return;
      setStatusTimeline((prev) => {
        const recentKeys = prev.
        slice(-6).
        map((entry) =>
        entry.
        replace(/^\[[^\]]+\]\s*/, '').
        replace(/[\u200B-\u200D\uFEFF]/g, '').
        replace(/\s+/g, ' ').
        trim().
        toLowerCase()
        );
        if (recentKeys.includes(dedupeKey)) return prev;
        timelineSeenRef.current.add(dedupeKey);
        return [...prev, `[${timestamp()}] ${safeMessage}`].slice(-160);
      });
    }, []);

    useEffect(() => {
      if (!isOpen) {
        openResetKeyRef.current = null;
        return;
      }
      const resetKey = `${fornecedor?.id || 'none'}::${initialProductTypeId || 'none'}`;
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
      setExtractionMode('ocr');
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
          setProductTypes(data.items || data || []);
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
          const attrs = details?.attribute_templates || details?.attributeTemplates || [];
          const attrOptions = attrs.map((a) => ({
            value: `attr:${a.attribute_key}`,
            label: `Atributo: ${a.label || a.attribute_key}`
          }));
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

    const handlePreview = async () => {
      if (!selectedFile) return;
      setIsLoading(true);
      setLoadingMessage('Gerando preview...');
      setPreviewError('');
      appendTimeline('Iniciando geração de preview do arquivo.');
      try {
        const preview = await fornecedorService.previewCatalogo(
          selectedFile,
          pageCount,
          startPage,
          fornecedor.id
        );
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
          `Preview gerado com sucesso. File ID ${preview.fileId}. ${preview.numPages || 0} páginas detectadas.`
        );
        if (preview.previewImages?.length > 1) {
          setShowPagePicker(true);
        }
      } catch (err) {
        const detail = toErrorDetail(err, 'Falha ao gerar preview.');
        setPreviewError(detail);
        appendTimeline(`Erro ao gerar preview: ${detail}`);
      } finally {
        setIsLoading(false);
        setLoadingMessage('');
      }
    };

    const launchRegionSelector = async (pageToUse) => {
      if (!selectedFile || !fileId) return;
      const buffer = await selectedFile.arrayBuffer();
      setPdfBytes(new Uint8Array(buffer));
      setSelectedPageForRegion(pageToUse);
      if (previewImages.length > 0) {
        const idx = Math.max(0, Math.min(previewImages.length - 1, pageToUse - startPage));
        setSelectedPreviewIndex(idx);
      }
      setSelectedBbox(null);
      setRegionPreview(null);
      setShowRegionModal(true);
      appendTimeline(`Abrindo seletor de região para a página ${pageToUse}.`);
    };

    const handleOpenRegionSelector = async () => {
      if (!selectedFile || !fileId) return;
      if (previewImages.length > 1) {
        setShowPagePicker(true);
        return;
      }
      await launchRegionSelector(selectedPageForRegion || startPage);
    };

    const handleRegionSelect = async ({
      page,
      bbox,
      bboxNorm,
      canvasWidth,
      canvasHeight,
      applyAllPages: applyAll
    }) => {
      if (!fileId) return;
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
        const detail = toErrorDetail(err, 'Falha ao extrair região.');
        setRegionError(detail);
        appendTimeline(`Erro ao extrair região: ${detail}`);
      } finally {
        setIsLoading(false);
        setLoadingMessage('');
      }
    };

    const openManualMapping = () => {
      const headers =
      regionPreview?.headers?.length ?
      regionPreview.headers :
      manualMappingRows.length > 0 ?
      Object.keys(manualMappingRows[0]) :
      FALLBACK_HEADERS;
      const rows = manualMappingRows?.length ? manualMappingRows : [];
      setRegionPreview({ headers, rows });
      setShowMappingModal(true);
      appendTimeline('Abrindo mapeamento manual de colunas.');
    };

    const handleConfirmMapping = async (map) => {
      setMapping(map);
      appendTimeline(`Mapeamento atualizado com ${Object.keys(map || {}).length} coluna(s).`);
      try {
        if (fornecedor?.id) {
          await fornecedorService.setFornecedorMapping(fornecedor.id, map);
          appendTimeline('Mapeamento salvo no fornecedor com sucesso.');
        }
      } catch (err) {
        console.warn('Falha ao salvar mapeamento no fornecedor:', err);
        appendTimeline('Falha ao salvar mapeamento padrão no fornecedor.');
      }
      setShowMappingModal(false);
    };

    const pollStatus = async (id, runId) => {
      if (pollLoopActiveRef.current && pollRunRef.current === runId) return;

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
            const statusValue = String(statusRaw?.status || '').trim().toUpperCase();
            const canonicalStatus =
            statusValue === 'DONE' || statusValue === 'COMPLETED' ? 'IMPORTED' : statusValue;
            const status = {
              ...statusRaw,
              status: canonicalStatus || statusRaw?.status || 'PROCESSING'
            };
            setStatusData(status);

            const pagesProcessed = status?.pages_processed ?? 0;
            const pagesTotal = status?.total_pages ?? status?.pages_total ?? expectedPages ?? 0;
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
                    setResultData(normalizePayloadStrings(res));
                    appendTimeline('Resultado final carregado.');
                    keepPolling = false;
                  }
                } catch (err) {
                  const detail = normalizeDisplayText(
                    toErrorDetail(err, 'Falha ao obter resultado final da importação.')
                  );
                  const waitingResult =
                  /ainda n[ãa]o dispon[íi]vel|not available|still processing/i.test(detail);
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
            const detail = toErrorDetail(err, 'Falha ao consultar status da importação.');
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

    const startImport = async () => {
      if (!fileId) {
        setError('Gere o preview primeiro.');
        return;
      }

      const ptId = productTypeId ? parseInt(productTypeId, 10) : null;
      if (!ptId) {
        setError('Selecione um tipo de produto.');
        return;
      }

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
        const selectedPages = applyAllPages ?
        null :
        selectedPageForRegion ?
        [selectedPageForRegion] :
        null;

        const estimatedTotal = selectedPages?.length ?
        selectedPages.length :
        previewData?.numPages || 0;
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

        await fornecedorService.finalizarImportacaoCatalogo({
          fileId,
          productTypeId: ptId,
          fornecedorId: fornecedor.id,
          mapping: mapping && Object.keys(mapping).length ? mapping : null,
          pages: selectedPages,
          region: selectedBboxNorm || selectedBbox,
          extractionMode
        });
      } catch (err) {
        pollRunRef.current += 1;
        setStep('preview');
        const detail = normalizeDisplayText(toErrorDetail(err, 'Falha ao iniciar processamento.'));
        setError(detail);
        appendTimeline(`Erro ao iniciar processamento: ${detail}`);
      } finally {
        setIsLoading(false);
        setLoadingMessage('');
      }
    };

    if (!isOpen) return null;

    const mappedHeaders = regionPreview?.headers || previewData?.headers || FALLBACK_HEADERS;
    const mappedRows = Array.isArray(regionPreview?.rows) ?
    regionPreview.rows :
    Array.isArray(previewData?.sampleRows) ?
    previewData.sampleRows :
    Array.isArray(manualMappingRows) ?
    manualMappingRows :
    [];

    const criticalErrorsCount = resultData?.stats?.erros ?? (resultData?.errors?.length || 0);
    const hasPartialSuccess = Boolean(resultData?.stats?.partial_success) ||
    (resultData?.stats?.produtos_criados ?? 0) + (resultData?.stats?.produtos_atualizados ?? 0) > 0 &&
    criticalErrorsCount > 0;


    const pagesProcessed = statusData?.pages_processed ?? resultData?.stats?.pages_processed ?? 0;
    const pagesTotal =
    statusData?.total_pages ??
    statusData?.pages_total ??
    resultData?.stats?.pages_total ??
    expectedPages ??
    0;
    const progressPct = pagesTotal > 0 ? Math.min(100, Math.round(pagesProcessed / pagesTotal * 100)) : 0;
    const terminalStatuses = new Set(['IMPORTED', 'DONE', 'FAILED', 'PARTIAL']);
    const statusNormalized = String(statusData?.status || '').trim().toUpperCase();
    const isTerminalStatus = terminalStatuses.has(statusNormalized);
    const processingActive = !statusData || !isTerminalStatus;
    const waitingFinalResult = step === 'processing' && isTerminalStatus && !resultData && !error;
    const elapsedSec = processingStartedAt ? Math.max(0, Math.floor((Date.now() - processingStartedAt) / 1000)) : 0;
    const etaSec = pagesProcessed > 0 && pagesTotal > pagesProcessed ?
    Math.max(0, Math.round((elapsedSec / pagesProcessed) * (pagesTotal - pagesProcessed))) :
    0;
    const showLoadingPopup = isLoading || step === 'processing' && !error && (processingActive || waitingFinalResult);
    const loadingPopupMessage =
    step === 'processing' && processingActive ?
    'Processando importação do catálogo...' :
    step === 'processing' && waitingFinalResult ?
    'Aguardando consolidação do resultado final...' :
    loadingMessage || 'Processando...';
    const currentStepIndex = Math.max(0, STEP_FLOW.indexOf(step));
    const selectedScopeLabel = applyAllPages ?
    'todas as páginas do PDF' :
    `somente página ${selectedPageForRegion || startPage}`;
    const canStartImport = Boolean(fileId && productTypeId) && !isLoading;
    const hasPrimaryMapping = Object.values(mapping || {}).some((dest) =>
    ['auto:sku_nome', 'nome_base', 'sku_original'].includes(dest)
    );
    const canStartWithMapping = canStartImport && hasPrimaryMapping;
    const discardedNonCritical = resultData?.stats?.descartes_nao_criticos ?? 0;
    const quarantineCount =
    resultData?.stats?.quarentena_nao_critica ?? (resultData?.quarantine_non_critical?.length || 0);
    const acceptedQualityAvg = resultData?.stats?.qualidade_score_medio_aceitas;
    const quarantineQualityAvg = resultData?.stats?.qualidade_score_medio_quarentena;
    const resultOutput = resultData?.output && typeof resultData.output === 'object' ? resultData.output : {};
    const resultOutputHeadline = normalizeDisplayText(resultOutput?.headline || '');
    const resultOutputLabel = normalizeDisplayText(resultOutput?.status_label || '');
    const resultOutputPages = resultOutput?.pages && typeof resultOutput.pages === 'object' ? resultOutput.pages : {};
    const resultTopReasons = Array.isArray(resultData?.top_reasons) ?
    resultData.top_reasons.slice(0, 5) :
    [];

    return (
      <div className="wizard-container" aria-live="polite">
      {showLoadingPopup &&
        <LoadingPopup
          title="Importação de catálogo em andamento"
          message={loadingPopupMessage}
          isOpen={showLoadingPopup}
          progressPercent={progressPct}
          progressLabel={`${pagesProcessed}/${pagesTotal || '?'} páginas processadas`}
          chips={[
          { label: 'Status', value: statusData?.status || 'PROCESSING' },
          { label: 'Arquivo', value: fileId ? `#${fileId}` : '-' },
          { label: 'Tempo', value: formatElapsed(elapsedSec) },
          { label: 'ETA', value: etaSec > 0 ? formatElapsed(etaSec) : '-' }]}
          details={statusTimeline.slice(-5)} />

        }

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
            <p>Selecione o arquivo e defina um recorte inicial de páginas para gerar o preview.</p>
          </header>

          <div className="wizard-upload-block">
            <label htmlFor="wizard-file-input" className="wizard-file-label">
              Arquivo do catálogo (PDF, XLSX ou CSV)
            </label>
            <input
              id="wizard-file-input"
              type="file"
              accept=".pdf,.xlsx,.xls,.csv"
              onChange={handleFileChange}
              aria-label="Arquivo de catálogo" />
            
            {selectedFile && <p className="wizard-selected-file">Arquivo selecionado: {selectedFile.name}</p>}
            <div className="wizard-inline-fields">
              <label htmlFor="wizard-start-page">
                Página inicial
                <input
                  id="wizard-start-page"
                  type="number"
                  min="1"
                  value={startPage}
                  onChange={(e) => setStartPage(Math.max(1, parseInt(e.target.value || '1', 10)))}
                  className="wizard-small-number-input" />
                
              </label>
              <label htmlFor="wizard-page-count">
                Quantidade de páginas
                <input
                  id="wizard-page-count"
                  type="number"
                  min="1"
                  value={pageCount}
                  onChange={(e) => setPageCount(Math.max(1, parseInt(e.target.value || '1', 10)))}
                  className="wizard-small-number-input" />
                
              </label>
            </div>
          </div>
          <div className="wizard-actions-row">
            <button onClick={handlePreview} disabled={!selectedFile || isLoading} type="button">
              Gerar Preview
            </button>
          </div>
          {previewError && <p className="wizard-error-text">{previewError}</p>}
        </section>
        }

      {step === 'preview' && previewData &&
        <section className="wizard-panel">
          <header className="wizard-panel-header">
            <h3>Passo 2: Revisar e mapear dados</h3>
            <p>
              File ID {fileId || '-'} | páginas no arquivo: {previewData.numPages || 0}
            </p>
          </header>

          {!previewData.headers && !previewImages.length &&
          <p className="wizard-warning-text">
              Nenhum preview disponível. Verifique se o arquivo é suportado.
            </p>
          }

          {previewData.headers && sampleRows.length > 0 &&
          <div className="wizard-table-block">
              <p>Prévia das colunas detectadas:</p>
              <div className="wizard-table-wrap">
                <table className="preview-table">
                  <thead>
                    <tr>
                      {previewData.headers.map((h) =>
                    <th key={h}>{h}</th>
                    )}
                    </tr>
                  </thead>
                  <tbody>
                    {sampleRows.slice(0, 5).map((row, idx) =>
                  <tr key={idx}>
                        {previewData.headers.map((h) =>
                    <td key={h}>{formatCellValue(row?.[h])}</td>
                    )}
                      </tr>
                  )}
                  </tbody>
                </table>
              </div>
            </div>
          }

          {previewImages.length > 0 &&
          <div className="wizard-preview-images-block">
              <p>
                Prévia de páginas (PDF): mostrando{' '}
                {selectedPreviewIndex != null ? 1 : previewImages.length} página(s)
              </p>
              <div className="wizard-preview-images-grid">
                {(selectedPreviewIndex != null ? [previewImages[selectedPreviewIndex]] : previewImages).map((img, idx) => {
                const absoluteIdx = selectedPreviewIndex != null ? selectedPreviewIndex : idx;
                const pageNumber = startPage + absoluteIdx;
                const src = getPreviewImageSrc(img);
                if (!src) return null;
                return (
                  <figure key={`${pageNumber}-${idx}`} className="wizard-preview-figure">
                      <img
                      src={src}
                      alt={`Página ${pageNumber}`}
                      className="wizard-preview-image" />
                    
                      <figcaption>Página {pageNumber}</figcaption>
                    </figure>);

              })}
              </div>
            </div>
          }

          <div className="wizard-action-grid">
            <section className="wizard-action-card">
              <h4>1) Definir extração e mapeamento</h4>
              <p>Ajuste a região da tabela e confira o mapeamento de colunas antes de importar.</p>
              <div className="wizard-actions-row">
                <button type="button" onClick={() => setShowMappingModal(true)}>
                  Definir mapeamento
                </button>
                <button type="button" onClick={handleOpenRegionSelector} disabled={!fileId}>
                  Selecionar região
                </button>
                <button type="button" onClick={openManualMapping}>
                  Mapear manualmente
                </button>
              </div>
            </section>

            <section className="wizard-action-card">
              <h4>2) Definir escopo e tipo de produto</h4>
              <div className="wizard-inline-fields">
                <label htmlFor="wizard-page-select">
                  Página para seleção
                  <input
                    id="wizard-page-select"
                    type="number"
                    min="1"
                    value={selectedPageForRegion || startPage}
                    onChange={(e) => {
                      const val = Math.max(1, parseInt(e.target.value || '1', 10));
                      setSelectedPageForRegion(val);
                    }}
                    className="wizard-small-number-input" />
                  
                </label>

                <label htmlFor="wizard-product-type">
                  Tipo de Produto
                  <select
                    id="wizard-product-type"
                    value={productTypeId}
                    onChange={(e) => handleProductTypeChange(e.target.value)}
                    className="wizard-inline-select">
                    
                    <option value="">Selecione...</option>
                    {productTypes.map((pt) => {
                      const value = pt.id;
                      if (value === null || value === undefined) return null;
                      const label = pt.friendly_name || pt.nome || pt.name || pt.slug || pt.key_name || value;
                      return (
                        <option key={value} value={value}>
                          {label}
                        </option>);

                    })}
                  </select>
                </label>

                <label htmlFor="wizard-extraction-mode">
                  Modo de Extracao
                  <select
                    id="wizard-extraction-mode"
                    value={extractionMode}
                    onChange={(e) => setExtractionMode(e.target.value)}
                    className="wizard-inline-select">
                    <option value="table">Tabela</option>
                    <option value="ocr">OCR</option>
                    <option value="ia">IA</option>
                  </select>
                </label>
              </div>
              <label className="wizard-checkbox-label" htmlFor="wizard-apply-all">
                <input
                  id="wizard-apply-all"
                  type="checkbox"
                  checked={applyAllPages}
                  onChange={(e) => setApplyAllPages(e.target.checked)}
                  className="wizard-inline-checkbox" />
                
                Aplicar região em todas as páginas
              </label>
              <button type="button" onClick={startImport} disabled={!canStartWithMapping}>
                Iniciar Processamento
              </button>
              {!productTypeId &&
              <p className="wizard-warning-text">
                  Selecione o tipo de produto para habilitar a importação final.
                </p>
              }
              {productTypeId && !hasPrimaryMapping &&
              <p className="wizard-warning-text">
                  Defina ao menos uma coluna como <strong>SKU + Nome (Auto)</strong>, <strong>Nome Base</strong> ou <strong>SKU</strong>.
                </p>
              }
            </section>
          </div>

          <p className="wizard-scope-hint">
            Escopo atual: {selectedScopeLabel}
          </p>

          {regionPreview?.headers &&
          <div className="wizard-region-preview-block wizard-table-block">
              <p>Prévia da região selecionada:</p>
              <div className="wizard-table-wrap">
                <table className="preview-table">
                  <thead>
                    <tr>
                      {regionPreview.headers.map((h) =>
                    <th key={h}>{h}</th>
                    )}
                    </tr>
                  </thead>
                  <tbody>
                    {regionPreview.rows.map((row, idx) =>
                  <tr key={idx}>
                        {regionPreview.headers.map((h) =>
                    <td key={h}>{formatCellValue(row?.[h])}</td>
                    )}
                      </tr>
                  )}
                  </tbody>
                </table>
              </div>
            </div>
          }
          {regionError && <p className="wizard-error-text">{regionError}</p>}

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
              {LogoImg ? <img src={LogoImg} alt="CatalogAI" className="wizard-processing-logo" /> : null}
              <div>
                <strong>Status:</strong> {statusData?.status || 'PROCESSING'}
                <div>{`Páginas: ${pagesProcessed}/${pagesTotal || '?'}`}</div>
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
              {statusTimeline.length === 0 ?
              <p>Aguardando atualizações...</p> :

              <ul>
                  {statusTimeline.map((line, idx) =>
                <li key={`${line}-${idx}`}>{line}</li>
                )}
                </ul>
              }
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
              {statusData?.status === 'FAILED' && resultData?.errors?.length > 0 &&
            <p className="wizard-result-error">
                  Falha: {resultData.errors[0]?.erro_processamento_pdf || resultData.errors[0]?.erro_processamento || 'Verifique os detalhes em Erros/Log.'}
                </p>
            }
              {(statusData?.status === 'IMPORTED' || statusData?.status === 'DONE' || statusData?.status === 'PARTIAL') && hasPartialSuccess &&
            <p className="wizard-result-warning">
                  Importação concluída com alertas: há erros críticos que exigem revisão.
                </p>
            }
              {(resultData.stats || resultData.created || resultData.updated || resultData.errors) &&
            <ul className="wizard-result-list">
                  <li>Criados: {resultData?.stats?.produtos_criados ?? (resultData?.created?.length || 0)}</li>
                  <li>Atualizados: {resultData?.stats?.produtos_atualizados ?? (resultData?.updated?.length || 0)}</li>
                  <li>Erros críticos: {criticalErrorsCount}</li>
                  <li>Descartes não críticos: {discardedNonCritical}</li>
                  <li>Quarentena (não importados): {quarantineCount}</li>
                  <li>
                    Páginas: {resultData?.stats?.pages_processed ?? statusData?.pages_processed ?? 0}/
                    {resultData?.stats?.pages_total ?? statusData?.total_pages ?? statusData?.pages_total ?? 0}
                  </li>
                  {typeof resultOutputPages?.progress_pct === 'number' &&
              <li>Progresso final: {resultOutputPages.progress_pct}%</li>
              }
                  <li>Formato: {resultData?.stats?.ext || selectedFile?.name?.split('.').pop()?.toLowerCase() || '-'}</li>
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
                        {normalizeDisplayText(item?.reason || '-')} ({item?.count ?? 0})
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
            key={`pdf-region-${selectedPageForRegion || startPage}`}
            file={pdfBytes}
            onSelect={handleRegionSelect}
            initialPage={selectedPageForRegion || startPage}
            initialApplyAll={applyAllPages}
            onApplyAllChange={setApplyAllPages} />

          }
      </Modal>

      <Modal
          isOpen={showPagePicker}
          onClose={() => setShowPagePicker(false)}
          title="Escolha a página para selecionar a região">
          
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

      <hr className="wizard-footer-divider" />
      <button type="button" onClick={onClose}>
        Fechar
      </button>
    </div>);

  }
const BASE_FIELD_OPTIONS = [{ value: 'nome_base', label: 'Nome Base' }, { value: 'sku_original', label: 'SKU' }, { value: 'auto:sku_nome', label: 'SKU + Nome (Auto)' }, { value: 'ean_original', label: 'Código de Barras (EAN-13)' }, { value: 'preco_original', label: 'Preço' }, { value: 'descricao_original', label: 'Descrição' }, { value: 'marca', label: 'Marca' }, { value: 'categoria_original', label: 'Categoria' }, { value: 'attr:codigo_original', label: 'Atributo: Código Original' }, { value: 'attr:aplicacao', label: 'Atributo: Aplicação' }, { value: 'attr:material', label: 'Atributo: Material' }];const FALLBACK_HEADERS = ['col_0', 'col_1', 'col_2', 'col_3', 'col_4'];const STEP_FLOW = ['upload', 'preview', 'processing'];const POLL_INTERVAL_MS = 2000;const MAX_RESULT_WAIT_MS = 60000;const MAX_RESULT_ATTEMPTS = 30;const MAX_ABSOLUTE_POLL_MS = 5 * 60 * 1000;const STEP_LABELS = { upload: 'Upload', preview: 'Preview e Mapeamento', processing: 'Processamento' };export default ImportCatalogWizard;
