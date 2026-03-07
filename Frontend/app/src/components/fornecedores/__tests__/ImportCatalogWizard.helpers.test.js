import {
  appendUniqueTimelineEntry,
  buildWizardResetKey,
  buildWizardViewModel,
  cloneFornecedorMapping,
  extractProductTypeAttributes,
  extractProductTypesCollection,
  formatCellValue,
  formatElapsed,
  getPreviewImageSrc,
  normalizePayloadStrings,
  resolveManualMappingPreview,
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
});