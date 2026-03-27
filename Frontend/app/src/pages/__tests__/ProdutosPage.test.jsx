import { fireEvent, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { renderWithQueryClient } from '../../../test-utils/renderWithQueryClient.jsx';
import { MemoryRouter } from 'react-router-dom';
import ProdutosPage from '../ProdutosPage.jsx';
import {
  normalizeProductListPayload,
  resolveGenerationHandler,
} from '../ProdutosPage.helpers.js';
import productService from '../../services/productService';
import {
  showErrorToast,
  showInfoToast,
  showSuccessToast,
  showWarningToast,
} from '../../utils/notifications';

const mockNavigate = jest.fn();
let mockEffectiveMode = 'basic';
let mockProductTypesState = {
  productTypes: [],
  isLoading: false,
  error: null,
};

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../../services/productService', () => ({
  __esModule: true,
  default: {
    getProdutos: jest.fn(),
    getProdutosIds: jest.fn(),
    getProdutoById: jest.fn(),
    batchDeleteProdutos: jest.fn(),
    gerarTitulosProduto: jest.fn(),
    gerarDescricaoProduto: jest.fn(),
    gerarTitulosProdutoModoBasico: jest.fn(),
    gerarDescricaoProdutoModoBasico: jest.fn(),
    batchGeneration: jest.fn(),
    iniciarEnriquecimentoWebProduto: jest.fn(),
  },
}));

jest.mock('../../components/common/Modal', () => ({
  __esModule: true,
  default: ({ children }) => <div data-testid="modal-wrapper">{children}</div>,
}));

jest.mock('../../components/common/LoadingOverlay.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, message }) => (isOpen ? <div data-testid="page-loading-overlay">{message}</div> : null),
}));

jest.mock('../../components/ProductEditModal', () => ({
  __esModule: true,
  default: ({ product, showAiFeatures, onClose, onOpenContentView, onProductUpdated }) => (
    <div
      data-testid="product-edit-modal"
      data-product-id={String(product?.id ?? 'new')}
      data-ai={String(showAiFeatures)}
    >
      <button type="button" onClick={() => onOpenContentView?.(product?.id ?? 999)}>
        open-content-from-modal
      </button>
      <button type="button" onClick={() => onOpenContentView?.()}>
        open-content-without-id
      </button>
      <button
        type="button"
        onClick={() =>
          onProductUpdated?.({
            ...(product || {}),
            id: product?.id ?? 2558,
            nome_base: 'Produto Atualizado via Modal',
          })
        }
      >
        simulate-update-product
      </button>
      <button
        type="button"
        onClick={() =>
          onProductUpdated?.({
            ...(product || {}),
            id: 3999,
            nome_base: 'Produto Inserido via Modal',
          })
        }
      >
        simulate-insert-product
      </button>
      <button type="button" onClick={() => onClose?.()}>
        close-product-edit-modal
      </button>
    </div>
  ),
}));

jest.mock('../../contexts/AppExperienceContext', () => ({
  useAppExperience: () => ({
    effectiveMode: mockEffectiveMode,
  }),
}));

jest.mock('../../contexts/ProductTypeContext', () => ({
  useProductTypes: () => mockProductTypesState,
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showSuccessToast: jest.fn(),
  showInfoToast: jest.fn(),
  showWarningToast: jest.fn(),
}));

const baseItems = [
  {
    id: 2558,
    nome_base: 'Reservatorio de AR 20 Litros',
    sku: '987 308 430 7005',
    fornecedor_id: 3,
    status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
    status_titulo_ia: 'CONCLUIDO',
    status_descricao_ia: 'CONCLUIDO',
    data_atualizacao: '2026-03-07T12:00:00Z',
  },
  {
    id: 2559,
    nome_base: 'Valvula de Pressao',
    sku: 'ABC-99',
    fornecedor_id: 4,
    status_enriquecimento_web: 'NAO_INICIADO',
    status_titulo_ia: 'NAO_INICIADO',
    status_descricao_ia: 'NAO_INICIADO',
    data_atualizacao: '2026-03-07T13:00:00Z',
  },
];

function renderPage(initialEntries = ['/produtos']) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={initialEntries}>
      <ProdutosPage />
    </MemoryRouter>
  );
}

