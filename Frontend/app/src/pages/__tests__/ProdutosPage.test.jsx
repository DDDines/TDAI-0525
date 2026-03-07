import { fireEvent, render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import ProdutosPage from '../ProdutosPage.jsx';
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
  default: ({ product, showAiFeatures, onClose, onOpenContentView }) => (
    <div
      data-testid="product-edit-modal"
      data-product-id={String(product?.id ?? 'new')}
      data-ai={String(showAiFeatures)}
    >
      <button type="button" onClick={() => onOpenContentView?.(product?.id ?? 999)}>
        open-content-from-modal
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
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <ProdutosPage />
    </MemoryRouter>
  );
}

describe('ProdutosPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useRealTimers();
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

  test('gera titulos em lote no modo basico e agenda refresh da lista', async () => {
    jest.useFakeTimers();
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByText('Gerar Títulos'));

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

    fireEvent.click(screen.getByText('close-product-edit-modal'));
    await waitFor(() => {
      expect(screen.queryByTestId('product-edit-modal')).not.toBeInTheDocument();
    });
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
    fireEvent.click(screen.getByText('Gerar Títulos IA'));
    await waitFor(() => {
      expect(productService.gerarTitulosProduto).toHaveBeenCalledWith(2558);
    });

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByText('Gerar Descrições IA'));
    await waitFor(() => {
      expect(productService.gerarDescricaoProduto).toHaveBeenCalledWith(2558);
    });
  });

  test('gera descricoes no modo basico e agenda refresh da lista', async () => {
    jest.useFakeTimers();
    renderPage();
    await screen.findByText('Reservatorio de AR 20 Litros');

    fireEvent.click(screen.getAllByRole('checkbox')[1]);
    fireEvent.click(screen.getByText('Gerar Descrições'));

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

  test('mostra warning quando o contexto de tipos reporta erro', async () => {
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
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
    consoleErrorSpy.mockRestore();
  });
});
