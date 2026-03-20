import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { renderWithQueryClient } from '../../../test-utils/renderWithQueryClient.jsx';

import EnriquecimentoPage from '../EnriquecimentoPage.jsx';
import productService from '../../services/productService';
import usoIAService from '../../services/usoIAService';
import {
  showErrorToast,
  showInfoToast,
  showSuccessToast,
  showWarningToast,
} from '../../utils/notifications';

let mockEffectiveMode = 'basic';

jest.mock('../../services/productService', () => ({
  __esModule: true,
  default: {
    getProdutos: jest.fn(),
    getProdutosIds: jest.fn(),
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

jest.mock('../../contexts/AppExperienceContext.jsx', () => ({
  useAppExperience: () => ({
    effectiveMode: mockEffectiveMode,
  }),
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
    selectionMenuItems = [],
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
      {selectionMenuItems.map((item) => (
        <button
          key={item.key}
          onClick={() => item.onClick?.()}
          disabled={item.disabled}
        >
          {item.label}
        </button>
      ))}
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
    mockEffectiveMode = 'basic';
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    productService.getProdutos.mockResolvedValue({
      items: [baseProduto],
      total_items: 25,
    });
    productService.getProdutosIds.mockResolvedValue({ ids: [1] });
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
    renderWithQueryClient(<EnriquecimentoPage />);

    await waitFor(() => expect(productService.getProdutos).toHaveBeenCalledTimes(1));
    expect(productService.getProdutos).toHaveBeenLastCalledWith({
      enrichment_scope: 'enriched',
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
        enrichment_scope: 'enriched',
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
        enrichment_scope: 'enriched',
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
        enrichment_scope: 'enriched',
        skip: 10,
        limit: 10,
        search: 'reservatorio',
        sort_by: 'nome_base',
        sort_order: 'asc',
      });
    });
  });

  test('calls enrichment endpoint and polls until terminal success', async () => {
    renderWithQueryClient(<EnriquecimentoPage />);

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

  test('shows a warning toast when enrichment finishes with partial data', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      id: 1,
      status_enriquecimento_web: 'CONCLUIDO_COM_DADOS_PARCIAIS',
    });

    renderWithQueryClient(<EnriquecimentoPage />);

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
    expect(showWarningToast).toHaveBeenCalledWith(
      'Enriquecimento web finalizado com pendências para os produtos selecionados.'
    );
    expect(showSuccessToast).not.toHaveBeenCalledWith(
      'Enriquecimento web finalizado para os produtos selecionados.'
    );
  });

  test('allows explicit IA opt-in in complete mode before starting enrichment', async () => {
    mockEffectiveMode = 'complete';
    renderWithQueryClient(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('select-first'));
    await userEvent.click(screen.getByLabelText(/Usar IA no enriquecimento web/i));
    await userEvent.click(screen.getByRole('button', { name: /Enriquecer Web \+ IA/i }));

    await waitFor(() =>
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(1, {
        usarIA: true,
      })
    );
  });

  test('supports selecting the current page and all filtered results', async () => {
    renderWithQueryClient(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });

    await userEvent.click(screen.getByRole('button', { name: /Selecionar página atual/i }));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('1');
    expect(
      screen.getByText('1 item(ns) selecionado(s) (página atual)')
    ).toBeInTheDocument();

    productService.getProdutosIds.mockResolvedValueOnce({ ids: [1, 8, 9] });
    await userEvent.click(screen.getByRole('button', { name: /Selecionar todos os resultados da pesquisa/i }));

    await waitFor(() => {
      expect(productService.getProdutosIds).toHaveBeenCalledWith({
        enrichment_scope: 'enriched',
        limit: undefined,
        search: undefined,
        skip: undefined,
        sort_by: 'id',
        sort_order: 'desc',
      });
    });
    expect(screen.getByTestId('selecionados')).toHaveTextContent('1,8,9');
    expect(
      screen.getByText('3 item(ns) selecionado(s) (todos os resultados)')
    ).toBeInTheDocument();
    expect(showInfoToast).not.toHaveBeenCalledWith(
      '3 item(ns) selecionado(s) em todos os resultados filtrados.'
    );
  });

  test('clears selection when the list context changes', async () => {
    renderWithQueryClient(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });

    await userEvent.click(screen.getByText('select-first'));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('1');

    fireEvent.change(screen.getByPlaceholderText(/Nome, SKU/i), {
      target: { value: 'contexto novo' },
    });
    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith({
        enrichment_scope: 'enriched',
        skip: 0,
        limit: 10,
        search: 'contexto novo',
        sort_by: 'id',
        sort_order: 'desc',
      });
    });
    expect(screen.getByTestId('selecionados')).toHaveTextContent('');
    expect(screen.queryByText('Nenhum item selecionado')).not.toBeInTheDocument();
    expect(screen.queryByText(/item\(ns\) selecionado\(s\)/i)).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('select-first'));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('1');
    await userEvent.click(screen.getByText('next-page'));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('');
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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

  test('ignores polled entries without id while caching the valid selected products', async () => {
    jest.useFakeTimers();
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        baseProduto,
        {
          ...baseProduto,
          id: 2,
          nome_base: 'Produto Secundario',
        },
      ],
      total_items: 2,
    });
    productService.getProdutoById
      .mockResolvedValueOnce({
        id: 1,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      })
      .mockResolvedValueOnce({
        id: null,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      });

    renderWithQueryClient(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Secundario');
    });

    fireEvent.click(screen.getByRole('button', { name: /Selecionar página atual/i }));
    fireEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(1);
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2);
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

    renderWithQueryClient(<EnriquecimentoPage />);

    expect(
      await screen.findByText('Erro ao carregar produtos: Falha ao buscar produtos.')
    ).toBeInTheDocument();
    expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('');
  });

  test('toggles page selection off and sorts descending on the second click', async () => {
    renderWithQueryClient(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });

    await userEvent.click(screen.getByRole('button', { name: /Selecionar página atual/i }));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('1');

    await userEvent.click(screen.getByRole('button', { name: /Limpar seleção/i }));
    expect(screen.getByTestId('selecionados')).toHaveTextContent('');

    await userEvent.click(screen.getByText('sort-name'));
    await userEvent.click(screen.getByText('sort-name'));

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith({
        enrichment_scope: 'enriched',
        skip: 0,
        limit: 10,
        search: undefined,
        sort_by: 'nome_base',
        sort_order: 'desc',
      });
    });
  });

  test('updates the query when the enrichment scope filter changes', async () => {
    renderWithQueryClient(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });

    await userEvent.selectOptions(screen.getByRole('combobox'), 'pending');

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith({
        enrichment_scope: 'pending',
        skip: 0,
        limit: 10,
        search: undefined,
        sort_by: 'id',
        sort_order: 'desc',
      });
    });
  });

  test('toggles the same row selection on and off', async () => {
    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

    await waitFor(() => {
      expect(screen.getByTestId('produtos-renderizados')).toHaveTextContent('Produto Teste');
    });
    await userEvent.click(screen.getByText('select-first'));
    await userEvent.click(screen.getByRole('button', { name: /Enriquecer Web/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('falha no start');
    });
    expect(productService.getProdutos).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId('status-renderizados')).toHaveTextContent('1:FALHA');
  });

  test('falls back to a generic start error and timed refresh when polling cannot read any product', async () => {
    jest.useFakeTimers();
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce({});
    productService.getProdutos.mockResolvedValue({
      items: [baseProduto],
      total_items: 1,
    });

    renderWithQueryClient(<EnriquecimentoPage />);

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
      expect(screen.getByRole('button', { name: /Enriquecer Web/i })).not.toBeDisabled();
    });

    fireEvent.click(
      screen.getByRole('button', { name: /Enriquecer Web/i })
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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    renderWithQueryClient(<EnriquecimentoPage />);

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

    expect(productService.getProdutoById).toHaveBeenCalledTimes(2);
  }, 15000);

  test('stops polling when the page unmounts', async () => {
    jest.useFakeTimers();
    productService.getProdutoById.mockResolvedValue({
      id: 1,
      status_enriquecimento_web: 'EM_PROGRESSO',
    });

    const { unmount } = renderWithQueryClient(<EnriquecimentoPage />);

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

    unmount();

    await act(async () => {
      jest.advanceTimersByTime(3000);
      await Promise.resolve();
    });

    expect(productService.getProdutoById).toHaveBeenCalledTimes(1);
    expect(showSuccessToast).not.toHaveBeenCalledWith(
      'Enriquecimento web finalizado para os produtos selecionados.'
    );
    expect(showInfoToast).not.toHaveBeenCalledWith(
      'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
    );
  }, 15000);
});


