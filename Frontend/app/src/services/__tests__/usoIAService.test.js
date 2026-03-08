import usoIAService from '../usoIAService';
import apiClient from '../apiClient';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

describe('usoIAService', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('gets IA usage history for a product and for the current user', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: [{ id: 1 }] })
      .mockResolvedValueOnce({ data: { items: [{ id: 2 }], total_items: 1 } });

    await expect(
      usoIAService.getHistoricoUsoIAPorProduto(2558, { skip: 0, limit: 5 })
    ).resolves.toEqual([{ id: 1 }]);
    await expect(usoIAService.getMeuHistoricoUsoIA({ tipo_acao: 'geracao' })).resolves.toEqual({
      items: [{ id: 2 }],
      total_items: 1,
    });

    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/uso-ia/por-produto/2558', {
      params: { skip: 0, limit: 5 },
    });
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/uso-ia/', {
      params: { tipo_acao: 'geracao' },
    });
  });

  test('returns backend payloads on product-history and my-history failures', async () => {
    apiClient.get
      .mockRejectedValueOnce({ response: { data: { detail: 'produto indisponivel' } } })
      .mockRejectedValueOnce({ response: { data: { detail: 'usuario sem acesso' } } });

    await expect(usoIAService.getHistoricoUsoIAPorProduto(12)).rejects.toEqual({
      detail: 'produto indisponivel',
    });
    await expect(usoIAService.getMeuHistoricoUsoIA()).rejects.toEqual({
      detail: 'usuario sem acesso',
    });
  });

  test('gets history types and falls back to explicit errors on failures', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: ['geracao_titulo_ia'] })
      .mockRejectedValueOnce(new Error('timeout'))
      .mockRejectedValueOnce(new Error('offline'));

    await expect(usoIAService.getTiposHistorico()).resolves.toEqual(['geracao_titulo_ia']);
    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/historico/tipos');

    await expect(usoIAService.getMeuHistoricoUsoIA()).rejects.toThrow(
      'Failed to fetch my IA usage history'
    );
    await expect(usoIAService.getTiposHistorico()).rejects.toThrow(
      'Failed to fetch historico types'
    );
  });

  test('falls back to explicit errors when the product history request has no backend payload', async () => {
    apiClient.get.mockRejectedValueOnce(new Error('offline'));

    await expect(usoIAService.getHistoricoUsoIAPorProduto(99)).rejects.toThrow(
      'Failed to fetch IA usage history for product 99'
    );
  });
});
