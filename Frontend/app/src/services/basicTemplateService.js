/**
 * Basic generation template persistence for non-AI mode.
 */

import apiClient from './apiClient';

const LEGACY_STORAGE_KEY = 'catalogai_basic_generation_templates_v1';

const DEFAULT_BASIC_GENERATION_TEMPLATES = {
  titleTemplate: '{titulo_base}',
  descriptionTemplate: [
    '{nome_base}',
    '',
    'Resumo tecnico:',
    '{technical_summary}',
    '',
    'Aplicacao:',
    '{application}',
    '',
    'Referencia:',
    '{reference}',
    '',
    'Material:',
    '{material}',
    '',
    'Conteudo da embalagem:',
    '{content}',
    '',
    'Especificacoes tecnicas:',
    '{specs}',
    '',
    'Destaques tecnicos:',
    '{bullets}',
  ].join('\n'),
};

let cachedOverview = null;

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeTemplate(value, fallbackValue) {
  const text = String(value || '').replace(/\r\n/g, '\n').trim();
  if (!text) {
    return fallbackValue;
  }
  return text.slice(0, 2000);
}

function normalizeScope(scope) {
  return String(scope || '').trim().toLowerCase() === 'company' ? 'company' : 'user';
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

function readLegacyTemplates() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return { ...DEFAULT_BASIC_GENERATION_TEMPLATES };
  }
  const parsed = safeParse(window.localStorage.getItem(LEGACY_STORAGE_KEY));
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

function clearLegacyTemplates() {
  if (typeof window !== 'undefined' && window.localStorage) {
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
  }
}

function hasLegacyCustomTemplates(systemDefaults) {
  const legacyTemplates = readLegacyTemplates();
  return (
    legacyTemplates.titleTemplate !== systemDefaults.titleTemplate
    || legacyTemplates.descriptionTemplate !== systemDefaults.descriptionTemplate
  );
}

function normalizeConfig(config, systemDefaults) {
  if (!config) {
    return null;
  }
  return {
    ...config,
    titleTemplate: normalizeTemplate(config.title_template, systemDefaults.titleTemplate),
    descriptionTemplate: normalizeTemplate(
      config.description_template,
      systemDefaults.descriptionTemplate
    ),
  };
}

function normalizeOverviewPayload(payload = {}) {
  const systemDefaults = {
    titleTemplate: normalizeTemplate(
      payload?.system_defaults?.title_template,
      DEFAULT_BASIC_GENERATION_TEMPLATES.titleTemplate
    ),
    descriptionTemplate: normalizeTemplate(
      payload?.system_defaults?.description_template,
      DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate
    ),
  };

  const effectiveConfig = payload?.effective_config || {};

  return {
    companyIdentifier: payload?.company_identifier || null,
    systemDefaults,
    companyConfig: normalizeConfig(payload?.company_config, systemDefaults),
    userConfig: normalizeConfig(payload?.user_config, systemDefaults),
    effectiveConfig: {
      source: effectiveConfig?.source || 'system',
      sourceLabel: effectiveConfig?.source_label || 'Sistema',
      isCustom: Boolean(effectiveConfig?.is_custom),
      titleTemplate: normalizeTemplate(
        effectiveConfig?.title_template,
        systemDefaults.titleTemplate
      ),
      descriptionTemplate: normalizeTemplate(
        effectiveConfig?.description_template,
        systemDefaults.descriptionTemplate
      ),
    },
  };
}

function buildTemplatesForScope(overview, scope = 'user') {
  const normalizedScope = normalizeScope(scope);
  const sourceConfig = normalizedScope === 'company' ? overview.companyConfig : overview.userConfig;
  const fallback = overview.systemDefaults;
  return {
    titleTemplate: normalizeTemplate(sourceConfig?.titleTemplate, fallback.titleTemplate),
    descriptionTemplate: normalizeTemplate(
      sourceConfig?.descriptionTemplate,
      fallback.descriptionTemplate
    ),
  };
}

async function migrateLegacyTemplatesIfNeeded(overview) {
  if (!overview || overview.companyConfig || overview.userConfig) {
    return overview;
  }

  if (!hasLegacyCustomTemplates(overview.systemDefaults)) {
    clearLegacyTemplates();
    return overview;
  }

  const legacyTemplates = readLegacyTemplates();
  await apiClient.put('/templates-basicos', {
    scope_type: 'user',
    title_template: legacyTemplates.titleTemplate,
    description_template: legacyTemplates.descriptionTemplate,
    is_active: true,
  });
  clearLegacyTemplates();
  const response = await apiClient.get('/templates-basicos/overview');
  return normalizeOverviewPayload(response.data);
}

