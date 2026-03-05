import productService from '../productService';
import apiClient from '../apiClient';

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

describe('productService basic generation fallback', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
});
