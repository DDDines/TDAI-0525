import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ProductTypeProvider, useProductTypes } from '../ProductTypeContext.jsx';
import productTypeService from '../../services/productTypeService';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';
import { useAuth } from '../AuthContext';

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

describe('ProductTypeContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(console, 'error').mockImplementation(() => {});
    useAuth.mockReturnValue({
      user: { email: 'admin@example.com' },
      isLoading: false,
    });
    productTypeService.getProductTypes.mockResolvedValue([
      { id: 1, friendly_name: 'Moto' },
    ]);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('does not fetch product types when there is no authenticated user', async () => {
    useAuth.mockReturnValue({
      user: null,
      isLoading: false,
    });

    render(
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
    render(
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

    render(
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

  test('surfaces fetch errors to the UI', async () => {
    productTypeService.getProductTypes.mockRejectedValueOnce(
      new Error('Falha ao carregar tipos de produto.')
    );

    render(
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

  test('requires authentication before adding a product type', async () => {
    useAuth.mockReturnValue({
      user: null,
      isLoading: false,
    });

    render(
      <ProductTypeProvider>
        <Probe />
      </ProductTypeProvider>
    );

    fireEvent.click(screen.getByText('add'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Você precisa estar logado para adicionar um tipo de produto.'
      );
    });
  });
});
