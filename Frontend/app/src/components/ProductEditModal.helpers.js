/**
 * Product edit modal helper functions.
 *
 * Centralizes pure data coercion and normalization used by ProductEditModal.
 */
function foldText(value) {
  return String(value || '')
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function isEmptyLike(value) {
  if (value === null || value === undefined) return true;
  const text = String(value).trim();
  if (!text) return true;
  const folded = foldText(text);
  return ['none', 'null', 'nan', 'na', '-', '--'].includes(folded);
}

function extractGeneratedTitles(prod) {
  const directTitles = Array.isArray(prod?.titulos_sugeridos) ? prod.titulos_sugeridos : [];
  const rawTitles = Array.isArray(prod?.dados_brutos_web?.titulos_sugeridos_gerados)
    ? prod.dados_brutos_web.titulos_sugeridos_gerados
    : [];
  const merged = [...directTitles, ...rawTitles]
    .map((item) => String(item || '').trim())
    .filter(Boolean);
  const seen = new Set();
  const unique = [];
  merged.forEach((item) => {
    const folded = item.toLowerCase();
    if (seen.has(folded)) return;
    seen.add(folded);
    unique.push(item);
  });
  return unique.slice(0, 10);
}

function normalizeDynamicAttrsToTemplateKeys(dynamicAttrsRaw, attributeTemplates) {
  const result = { ...(dynamicAttrsRaw || {}) };
  const entries = Object.entries(dynamicAttrsRaw || {});

  const findAliasValue = (aliases) => {
    for (const [key, value] of entries) {
      if (isEmptyLike(value)) continue;
      const keyNorm = foldText(key);
      if (!keyNorm) continue;
      for (const alias of aliases) {
        const aliasNorm = foldText(alias);
        if (!aliasNorm) continue;
        if (
          keyNorm === aliasNorm ||
          keyNorm.includes(aliasNorm) ||
          aliasNorm.includes(keyNorm)
        ) {
          return value;
        }
      }
    }
    return null;
  };

  (attributeTemplates || []).forEach((tpl) => {
    const targetKey = tpl?.attribute_key;
    if (!targetKey) return;
    if (!isEmptyLike(result[targetKey])) return;

    const label = tpl?.label || targetKey;
    const labelNorm = foldText(label);
    const aliases = [label, targetKey];

    if (labelNorm.includes('titulo') || labelNorm.includes('title') || labelNorm.includes('nome')) {
      aliases.push('titulo', 'title', 'nome');
    }
    if (labelNorm === 'id' || labelNorm.includes('codigo') || labelNorm.includes('referencia')) {
      aliases.push('id', 'codigo_original', 'codigo', 'cod', 'referencia', 'ref');
    }
    if (labelNorm.includes('descricao') || labelNorm.includes('desc')) {
      aliases.push('descricao', 'description', 'desc');
    }

    const value = findAliasValue(aliases);
    if (!isEmptyLike(value)) {
      result[targetKey] = value;
    }
  });

  return result;
}

function coerceFormFieldValue(name, value, type, checked) {
  if (name === 'imagens_secundarias_urls') {
    return value.split(',').map((url) => url.trim()).filter(Boolean);
  }
  if (type === 'checkbox') {
    return checked;
  }
  return value;
}

export { coerceFormFieldValue, extractGeneratedTitles, normalizeDynamicAttrsToTemplateKeys };
