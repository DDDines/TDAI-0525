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
    getProdutoById: jest.fn(),
    batchDeleteProdutos: jest.fn(),
    gerarTitulosProduto: jest.fn(),
    gerarDescricaoProduto: jest.fn(),
    gerarTitulosProdutoModoBasico: jest.fn(),
    gerarDescricaoProdutoModoBasico: jest.fn(),
    iniciarEnriquecimentoWebProduto: jest.fn(),
  },
}));

jest.mock('../../components/common/Modal', () => ({
  __esModule: true,
  default: ({ children }) => <div data-testid="modal-wrapper">{children}</div>,
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
    productService.batchDeleteProdutos.mockResolvedValue({ deleted: 1 });
    productService.gerarTitulosProduto.mockResolvedValue({ ok: true });
    productService.gerarDescricaoProduto.mockResolvedValue({ ok: true });
    productService.gerarTitulosProdutoModoBasico.mockResolvedValue({ ok: true });
    productService.gerarDescricaoProdutoModoBasico.mockResolvedValue({ ok: true });
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
    expect(screen.getAllByText('Web').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Tit').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Desc').length).toBeGreaterThan(0);
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

    fireEvent.click(screen.getByTitle('Atualizar lista de produtos'));

    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenCalledTimes(5);
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

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /Gerar T/i }));

    await waitFor(() => {
      expect(productService.gerarTitulosProdutoModoBasico).toHaveBeenCalledWith(2558);
    });
    expect(showInfoToast).toHaveBeenCalledWith('Geração de títulos iniciada para 1 produto(s).');

    await act(async () => {
      jest.advanceTimersByTime(15000);
    });

    await waitFor(() => {
      expect(showInfoToast).toHaveBeenCalledWith(
        'Atualizando lista para verificar resultados da geração de títulos...'
      );
      expect(productService.getProdutos).toHaveBeenCalledTimes(2);
    });
  });

  test('deleta os produtos selecionados em lote', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByText('Deletar'));

    await waitFor(() => {
      expect(productService.batchDeleteProdutos).toHaveBeenCalledWith([2558]);
    });
    expect(showSuccessToast).toHaveBeenCalledWith('1 produto(s) deletado(s) com sucesso!');
    expect(window.confirm).toHaveBeenCalledWith(
      'Tem certeza que deseja deletar 1 produto(s) selecionado(s)?'
    );
  });

  test('inicia enriquecimento web em lote e consulta o status do produto', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
    });
    expect(showInfoToast).toHaveBeenCalledWith('Enriquecimento web iniciado para 1 produto(s).');
    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledWith('2558');
    });
  });

  test('interrompe o polling de enriquecimento ao desmontar a pagina apos falhas de consulta', async () => {
    jest.useFakeTimers();
    productService.getProdutoById.mockRejectedValue(new Error('poll indisponivel'));

    const { unmount } = renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
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
    expect(mockNavigate).toHaveBeenCalledWith('/produtos', { replace: true });
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

    fireEvent.click(screen.getByText('+ Novo Produto'));

    expect(await screen.findByTestId('product-edit-modal')).toHaveAttribute('data-product-id', 'new');

    fireEvent.click(screen.getByText('open-content-from-modal'));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/999/conteudo', {
      state: {
        productIds: [2558, 2559],
        productQuery: {
          sort_by: 'id',
          sort_order: 'desc',
        },
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

  test('respeita cancelamento e mostra erro ao falhar deletar em lote', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);

    window.confirm = jest.fn(() => false);
    fireEvent.click(screen.getByText('Deletar'));
    expect(productService.batchDeleteProdutos).not.toHaveBeenCalled();

    window.confirm = jest.fn(() => true);
    productService.batchDeleteProdutos.mockRejectedValueOnce(new Error('sem permissao'));
    fireEvent.click(screen.getByText('Deletar'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('sem permissao');
    });
  });

  test('processa enriquecimento web parcial e marca falha local para itens rejeitados', async () => {
    productService.iniciarEnriquecimentoWebProduto
      .mockRejectedValueOnce(new Error('sem fonte'))
      .mockResolvedValueOnce({ ok: true });
    productService.getProdutoById.mockResolvedValueOnce({
      ...baseItems[1],
      status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
    });

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
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

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
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
    fireEvent.change(screen.getByDisplayValue('Status Título IA'), {
      target: { value: 'CONCLUIDO' },
    });
    fireEvent.change(screen.getByDisplayValue('Status Descrição IA'), {
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

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /Gerar T.*IA/i }));
    await waitFor(() => {
      expect(productService.gerarTitulosProduto).toHaveBeenCalledWith(2558);
    });

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri.*IA/i }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProduto).toHaveBeenCalledWith(2558);
    });
  });

  test('gera descricoes no modo basico e agenda refresh da lista', async () => {
    jest.useFakeTimers();
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri/i }));

    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(2558);
    });
    expect(showInfoToast).toHaveBeenCalledWith('Geração de descrições iniciada para 1 produto(s).');

    await act(async () => {
      jest.advanceTimersByTime(15000);
    });

    await waitFor(() => {
      expect(showInfoToast).toHaveBeenCalledWith(
        'Atualizando lista para verificar resultados da geração de descrições...'
      );
    });
  });

  test('permite selecionar tudo, desmarcar um item e limpar a selecao em lote', async () => {
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    const [selectAllCheckbox, firstRowCheckbox] = screen.getAllByRole('checkbox');

    fireEvent.click(selectAllCheckbox);
    expect(screen.getByText('2 produto(s) selecionado(s)')).toBeInTheDocument();

    fireEvent.click(firstRowCheckbox);
    expect(screen.getByText('1 produto(s) selecionado(s)')).toBeInTheDocument();

    fireEvent.click(selectAllCheckbox);
    expect(screen.getByText('2 produto(s) selecionado(s)')).toBeInTheDocument();

    fireEvent.click(selectAllCheckbox);
    expect(screen.queryByText(/produto\(s\) selecionado\(s\)/i)).not.toBeInTheDocument();
  });

  test('marca falha quando a geracao de conteudo retorna erro', async () => {
    productService.gerarDescricaoProdutoModoBasico.mockRejectedValueOnce(new Error('modelo basico indisponivel'));

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByRole('button', { name: /Gerar Descri/i }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao gerar descricao para produto ID 2558: modelo basico indisponivel'
      );
    });
    expect(screen.getByTitle('Falha')).toBeInTheDocument();
  });

  test('uses the default batch delete fallback when the backend rejects without details', async () => {
    productService.batchDeleteProdutos.mockRejectedValueOnce({});

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByText('Deletar'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao deletar produtos.');
    });
  });

  test('marks all selected products as failed when every enrichment start request is rejected', async () => {
    productService.iniciarEnriquecimentoWebProduto.mockRejectedValue(new Error('sem conector'));

    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        'Erro ao iniciar enriquecimento para produto ID 2558: sem conector'
      );
    });
    expect(productService.getProdutoById).not.toHaveBeenCalled();
    expect(screen.getByTitle('Falha')).toBeInTheDocument();
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

    fireEvent.change(document.querySelector('.items-per-page-select'), {
      target: { value: '25' },
    });

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
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByText('Enriquecer Web'));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(2558);
    });

    for (let step = 0; step < 120; step += 1) {
      // The polling loop schedules the next iteration via timeout on each pass.
      await jest.advanceTimersByTimeAsync(3000);
    }

    await waitFor(() => {
      expect(showInfoToast).toHaveBeenCalledWith(
        'O enriquecimento web ainda pode estar em andamento em segundo plano. Atualizando a lista.'
      );
    });
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

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
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


