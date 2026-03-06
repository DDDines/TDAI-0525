import productService from '../productService';
import apiClient from '../apiClient';
import basicTemplateService from '../basicTemplateService';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('../basicTemplateService', () => ({
  __esModule: true,
  default: {
    resolveCustomTemplateForRequest: jest.fn(() => null),
  },
}));

describe('productService basic generation fallback', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    basicTemplateService.resolveCustomTemplateForRequest.mockReturnValue(null);
  });

  test('gerarTitulosProdutoModoBasico calls backend basic generation endpoint', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { msg: 'ok' } });

    await productService.gerarTitulosProdutoModoBasico(10);

    expect(apiClient.post).toHaveBeenCalledWith('/geracao/titulos/basico/10');
  });

  test('gerarDescricaoProdutoModoBasico calls backend basic generation endpoint', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { msg: 'ok' } });

    await productService.gerarDescricaoProdutoModoBasico(22);

    expect(apiClient.post).toHaveBeenCalledWith('/geracao/descricao/basico/22');
  });

  test('gerarTitulosProdutoModoBasico sends custom template when available', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { msg: 'ok' } });
    basicTemplateService.resolveCustomTemplateForRequest.mockReturnValueOnce(
      '{nome_base} {sku}'
    );

    await productService.gerarTitulosProdutoModoBasico(33);

    expect(apiClient.post).toHaveBeenCalledWith(
      '/geracao/titulos/basico/33',
      null,
      {
        params: {
          template: '{nome_base} {sku}',
        },
      }
    );
  });
});
