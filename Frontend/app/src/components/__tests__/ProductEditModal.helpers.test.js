import {
  buildInitialDynamicAttributes,
  coerceFormFieldValue,
  extractGeneratedTitles,
  normalizeDynamicAttrsToTemplateKeys,
  resolveProductFormStage,
  resolveServiceErrorDetail,
  resolveShowAiFeatures,
  sanitizeProdutoData,
} from '../ProductEditModal.helpers.js';

describe('ProductEditModal helpers', () => {
  test('extractGeneratedTitles handles missing arrays, falsy values and duplicate casing', () => {
    expect(extractGeneratedTitles()).toEqual([]);
    expect(
      extractGeneratedTitles({
        titulos_sugeridos: ['Titulo A', null, '  '],
        dados_brutos_web: { titulos_sugeridos_gerados: ['titulo a', 'Titulo B'] },
      })
    ).toEqual(['Titulo A', 'Titulo B']);
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
});
