import { QueryClient } from '@tanstack/react-query';
import { appQueryClient, createAppQueryClient } from '../queryClient.js';

describe('queryClient', () => {
  test('creates query clients with the expected defaults', () => {
    const client = createAppQueryClient();

    expect(client).toBeInstanceOf(QueryClient);
    expect(client.getDefaultOptions()).toEqual({
      queries: {
        staleTime: 15_000,
        gcTime: 5 * 60_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    });
  });

  test('exports a shared singleton app query client', () => {
    expect(appQueryClient).toBeInstanceOf(QueryClient);
    expect(appQueryClient.getDefaultOptions().queries.retry).toBe(1);
    expect(appQueryClient.getDefaultOptions().mutations.retry).toBe(0);
  });
});
