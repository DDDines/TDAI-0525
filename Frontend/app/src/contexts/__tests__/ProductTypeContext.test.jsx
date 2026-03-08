import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ProductTypeProvider, useProductTypes } from '../ProductTypeContext.jsx';
import productTypeService from '../../services/productTypeService';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';
import { useAuth } from '../AuthContext';
import {
  createTestQueryClient,
  renderWithQueryClient,
} from '../../../test-utils/renderWithQueryClient.jsx';

jest.mock('../../services/productTypeService', () => ({
  __esModule: true,
  default: {
    getProductTypes: jest.fn(),
    createProductType: jest.fn(),
    updateProductType: jest.fn(),
    deleteProductType: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showSuccessToast: jest.fn(),
}));

jest.mock('../AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
  },
}));

function Probe() {
  const context = useProductTypes();
  return (
    <div>
      <div data-testid="loading">{String(context.isLoading)}</div>
      <div data-testid="error">{context.error || ''}</div>
      <div data-testid="names">
        {context.productTypes.map((item) => item.friendly_name).join(',')}
      </div>
      <button onClick={() => context.refreshProductTypes()}>refresh</button>
      <button
        onClick={() =>
          context.addProductType({ friendly_name: 'Caminhao' }).catch(() => {})
        }
      >
        add
      </button>
      <button
        onClick={() =>
          context.updateProductType(1, { friendly_name: 'Atualizado' }).catch(() => {})
        }
      >
        update
      </button>
      <button onClick={() => context.removeProductType(1).catch(() => {})}>remove</button>
    </div>
  );
}

function InvalidProbe() {
  useProductTypes();
  return <div>invalid</div>;
}

