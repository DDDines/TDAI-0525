import {
  formatCellValue,
  getPreviewImageSrc,
  formatElapsed,
  normalizePayloadStrings,
} from '../ImportCatalogWizard.helpers.js';

describe('ImportCatalogWizard helpers', () => {
  test('formats cell values and preview image sources safely', () => {
    expect(formatCellValue(null)).toBe('');
    expect(formatCellValue(undefined)).toBe('');
    expect(formatCellValue({ sku: 'ABC' })).toBe('{"sku":"ABC"}');
    expect(formatCellValue(42)).toBe('42');

    expect(getPreviewImageSrc('')).toBeNull();
    expect(getPreviewImageSrc('   ')).toBeNull();
    expect(getPreviewImageSrc('data:image/png;base64,abc')).toBe('data:image/png;base64,abc');
    expect(getPreviewImageSrc('raw-base64')).toBe('data:image/png;base64,raw-base64');
    expect(getPreviewImageSrc({ image: 'data:image/png;base64,xyz' })).toBe(
      'data:image/png;base64,xyz'
    );
    expect(getPreviewImageSrc({})).toBeNull();
  });

  test('formats elapsed time and normalizes nested payload strings', () => {
    expect(formatElapsed(-1)).toBe('0s');
    expect(formatElapsed(Number.NaN)).toBe('0s');
    expect(formatElapsed(7)).toBe('7s');
    expect(formatElapsed(125)).toBe('2m 5s');

    expect(
      normalizePayloadStrings({
        headline: 'Relat?rio',
        lines: ['Importa??o conclu?da', { label: 'Descri??o' }],
      })
    ).toEqual({
      headline: 'Relatório',
      lines: ['Importação concluída', { label: 'Descrição' }],
    });
  });
});