function getSelectionMenuTrigger() {
  return screen.getByLabelText(/Opções de seleção/i);
}

function getFirstProductRowCheckbox() {
  return screen
    .getAllByRole('checkbox')
    .filter((checkbox) => !checkbox.getAttribute('aria-label'))[0];
}

describe('ProdutosPage', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockEffectiveMode = 'basic';
    mockProductTypesState = {
      productTypes: [],
      isLoading: false,
      error: null,
    };
    productService.getProdutos.mockResolvedValue({
      items: baseItems,
      total_items: baseItems.length,
    });
    productService.getProdutosIds.mockResolvedValue({ ids: baseItems.map((item) => item.id) });
    productService.batchDeleteProdutos.mockResolvedValue({ deleted: 1 });
    productService.gerarTitulosProduto.mockResolvedValue({ ok: true });
    productService.gerarDescricaoProduto.mockResolvedValue({ ok: true });
    productService.gerarTitulosProdutoModoBasico.mockResolvedValue({ ok: true });
    productService.gerarDescricaoProdutoModoBasico.mockResolvedValue({ ok: true });
    productService.batchGeneration.mockResolvedValue({ agendados: 2, ignorados: 0, detalhes: [] });
    productService.iniciarEnriquecimentoWebProduto.mockResolvedValue({ ok: true });
    productService.getProdutoById.mockResolvedValue(baseItems[0]);
    window.confirm = jest.fn(() => true);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('mantem chips de status de titulo e descricao visiveis mesmo no modo basico', async () => {
    renderPage();

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenCalled();
    });

    expect(await screen.findByText('Reservatorio de AR 20 Litros')).toBeInTheDocument();
    expect(screen.getAllByLabelText(/Enriquecimento web: Concluído/i).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/Títulos: Concluído/i).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/Descrição: Concluído/i).length).toBeGreaterThan(0);
  });

  test('usa o loader de tela enquanto a lista inicial de produtos ainda nao chegou', async () => {
    let resolveProdutos;
    productService.getProdutos.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveProdutos = resolve;
        })
    );

    renderPage();

    expect(screen.getByTestId('page-loading-overlay')).toHaveTextContent('Carregando produtos...');

    resolveProdutos({
      items: baseItems,
      total_items: baseItems.length,
    });

    expect(await screen.findByText('Reservatorio de AR 20 Litros')).toBeInTheDocument();
  });

  test('mostra estado de erro e permite tentar novamente', async () => {
    productService.getProdutos
      .mockRejectedValueOnce(new Error('Falha ao carregar produtos.'))
      .mockResolvedValueOnce({
        items: [baseItems[0]],
        total_items: 1,
      });

    renderPage();

    expect(await screen.findByText(/Erro ao carregar produtos/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Tentar novamente'));

    expect(await screen.findByText('Reservatorio de AR 20 Litros')).toBeInTheDocument();
    expect(productService.getProdutos).toHaveBeenCalledTimes(2);
  });

  test('supports selecting the current page and all filtered product results', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: baseItems,
      total_items: 3,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Reservatorio de AR 20 Litros')).toBeInTheDocument();
    });

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar página atual' }));
    expect(
      screen.getByText('2 item(ns) selecionado(s) (página atual)')
    ).toBeInTheDocument();

    productService.getProdutosIds.mockResolvedValueOnce({ ids: [2558, 2559, 3000] });
    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar todos os resultados da pesquisa' }));

    await waitFor(() => {
      expect(productService.getProdutosIds).toHaveBeenCalledWith({
        sort_by: 'id',
        sort_order: 'desc',
      });
    });
    await waitFor(() => {
      expect(
        screen.getByText('3 item(ns) selecionado(s) (todos os resultados)')
      ).toBeInTheDocument();
    });
    fireEvent.click(getSelectionMenuTrigger());
    expect(screen.getByRole('menuitem', { name: 'Selecionar página atual' })).toBeInTheDocument();
    expect(showInfoToast).not.toHaveBeenCalledWith(
      '3 produto(s) selecionado(s) em todos os resultados filtrados.'
    );
  });

  test('clears product selection when filters change', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Reservatorio de AR 20 Litros')).toBeInTheDocument();
    });

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar página atual' }));
    expect(
      screen.getByText('2 item(ns) selecionado(s) (página atual)')
    ).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Buscar por nome, SKU, EAN...'), {
      target: { value: 'Reservatorio' },
    });

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith({
        skip: 0,
        limit: 10,
        search: 'Reservatorio',
        sort_by: 'id',
        sort_order: 'desc',
      });
    });
    expect(screen.queryByText('Nenhum item selecionado')).not.toBeInTheDocument();
    expect(screen.queryByText(/item\(ns\) selecionado\(s\)/i)).not.toBeInTheDocument();
  });

  test('treats malformed list payloads as empty and shows the loading label for product types', async () => {
    mockProductTypesState = {
      productTypes: [],
      isLoading: true,
      error: null,
    };
    productService.getProdutos.mockResolvedValueOnce({
      items: null,
      total_items: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenCalled();
    });

    expect(screen.queryByText('Reservatorio de AR 20 Litros')).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Carregando tipos...' })).toBeInTheDocument();
  });

  test('mantem a lista de produtos visivel mesmo quando o carregamento dos tipos falha', async () => {
    mockProductTypesState = {
      productTypes: [],
      isLoading: false,
      error: new Error('Falha ao carregar tipos'),
    };

    renderPage();

    expect(await screen.findByText('Reservatorio de AR 20 Litros')).toBeInTheDocument();
    expect(screen.getByText('Valvula de Pressao')).toBeInTheDocument();
  });

  test('normaliza payloads de lista com total invalido para um contador seguro', () => {
    expect(
      normalizeProductListPayload({
        items: [baseItems[0]],
        total_items: '1',
      })
    ).toEqual({
      items: [baseItems[0]],
      total_items: 0,
    });
  });

  test('uses the default list error fallback when the backend rejects without details', async () => {
    productService.getProdutos.mockRejectedValueOnce({});

    renderPage();

    expect(await screen.findByText(/Falha ao carregar produtos\./i)).toBeInTheDocument();
  });

  test('recarrega a lista com filtros de busca e ordenacao atualizados', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    const searchInput = screen.getByPlaceholderText('Buscar por nome, SKU, EAN...');
    fireEvent.change(searchInput, { target: { value: 'pressao' } });

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith(
        expect.objectContaining({
          search: 'pressao',
          sort_by: 'id',
          sort_order: 'desc',
          skip: 0,
          limit: 10,
        })
      );
    });

    fireEvent.click(screen.getByText(/Nome Base/));

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith(
        expect.objectContaining({
          search: 'pressao',
          sort_by: 'nome_base',
          sort_order: 'asc',
        })
      );
    });

    fireEvent.click(screen.getByText(/Nome Base/));

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith(
        expect.objectContaining({
          search: 'pressao',
          sort_by: 'nome_base',
          sort_order: 'desc',
        })
      );
    });

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenCalledTimes(4);
    });
  });

  test('abre a visao de conteudo com a lista completa de ids e query atual', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByTitle('Ver conteúdo gerado')[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/produtos/2558/conteudo', {
      state: {
        productIds: [2558, 2559],
        productQuery: {
          sort_by: 'id',
          sort_order: 'desc',
        },
        returnTo: '/produtos?page=1&limit=10&sort_by=id&sort_order=desc',
      },
    });
  });

  test('ignora a abertura de conteudo quando o produto nao possui id valido', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [{ ...baseItems[0], id: 0 }],
      total_items: 1,
    });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getByTitle(/Ver conte.+do gerado/i));

    expect(mockNavigate).not.toHaveBeenCalled();
  });

  test('gera titulos em lote no modo basico e agenda refresh da lista', async () => {
    jest.useFakeTimers();
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByRole('button', { name: /Gerar T/i }));

    await waitFor(() => {
      expect(productService.batchGeneration).toHaveBeenCalledWith(
        expect.objectContaining({
          produtoIds: [2558],
          tipo: 'titulo',
          provider: 'basico',
        })
      );
    });
    expect(showInfoToast).not.toHaveBeenCalledWith('Geração de títulos iniciada para 1 produto(s).');

    await act(async () => {
      jest.advanceTimersByTime(15000);
    });

    await waitFor(() => {
      expect(showInfoToast).not.toHaveBeenCalledWith(
        'Atualizando lista para verificar resultados da geração de títulos...'
      );
      expect(productService.getProdutos).toHaveBeenCalledTimes(2);
    });
  });

  test('deleta os produtos selecionados em lote', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Ocultar'));

    await waitFor(() => {
      expect(productService.batchDeleteProdutos).toHaveBeenCalledWith([2558]);
    });
    expect(showSuccessToast).toHaveBeenCalledWith('1 produto(s) ocultado(s) com sucesso.');
    expect(window.confirm).toHaveBeenCalledWith(
      'Tem certeza que deseja ocultar 1 produto(s) selecionado(s)?'
    );
  });

  test('inicia enriquecimento web em lote e consulta o status do produto', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
    });
    expect(showInfoToast).not.toHaveBeenCalledWith('Enriquecimento web basico iniciado para 1 produto(s).');
    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledWith('2558');
    });
  });

  test('permite optar por IA no enriquecimento web quando a experiencia completa esta ativa', async () => {
    mockEffectiveMode = 'complete';
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByLabelText(/Usar IA no enriquecimento web/i));
    fireEvent.click(screen.getByText('Enriquecer Web + IA'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558, {
        usarIA: true,
      });
    });
  });

  test('interrompe o polling de enriquecimento ao desmontar a pagina apos falhas de consulta', async () => {
    jest.useFakeTimers();
    productService.getProdutoById.mockRejectedValue(new Error('poll indisponivel'));

    const { unmount } = renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
    });
    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledWith('2558');
    });

    unmount();

    await act(async () => {
      jest.advanceTimersByTime(3000);
    });

    expect(productService.getProdutoById).toHaveBeenCalledTimes(1);
  });

  test('carrega produto por query string e abre modal de edicao', async () => {
    renderPage(['/produtos?id=2558']);

    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledWith('2558');
    });
    expect(await screen.findByTestId('product-edit-modal')).toBeInTheDocument();
  });

  test('mostra toast de erro quando carregar produto via query string falha', async () => {
    productService.getProdutoById.mockRejectedValueOnce(new Error('produto nao encontrado'));

    renderPage(['/produtos?id=9999']);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('produto nao encontrado');
    });
  });

  test('uses the default query-string load error when the backend returns an empty failure object', async () => {
    productService.getProdutoById.mockRejectedValueOnce({});

    renderPage(['/produtos?id=9999']);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao carregar produto.');
    });
  });

  test('abre modal de novo produto, fecha e propaga navegacao de conteudo a partir do modal', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getByRole('button', { name: /Novo Produto/i }));

    expect(await screen.findByTestId('product-edit-modal')).toHaveAttribute('data-product-id', 'new');

    fireEvent.click(screen.getByText('open-content-from-modal'));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/999/conteudo', {
      state: {
        productIds: [2558, 2559],
        productQuery: {
          sort_by: 'id',
          sort_order: 'desc',
        },
        returnTo: '/produtos?page=1&limit=10&sort_by=id&sort_order=desc',
      },
    });

    fireEvent.click(screen.getByText('open-content-without-id'));
    expect(mockNavigate).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('close-product-edit-modal'));
    await waitFor(() => {
      expect(screen.queryByTestId('product-edit-modal')).not.toBeInTheDocument();
    });
  });

  test('aplica update vindo do modal e atualiza a lista local', async () => {
    renderPage(['/produtos?id=2558']);

    expect(await screen.findByTestId('product-edit-modal')).toBeInTheDocument();

    fireEvent.click(screen.getByText('simulate-update-product'));

    expect(await screen.findByText('Produto Atualizado via Modal')).toBeInTheDocument();
    expect(screen.queryByText('Reservatorio de AR 20 Litros')).not.toBeInTheDocument();
  });

  test('insere o produto atualizado na lista local quando ele nao existia anteriormente', async () => {
    renderPage(['/produtos?id=2558']);

    expect(await screen.findByTestId('product-edit-modal')).toBeInTheDocument();

    fireEvent.click(screen.getByText('simulate-insert-product'));

    expect(await screen.findByText('Produto Inserido via Modal')).toBeInTheDocument();
  });

  test('respeita cancelamento e mostra erro ao falhar ocultacao em lote', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());

    window.confirm = jest.fn(() => false);
    fireEvent.click(screen.getByText('Ocultar'));
    expect(productService.batchDeleteProdutos).not.toHaveBeenCalled();

    window.confirm = jest.fn(() => true);
    productService.batchDeleteProdutos.mockRejectedValueOnce(new Error('sem permissao'));
    fireEvent.click(screen.getByText('Ocultar'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('sem permissao');
    });
  });

  test('processa enriquecimento web parcial e marca falha local para itens rejeitados', async () => {
    productService.iniciarEnriquecimentoWebProduto
      .mockRejectedValueOnce(new Error('sem fonte'))
      .mockResolvedValueOnce({ ok: true });
    productService.getProdutoById.mockImplementation(async (produtoId) => {
      if (String(produtoId) === '2559') {
        return {
          ...baseItems[1],
          status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
        };
      }

      return {
        ...baseItems[0],
        status_enriquecimento_web: 'NAO_INICIADO',
      };
    });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar página atual' }));
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2559);
    });
    expect(showErrorToast).toHaveBeenCalledWith(
      'Erro ao iniciar enriquecimento para produto ID 2558: sem fonte'
    );
    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledWith('2559');
    });
    await waitFor(() => {
      expect(showSuccessToast).toHaveBeenCalledWith(
        'Enriquecimento web finalizado para o produto selecionado.'
      );
    });
  });

  test('ignora produtos sem id retornados no polling enquanto atualiza os itens validos', async () => {
    productService.getProdutoById
      .mockResolvedValueOnce({
        ...baseItems[0],
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      })
      .mockResolvedValueOnce({
        ...baseItems[1],
        id: null,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar página atual' }));
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2559);
    });
    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledWith('2558');
      expect(productService.getProdutoById).toHaveBeenCalledWith('2559');
    });
  });

  test('mostra warning quando o enriquecimento em lote termina com pendências', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      ...baseItems[0],
      status_enriquecimento_web: 'CONCLUIDO_COM_DADOS_PARCIAIS',
    });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
    });
    await waitFor(() => {
      expect(showWarningToast).toHaveBeenCalledWith(
        'Enriquecimento web finalizado com pendências para o produto selecionado.'
      );
    });
  });

  test('usa filtros e geracao IA quando o modo completo esta ativo', async () => {
    mockEffectiveMode = 'complete';
    mockProductTypesState = {
      productTypes: [{ id: 7, friendly_name: 'Freios' }],
      isLoading: false,
      error: null,
    };

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.change(screen.getByDisplayValue('Status'), {
      target: { value: 'CONCLUIDO_SUCESSO' },
    });
    fireEvent.change(screen.getByDisplayValue('Título IA'), {
      target: { value: 'CONCLUIDO' },
    });
    fireEvent.change(screen.getByDisplayValue('Descrição IA'), {
      target: { value: 'NAO_INICIADO' },
    });
    fireEvent.change(screen.getByDisplayValue('Todos os tipos'), {
      target: { value: '7' },
    });

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith(
        expect.objectContaining({
          status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
          status_titulo_ia: 'CONCLUIDO',
          status_descricao_ia: 'NAO_INICIADO',
          product_type_id: '7',
        })
      );
    });

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByRole('button', { name: /Gerar T.*IA/i }));
    await waitFor(() => {
      expect(productService.batchGeneration).toHaveBeenCalledWith(
        expect.objectContaining({
          produtoIds: [2558],
          tipo: 'titulo',
          provider: 'openai',
        })
      );
    });

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri.*IA/i }));
    await waitFor(() => {
      expect(productService.batchGeneration).toHaveBeenCalledWith(
        expect.objectContaining({
          produtoIds: [2558],
          tipo: 'descricao',
          provider: 'openai',
        })
      );
    });
  });

  test('gera descricoes no modo basico e agenda refresh da lista', async () => {
    jest.useFakeTimers();
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri/i }));

    await waitFor(() => {
      expect(productService.batchGeneration).toHaveBeenCalledWith(
        expect.objectContaining({
          produtoIds: [2558],
          tipo: 'descricao',
          provider: 'basico',
        })
      );
    });
    expect(showInfoToast).not.toHaveBeenCalledWith('Geração de descrições iniciada para 1 produto(s).');

    await act(async () => {
      jest.advanceTimersByTime(15000);
    });

    await waitFor(() => {
      expect(showInfoToast).not.toHaveBeenCalledWith(
        'Atualizando lista para verificar resultados da geração de descrições...'
      );
    });
  });

  test('mostra sucesso quando a geracao em lote termina sem pendências', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri/i }));

    await waitFor(() => {
      expect(productService.batchGeneration).toHaveBeenCalledWith(
        expect.objectContaining({
          produtoIds: [2558],
          tipo: 'descricao',
          provider: 'basico',
        })
      );
    });
    await waitFor(() => {
      expect(showSuccessToast).toHaveBeenCalledWith(
        'Geração de descrições finalizada para o produto selecionado.'
      );
    });
  });

  test('permite selecionar tudo, desmarcar um item e limpar a selecao em lote', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    const firstRowCheckbox = getFirstProductRowCheckbox();

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar página atual' }));
    expect(screen.getByText('2 item(ns) selecionado(s) (página atual)')).toBeInTheDocument();
    expect(screen.queryByText('2 produto(s) selecionado(s)')).not.toBeInTheDocument();

    fireEvent.click(firstRowCheckbox);
    expect(screen.getByText('1 item(ns) selecionado(s) (seleção manual)')).toBeInTheDocument();
    expect(screen.queryByText('1 produto(s) selecionado(s)')).not.toBeInTheDocument();

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar página atual' }));
    expect(screen.getByText('2 item(ns) selecionado(s) (página atual)')).toBeInTheDocument();
    expect(screen.queryByText('2 produto(s) selecionado(s)')).not.toBeInTheDocument();

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Limpar seleção' }));
    expect(screen.queryByText(/produto\(s\) selecionado\(s\)/i)).not.toBeInTheDocument();
  });

  test('executa enriquecimento web ao clicar no status da linha e pede confirmacao quando ja esta concluido', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByLabelText(/Enriquecimento web: Concluído/i)[0]);

    expect(window.confirm).toHaveBeenCalledWith(
      'A etapa de enriquecimento web para "Reservatorio de AR 20 Litros" já foi concluída. Deseja executar novamente?'
    );
    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
    });
  });

  test('nao reexecuta o processo da linha quando a confirmacao de retrabalho e cancelada', async () => {
    window.confirm = jest.fn(() => false);

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByLabelText(/Enriquecimento web: Concluído/i)[0]);

    expect(productService.iniciarEnriquecimentoWebProduto).not.toHaveBeenCalled();
  });

  test('nao dispara novamente a acao da linha quando o processo ja esta pendente', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        {
          ...baseItems[0],
          status_titulo_ia: 'PENDENTE',
        },
      ],
      total_items: 1,
    });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getByLabelText(/Títulos: Pendente/i));

    expect(productService.gerarTitulosProdutoModoBasico).not.toHaveBeenCalled();
    expect(productService.gerarTitulosProduto).not.toHaveBeenCalled();
  });

  test('avisa sobre informacoes incompletas antes de gerar descricao sem enriquecimento web concluido', async () => {
    renderPage();
    await screen.findByText('Valvula de Pressao');

    fireEvent.click(screen.getAllByLabelText(/Descrição: Não iniciado/i)[0]);

    expect(window.confirm).toHaveBeenCalledWith(
      'O enriquecimento web de "Valvula de Pressao" ainda não foi concluído. Se continuar agora, as descrições serão geradas com informações incompletas. Deseja continuar mesmo assim?'
    );
    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(2559);
    });
  });

  test('nao gera titulo quando o aviso de informacoes incompletas e cancelado', async () => {
    window.confirm = jest.fn(() => false);

    renderPage();
    await screen.findByText('Valvula de Pressao');

    fireEvent.click(screen.getAllByLabelText(/Títulos: Não iniciado/i)[0]);

    expect(window.confirm).toHaveBeenCalledWith(
      'O enriquecimento web de "Valvula de Pressao" ainda não foi concluído. Se continuar agora, os títulos serão gerados com informações incompletas. Deseja continuar mesmo assim?'
    );
    expect(productService.gerarTitulosProdutoModoBasico).not.toHaveBeenCalled();
  });

  test('gera titulo diretamente quando o enriquecimento web ja terminou mesmo sem encontrar fonte', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [
        {
          ...baseItems[1],
          id: 3001,
          nome_base: 'Sem Fonte',
          status_enriquecimento_web: 'NENHUMA_FONTE_ENCONTRADA',
          status_titulo_ia: 'NAO_INICIADO',
        },
      ],
      total_items: 1,
    });

    renderPage();
    await screen.findByText('Sem Fonte');

    fireEvent.click(screen.getByLabelText(/Títulos: Não iniciado/i));

    await waitFor(() => {
      expect(productService.gerarTitulosProdutoModoBasico).toHaveBeenCalledWith(3001);
    });
    expect(window.confirm).not.toHaveBeenCalled();
  });

  test('marca falha quando a geracao de conteudo retorna erro', async () => {
    productService.batchGeneration.mockRejectedValueOnce(new Error('modelo basico indisponivel'));

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'modelo basico indisponivel'
      );
    });
    expect(screen.getByLabelText(/Descrição: Falha/i)).toBeInTheDocument();
  });

  test('mostra warning quando a geracao em lote termina com falha terminal', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      ...baseItems[0],
      status_descricao_ia: 'FALHA',
    });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri/i }));

    await waitFor(() => {
      expect(productService.batchGeneration).toHaveBeenCalledWith(
        expect.objectContaining({
          produtoIds: [2558],
          tipo: 'descricao',
          provider: 'basico',
        })
      );
    });
    await waitFor(() => {
      expect(showWarningToast).toHaveBeenCalledWith(
        'A geração de descrições terminou com pendências para o produto selecionado.'
      );
    });
  });

  test('uses the default batch delete fallback when the backend rejects without details', async () => {
    productService.batchDeleteProdutos.mockRejectedValueOnce({});

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Ocultar'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao ocultar produtos.');
    });
  });

  test('marks all selected products as failed when every enrichment start request is rejected', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValue(new Error('sem conector'));

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao iniciar enriquecimento para produto ID 2558: sem conector'
      );
    });
    expect(productService.getProdutoById).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/Enriquecimento web: Falha/i)).toBeInTheDocument();
  });

  test('uses the default batch enrichment fallback when the backend rejects without details', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValueOnce({});

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao iniciar enriquecimento para produto ID 2558.'
      );
    });
    expect(screen.getByLabelText(/Enriquecimento web: Falha/i)).toBeInTheDocument();
  });

  test('ignora itens ja pendentes ao iniciar enriquecimento em lote', async () => {
    productService.getProdutoById.mockImplementation(async (produtoId) => {
      if (String(produtoId) === '2558') {
        return {
          ...baseItems[0],
          status_enriquecimento_web: 'PENDENTE',
        };
      }
      return {
        ...baseItems[1],
        status_enriquecimento_web: 'NAO_INICIADO',
      };
    });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar página atual' }));
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledTimes(1);
    });
    expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2559);
    expect(showInfoToast).toHaveBeenCalledWith(
      '1 produto já estava em processamento de enriquecimento web e foi ignorado.'
    );
  });

  test('uses the default batch generation fallback when the backend rejects without details', async () => {
    productService.batchGeneration.mockRejectedValueOnce({});

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao agendar geração em lote.');
    });
    expect(screen.getByLabelText(/Descrição: Falha/i)).toBeInTheDocument();
  });

  test('ignora itens ja pendentes ao iniciar geracao em lote', async () => {
    productService.getProdutoById.mockImplementation(async (produtoId) => {
      if (String(produtoId) === '2558') {
        return {
          ...baseItems[0],
          status_descricao_ia: 'PENDENTE',
        };
      }
      return {
        ...baseItems[1],
        status_descricao_ia: 'NAO_INICIADO',
      };
    });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getSelectionMenuTrigger());
    fireEvent.click(screen.getByRole('menuitem', { name: 'Selecionar página atual' }));
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri/i }));

    await waitFor(() => {
      expect(productService.batchGeneration).toHaveBeenCalledTimes(1);
    });
    expect(productService.batchGeneration).toHaveBeenCalledWith(
      expect.objectContaining({
        produtoIds: [2559],
        tipo: 'descricao',
        provider: 'basico',
      })
    );
    expect(showInfoToast).toHaveBeenCalledWith(
      '1 produto já estava em processamento de geração de descrições e foi ignorado.'
    );
  });

  test('permite trocar o tamanho da pagina e reseta a navegacao para a primeira pagina', async () => {
    const manyItems = Array.from({ length: 10 }, (_, index) => ({
      ...baseItems[index % baseItems.length],
      id: index + 1,
      nome_base: `Produto ${index + 1}`,
      sku: `SKU-${index + 1}`,
    }));

    productService.getProdutos
      .mockResolvedValueOnce({
        items: manyItems,
        total_items: 30,
      })
      .mockResolvedValueOnce({
        items: manyItems.map((item) => ({ ...item, id: item.id + 10 })),
        total_items: 30,
      })
      .mockResolvedValueOnce({
        items: Array.from({ length: 25 }, (_, index) => ({
          ...baseItems[index % baseItems.length],
          id: index + 1,
          nome_base: `Produto Ajustado ${index + 1}`,
          sku: `SKU-AJUSTADO-${index + 1}`,
        })),
        total_items: 30,
      });

    renderPage();
    await screen.findByText('Produto 1');

    fireEvent.click(screen.getByRole('button', { name: /Pr.+xima/i }));

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith(
        expect.objectContaining({
          skip: 10,
          limit: 10,
        })
      );
    });

    fireEvent.click(screen.getByRole('button', { name: 'Itens por página' }));
    fireEvent.click(screen.getByRole('menuitemradio', { name: '25/página' }));

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenLastCalledWith(
        expect.objectContaining({
          skip: 0,
          limit: 25,
        })
      );
    });
  });

  test('avisa quando o polling de enriquecimento nao chega ao estado terminal', async () => {
    jest.useFakeTimers();
    productService.getProdutoById.mockResolvedValue({
      ...baseItems[0],
      status_enriquecimento_web: 'EM_PROGRESSO',
    });

    renderPage();
    await act(async () => {
      await jest.advanceTimersByTimeAsync(100);
    });
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
    });

    for (let step = 0; step < 120; step += 1) {
      // The polling loop schedules the next iteration via timeout on each pass.
      await jest.advanceTimersByTimeAsync(3000);
    }

    expect(showInfoToast).not.toHaveBeenCalledWith(
      'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
    );
  });

  test('continua o polling quando o status enriquecimento vem vazio antes do estado terminal', async () => {
    jest.useFakeTimers();
    productService.getProdutoById
      .mockResolvedValueOnce({
        ...baseItems[0],
        status_enriquecimento_web: null,
      })
      .mockResolvedValueOnce({
        ...baseItems[0],
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(getFirstProductRowCheckbox());
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
    });

    await act(async () => {
      await jest.advanceTimersByTimeAsync(3000);
    });

    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledTimes(2);
    });
  });

  test('mostra warning quando o contexto de tipos reporta erro', async () => {
    mockProductTypesState = {
      productTypes: [],
      isLoading: false,
      error: new Error('tipos indisponiveis'),
    };

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'ProdutosPage: erro recebido do ProductTypeContext:',
      expect.any(Error)
    );
  });

  test('resolveGenerationHandler returns the correct handler for each mode and the noop fallback', async () => {
    expect(resolveGenerationHandler('titulo', true, productService)).toBe(productService.gerarTitulosProduto);
    expect(resolveGenerationHandler('descricao', true, productService)).toBe(productService.gerarDescricaoProduto);
    expect(resolveGenerationHandler('titulo', false, productService)).toBe(
      productService.gerarTitulosProdutoModoBasico
    );
    expect(resolveGenerationHandler('descricao', false, productService)).toBe(
      productService.gerarDescricaoProdutoModoBasico
    );
    expect(resolveGenerationHandler('titulo', true)).toBe(productService.gerarTitulosProduto);

    await expect(resolveGenerationHandler('invalido', false, productService)(2558)).resolves.toBeUndefined();
  });
});