async function getBasicGenerationTemplateOverview(options = {}) {
  const preferFresh = Boolean(options?.preferFresh);
  if (cachedOverview && !preferFresh) {
    return clone(cachedOverview);
  }

  try {
    const response = await apiClient.get('/templates-basicos/overview');
    let normalizedOverview = normalizeOverviewPayload(response.data);
    normalizedOverview = await migrateLegacyTemplatesIfNeeded(normalizedOverview);
    cachedOverview = normalizedOverview;
    return clone(normalizedOverview);
  } catch (error) {
    throw error.response?.data || error;
  }
}

async function getBasicGenerationTemplates(options = {}) {
  const overview = await getBasicGenerationTemplateOverview(options);
  return {
    ...overview.effectiveConfig,
    ...buildTemplatesForScope(overview, options?.scope),
  };
}

async function saveBasicGenerationTemplates(partialTemplates = {}, options = {}) {
  const scope = normalizeScope(options?.scope);
  const overview = await getBasicGenerationTemplateOverview();
  const currentTemplates = buildTemplatesForScope(overview, scope);
  const payload = {
    scope_type: scope,
    title_template: normalizeTemplate(
      partialTemplates.titleTemplate ?? currentTemplates.titleTemplate,
      overview.systemDefaults.titleTemplate
    ),
    description_template: normalizeTemplate(
      partialTemplates.descriptionTemplate ?? currentTemplates.descriptionTemplate,
      overview.systemDefaults.descriptionTemplate
    ),
    is_active: true,
  };

  try {
    await apiClient.put('/templates-basicos', payload);
    cachedOverview = null;
    const refreshedOverview = await getBasicGenerationTemplateOverview({ preferFresh: true });
    return {
      ...buildTemplatesForScope(refreshedOverview, scope),
      overview: refreshedOverview,
      scope,
    };
  } catch (error) {
    throw error.response?.data || error;
  }
}

async function resetBasicGenerationTemplates(options = {}) {
  const scope = normalizeScope(options?.scope);
  const overview = await getBasicGenerationTemplateOverview();
  const scopeConfig = scope === 'company' ? overview.companyConfig : overview.userConfig;
  if (!scopeConfig) {
    return {
      ...buildTemplatesForScope(overview, scope),
      overview,
      scope,
    };
  }
  try {
    await apiClient.delete(`/templates-basicos/${scope}`);
  } catch (error) {
    throw error.response?.data || error;
  }
  cachedOverview = null;
  const refreshedOverview = await getBasicGenerationTemplateOverview({ preferFresh: true });
  return {
    ...buildTemplatesForScope(refreshedOverview, scope),
    overview: refreshedOverview,
    scope,
  };
}

async function resolveCustomTemplateForRequest(kind, explicitTemplate) {
  const trimmedExplicit = String(explicitTemplate || '').trim();
  if (trimmedExplicit) {
    return trimmedExplicit;
  }

  try {
    const overview = await getBasicGenerationTemplateOverview();
    if (kind === 'title') {
      return overview.effectiveConfig.titleTemplate !== overview.systemDefaults.titleTemplate
        ? overview.effectiveConfig.titleTemplate
        : null;
    }
    if (kind === 'description') {
      return overview.effectiveConfig.descriptionTemplate !== overview.systemDefaults.descriptionTemplate
        ? overview.effectiveConfig.descriptionTemplate
        : null;
    }
    return null;
  } catch {
    const legacyTemplates = readLegacyTemplates();
    if (kind === 'title') {
      return legacyTemplates.titleTemplate !== DEFAULT_BASIC_GENERATION_TEMPLATES.titleTemplate
        ? legacyTemplates.titleTemplate
        : null;
    }
    if (kind === 'description') {
      return legacyTemplates.descriptionTemplate !== DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate
        ? legacyTemplates.descriptionTemplate
        : null;
    }
    return null;
  }
}

function clearBasicGenerationTemplateCache() {
  cachedOverview = null;
}

export {
  DEFAULT_BASIC_GENERATION_TEMPLATES,
  clearBasicGenerationTemplateCache,
  getBasicGenerationTemplateOverview,
  getBasicGenerationTemplates,
  saveBasicGenerationTemplates,
  resetBasicGenerationTemplates,
  resolveCustomTemplateForRequest,
};

export default {
  DEFAULT_BASIC_GENERATION_TEMPLATES,
  clearBasicGenerationTemplateCache,
  getBasicGenerationTemplateOverview,
  getBasicGenerationTemplates,
  saveBasicGenerationTemplates,
  resetBasicGenerationTemplates,
  resolveCustomTemplateForRequest,
};
