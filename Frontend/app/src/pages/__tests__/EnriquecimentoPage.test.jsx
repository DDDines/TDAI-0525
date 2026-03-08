import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
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
      <div data-testid="status-renderizados">
        {produtos.map((item) => `${item.id}:${item.status_enriquecimento_web || 'vazio'}`).join(',')}
      </div>
      <div data-testid="selecionados">{Array.from(selectedProdutos).join(',')}</div>
      <button onClick={() => onSelectProduto(produtos[0]?.id)}>select-first</button>
      <button onClick={() => onSelectAllProdutos(true)}>select-all</button>
      <button onClick={() => onSelectAllProdutos(false)}>clear-all</button>
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
  let consoleWarnSpy;
  let consoleErrorSpy;
  let consoleLogSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
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

  afterEach(() => {
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
    consoleLogSpy.mockRestore();
    jest.useRealTimers();
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

  test('truncates very long inline logs before notifying the user', async () => {
    const longLog = 'x'.repeat(260);
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        {
          ...baseProduto,
          log_enriquecimento_web: { historico_mensagens: [longLog] },
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
      expect.stringMatching(/^Log de enriquecimento.*\.\.\.$/)
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

  test('warns when product payload format is invalid', async () => {
    productService.getProdutos.mockResolvedValueOnce({ invalid: true });

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Formato de dados inesperado recebido para produtos:',
        { invalid: true }
      );
    });
    expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('');
  });

  test('keeps unmatched products untouched while local and fetched statuses update only selected ids', async () => {
    jest.useFakeTimers();
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        baseProduto,
        {
          ...baseProduto,
          id: 2,
          nome_base: 'Produto Secundario',
          status_enriquecimento_web: 'NAO_INICIADO',
        },
      ],
      total_items: 2,
    });
    productService.getProdutoById
      .mockResolvedValueOnce({
        id: 1,
        status_enriquecimento_web: null,
      })
      .mockResolvedValueOnce({
        id: 1,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      });

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Secundario');
    });

    fireEvent.click(screen.getByText('select-first'));
    fireEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(screen.getByTestId('status-renderizados')).toHaveTextContent(
        '1:vazio,2:NAO_INICIADO'
      );
    });

    await act(async () => {
      await jest.advanceTimersByTimeAsync(3000);
    });

    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledTimes(2);
      expect(showSuccessToast).toHaveBeenCalledWith(
        'Enriquecimento web finalizado para os produtos selecionados.'
      );
    });
  }, 15000);

  test('shows the fallback fetch error when the product request has no message', async () => {
    productService.getProdutos.mockRejectedValueOnce({});

    render(<EnriquecimentoPage />);

    expect(
      await screen.findByText('Erro ao carregar produtos: Falha ao buscar produtos.')
    ).toBeInTheDocument();
    expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('');
  });

  test('toggles select-all off and sorts descending on the second click', async () => {
    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });

    await userEvent.click(screen.getByText('select-all'));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('1');

    await userEvent.click(screen.getByText('clear-all'));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('');

    await userEvent.click(screen.getByText('sort-name'));
    await userEvent.click(screen.getByText('sort-name'));

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        search: undefined,
        sort_by: 'nome_base',
        sort_order: 'desc',
      });
    });
  });

  test('toggles the same row selection on and off', async () => {
    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });

    await userEvent.click(screen.getByText('select-first'));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('1');

    await userEvent.click(screen.getByText('select-first'));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('');
  });

  test('shows info fallback when a failed product has no external history details', async () => {
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
    usoIAService.getHistoricoUsoIAPorProduto.mockResolvedValueOnce([]);

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('row-click'));

    await waitFor(() => {
      expect(showInfoToast).toHaveBeenCalledWith(
        expect.stringMatching(/sem log detalhado/i)
      );
    });
  });

  test('does not emit row-detail notifications when the product has no status or log yet', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        {
          ...baseProduto,
          status_enriquecimento_web: null,
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

    expect(showInfoToast).not.toHaveBeenCalled();
    expect(showErrorToast).not.toHaveBeenCalled();
  });

  test('refreshes the list immediately when every enrichment start fails', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce(
      new Error('falha no start')
    );

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('select-first'));
    await userEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('falha no start');
    });
    expect(productService.getProdutos).toHaveBeenCalledTimes(2);
  });

  test('falls back to a generic start error and timed refresh when polling cannot read any product', async () => {
    jest.useFakeTimers();
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce({});
    productService.getProdutos.mockResolvedValue({
      items: [baseProduto],
      total_items: 1,
    });

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });

    fireEvent.click(screen.getByText('select-first'));
    fireEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro desconhecido ao iniciar enriquecimento para produto ID 1.'
      );
    });

    productService.iniciarEnriquecimentoWebProduto.mockResolvedValueOnce({ ok: true });
    productService.getProdutoById.mockRejectedValue({});
    fireEvent.click(screen.getByText('select-first'));

    await waitFor(() => {
      expect(screen.getByTestId('selecionados')).toHaveTextContent('1');
      expect(screen.getByRole('button', { name: /Enriquecer Web \(1\) selecionado\(s\)/i })).not.toBeDisabled();
    });

    fireEvent.click(
      screen.getByRole('button', { name: /Enriquecer Web \(1\) selecionado\(s\)/i })
    );

    await waitFor(() =>
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(1)
    );

    for (let i = 0; i < 121; i += 1) {
      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });
    }

    await waitFor(() => {
      expect(showInfoToast).toHaveBeenCalledWith(
        'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
      );
    });
  }, 15000);

  test('falls back to a timed refresh when polling never reaches a terminal status', async () => {
    jest.useFakeTimers();
    productService.getProdutoById.mockResolvedValue({
      id: 1,
      status_enriquecimento_web: 'EM_PROGRESSO',
    });

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    fireEvent.click(screen.getByText('select-first'));
    fireEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() =>
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(1)
    );

    for (let i = 0; i < 121; i += 1) {
      await act(async () => {
        jest.advanceTimersByTime(3000);
        await Promise.resolve();
      });
    }
    await act(async () => {
      jest.runOnlyPendingTimers();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(showInfoToast).toHaveBeenCalledWith(
        'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
      );
    });
  }, 15000);

  test('cancels the previous polling loop when a new enrichment batch starts', async () => {
    jest.useFakeTimers();
    productService.getProdutoById.mockResolvedValue({
      id: 1,
      status_enriquecimento_web: 'EM_PROGRESSO',
    });

    render(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });

    fireEvent.click(screen.getByText('select-first'));
    fireEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() =>
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledTimes(1)
    );
    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByText('select-first'));
    fireEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() =>
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledTimes(2)
    );
    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledTimes(2);
    });

    await act(async () => {
      jest.advanceTimersByTime(3000);
      await Promise.resolve();
    });

    expect(productService.getProdutoById).toHaveBeenCalledTimes(3);
  }, 15000);
});
