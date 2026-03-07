import { extractErrorMessage } from '../errorDetails';

describe('extractErrorMessage', () => {
  test('handles the supported payload shapes in priority order', () => {
    expect(extractErrorMessage(null, 'fallback')).toBe('fallback');
    expect(extractErrorMessage('erro bruto', 'fallback')).toBe('erro bruto');
    expect(extractErrorMessage({ detail: 'detalhe' }, 'fallback')).toBe('detalhe');
    expect(
      extractErrorMessage(
        { detail: [{ loc: ['body', 'nome'], msg: 'obrigatorio' }, { msg: 'generico' }] },
        'fallback'
      )
    ).toBe('body.nome: obrigatorio; generico');
    expect(extractErrorMessage({ detail: { campo: 'sku' } }, 'fallback')).toBe(
      '{"campo":"sku"}'
    );
    expect(extractErrorMessage({ message: 'timeout' }, 'fallback')).toBe('timeout');
    expect(extractErrorMessage({ status: 500 }, 'fallback')).toBe('fallback');
  });
});
