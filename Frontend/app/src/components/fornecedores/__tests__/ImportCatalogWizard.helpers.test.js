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
  formatElapsed,
  getProductTypeOptionLabel,
  getPreviewImageSrc,
  normalizeImportStatus,
  normalizePreviewPayload,
  normalizePayloadStrings,
  resolveMappingEditorState,
  resolveManualMappingPreview,
  resolvePreviewImageIndex,
  resolveWizardPage,
  sanitizePositivePageInput,
} from '../ImportCatalogWizard.helpers.js';

describe('ImportCatalogWizard helpers', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('formats cell values and preview image sources safely', () => {
    expect(formatCellValue(null)).toBe('');
    expect(formatCellValue(undefined)).toBe('');
    expect(formatCellValue({ sku: 'ABC' })).toBe('{"sku":"ABC"}');
    expect(formatCellValue(42)).toBe('42');

    expect(getPreviewImageSrc('')).toBeNull();
    expect(getPreviewImageSrc('   ')).toBeNull();
    expect(getPreviewImageSrc('data:image/png;base64,abc')).toBe('data:image/png;base64,abc');
    expect(getPreviewImageSrc('raw-base64')).toBe('data:image/png;base64,raw-base64');
    expect(getPreviewImageSrc({ image: 'data:image/png;base64,xyz' })).toBe(
      'data:image/png;base64,xyz'
    );
    expect(getPreviewImageSrc({})).toBeNull();
  });

  test('formats elapsed time and normalizes nested payload strings', () => {
    expect(formatElapsed(-1)).toBe('0s');
    expect(formatElapsed(Number.NaN)).toBe('0s');
    expect(formatElapsed(7)).toBe('7s');
    expect(formatElapsed(125)).toBe('2m 5s');

    expect(
      normalizePayloadStrings({
        headline: 'Relat?rio',
        lines: ['Importa??o conclu?da', { label: 'Descri??o' }],
      })
    ).toEqual({
      headline: 'Relatório',
      lines: ['Importação concluída', { label: 'Descrição' }],
    });
  });

  test('appends timeline entries only when the normalized message is unique and meaningful', () => {
    expect(appendUniqueTimelineEntry([], '', '10:00:00')).toEqual({
      appended: false,
      dedupeKey: '',
      entries: [],
    });

    expect(
      appendUniqueTimelineEntry(
        ['[10:00:00] Preview gerado com sucesso.'],
        '  Preview gerado com sucesso.  ',
        '10:00:01'
      )
    ).toEqual({
      appended: false,
      dedupeKey: 'preview gerado com sucesso.',
      entries: ['[10:00:00] Preview gerado com sucesso.'],
    });

    expect(
      appendUniqueTimelineEntry(
        ['[10:00:00] Preview gerado com sucesso.'],
        'Processamento iniciado',
        '10:00:02'
      )
    ).toEqual({
      appended: true,
      dedupeKey: 'processamento iniciado',
      entries: [
        '[10:00:00] Preview gerado com sucesso.',
        '[10:00:02] Processamento iniciado',
      ],
    });
  });

  test('normalizes mapping keys and product type collections safely', () => {
    const originalMapping = { sku: 'codigo' };
    const clonedMapping = cloneFornecedorMapping(originalMapping);

    expect(clonedMapping).toEqual({ sku: 'codigo' });
    expect(clonedMapping).not.toBe(originalMapping);
    expect(cloneFornecedorMapping(null)).toEqual({});

    expect(buildWizardResetKey(undefined, '')).toBe('none::none');
    expect(buildWizardResetKey(7, 11)).toBe('7::11');

    expect(extractProductTypesCollection({ items: [{ id: 1 }] })).toEqual([{ id: 1 }]);
    expect(extractProductTypesCollection([{ id: 2 }])).toEqual([{ id: 2 }]);
    expect(extractProductTypesCollection({})).toEqual([]);

    expect(extractProductTypeAttributes({ attribute_templates: [{ attribute_key: 'sku' }] })).toEqual([
      { attribute_key: 'sku' },
    ]);
    expect(extractProductTypeAttributes({ attributeTemplates: [{ attribute_key: 'ean' }] })).toEqual([
      { attribute_key: 'ean' },
    ]);
    expect(extractProductTypeAttributes(null)).toEqual([]);
  });

  test('builds attribute and product type labels with safe fallbacks', () => {
    expect(buildAttributeOption({ attribute_key: 'cor', label: 'Cor' })).toEqual({
      value: 'attr:cor',
      label: 'Atributo: Cor',
    });
    expect(buildAttributeOption({ attribute_key: 'sku' })).toEqual({
      value: 'attr:sku',
      label: 'Atributo: sku',
    });

    expect(getProductTypeOptionLabel({ friendly_name: 'Linha Pesada' })).toBe('Linha Pesada');
    expect(getProductTypeOptionLabel({ friendly_name: '', nome: 'Motores' })).toBe('Motores');
    expect(getProductTypeOptionLabel({ name: 'Bombas' })).toBe('Bombas');
    expect(getProductTypeOptionLabel({ slug: 'suspensao' })).toBe('suspensao');
    expect(getProductTypeOptionLabel({ key_name: 'filtros' })).toBe('filtros');
    expect(getProductTypeOptionLabel({ id: 9 })).toBe('9');
  });

  test('normalizes preview payloads, import requests and polling status safely', () => {
    expect(resolveWizardPage(undefined, 7)).toBe(7);
    expect(resolveWizardPage('5', 2)).toBe(5);
    expect(resolveWizardPage(null, null)).toBe(1);
    expect(sanitizePositivePageInput('', 4)).toBe(4);
    expect(sanitizePositivePageInput('0', 4)).toBe(4);
    expect(sanitizePositivePageInput('6', 4)).toBe(6);
    expect(resolvePreviewImageIndex(0, 3, 1)).toBeNull();
    expect(resolvePreviewImageIndex(4, 7, 5)).toBe(2);
    expect(buildTimelineLines([])).toEqual(['Aguardando atualizações...']);
    expect(buildTimelineLines(['linha 1'])).toEqual(['linha 1']);

    expect(
      normalizePreviewPayload({
        fileId: undefined,
        headers: 'invalid',
        sampleRows: null,
        previewImages: null,
        numPages: undefined,
      })
    ).toEqual(
      expect.objectContaining({
        fileId: null,
        headers: null,
        sampleRows: [],
        previewImages: [],
        numPages: 0,
        tablePages: [],
      })
    );

    expect(
      resolveMappingEditorState({
        regionPreview: { headers: ['sku'] },
        manualMappingRows: [{ sku: 'A1' }],
        fallbackHeaders: ['fallback'],
      })
    ).toEqual({
      headers: ['sku'],
      rows: [{ sku: 'A1' }],
    });

    expect(
      resolveMappingEditorState({
        regionPreview: null,
        manualMappingRows: [{ nome: 'Filtro' }],
        fallbackHeaders: ['fallback'],
      })
    ).toEqual({
      headers: ['nome'],
      rows: [{ nome: 'Filtro' }],
    });

    expect(
      normalizeImportStatus({ status: ' completed ', pages_total: 6 }, 10)
    ).toEqual(
      expect.objectContaining({
        status: 'IMPORTED',
        pages_processed: 0,
        total_pages: 6,
      })
    );

    expect(
      normalizeImportStatus({ status: null }, 3)
    ).toEqual(
      expect.objectContaining({
        status: 'PROCESSING',
        pages_processed: 0,
        total_pages: 3,
      })
    );

    expect(
      buildImportStartPayload({
        fileId: 44,
        productTypeId: '',
        fornecedorId: 8,
        mapping: {},
        selectedPageForRegion: null,
        startPage: 9,
        applyAllPages: false,
        previewData: { numPages: 0 },
        selectedBboxNorm: null,
        selectedBbox: { x: 1 },
        extractionMode: 'ocr',
      })
    ).toEqual({
      estimatedTotal: 1,
      payload: {
        fileId: 44,
        productTypeId: null,
        fornecedorId: 8,
        mapping: null,
        pages: [9],
        region: { x: 1 },
        extractionMode: 'ocr',
      },
    });
  });

  test('resolves manual mapping preview from region, preview or manual rows', () => {
    expect(
      resolveManualMappingPreview({
        regionPreview: { headers: ['A'], rows: [{ A: '1' }] },
        previewData: { headers: ['B'], sampleRows: [{ B: '2' }] },
        manualMappingRows: [{ C: '3' }],
        fallbackHeaders: ['fallback'],
      })
    ).toEqual({
      headers: ['A'],
      rows: [{ A: '1' }],
    });

    expect(
      resolveManualMappingPreview({
        regionPreview: null,
        previewData: { headers: ['B'], sampleRows: [{ B: '2' }] },
        manualMappingRows: [{ C: '3' }],
        fallbackHeaders: ['fallback'],
      })
    ).toEqual({
      headers: ['B'],
      rows: [{ B: '2' }],
    });

    expect(
      resolveManualMappingPreview({
        regionPreview: null,
        previewData: null,
        manualMappingRows: [{ C: '3' }],
        fallbackHeaders: ['fallback'],
      })
    ).toEqual({
      headers: ['fallback'],
      rows: [{ C: '3' }],
    });

    expect(
      resolveManualMappingPreview({
        regionPreview: { headers: [], rows: null },
        previewData: { headers: [], sampleRows: null },
        manualMappingRows: [{ fallback: '1' }],
        fallbackHeaders: ['fallback'],
      })
    ).toEqual({
      headers: ['fallback'],
      rows: [{ fallback: '1' }],
    });

    expect(
      resolveManualMappingPreview({
        regionPreview: { headers: [], rows: null },
        previewData: { headers: [], sampleRows: null },
        manualMappingRows: null,
        fallbackHeaders: ['fallback'],
      })
    ).toEqual({
      headers: ['fallback'],
      rows: [],
    });
  });

  test('builds a processing view model with partial success and result details', () => {
    jest.spyOn(Date, 'now').mockReturnValue(90_000);

    expect(
      buildWizardViewModel({
        resultData: {
          stats: {
            partial_success: false,
            produtos_criados: 2,
            produtos_atualizados: 1,
            erros: 1,
            descartes_nao_criticos: 4,
            qualidade_score_medio_aceitas: 91,
            pages_total: 10,
          },
          quarantine_non_critical: [{ id: 1 }, { id: 2 }],
          output: {
            headline: 'Relat?rio final',
            status_label: 'Conclu?do',
            pages: { progress_pct: 80 },
          },
          top_reasons: Array.from({ length: 8 }, (_, index) => ({ reason: `Motivo ${index}`, count: index + 1 })),
        },
        statusData: {
          status: 'DONE',
          pages_processed: 8,
          total_pages: 10,
        },
        expectedPages: 12,
        step: 'processing',
        error: '',
        processingStartedAt: 30_000,
        isLoading: false,
        loadingMessage: '',
        applyAllPages: true,
        selectedPageForRegion: 4,
        startPage: 2,
        fileId: 55,
        mapping: { titulo: 'nome_base', codigo: 'sku_original' },
        productTypeId: '8',
        selectedFile: new File(['conteudo'], 'catalogo.csv'),
      })
    ).toEqual(
      expect.objectContaining({
        criticalErrorsCount: 1,
        hasPartialSuccess: true,
        pagesProcessed: 8,
        pagesTotal: 10,
        progressPct: 80,
        processingActive: false,
        waitingFinalResult: false,
        elapsedSec: 60,
        etaSec: 15,
        showLoadingPopup: false,
        loadingPopupMessage: 'Processando...',
        selectedScopeLabel: 'todas as páginas do PDF',
        canStartImport: true,
        hasPrimaryMapping: true,
        canStartWithMapping: true,
        discardedNonCritical: 4,
        quarantineCount: 2,
        acceptedQualityAvg: 91,
        resultOutputHeadline: 'Relatório final',
        resultOutputLabel: 'Concluído',
        resultTopReasons: expect.arrayContaining([{ reason: 'Motivo 0', count: 1 }]),
        formatExt: 'csv',
      })
    );
  });

  test('builds fallback wizard state when no result data exists yet', () => {
    jest.spyOn(Date, 'now').mockReturnValue(10_000);

    expect(
      buildWizardViewModel({
        resultData: null,
        statusData: null,
        expectedPages: 6,
        step: 'processing',
        error: '',
        processingStartedAt: null,
        isLoading: true,
        loadingMessage: 'Carregando preview...',
        applyAllPages: false,
        selectedPageForRegion: null,
        startPage: 3,
        fileId: null,
        mapping: {},
        productTypeId: '',
        selectedFile: new File(['conteudo'], 'catalogo.PDF'),
      })
    ).toEqual(
      expect.objectContaining({
        criticalErrorsCount: 0,
        hasPartialSuccess: false,
        pagesProcessed: 0,
        pagesTotal: 6,
        progressPct: 0,
        processingActive: true,
        waitingFinalResult: false,
        elapsedSec: 0,
        etaSec: 0,
        showLoadingPopup: true,
        loadingPopupMessage: 'Processando importação do catálogo...',
        selectedScopeLabel: 'somente página 3',
        canStartImport: false,
        hasPrimaryMapping: false,
        canStartWithMapping: false,
        quarantineCount: 0,
        resultOutputHeadline: '',
        resultOutputLabel: '',
        resultTopReasons: [],
        formatExt: 'pdf',
      })
    );
  });

  test('builds wizard state from secondary counters and sparse mappings', () => {
    expect(
      buildWizardViewModel({
        resultData: {
          stats: {
            pages_processed: 4,
            pages_total: 9,
            quarentena_nao_critica: 7,
          },
          output: null,
        },
        statusData: {
          status: 'partial',
          pages_total: 6,
        },
        expectedPages: 12,
        step: 'preview',
        error: '',
        processingStartedAt: null,
        isLoading: false,
        loadingMessage: 'Preview',
        applyAllPages: false,
        selectedPageForRegion: 5,
        startPage: 2,
        fileId: 10,
        mapping: null,
        productTypeId: '',
        selectedFile: null,
      })
    ).toEqual(
      expect.objectContaining({
        pagesProcessed: 4,
        pagesTotal: 6,
        showLoadingPopup: false,
        hasPrimaryMapping: false,
        quarantineCount: 7,
        selectedScopeLabel: 'somente página 5',
        formatExt: '-',
      })
    );

    expect(
      buildWizardViewModel({
        resultData: {
          stats: {
            pages_total: 11,
          },
        },
        statusData: null,
        expectedPages: null,
        step: 'processing',
        error: 'falha',
        processingStartedAt: null,
        isLoading: false,
        loadingMessage: '',
        applyAllPages: false,
        selectedPageForRegion: null,
        startPage: 4,
        fileId: 12,
        mapping: {},
        productTypeId: '1',
        selectedFile: new File(['conteudo'], 'catalogo.json'),
      })
    ).toEqual(
      expect.objectContaining({
        pagesTotal: 11,
        selectedScopeLabel: 'somente página 4',
      })
    );

    expect(
      buildWizardViewModel({
        resultData: null,
        statusData: null,
        expectedPages: undefined,
        step: 'upload',
        error: '',
        processingStartedAt: null,
        isLoading: false,
        loadingMessage: '',
        applyAllPages: false,
        selectedPageForRegion: null,
        startPage: 1,
        fileId: null,
        mapping: {},
        productTypeId: '',
        selectedFile: null,
      })
    ).toEqual(
      expect.objectContaining({
        pagesTotal: 0,
      })
    );
  });

  test('deduplicates recent timeline entries even when previous entries are sparse', () => {
    expect(
      appendUniqueTimelineEntry(
        [null, '[10:00:00] Processamento iniciado'],
        'processamento iniciado',
        '10:00:01'
      )
    ).toEqual({
      appended: false,
      dedupeKey: 'processamento iniciado',
      entries: [null, '[10:00:00] Processamento iniciado'],
    });
  });

  test('builds failure details and top reason fallbacks when result payload is sparse', () => {
    expect(
      buildWizardViewModel({
        resultData: {
          errors: [{ erro_processamento: 'Falha parcial' }],
          top_reasons: [{ reason: '', count: undefined }],
        },
        statusData: { status: 'FAILED', pages_total: 2 },
        expectedPages: undefined,
        step: 'processing',
        error: '',
        processingStartedAt: null,
        isLoading: false,
        loadingMessage: '',
        applyAllPages: false,
        selectedPageForRegion: undefined,
        startPage: 1,
        fileId: null,
        mapping: {},
        productTypeId: '',
        selectedFile: null,
      })
    ).toEqual(
      expect.objectContaining({
        failedMessage: 'Falha parcial',
        showFailedResultMessage: true,
        resultTopReasons: [{ reason: '-', count: 0 }],
      })
    );

    expect(
      buildWizardViewModel({
        resultData: {
          errors: [{}],
        },
        statusData: { status: 'FAILED' },
        expectedPages: undefined,
        step: 'processing',
        error: '',
        processingStartedAt: null,
        isLoading: false,
        loadingMessage: '',
        applyAllPages: false,
        selectedPageForRegion: undefined,
        startPage: 1,
        fileId: null,
        mapping: {},
        productTypeId: '',
        selectedFile: null,
      })
    ).toEqual(
      expect.objectContaining({
        failedMessage: 'Verifique os detalhes em Erros/Log.',
      })
    );

    expect(
      normalizeImportStatus({}, undefined)
    ).toEqual(
      expect.objectContaining({
        total_pages: 0,
      })
    );

    expect(
      resolveMappingEditorState({
        regionPreview: null,
        manualMappingRows: null,
        fallbackHeaders: ['fallback'],
      })
    ).toEqual({
      headers: ['fallback'],
      rows: [],
    });

    expect(buildAttributeOption({ label: 'Sem chave' })).toEqual({
      value: 'attr:',
      label: 'Atributo: Sem chave',
    });
    expect(getProductTypeOptionLabel({})).toBe('');
  });
});
