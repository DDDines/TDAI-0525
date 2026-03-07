import historicoService, { getHistorico } from '../historicoService';
import apiClient from '../apiClient';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

describe('historicoService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('forwards params to the historico endpoint', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: { items: [{ id: 1 }], total_items: 1 } })
      .mockResolvedValueOnce({ data: { items: [{ id: 1 }], total_items: 1 } });

    await expect(getHistorico({ skip: 20, limit: 10 })).resolves.toEqual({
      items: [{ id: 1 }],
      total_items: 1,
    });
    await expect(historicoService.getHistorico({ limit: 5 })).resolves.toEqual({
      items: [{ id: 1 }],
      total_items: 1,
    });

    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/historico/', {
      params: { skip: 20, limit: 10 },
    });
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/historico/', {
      params: { limit: 5 },
    });
  });

  test('uses an empty params object by default', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { items: [] } });

    await expect(getHistorico()).resolves.toEqual({ items: [] });

    expect(apiClient.get).toHaveBeenCalledWith('/historico/', {
      params: {},
    });
  });
});
