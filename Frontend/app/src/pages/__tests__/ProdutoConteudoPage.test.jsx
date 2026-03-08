import React from 'react';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { renderWithQueryClient } from '../../../test-utils/renderWithQueryClient.jsx';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProdutoConteudoPage from '../ProdutoConteudoPage.jsx';
import productService from '../../services/productService';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';

const mockNavigate = jest.fn();

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
    getProdutoById: jest.fn(),
    getProdutos: jest.fn(),
    registrarFeedbackConteudoGerado: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showSuccessToast: jest.fn(),
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    error: jest.fn(),
  },
}));

function renderPage(initialEntry) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/produtos/:produtoId/conteudo" element={<ProdutoConteudoPage />} />
      </Routes>
    </MemoryRouter>
  );
}

function renderPageWithoutRouteParam(initialEntry = '/conteudo-sem-id') {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="*" element={<ProdutoConteudoPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProdutoConteudoPage', () => {
  let feedbackReject;

  beforeEach(() => {
    jest.clearAllMocks();
    productService.getProdutos.mockResolvedValue({
      items: [{ id: 30 }, { id: 31 }, { id: 32 }],
      total_items: 3,
    });
    productService.getProdutoById.mockResolvedValue({
      id: 31,
      nome_base: 'Reservatorio de Ar',
      titulos_sugeridos: ['Titulo A', 'Titulo B', 'Titulo A'],
      descricao_chat_api: 'Fundada em 1999. Produto ideal para sistemas de freio pesado.',
      dados_brutos_web: {
        titulos_sugeridos_gerados: ['Titulo C', 'Titulo B', 'Titulo D', 'Titulo E'],
      },
    });
    productService.registrarFeedbackConteudoGerado.mockResolvedValue({
      id: 31,
      nome_base: 'Reservatorio de Ar',
      titulos_sugeridos: ['Titulo A'],
      descricao_chat_api: 'Produto ideal para sistemas de freio pesado.',
      dados_brutos_web: {
        feedback_conteudo: {
          valor: 'gostei',
          comentario: 'Conteudo consistente',
        },
      },
    });
    feedbackReject = null;
  });

  test('renders unique generated titles, sanitizes company timeline claims and enables navigation', async () => {
    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [30, 31, 32],
        productQuery: { sort_by: 'id', sort_order: 'desc' },
      },
    });

    await waitFor(() => {
      expect(productService.getProdutoById).toHaveBeenCalledWith('31');
    });

    expect(await screen.findByText('Titulo A')).toBeInTheDocument();
    expect(screen.getByText('Titulo B')).toBeInTheDocument();
    expect(screen.getByText('Titulo C')).toBeInTheDocument();
    expect(screen.getByText('Titulo D')).toBeInTheDocument();
    expect(screen.getByText('Titulo E')).toBeInTheDocument();
    expect(
      screen.getByText('Produto ideal para sistemas de freio pesado.')
    ).toBeInTheDocument();
    expect(screen.queryByText(/Fundada em 1999/)).not.toBeInTheDocument();

    expect(screen.getByRole('button', { name: /Produto Anterior/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /Pr.+ximo Produto/i })).toBeEnabled();
  });

  test('navigates to adjacent products while preserving the ordering state', async () => {
    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [30, 31, 32],
        productQuery: { sort_by: 'nome_base', sort_order: 'asc', search: 'ar' },
      },
    });

    await screen.findByText('Titulo A');

    fireEvent.click(screen.getByRole('button', { name: /Pr.+ximo Produto/i }));

    expect(mockNavigate).toHaveBeenCalledWith('/produtos/32/conteudo', {
      state: {
        productIds: [30, 31, 32],
        productQuery: {
          sort_by: 'nome_base',
          sort_order: 'asc',
          search: 'ar',
        },
      },
    });
  });

  test('saves feedback for generated content and updates the screen state', async () => {
    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [30, 31, 32],
        productQuery: { sort_by: 'id', sort_order: 'desc' },
      },
    });

    await screen.findByText('Titulo A');

    fireEvent.change(screen.getByPlaceholderText(/Ex:/i), {
      target: { value: 'Conteudo consistente' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Gostei' }));

    await waitFor(() => {
      expect(productService.registrarFeedbackConteudoGerado).toHaveBeenCalledWith(31, {
        valor: 'gostei',
        comentario: 'Conteudo consistente',
      });
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Feedback salvo com sucesso.');
  });

  test('shows an error toast when the product content cannot be loaded', async () => {
    productService.getProdutoById.mockRejectedValueOnce(new Error('Falha ao carregar conteudo.'));

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [31],
        productQuery: { sort_by: 'id', sort_order: 'desc' },
      },
    });

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao carregar conteudo.');
    });
  });

  test('falls back to placeholders and disables feedback when there is no generated content', async () => {
    productService.getProdutos.mockRejectedValueOnce(new Error('lista indisponivel'));
    productService.getProdutoById.mockResolvedValueOnce({
      id: 31,
      nome_base: 'Produto sem conteudo',
      titulos_sugeridos: [],
      descricao_chat_api: '',
      descricao_original: '',
      dados_brutos_web: {},
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
    });

    expect(await screen.findByText(/Produto #31 - Produto sem conteudo/i)).toBeInTheDocument();
    expect(
      await screen.findAllByText((content) =>
        content.includes('Titulo ainda') && content.includes('posicao')
      )
    ).toHaveLength(5);
    expect(screen.getByText(/Descricao ainda nao gerada/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Gostei' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /N.*Gostei/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Produto Anterior/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Pr.+ximo Produto/i })).toBeDisabled();
  });

  test('sanitizes list query defaults, preserves full-list navigation and supports header actions', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [{ id: 29 }, { id: 30 }, { id: 31 }, { id: 32 }, { id: 33 }],
      total_items: 5,
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: ['31', '31', 'invalido', 30, 0, 29],
        productQuery: {
          fornecedor_id: 22,
          sort_by: '',
          sort_order: '',
          ignored: 'x',
          status_titulo_ia: null,
        },
      },
    });

    await screen.findByText('Titulo A');

    expect(productService.getProdutos).toHaveBeenCalledWith({
      fornecedor_id: 22,
      sort_by: 'id',
      sort_order: 'asc',
      skip: 0,
      limit: 200,
    });

    fireEvent.click(screen.getByRole('button', { name: /Voltar para Produtos/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos');

    fireEvent.click(screen.getByRole('button', { name: /Abrir Edi/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos?id=31');

    fireEvent.click(screen.getByRole('button', { name: /Produto Anterior/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/30/conteudo', {
      state: {
        productIds: [29, 30, 31, 32, 33],
        productQuery: {
          fornecedor_id: 22,
          sort_by: 'id',
          sort_order: 'asc',
        },
      },
    });
  });

  test('loads saved feedback, preserves timeline-only text when needed and handles feedback save failures', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      id: 31,
      nome_base: 'Reservatorio de Ar',
      titulos_sugeridos: ['Titulo A'],
      descricao_chat_api: 'Fundada em 1999.',
      dados_brutos_web: {
        feedback_conteudo: {
          valor: 'nao_gostei',
          comentario: 'Texto muito institucional',
        },
      },
    });
    productService.registrarFeedbackConteudoGerado.mockImplementationOnce(
      () =>
        new Promise((resolve, reject) => {
          feedbackReject = reject;
        })
    );

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [31],
        productQuery: { sort_by: 'id', sort_order: 'desc' },
      },
    });

    expect(await screen.findByDisplayValue('Texto muito institucional')).toBeInTheDocument();
    expect(screen.getByText('Fundada em 1999.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /N.*Gostei/i }));

    expect(productService.registrarFeedbackConteudoGerado).toHaveBeenCalledWith(31, {
      valor: 'nao_gostei',
      comentario: 'Texto muito institucional',
    });
    expect(screen.getByRole('button', { name: 'Gostei' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /N.*Gostei/i })).toBeDisabled();
    expect(screen.getByPlaceholderText(/Ex:/i)).toBeDisabled();

    feedbackReject(new Error('Falha ao salvar feedback.'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao salvar feedback.');
    });
    expect(screen.getByRole('button', { name: 'Gostei' })).toBeEnabled();
  });

  test('uses alternate description sources and shows seo fallback content', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      id: 31,
      nome_base: 'Reservatorio de Ar',
      titulos_sugeridos: [],
      descricao_chat_api: '',
      descricao_original: '',
      dados_brutos_web: {
        descricao_gerada: '',
        descricao_detalhada_seo: 'Descricao SEO aproveitavel.',
      },
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    expect(await screen.findByText('Descricao SEO aproveitavel.')).toBeInTheDocument();
  });

  test('keeps empty saved comments and preserves timeline-only descriptions when they are the first valid candidate', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      id: 31,
      nome_base: 'Reservatorio de Ar',
      titulos_sugeridos: ['Titulo A'],
      descricao_chat_api: 'Fundada em 1999.',
      dados_brutos_web: {
        feedback_conteudo: {
          valor: 'gostei',
        },
      },
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    expect(await screen.findByText('Fundada em 1999.')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Ex:/i)).toHaveValue('');
  });

  test('keeps the state ordering when the backend list returns no items', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [],
      total_items: 0,
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [30, 31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    await screen.findByText('Titulo A');

    fireEvent.click(screen.getByRole('button', { name: /Produto Anterior/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/30/conteudo', {
      state: {
        productIds: [30, 31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });
  });

  test('preserves ids from state when the full-list fetch fails after mount', async () => {
    productService.getProdutos.mockRejectedValueOnce(new Error('lista indisponivel'));

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [30, 31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    await screen.findByText('Titulo A');

    fireEvent.click(screen.getByRole('button', { name: /Produto Anterior/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/30/conteudo', {
      state: {
        productIds: [30, 31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });
  });

  test('stops the full-list fetch when a partial page is returned without total count', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [{ id: 31 }],
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [],
        productQuery: { fornecedor_id: 99 },
      },
    });

    await screen.findByText('Titulo A');

    expect(productService.getProdutos).toHaveBeenCalledTimes(1);
    expect(productService.getProdutos).toHaveBeenCalledWith({
      fornecedor_id: 99,
      sort_by: 'id',
      sort_order: 'asc',
      skip: 0,
      limit: 200,
    });
    expect(screen.getByRole('button', { name: /Produto Anterior/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Pr.+ximo Produto/i })).toBeDisabled();
  });

  test('continues fetching the full list when the first page is full and falls back to the route id', async () => {
    const fullPage = Array.from({ length: 200 }, (_, index) => ({ id: index + 1 }));
    productService.getProdutos
      .mockResolvedValueOnce({
        items: fullPage,
      })
      .mockResolvedValueOnce({
        items: [{ id: 201 }],
      });
    productService.getProdutoById.mockResolvedValueOnce({
      id: null,
      nome_base: 'Produto vindo da rota',
      titulos_sugeridos: ['Titulo da rota'],
      descricao_chat_api: 'Descricao valida.',
      dados_brutos_web: {},
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [],
        productQuery: { fornecedor_id: 88 },
      },
    });

    expect(await screen.findByText('Titulo da rota')).toBeInTheDocument();
    await waitFor(() => {
      expect(productService.getProdutos).toHaveBeenCalledTimes(2);
    });

    fireEvent.click(screen.getByRole('button', { name: /Produto Anterior/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/30/conteudo', {
      state: {
        productIds: Array.from({ length: 201 }, (_, index) => index + 1),
        productQuery: {
          fornecedor_id: 88,
          sort_by: 'id',
          sort_order: 'asc',
        },
      },
    });
  });

  test('treats non-array list payloads as empty while preserving the loaded product id', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: { invalid: true },
      total_items: 0,
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    expect(await screen.findByText('Titulo A')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Produto Anterior/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Pr.+ximo Produto/i })).toBeDisabled();
  });

  test('adds the loaded product id to the ordered navigation list when it was missing', async () => {
    productService.getProdutos.mockResolvedValueOnce({
      items: [{ id: 29 }, { id: 30 }],
      total_items: 2,
    });
    productService.getProdutoById.mockResolvedValueOnce({
      id: 35,
      nome_base: 'Produto novo na lista',
      titulos_sugeridos: ['Titulo unico'],
      descricao_chat_api: 'Descricao aproveitavel.',
      dados_brutos_web: {},
    });

    renderPage({
      pathname: '/produtos/35/conteudo',
      state: {
        productIds: [30],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    expect(await screen.findByText('Titulo unico')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Produto Anterior/i })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole('button', { name: /Produto Anterior/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/30/conteudo', {
      state: {
        productIds: [29, 30, 35],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });
  });

  test('ignores feedback submission when the loaded content still has no persisted product id', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      id: null,
      nome_base: 'Rascunho temporario',
      titulos_sugeridos: ['Titulo provisório'],
      descricao_chat_api: 'Descricao provisoria.',
      dados_brutos_web: {},
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    expect(await screen.findByText(/Titulo provis.rio/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Gostei' }));

    expect(productService.registrarFeedbackConteudoGerado).not.toHaveBeenCalled();
    expect(showSuccessToast).not.toHaveBeenCalled();
    expect(showErrorToast).not.toHaveBeenCalled();
  });

  test('uses default load and save error fallbacks when service errors are empty', async () => {
    productService.getProdutoById.mockRejectedValueOnce({});

    const firstRender = renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao carregar conteudo do produto.');
    });

    firstRender.unmount();
    jest.clearAllMocks();
    productService.getProdutoById.mockResolvedValueOnce({
      id: 31,
      nome_base: 'Reservatorio de Ar',
      titulos_sugeridos: ['Titulo A'],
      descricao_chat_api: 'Descricao valida.',
      dados_brutos_web: {},
    });
    productService.registrarFeedbackConteudoGerado.mockRejectedValueOnce({});

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        productIds: [31],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    await screen.findByText('Descricao valida.');
    fireEvent.click(screen.getByRole('button', { name: 'Gostei' }));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao salvar feedback.');
    });
  });

  test('falls back to product id zero when neither the route param nor the loaded payload exposes an id', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      id: null,
      nome_base: 'Produto sem rota',
      titulos_sugeridos: ['Titulo sem rota'],
      descricao_chat_api: 'Descricao sem rota.',
      dados_brutos_web: {},
    });

    renderPageWithoutRouteParam();

    expect(await screen.findByText('Titulo sem rota')).toBeInTheDocument();
    expect(productService.getProdutoById).toHaveBeenCalledWith(undefined);
    expect(screen.getByRole('button', { name: /Produto Anterior/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Pr.+ximo Produto/i })).toBeDisabled();
  });
});




