import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
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
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/produtos/:produtoId/conteudo" element={<ProdutoConteudoPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ProdutoConteudoPage', () => {
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

    expect(screen.getByText('Titulo A')).toBeInTheDocument();
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
});
