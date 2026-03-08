import { buildListQueryKey, normalizeKeyValue, queryKeys } from '../queryKeys.js';

describe('queryKeys', () => {
  test('normalizes scalars, arrays and nested objects while removing empty values', () => {
    expect(
      normalizeKeyValue({
        z: '',
        b: 2,
        a: {
          empty: undefined,
          nested: 'ok',
        },
        list: [1, null, 'x'],
      })
    ).toEqual({
      a: { nested: 'ok' },
      b: 2,
      list: [1, undefined, 'x'],
    });
  });

  test('builds stable list keys with sorted params', () => {
    expect(buildListQueryKey('produtos', { b: 2, a: 1, vazio: '' })).toEqual([
      'produtos',
      { a: 1, b: 2 },
    ]);
  });

  test('exports domain-specific query-key factories', () => {
    expect(queryKeys.productTypes()).toEqual(['product-types']);
    expect(queryKeys.produtos({ search: 'abc' })).toEqual(['produtos', { search: 'abc' }]);
    expect(queryKeys.produto(7)).toEqual(['produto', '7']);
    expect(queryKeys.orderedProductIds({ sort_by: 'id' })).toEqual([
      'produto-navigation',
      { sort_by: 'id' },
    ]);
    expect(queryKeys.fornecedores({ termo_busca: 'x' })).toEqual([
      'fornecedores',
      { termo_busca: 'x' },
    ]);
    expect(queryKeys.catalogImportStatus(8)).toEqual(['catalog-import-status', '8']);
    expect(queryKeys.catalogImportResult(8)).toEqual(['catalog-import-result', '8']);
    expect(queryKeys.fornecedorImportProgress(9)).toEqual([
      'fornecedor-import-progress',
      '9',
    ]);
  });
});
