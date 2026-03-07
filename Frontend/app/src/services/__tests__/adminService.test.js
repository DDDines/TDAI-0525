import adminService from '../adminService';
import apiClient from '../apiClient';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

describe('adminService', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('gets total counts from the analytics endpoint', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { products: 12, suppliers: 4 } });

    await expect(adminService.getTotalCounts()).resolves.toEqual({
      products: 12,
      suppliers: 4,
    });

    expect(apiClient.get).toHaveBeenCalledWith('/admin/analytics/counts');
  });

  test('throws a fallback error when total counts request has no backend payload', async () => {
    apiClient.get.mockRejectedValueOnce(new Error('network down'));

    await expect(adminService.getTotalCounts()).rejects.toThrow(
      'Falha ao buscar contagens totais.'
    );
  });

  test('rethrows backend payload for status counts and recent activities', async () => {
    apiClient.get
      .mockRejectedValueOnce({ response: { data: { detail: 'status indisponivel' } } })
      .mockResolvedValueOnce({ data: [{ id: 1, acao: 'geracao' }] });

    await expect(adminService.getProductStatusCounts()).rejects.toEqual({
      detail: 'status indisponivel',
    });
    await expect(adminService.getRecentActivities()).resolves.toEqual([
      { id: 1, acao: 'geracao' },
    ]);

    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/admin/analytics/product-status-counts');
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/admin/analytics/recent-activities');
  });

  test('gets recent history with the provided limit and falls back on missing payloads', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: [{ id: 5 }] })
      .mockRejectedValueOnce(new Error('timeout'));

    await expect(adminService.getRecentHistorico(9)).resolves.toEqual([{ id: 5 }]);
    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/admin/analytics/recent-historico', {
      params: { limit: 9 },
    });

    await expect(adminService.getRecentHistorico()).rejects.toThrow(
      'Falha ao buscar histórico recente.'
    );
  });
});
