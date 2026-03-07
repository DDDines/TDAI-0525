import {
  coerceFormFieldValue,
  extractGeneratedTitles,
  normalizeDynamicAttrsToTemplateKeys,
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
});
