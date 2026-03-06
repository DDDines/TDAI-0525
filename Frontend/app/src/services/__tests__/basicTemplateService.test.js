import basicTemplateService, {
  DEFAULT_BASIC_GENERATION_TEMPLATES,
} from '../basicTemplateService';

describe('basicTemplateService', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  test('returns default templates when storage is empty', () => {
    const templates = basicTemplateService.getBasicGenerationTemplates();
    expect(templates).toEqual(DEFAULT_BASIC_GENERATION_TEMPLATES);
  });

  test('persists and resolves custom templates', () => {
    basicTemplateService.saveBasicGenerationTemplates({
      titleTemplate: '{nome_base} {sku}',
      descriptionTemplate: 'Resumo: {descricao_web}',
    });

    const templates = basicTemplateService.getBasicGenerationTemplates();
    expect(templates.titleTemplate).toBe('{nome_base} {sku}');
    expect(templates.descriptionTemplate).toBe('Resumo: {descricao_web}');
    expect(
      basicTemplateService.resolveCustomTemplateForRequest('title')
    ).toBe('{nome_base} {sku}');
  });
});
