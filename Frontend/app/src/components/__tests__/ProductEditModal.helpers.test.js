import {
  buildProductFormState,
  buildInitialDynamicAttributes,
  coerceFormFieldValue,
  extractIaSuggestionMap,
  extractGeneratedTitles,
  handleContentViewNavigation,
  logAsyncPollError,
  normalizeDynamicAttrsToTemplateKeys,
  resolveProductFormStage,
  resolveServiceErrorDetail,
  resolveShowAiFeatures,
  sanitizeProdutoData,
} from '../ProductEditModal.helpers.js';

describe('ProductEditModal helpers', () => {
  test('extractGeneratedTitles prefers final generated titles and only falls back to raw suggestions when needed', () => {
    expect(extractGeneratedTitles()).toEqual([]);
    expect(
      extractGeneratedTitles({
        titulos_sugeridos: ['Titulo A', null, '  '],
        dados_brutos_web: { titulos_sugeridos_gerados: ['titulo a', 'Titulo B'] },
      })
    ).toEqual(['Titulo A']);
    expect(
      extractGeneratedTitles({
        titulos_sugeridos: [],
        dados_brutos_web: { titulos_sugeridos_gerados: ['Titulo B', 'titulo b', 'Titulo C'] },
      })
    ).toEqual(['Titulo B', 'Titulo C']);
  });

  test('normalizeDynamicAttrsToTemplateKeys skips empty-like values and blank aliases', () => {
    expect(
      normalizeDynamicAttrsToTemplateKeys(
        {
          ' ': 'ignorar',
          nome: 'Produto X',
          codigo_original: '--',
          descricao_curta: '   ',
          referencia_manual: 'REF-9',
        },
        [
          { attribute_key: 'titulo_auto', label: 'Nome comercial' },
          { attribute_key: 'referencia', label: ' ' },
          { attribute_key: 'descricao_longa', label: 'Descricao' },
        ]
      )
    ).toEqual(
      expect.objectContaining({
        nome: 'Produto X',
        codigo_original: '--',
        descricao_curta: '   ',
        referencia_manual: 'REF-9',
        titulo_auto: 'Produto X',
      })
    );
  });

  test('normalizeDynamicAttrsToTemplateKeys preserves existing target values and matches aliases by inclusion', () => {
    expect(
      normalizeDynamicAttrsToTemplateKeys(
        {
          titulo_auto: 'Ja existe',
          'codigo do fabricante': 'COD-10',
          'descricao detalhada': 'Texto tecnico',
        },
        [
          { attribute_key: 'titulo_auto', label: 'Titulo SEO' },
          { attribute_key: 'codigo_fabricante', label: 'Codigo' },
          { attribute_key: 'descricao_curta', label: 'Desc' },
        ]
      )
    ).toEqual(
      expect.objectContaining({
        titulo_auto: 'Ja existe',
        codigo_fabricante: 'COD-10',
        descricao_curta: 'Texto tecnico',
      })
    );
  });

  test('normalizeDynamicAttrsToTemplateKeys tolerates sparse inputs and template fallback labels', () => {
    expect(
      normalizeDynamicAttrsToTemplateKeys(null, null)
    ).toEqual({});

    expect(
      normalizeDynamicAttrsToTemplateKeys(
        {
          '': 'ignorar',
          referencia: 'REF-10',
          descricao: null,
        },
        [
          { attribute_key: 'referencia' },
          { attribute_key: 'descricao_curta', label: undefined },
          { attribute_key: 'titulo_auto', label: '' },
        ]
      )
    ).toEqual(
      expect.objectContaining({
        referencia: 'REF-10',
      })
    );
  });

  test('extracts IA suggestions and builds product form state with safe fallbacks', () => {
    const initialSnapshot = {
      nome_base: '',
      dynamic_attributes: {},
    };

    expect(
      buildProductFormState(null, [], new Set(), initialSnapshot)
    ).toEqual({
      formData: initialSnapshot,
      iaSuggestions: {},
      selectedIaSuggestions: {},
    });

    expect(extractIaSuggestionMap(null)).toEqual({});
    expect(
      extractIaSuggestionMap({
        especificacoes_tecnicas_dict: Object.create(
          { herdado: 'ignorar' },
          {
            largura: { value: '20cm', enumerable: true },
            material: { value: 'Aco', enumerable: true },
          }
        ),
      })
    ).toEqual({
      largura: '20cm',
      material: 'Aco',
    });

    expect(
      buildProductFormState(
        {
          product_type: {
            id: 7,
            attribute_templates: [{ attribute_key: 'cor', label: '' }],
          },
          dynamic_attributes: {
            cor: '',
            nome: 'Filtro premium',
          },
          imagens_secundarias_urls: null,
          dados_brutos_web: {
            especificacoes_tecnicas_dict: { pressao: '10bar' },
            titulos_sugeridos_gerados: ['Titulo A'],
          },
          ativo_marketplace: null,
          log_enriquecimento_web: null,
          status_enriquecimento_web: '',
          status_titulo_ia: undefined,
          status_descricao_ia: undefined,
        },
        [{ id: 7, attribute_templates: [{ attribute_key: 'cor', label: 'Cor' }] }],
        new Set(['nome_base']),
        {
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
        }
      )
    ).toEqual(
      expect.objectContaining({
        formData: expect.objectContaining({
          dynamic_attributes: { cor: '', nome: 'Filtro premium' },
          imagens_secundarias_urls: [],
          titulos_sugeridos: ['Titulo A'],
          ativo_marketplace: false,
          log_enriquecimento_web: { historico_mensagens: [] },
          status_enriquecimento_web: null,
          status_titulo_ia: null,
          status_descricao_ia: null,
        }),
        iaSuggestions: { pressao: '10bar' },
        selectedIaSuggestions: { pressao: false },
      })
    );

    expect(
      buildProductFormState(
        {
          dynamic_attributes: 'invalido',
          product_type_id: '',
          product_type: { id: 9 },
        },
        [
          {
            id: 9,
            attribute_templates: [{ attribute_key: 'codigo_fabricante', label: 'Codigo' }],
          },
        ],
        new Set(),
        initialSnapshot
      )
    ).toEqual(
      expect.objectContaining({
        formData: expect.objectContaining({
          dynamic_attributes: {},
        }),
      })
    );

    expect(
      buildProductFormState(
        {
          dynamic_attributes: { sku_tecnico: 'ABC-10' },
          product_type_id: 3,
          dados_brutos_web: null,
        },
        { id: 3, attribute_templates: [{ attribute_key: 'sku_tecnico', label: 'SKU Tecnico' }] },
        new Set(),
        initialSnapshot
      )
    ).toEqual(
      expect.objectContaining({
        formData: expect.objectContaining({
          dynamic_attributes: { sku_tecnico: 'ABC-10' },
          dados_brutos_web: {},
        }),
      })
    );
  });

  test('coerceFormFieldValue keeps checkbox and plain values stable', () => {
    expect(coerceFormFieldValue('ativo_marketplace', 'ignored', 'checkbox', false)).toBe(false);
    expect(coerceFormFieldValue('nome_base', 'Produto X', 'text', true)).toBe('Produto X');
  });

  test('resolves ai mode, stage and dynamic template defaults', () => {
    expect(resolveShowAiFeatures(true, 'basic')).toBe(true);
    expect(resolveShowAiFeatures(undefined, 'complete')).toBe(true);
    expect(resolveShowAiFeatures(undefined, 'basic')).toBe(false);

    expect(resolveProductFormStage({ id: 10 }, '', '')).toBe('form');
    expect(resolveProductFormStage(null, '', '')).toBe('selectFornecedor');
    expect(resolveProductFormStage(null, 1, '')).toBe('selectType');
    expect(resolveProductFormStage(null, 1, 2)).toBe('form');

    expect(
      buildInitialDynamicAttributes(
        {
          attribute_templates: [
            { attribute_key: 'titulo_auto', field_type: 'text', default_value: 'Padrao' },
            { attribute_key: 'ativo_marketplace', field_type: 'boolean', default_value: '1' },
            { attribute_key: 'manual', field_type: 'boolean', default_value: null },
          ],
        },
        new Set(['ativo_marketplace'])
      )
    ).toEqual({
      titulo_auto: 'Padrao',
      manual: false,
    });

    expect(buildInitialDynamicAttributes(null, new Set())).toBeNull();
  });

  test('buildInitialDynamicAttributes handles boolean false defaults and non-string field types', () => {
    expect(
      buildInitialDynamicAttributes(
        {
          attribute_templates: [
            { attribute_key: 'ativo', field_type: 'boolean', default_value: 'false' },
            { attribute_key: 'metadata', field_type: null, default_value: null },
            { attribute_key: 'flag', field_type: 'boolean', default_value: '1' },
          ],
        },
        new Set()
      )
    ).toEqual({
      ativo: false,
      metadata: '',
      flag: true,
    });
  });

  test('sanitizes numeric fields and resolves service errors by priority', () => {
    expect(
      sanitizeProdutoData({
        preco_custo: '10.5',
        preco_venda: '',
        preco_promocional: '8.9',
        estoque_disponivel: '3',
        peso_gramas: '',
        fornecedor_id: '12',
        product_type_id: '',
      })
    ).toEqual(
      expect.objectContaining({
        preco_custo: 10.5,
        preco_venda: null,
        preco_promocional: 8.9,
        estoque_disponivel: 3,
        peso_gramas: null,
        fornecedor_id: 12,
        product_type_id: null,
      })
    );

    expect(resolveServiceErrorDetail({ message: 'mensagem direta' }, 'fallback')).toBe(
      'mensagem direta'
    );
    expect(resolveServiceErrorDetail({ detail: 'detalhe' }, 'fallback')).toBe('detalhe');
    expect(
      resolveServiceErrorDetail({ response: { data: { detail: 'backend detail' } } }, 'fallback')
    ).toBe('backend detail');
    expect(
      resolveServiceErrorDetail({ response: { data: { msg: 'backend msg' } } }, 'fallback')
    ).toBe('backend msg');
    expect(resolveServiceErrorDetail(null, 'fallback')).toBe('fallback');
  });

  test('routes content view through callback, location fallback or noop', () => {
    const onClose = jest.fn();
    const onOpenContentView = jest.fn();
    const locationAssign = jest.fn();

    expect(handleContentViewNavigation(10, onClose, onOpenContentView, locationAssign)).toBe(
      'callback'
    );
    expect(onClose).toHaveBeenCalled();
    expect(onOpenContentView).toHaveBeenCalledWith(10);
    expect(locationAssign).not.toHaveBeenCalled();

    onClose.mockClear();
    onOpenContentView.mockClear();

    expect(handleContentViewNavigation(11, undefined, undefined, locationAssign)).toBe('location');
    expect(locationAssign).toHaveBeenCalledWith('/produtos/11/conteudo');

    expect(handleContentViewNavigation(12, undefined, undefined, undefined)).toBe('noop');
  });

  test('only logs async polling errors for the active run', () => {
    const logFn = jest.fn();

    expect(logAsyncPollError(logFn, 10, 10, 'poll', new Error('x'))).toBe(true);
    expect(logFn).toHaveBeenCalledWith('poll', expect.any(Error));

    logFn.mockClear();
    expect(logAsyncPollError(logFn, 11, 10, 'poll', new Error('x'))).toBe(false);
    expect(logFn).not.toHaveBeenCalled();
  });
});
