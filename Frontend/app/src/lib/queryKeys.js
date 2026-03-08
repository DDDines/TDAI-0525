/**
 * Stable query-key builders for server state.
 */

function normalizeKeyValue(value) {
  if (value === undefined || value === null || value === '') {
    return undefined;
  }
  if (Array.isArray(value)) {
    return value.map((item) => normalizeKeyValue(item));
  }
  if (typeof value === 'object') {
    const normalized = {};
    Object.keys(value)
      .sort()
      .forEach((key) => {
        const nextValue = normalizeKeyValue(value[key]);
        if (nextValue !== undefined) {
          normalized[key] = nextValue;
        }
      });
    return normalized;
  }
  return value;
}

function buildListQueryKey(baseKey, params = {}) {
  return [baseKey, normalizeKeyValue(params) || {}];
}

const queryKeys = {
  productTypes: () => ['product-types'],
  produtos: (params = {}) => buildListQueryKey('produtos', params),
  produto: (produtoId) => ['produto', String(produtoId ?? '')],
  orderedProductIds: (params = {}) => buildListQueryKey('produto-navigation', params),
  fornecedores: (params = {}) => buildListQueryKey('fornecedores', params),
  catalogImportStatus: (fileId) => ['catalog-import-status', String(fileId ?? '')],
  catalogImportResult: (fileId) => ['catalog-import-result', String(fileId ?? '')],
  fornecedorImportProgress: (jobId) => ['fornecedor-import-progress', String(jobId ?? '')],
};

export { buildListQueryKey, normalizeKeyValue, queryKeys };