describe('ProductTypeContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    useAuth.mockReturnValue({
      user: { email: 'admin@example.com' },
      isLoading: false,
    });
    productTypeService.getProductTypes.mockResolvedValue([{ id: 1, friendly_name: 'Moto' }]);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('waits for auth session loading before fetching product types', async () => {
    useAuth.mockReturnValue({
      user: { email: 'admin@example.com' },
      isLoading: true,
    });

    const { rerender } = renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    expect(productTypeService.getProductTypes).not.toHaveBeenCalled();

    useAuth.mockReturnValue({
      user: { email: 'admin@example.com' },
      isLoading: false,
    });

    rerender(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    await waitFor(() => {
      expect(productTypeService.getProductTypes).toHaveBeenCalledWith({
        skip: 0,
        limit: 500,
      });
    });
  });

  test('does not fetch product types when there is no authenticated user', async () => {
    useAuth.mockReturnValue({
      user: null,
      isLoading: false,
    });

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    expect(productTypeService.getProductTypes).not.toHaveBeenCalled();
    expect(screen.getByTestId('names')).toHaveTextContent('');
  });

  test('fetches product types for authenticated users and can refresh the list', async () => {
    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('Moto');
    });

    fireEvent.click(screen.getByText('refresh'));

    await waitFor(() => {
      expect(productTypeService.getProductTypes).toHaveBeenCalledTimes(2);
    });
    expect(productTypeService.getProductTypes).toHaveBeenLastCalledWith({
      skip: 0,
      limit: 500,
    });
  });

  test('adds, updates and removes product types while keeping local state in sync', async () => {
    productTypeService.createProductType.mockResolvedValueOnce({
      id: 2,
      friendly_name: 'Caminhao',
    });
    productTypeService.updateProductType.mockResolvedValueOnce({
      id: 1,
      friendly_name: 'Atualizado',
    });
    productTypeService.deleteProductType.mockResolvedValueOnce({ ok: true });

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('Moto');
    });

    fireEvent.click(screen.getByText('add'));
    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('Caminhao,Moto');
    });

    fireEvent.click(screen.getByText('update'));
    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('Atualizado,Caminhao');
    });

    fireEvent.click(screen.getByText('remove'));
    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('Caminhao');
    });

    expect(showSuccessToast).toHaveBeenCalledWith('Tipo de produto adicionado com sucesso!');
    expect(showSuccessToast).toHaveBeenCalledWith('Tipo de produto atualizado com sucesso!');
    expect(showSuccessToast).toHaveBeenCalledWith('Tipo de produto removido com sucesso!');
  });

  test('recovers from a malformed cached payload before appending a new type', async () => {
    const client = createTestQueryClient();
    client.setQueryData(['product-types'], { invalid: true });
    productTypeService.getProductTypes.mockImplementation(
      () => new Promise(() => {})
    );
    productTypeService.createProductType.mockResolvedValueOnce({
      id: 2,
      friendly_name: 'Caminhao',
    });

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>,
      { client }
    );

    fireEvent.click(screen.getByText('add'));

    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('Caminhao');
    });
  });

  test('builds a new local cache when a mutation succeeds before the first fetch resolves', async () => {
    const client = createTestQueryClient();
    productTypeService.getProductTypes.mockImplementation(
      () => new Promise(() => {})
    );
    productTypeService.createProductType.mockResolvedValueOnce({
      id: 2,
      friendly_name: 'Caminhao',
    });

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>,
      { client }
    );

    fireEvent.click(screen.getByText('add'));

    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('Caminhao');
    });
  });

  test('surfaces fetch errors to the UI', async () => {
    productTypeService.getProductTypes.mockRejectedValueOnce(
      new Error('Falha ao carregar tipos de produto.')
    );

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent(
        'Falha ao carregar tipos de produto.'
      );
    });
  });

  test('falls back to generic fetch and mutation errors when the service returns empty failures', async () => {
    productTypeService.getProductTypes.mockRejectedValueOnce({});

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('error')).toHaveTextContent(
        'Falha ao carregar tipos de produto.'
      );
    });

    productTypeService.createProductType.mockRejectedValueOnce({});
    productTypeService.updateProductType.mockRejectedValueOnce({});
    productTypeService.deleteProductType.mockRejectedValueOnce({});

    fireEvent.click(screen.getByText('add'));
    fireEvent.click(screen.getByText('update'));
    fireEvent.click(screen.getByText('remove'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao adicionar tipo de produto.');
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao atualizar tipo de produto.');
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao remover tipo de produto.');
    });
  });

  test('handles non-array fetch payloads and refresh attempts without an authenticated user', async () => {
    productTypeService.getProductTypes.mockResolvedValueOnce({ invalid: true });

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('');
    });

    useAuth.mockReturnValue({
      user: null,
      isLoading: false,
    });

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    fireEvent.click(screen.getAllByText('refresh')[1]);

    await waitFor(() => {
      expect(console.warn).toHaveBeenCalled();
    });
  });

  test('requires authentication before mutating product types', async () => {
    useAuth.mockReturnValue({
      user: null,
      isLoading: false,
    });

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    fireEvent.click(screen.getByText('add'));
    fireEvent.click(screen.getByText('update'));
    fireEvent.click(screen.getByText('remove'));

    await waitFor(() => {
      const messages = showErrorToast.mock.calls.map(([message]) => String(message));
      expect(messages.some((message) => /precisa estar logado.*adicionar/i.test(message))).toBe(true);
      expect(messages.some((message) => /precisa estar logado.*atualizar/i.test(message))).toBe(true);
      expect(messages.some((message) => /precisa estar logado.*remover/i.test(message))).toBe(true);
    });
  });

  test('surfaces service errors when add, update and remove fail', async () => {
    productTypeService.createProductType.mockRejectedValueOnce({
      response: { data: { detail: 'duplicado' } },
    });
    productTypeService.updateProductType.mockRejectedValueOnce({
      response: { data: { detail: 'nao encontrado' } },
    });
    productTypeService.deleteProductType.mockRejectedValueOnce({
      response: { data: { detail: 'em uso' } },
    });

    renderWithQueryClient(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('names')).toHaveTextContent('Moto');
    });

    fireEvent.click(screen.getByText('add'));
    fireEvent.click(screen.getByText('update'));
    fireEvent.click(screen.getByText('remove'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('duplicado');
      expect(showErrorToast).toHaveBeenCalledWith('nao encontrado');
      expect(showErrorToast).toHaveBeenCalledWith('em uso');
    });
  });

  test('throws when useProductTypes is called outside the provider', () => {
    expect(() => render(<InvalidProbe />)).toThrow(
      'useProductTypes deve ser usado dentro de um ProductTypeProvider'
    );
  });
});


