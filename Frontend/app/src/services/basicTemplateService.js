/**
 * Basic generation template persistence for non-AI mode.
 */

const STORAGE_KEY = 'catalogai_basic_generation_templates_v1';

const DEFAULT_BASIC_GENERATION_TEMPLATES = {
  titleTemplate: '{nome_base} {marca} {modelo} {sku} {keyword}',
  descriptionTemplate: [
    '{intro}',
    '',
    '{descricao_web}',
    '',
    'Especificacoes tecnicas:',
    '{specs}',
    '',
    'Destaques:',
    '{bullets}',
    '',
    'Palavras-chave: {keywords}',
  ].join('\n'),
};

function normalizeTemplate(value, fallbackValue) {
  const text = String(value || '').trim();
  if (!text) {
    return fallbackValue;
  }
  return text.slice(0, 2000);
}

function safeParse(value) {
  if (!value) {
    return {};
  }
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function getBasicGenerationTemplates() {
  if (typeof window === 'undefined') {
    return { ...DEFAULT_BASIC_GENERATION_TEMPLATES };
  }
  const parsed = safeParse(window.localStorage.getItem(STORAGE_KEY));
  return {
    titleTemplate: normalizeTemplate(
      parsed.titleTemplate,
      DEFAULT_BASIC_GENERATION_TEMPLATES.titleTemplate
    ),
    descriptionTemplate: normalizeTemplate(
      parsed.descriptionTemplate,
      DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate
    ),
  };
}

function saveBasicGenerationTemplates(partialTemplates = {}) {
  const current = getBasicGenerationTemplates();
  const merged = {
    titleTemplate: normalizeTemplate(
      partialTemplates.titleTemplate ?? current.titleTemplate,
      DEFAULT_BASIC_GENERATION_TEMPLATES.titleTemplate
    ),
    descriptionTemplate: normalizeTemplate(
      partialTemplates.descriptionTemplate ?? current.descriptionTemplate,
      DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate
    ),
  };

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  }
  return merged;
}

function resetBasicGenerationTemplates() {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(STORAGE_KEY);
  }
  return { ...DEFAULT_BASIC_GENERATION_TEMPLATES };
}

function resolveCustomTemplateForRequest(kind, explicitTemplate) {
  const trimmedExplicit = String(explicitTemplate || '').trim();
  if (trimmedExplicit) {
    return trimmedExplicit;
  }
  const templates = getBasicGenerationTemplates();
  if (kind === 'title') {
    return templates.titleTemplate !== DEFAULT_BASIC_GENERATION_TEMPLATES.titleTemplate ?
    templates.titleTemplate :
    null;
  }
  if (kind === 'description') {
    return templates.descriptionTemplate !== DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate ?
    templates.descriptionTemplate :
    null;
  }
  return null;
}

export {
  DEFAULT_BASIC_GENERATION_TEMPLATES,
  getBasicGenerationTemplates,
  saveBasicGenerationTemplates,
  resetBasicGenerationTemplates,
  resolveCustomTemplateForRequest,
};

export default {
  DEFAULT_BASIC_GENERATION_TEMPLATES,
  getBasicGenerationTemplates,
  saveBasicGenerationTemplates,
  resetBasicGenerationTemplates,
  resolveCustomTemplateForRequest,
};
