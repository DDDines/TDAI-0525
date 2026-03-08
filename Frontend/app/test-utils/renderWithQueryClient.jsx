import React from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { createAppQueryClient } from '../src/lib/queryClient.js';

export function createTestQueryClient() {
  const client = createAppQueryClient();
  client.setDefaultOptions({
    queries: {
      ...client.getDefaultOptions().queries,
      retry: false,
      gcTime: Infinity,
    },
    mutations: {
      ...client.getDefaultOptions().mutations,
      retry: false,
    },
  });
  return client;
}

export function renderWithQueryClient(ui, options = {}) {
  const client = options.client || createTestQueryClient();
  const Wrapper = ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );

  return {
    client,
    ...render(ui, {
      wrapper: Wrapper,
      ...options,
    }),
  };
}
