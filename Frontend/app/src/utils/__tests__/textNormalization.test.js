import { normalizeDisplayText } from '../textNormalization';

describe('normalizeDisplayText', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('returns empty string for nullish values', () => {
    expect(normalizeDisplayText(null)).toBe('');
    expect(normalizeDisplayText(undefined)).toBe('');
  });

  test('fixes common mojibake replacements used by product flows', () => {
    expect(normalizeDisplayText('P??gina 2 com conte??do')).toBe('Página 2 com conteúdo');
    expect(normalizeDisplayText('Importa??o com erro cr?tico')).toBe('Importação com erro crítico');
  });

  test('normalizes whitespace after replacements', () => {
    expect(normalizeDisplayText('  Relat?rio    n?o dispon?veis  ')).toBe('Relatório não disponíveis');
  });

  test('returns the original text when TextDecoder throws', () => {
    const originalTextDecoder = global.TextDecoder;
    const textDecoderSpy = jest.spyOn(global, 'TextDecoder').mockImplementation(() => {
      throw new Error('decoder unavailable');
    });

    expect(normalizeDisplayText('P??gina 2')).toBe('Página 2');

    textDecoderSpy.mockRestore();
    global.TextDecoder = originalTextDecoder;
  });

  test('keeps the original text when decoding would add more mojibake markers', () => {
    const decode = jest.fn(() => 'ÃƒÃƒÃƒ');
    const textDecoderSpy = jest.spyOn(global, 'TextDecoder').mockImplementation(() => ({ decode }));

    expect(normalizeDisplayText('PÃƒ¡gina')).toBe('PÃƒ¡gina');

    textDecoderSpy.mockRestore();
  });

  test('adopts the decoded text when it reduces mojibake markers', () => {
    const decode = jest.fn(() => 'Página');
    const textDecoderSpy = jest.spyOn(global, 'TextDecoder').mockImplementation(() => ({ decode }));

    expect(normalizeDisplayText('PÃ¡gina')).toBe('Página');

    textDecoderSpy.mockRestore();
  });
});
