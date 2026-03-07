import searchService from '../searchService';
import apiClient from '../apiClient';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
  },
}));

describe('searchService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('trims the search term before sending it to the API', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { items: [{ id: 1 }] } });

    await expect(searchService.searchAll('  reservatorio  ')).resolves.toEqual({
      items: [{ id: 1 }],
    });

    expect(apiClient.get).toHaveBeenCalledWith('/search/', {
      params: { q: 'reservatorio' },
    });
  });

  test('sends an empty params object when the search term is blank', async () => {
    apiClient.get.mockResolvedValueOnce({ data: { items: [] } });

    await expect(searchService.searchAll('   ')).resolves.toEqual({ items: [] });

    expect(apiClient.get).toHaveBeenCalledWith('/search/', {
      params: {},
    });
  });
});
