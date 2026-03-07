import basicTemplateService, {
  DEFAULT_BASIC_GENERATION_TEMPLATES,
} from '../basicTemplateService';

const STORAGE_KEY = 'catalogai_basic_generation_templates_v1';

describe('basicTemplateService', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  test('returns default templates when storage is empty', () => {
    const templates = basicTemplateService.getBasicGenerationTemplates();

    expect(templates).toEqual(DEFAULT_BASIC_GENERATION_TEMPLATES);
  });

  test('returns defaults when localStorage is unavailable', () => {
    const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'localStorage');

    Object.defineProperty(window, 'localStorage', {
      value: undefined,
      configurable: true,
      writable: true,
    });

    expect(basicTemplateService.getBasicGenerationTemplates()).toEqual(
      DEFAULT_BASIC_GENERATION_TEMPLATES
    );

    Object.defineProperty(window, 'localStorage', originalDescriptor);
  });

  test('falls back to defaults when storage contains invalid or empty values', () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        titleTemplate: '   ',
        descriptionTemplate: '',
      })
    );

    expect(basicTemplateService.getBasicGenerationTemplates()).toEqual(
      DEFAULT_BASIC_GENERATION_TEMPLATES
    );

    window.localStorage.setItem(STORAGE_KEY, '{invalid-json');
    expect(basicTemplateService.getBasicGenerationTemplates()).toEqual(
      DEFAULT_BASIC_GENERATION_TEMPLATES
    );

    window.localStorage.setItem(STORAGE_KEY, '[]');
    expect(basicTemplateService.getBasicGenerationTemplates()).toEqual(
      DEFAULT_BASIC_GENERATION_TEMPLATES
    );
  });

  test('persists merged templates and trims overlong values', () => {
    const longDescription = 'x'.repeat(2505);

    basicTemplateService.saveBasicGenerationTemplates({
      titleTemplate: '{nome_base} {sku}',
      descriptionTemplate: longDescription,
    });

    const templates = basicTemplateService.getBasicGenerationTemplates();
    expect(templates.titleTemplate).toBe('{nome_base} {sku}');
    expect(templates.descriptionTemplate).toHaveLength(2000);

    const merged = basicTemplateService.saveBasicGenerationTemplates({
      titleTemplate: '   ',
    });

    expect(merged.titleTemplate).toBe(DEFAULT_BASIC_GENERATION_TEMPLATES.titleTemplate);
    expect(merged.descriptionTemplate).toHaveLength(2000);
  });

  test('supports empty saves, stringified payloads and environments without localStorage setters', () => {
    expect(basicTemplateService.saveBasicGenerationTemplates()).toEqual(
      DEFAULT_BASIC_GENERATION_TEMPLATES
    );

    window.localStorage.setItem(STORAGE_KEY, JSON.stringify('invalid-type'));
    expect(basicTemplateService.getBasicGenerationTemplates()).toEqual(
      DEFAULT_BASIC_GENERATION_TEMPLATES
    );

    const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'localStorage');
    Object.defineProperty(window, 'localStorage', {
      value: undefined,
      configurable: true,
      writable: true,
    });

    expect(
      basicTemplateService.saveBasicGenerationTemplates({
        titleTemplate: '{nome_base}',
      })
    ).toEqual({
      titleTemplate: '{nome_base}',
      descriptionTemplate: DEFAULT_BASIC_GENERATION_TEMPLATES.descriptionTemplate,
    });

    Object.defineProperty(window, 'localStorage', originalDescriptor);
  });

  test('resets persisted templates and resolves request-specific overrides', () => {
    basicTemplateService.saveBasicGenerationTemplates({
      titleTemplate: '{nome_base} {sku}',
      descriptionTemplate: 'Resumo: {descricao_web}',
    });

    expect(
      basicTemplateService.resolveCustomTemplateForRequest('title', '  {titulo_explicito}  ')
    ).toBe('{titulo_explicito}');
    expect(basicTemplateService.resolveCustomTemplateForRequest('title')).toBe(
      '{nome_base} {sku}'
    );
    expect(basicTemplateService.resolveCustomTemplateForRequest('description')).toBe(
      'Resumo: {descricao_web}'
    );

    const resetTemplates = basicTemplateService.resetBasicGenerationTemplates();
    expect(resetTemplates).toEqual(DEFAULT_BASIC_GENERATION_TEMPLATES);
    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(basicTemplateService.resolveCustomTemplateForRequest('title')).toBeNull();
    expect(basicTemplateService.resolveCustomTemplateForRequest('unknown')).toBeNull();
    expect(basicTemplateService.resolveCustomTemplateForRequest('description', '  ')).toBeNull();
  });
});
