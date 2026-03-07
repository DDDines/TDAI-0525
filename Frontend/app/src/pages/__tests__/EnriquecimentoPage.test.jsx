import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

import EnriquecimentoPage from '../EnriquecimentoPage.jsx';
import productService from '../../services/productService';
import usoIAService from '../../services/usoIAService';
import {
  showErrorToast,
  showInfoToast,
  showSuccessToast,
  showWarningToast,
} from '../../utils/notifications';

jest.mock('../../services/productService', () => ({
  __esModule: true,
  default: {
    getProdutos: jest.fn(),
    iniciarEnriquecimentoWebProduto: jest.fn(),
    getProdutoById: jest.fn(),
  },
}));

jest.mock('../../services/usoIAService', () => ({
  __esModule: true,
  default: {
    getHistoricoUsoIAPorProduto: jest.fn(() => Promise.resolve([])),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
  showInfoToast: jest.fn(),
  showWarningToast: jest.fn(),
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('../../components/produtos/ProductTable', () => ({
  __esModule: true,
  default: ({
    produtos,
    selectedProdutos,
    onSelectProduto,
    onSelectAllProdutos,
    onEdit,
    onSort,
  }) => (
    <div>
      <div data-testid="produtos-renderizados">{produtos.map((item) => item.nome_base).join(',')}</div>
      <div data-testid="selecionados">{Array.from(selectedProdutos).join(',')}</div>
      <button onClick={() => onSelectProduto(produtos[0]?.id)}>select-first</button>
      <button onClick={() => onSelectAllProdutos(true)}>select-all</button>
      <button onClick={() => onEdit(produtos[0])}>row-click</button>
      <button onClick={() => onSort('nome_base')}>sort-name</button>
    </div>
  ),
}));

jest.mock('../../components/common/PaginationControls', () => ({
  __esModule: true,
  default: ({ onPageChange }) => (
    <button onClick={() => onPageChange(1)}>next-page</button>
  ),
}));

const baseProduto = {
  id: 1,
  nome_base: 'Produto Teste',
  sku: 'SKU-1',
  fornecedor_id: 10,
  status_enriquecimento_web: 'NAO_INICIADO',
  status_titulo_ia: 'NAO_INICIADO',
  status_descricao_ia: 'NAO_INICIADO',
  data_atualizacao: null,
};

describe('EnriquecimentoPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    productService.getProdutos.mockResolvedValue({
      items: [baseProduto],
      total_items: 25,
    });
    productService.iniciarEnriquecimentoWebProduto.mockResolvedValue({
      msg: 'ok',
    });
    productService.getProdutoById.mockResolvedValue({
      id: 1,
      status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
    });
  });

  test('fetches products with search, sort and pagination params', async () => {
    render(<EnriquecimentoPage />);

    await waitFor(() => expect(productService.getProdutos).toHaveBeenCalledTimes(1));
    expect(productService.getProdutos).toHaveBeenLastCalledWith({
      skip: 0,
      limit: 10,
      search: undefined,
      sort_by: 'id',
      sort_order: 'desc',
    });

    fireEvent.change(screen.getByPlaceholderText(/Nome, SKU/i), {
      target: { value: 'reservatorio' },
    });
    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        search: 'reservatorio',
        sort_by: 'id',
        sort_order: 'desc',
      });
    });

    await userEvent.click(screen.getByText('sort-name'));
    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        search: 'reservatorio',
        sort_by: 'nome_base',
        sort_order: 'asc',
      });
    });

    await userEvent.click(screen.getByText('next-page'));
    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith({
        skip: 10,
        limit: 10,
        search: 'reservatorio',
        sort_by: 'nome_base',
        sort_order: 'asc',
      });
    });
  });

  test('calls enrichment endpoint and polls until terminal success', async () => {
    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('select-first'));
    await userEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() =>
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(1)
    );
    await waitFor(() =>
      expect(productService.getProdutoById).toHaveBeenCalledWith('1')
    );
    expect(showInfoToast).toHaveBeenCalledWith(
      expect.stringMatching(/Iniciando enriquecimento web/i)
    );
    expect(showSuccessToast).toHaveBeenCalledWith(
      'Enriquecimento web finalizado para os produtos selecionados.'
    );
    expect(showWarningToast).not.toHaveBeenCalled();
  });

  test('shows row logs when enrichment history exists', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        {
          ...baseProduto,
          log_enriquecimento_web: { historico_mensagens: ['linha 1', 'linha 2'] },
        },
      ],
      total_items: 1,
    });

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('row-click'));

    expect(showInfoToast).toHaveBeenCalledWith(
      expect.stringMatching(/Log de enriquecimento/i)
    );
  });

  test('shows latest usage-history failure details when failed product has no inline log', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        {
          ...baseProduto,
          status_enriquecimento_web: 'FALHA',
          log_enriquecimento_web: { historico_mensagens: [] },
        },
      ],
      total_items: 1,
    });
    usoIAService.getHistoricoUsoIAPorProduto.mockResolvedValueOnce([
      { resultado_gerado: 'Timeout no provedor externo' },
    ]);

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('row-click'));

    await waitFor(() => {
      expect(usoIAService.getHistoricoUsoIAPorProduto).toHaveBeenCalledWith(1, {
        limit: 1,
        skip: 0,
      });
    });
    expect(showInfoToast).toHaveBeenCalledWith(
      expect.stringMatching(/Ultimo erro registrado/i)
    );
  });

  test('shows fallback error when usage-history lookup fails for a failed product', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        {
          ...baseProduto,
          status_enriquecimento_web: 'FALHA',
          log_enriquecimento_web: { historico_mensagens: [] },
        },
      ],
      total_items: 1,
    });
    usoIAService.getHistoricoUsoIAPorProduto.mockRejectedValueOnce(new Error('boom'));

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('row-click'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        expect.stringMatching(/sem log detalhado/i)
      );
    });
  });

  test('shows plain status toast for products without log history or failure state', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        {
          ...baseProduto,
          status_enriquecimento_web: 'EM_PROGRESSO',
          log_enriquecimento_web: { historico_mensagens: [] },
        },
      ],
      total_items: 1,
    });

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('row-click'));

    expect(showInfoToast).toHaveBeenCalledWith(
      expect.stringMatching(/EM PROGRESSO/i)
    );
  });
});
