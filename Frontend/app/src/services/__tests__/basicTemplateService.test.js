import basicTemplateService, {
  DEFAULT_BASIC_GENERATION_TEMPLATES,
  clearBasicGenerationTemplateCache,
} from '../basicTemplateService';
import apiClient from '../apiClient';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

const STORAGE_KEY = 'catalogai_basic_generation_templates_v1';

function buildApiOverview(overrides = {}) {
  const systemDefaults = overrides.systemDefaults || {
    title_template: DEFAULT_BASIC_GENERATION_TEMPLATES.titleTemplate,
    description_template: DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate,
  };

  return {
    company_identifier: overrides.companyIdentifier || 'catalogai',
    system_defaults: systemDefaults,
    company_config: overrides.companyConfig ?? null,
    user_config: overrides.userConfig ?? null,
    effective_config:
      overrides.effectiveConfig || {
        source: 'system',
        source_label: 'Sistema',
        is_custom: false,
        title_template: systemDefaults.title_template,
        description_template: systemDefaults.description_template,
      },
  };
}

describe('basicTemplateService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    clearBasicGenerationTemplateCache();
    window.localStorage.clear();
  });

  test('loads the normalized overview from the backend and caches subsequent reads', async () => {
    apiClient.get.mockResolvedValueOnce({
      data: buildApiOverview({
        userConfig: {
          scope_type: 'user',
          title_template: '{nome_base} {marca}',
          description_template: 'Resumo: {technical_summary}',
        },
        effectiveConfig: {
          source: 'user',
          source_label: 'Pessoal',
          is_custom: true,
          title_template: '{nome_base} {marca}',
          description_template: 'Resumo: {technical_summary}',
        },
      }),
    });

    const overview = await basicTemplateService.getBasicGenerationTemplateOverview();
    const templates = await basicTemplateService.getBasicGenerationTemplates();

    expect(overview).toEqual({
      companyIdentifier: 'catalogai',
      systemDefaults: DEFAULT_BASIC_GENERATION_TEMPLATES,
      companyConfig: null,
      userConfig: {
        scope_type: 'user',
        title_template: '{nome_base} {marca}',
        description_template: 'Resumo: {technical_summary}',
        titleTemplate: '{nome_base} {marca}',
        descriptionTemplate: 'Resumo: {technical_summary}',
      },
      effectiveConfig: {
        source: 'user',
        sourceLabel: 'Pessoal',
        isCustom: true,
        titleTemplate: '{nome_base} {marca}',
        descriptionTemplate: 'Resumo: {technical_summary}',
      },
    });

    expect(templates).toEqual({
      source: 'user',
      sourceLabel: 'Pessoal',
      isCustom: true,
      titleTemplate: '{nome_base} {marca}',
      descriptionTemplate: 'Resumo: {technical_summary}',
    });
    expect(apiClient.get).toHaveBeenCalledTimes(1);
  });

  test('migrates legacy localStorage templates to the backend once when no override exists', async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        titleTemplate: '{nome_base} {sku}',
        descriptionTemplate: 'Resumo legado',
      })
    );

    apiClient.get
      .mockResolvedValueOnce({
        data: buildApiOverview(),
      })
      .mockResolvedValueOnce({
        data: buildApiOverview({
          userConfig: {
            scope_type: 'user',
            title_template: '{nome_base} {sku}',
            description_template: 'Resumo legado',
          },
          effectiveConfig: {
            source: 'user',
            source_label: 'Pessoal',
            is_custom: true,
            title_template: '{nome_base} {sku}',
            description_template: 'Resumo legado',
          },
        }),
      });
    apiClient.put.mockResolvedValueOnce({});

    const overview = await basicTemplateService.getBasicGenerationTemplateOverview({
      preferFresh: true,
    });

    expect(apiClient.put).toHaveBeenCalledWith('/templates-basicos', {
      scope_type: 'user',
      title_template: '{nome_base} {sku}',
      description_template: 'Resumo legado',
      is_active: true,
    });
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(overview.effectiveConfig.titleTemplate).toBe('{nome_base} {sku}');
    expect(overview.effectiveConfig.source).toBe('user');
  });

  test('saves templates for the selected scope and returns the refreshed overview', async () => {
    apiClient.get
      .mockResolvedValueOnce({
        data: buildApiOverview({
          companyConfig: {
            scope_type: 'company',
            title_template: '{titulo_base}',
            description_template: DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate,
          },
        }),
      })
      .mockResolvedValueOnce({
        data: buildApiOverview({
          companyConfig: {
            scope_type: 'company',
            title_template: '{nome_base} {marca}',
            description_template: 'Descricao corporativa',
          },
        }),
      });
    apiClient.put.mockResolvedValueOnce({});

    const result = await basicTemplateService.saveBasicGenerationTemplates(
      {
        titleTemplate: '{nome_base} {marca}',
        descriptionTemplate: 'Descricao corporativa',
      },
      { scope: 'company' }
    );

    expect(apiClient.put).toHaveBeenCalledWith('/templates-basicos', {
      scope_type: 'company',
      title_template: '{nome_base} {marca}',
      description_template: 'Descricao corporativa',
      is_active: true,
    });
    expect(result.scope).toBe('company');
    expect(result.titleTemplate).toBe('{nome_base} {marca}');
    expect(result.descriptionTemplate).toBe('Descricao corporativa');
    expect(result.overview.companyConfig.titleTemplate).toBe('{nome_base} {marca}');
  });

  test('resets templates without calling delete when the selected scope has no stored config', async () => {
    apiClient.get.mockResolvedValueOnce({
      data: buildApiOverview(),
    });

    const result = await basicTemplateService.resetBasicGenerationTemplates({
      scope: 'company',
    });

    expect(apiClient.delete).not.toHaveBeenCalled();
    expect(result).toEqual({
      ...DEFAULT_BASIC_GENERATION_TEMPLATES,
      overview: {
        companyIdentifier: 'catalogai',
        systemDefaults: DEFAULT_BASIC_GENERATION_TEMPLATES,
        companyConfig: null,
        userConfig: null,
        effectiveConfig: {
          source: 'system',
          sourceLabel: 'Sistema',
          isCustom: false,
          titleTemplate: DEFAULT_BASIC_GENERATION_TEMPLATES.titleTemplate,
          descriptionTemplate: DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate,
        },
      },
      scope: 'company',
    });
  });

  test('resolveCustomTemplateForRequest prefers explicit templates and effective overrides', async () => {
    expect(
      await basicTemplateService.resolveCustomTemplateForRequest('title', '  {titulo_explicito}  ')
    ).toBe('{titulo_explicito}');
    expect(apiClient.get).not.toHaveBeenCalled();

    apiClient.get.mockResolvedValueOnce({
      data: buildApiOverview({
        effectiveConfig: {
          source: 'user',
          source_label: 'Pessoal',
          is_custom: true,
          title_template: '{nome_base} {sku}',
          description_template: 'Resumo customizado',
        },
      }),
    });

    await expect(
      basicTemplateService.resolveCustomTemplateForRequest('title')
    ).resolves.toBe('{nome_base} {sku}');
    await expect(
      basicTemplateService.resolveCustomTemplateForRequest('description')
    ).resolves.toBe('Resumo customizado');
    await expect(
      basicTemplateService.resolveCustomTemplateForRequest('unknown')
    ).resolves.toBeNull();
  });

  test('falls back to legacy templates when the backend is unavailable', async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        titleTemplate: '{nome_base} {sku}',
        descriptionTemplate: 'Resumo legado',
      })
    );
    apiClient.get.mockRejectedValueOnce(new Error('offline'));
    apiClient.get.mockRejectedValueOnce(new Error('offline'));
    apiClient.get.mockRejectedValueOnce(new Error('offline'));

    await expect(
      basicTemplateService.resolveCustomTemplateForRequest('title')
    ).resolves.toBe('{nome_base} {sku}');
    await expect(
      basicTemplateService.resolveCustomTemplateForRequest('description')
    ).resolves.toBe('Resumo legado');
    await expect(
      basicTemplateService.resolveCustomTemplateForRequest('unknown')
    ).resolves.toBeNull();
  });
});
