import React from 'react';
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { renderWithQueryClient } from '../../../test-utils/renderWithQueryClient.jsx';
import ProdutoConteudoPage from '../ProdutoConteudoPage.jsx';
import productService from '../../services/productService';
import { showErrorToast, showSuccessToast, showWarningToast } from '../../utils/notifications';

const mockNavigate = jest.fn();
let mockEffectiveMode = 'basic';

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
    getProdutosIds: jest.fn(),
    deleteProduto: jest.fn(),
    iniciarEnriquecimentoWebProduto: jest.fn(),
    gerarTitulosProduto: jest.fn(),
    gerarDescricaoProduto: jest.fn(),
    gerarTitulosProdutoModoBasico: jest.fn(),
    gerarDescricaoProdutoModoBasico: jest.fn(),
    registrarFeedbackConteudoGerado: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showSuccessToast: jest.fn(),
  showWarningToast: jest.fn(),
}));

jest.mock('../../contexts/AppExperienceContext.jsx', () => ({
  useAppExperience: () => ({
    effectiveMode: mockEffectiveMode,
  }),
}));

function renderPage(initialEntry) {
  return renderWithQueryClient(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/produtos/:produtoId/conteudo" element={<ProdutoConteudoPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const richProduct = {
  id: 31,
  nome_base: 'Reservatório de Ar',
  marca: 'Wabco',
  sku: 'SKU-31',
  ean: '1234567890123',
  imagem_principal_url: 'https://cdn.example.com/produto-31.png',
  fornecedor: { nome: 'Fornecedor Prime' },
  product_type: {
    friendly_name: 'Automotivo',
    attribute_templates: [
      { attribute_key: 'material', label: 'Material' },
      { attribute_key: 'codigo_original', label: 'Código original' },
      { attribute_key: 'titulo_auto', label: 'Título' },
    ],
  },
  titulos_sugeridos: ['Título A', 'Título B', 'Título A'],
  descricao_chat_api:
    'Fundada em 1999. Reservatório indicado para sistemas de freio pesado.',
  dynamic_attributes: {
    material: 'Alumínio',
    codigo_original: 'WAB-31',
    titulo_auto: 'Não deve aparecer',
  },
  modelo: 'Linha Premium',
  categoria_original: 'Freio',
  dados_brutos_web: {
    especificacoes_tecnicas_dict: {
      capacidade: '20 litros',
    },
    nome: 'Tool-Check Modular Micro 1 Caminho do catalogo: Wera Tools > Tools > Tool-Check Modular Micro 1 URL da fonte: https://www.wera.de/en/tools/tool-check-modular-micro-1/',
    ool_check_modular_micro: '1/',
    lista_caracteristicas_beneficios_bullets:
      'Nome: Tool-Check Modular Micro 1 Caminho do catalogo: Wera Tools > Tools > Tool-Check Modular Micro 1 URL da fonte: https://www.wera.de/en/tools/tool-check-modular-micro-1/',
    fonte_principal_url: 'https://www.wera.de/en/tools/tool-check-modular-micro-1/',
    feedback_conteudo: {
      valor: 'gostei',
      comentario: 'Muito bom',
    },
    titulos_sugeridos_gerados: ['Título C'],
    descricao_gerada: 'Texto duplicado',
    log_interno: 'Não mostrar',
  },
  status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
  status_titulo_ia: 'CONCLUIDO_SUCESSO',
  status_descricao_ia: 'NAO_INICIADO',
};

describe('ProdutoConteudoPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    jest.spyOn(window, 'confirm').mockImplementation(() => true);
    mockEffectiveMode = 'basic';
    productService.getProdutosIds.mockResolvedValue({ ids: [30, 31, 32] });
    productService.getProdutos.mockResolvedValue({
      items: [{ id: 30 }, { id: 31 }, { id: 32 }],
      total_items: 3,
    });
    productService.getProdutoById.mockResolvedValue(richProduct);
    productService.deleteProduto.mockResolvedValue({ ...richProduct, is_deleted: true });
    productService.iniciarEnriquecimentoWebProduto.mockResolvedValue({ ok: true });
    productService.registrarFeedbackConteudoGerado.mockResolvedValue({
      ...richProduct,
      dados_brutos_web: {
        ...richProduct.dados_brutos_web,
        feedback_conteudo: {
          valor: 'gostei',
          comentario: 'Aprovado',
        },
      },
    });
    productService.gerarTitulosProduto.mockResolvedValue({ ok: true });
    productService.gerarDescricaoProduto.mockResolvedValue({ ok: true });
    productService.gerarTitulosProdutoModoBasico.mockResolvedValue({ ok: true });
    productService.gerarDescricaoProdutoModoBasico.mockResolvedValue({ ok: true });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
    window.confirm.mockRestore();
  });

  test('usa o nome do produto como heading, renderiza o resumo geral e remove o título genérico', async () => {
    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        returnTo: '/produtos?page=2',
        productIds: [30, 31, 32],
        productQuery: { sort_by: 'id', sort_order: 'asc' },
      },
    });

    expect(await screen.findByRole('heading', { name: 'Reservatório de Ar' })).toBeInTheDocument();
    expect(screen.queryByText(/Conteúdo Gerado do Produto/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Marca: Wabco/)).toBeInTheDocument();
    expect(screen.getByText('Fornecedor Prime')).toBeInTheDocument();
    expect(screen.getByText('Automotivo')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Fechar conteúdo do produto/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Abrir edição/i })).toBeInTheDocument();
    expect(screen.getByText('Material')).toBeInTheDocument();
    expect(screen.getByText('Alumínio')).toBeInTheDocument();
    expect(screen.getByText('Capacidade')).toBeInTheDocument();
    expect(screen.getByText('20 litros')).toBeInTheDocument();
    expect(screen.queryByText('Não deve aparecer')).not.toBeInTheDocument();
    expect(screen.queryByText('Texto duplicado')).not.toBeInTheDocument();
    expect(screen.queryByText('log_interno')).not.toBeInTheDocument();
    expect(screen.queryByText(/Tool-Check Modular Micro 1 Caminho do catalogo/i)).not.toBeInTheDocument();
    expect(screen.queryByText('1/')).not.toBeInTheDocument();
    expect(screen.getByText('Reservatório indicado para sistemas de freio pesado.')).toBeInTheDocument();
    expect(screen.queryByText(/Fundada em 1999/)).not.toBeInTheDocument();
  });

  test('fecha pela ação X usando returnTo e navega entre produtos mantendo o estado', async () => {
    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        returnTo: '/produtos?page=3&search=ar',
        productIds: [30, 31, 32],
        productQuery: { sort_by: 'nome_base', sort_order: 'asc', search: 'ar' },
      },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });

    fireEvent.click(screen.getByRole('button', { name: /Fechar conteúdo do produto/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos?page=3&search=ar');

    fireEvent.click(screen.getByRole('button', { name: /Próximo produto/i }));
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/32/conteudo', {
      state: {
        productIds: [30, 31, 32],
        productQuery: {
          sort_by: 'nome_base',
          sort_order: 'asc',
          search: 'ar',
        },
        returnTo: '/produtos?page=3&search=ar',
      },
    });
  });

  test('oculta o produto atual e abre o próximo item da lista', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        returnTo: '/produtos?page=3&search=ar',
        productIds: [30, 31, 32],
        productQuery: { sort_by: 'nome_base', sort_order: 'asc', search: 'ar' },
      },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });
    await user.click(screen.getByRole('button', { name: /Ocultar produto/i }));

    expect(window.confirm).toHaveBeenCalledWith(
      'Tem certeza que deseja ocultar "Reservatório de Ar"?\n\nEle será ocultado da lista, mas continuará salvo no banco de dados.'
    );
    await waitFor(() => {
      expect(productService.deleteProduto).toHaveBeenCalledWith(31);
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Produto ocultado com sucesso.');
    expect(mockNavigate).toHaveBeenCalledWith('/produtos/32/conteudo', {
      state: {
        productIds: [30, 32],
        productQuery: {
          sort_by: 'nome_base',
          sort_order: 'asc',
          search: 'ar',
        },
        returnTo: '/produtos?page=3&search=ar',
      },
      replace: true,
    });
  });

  test('volta para a lista quando o produto ocultado era o único da navegação', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    productService.getProdutosIds.mockResolvedValueOnce({ ids: [31] });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: {
        returnTo: '/produtos?page=5',
        productIds: [31],
        productQuery: { sort_by: 'id', sort_order: 'desc' },
      },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });
    await user.click(screen.getByRole('button', { name: /Ocultar produto/i }));

    await waitFor(() => {
      expect(productService.deleteProduto).toHaveBeenCalledWith(31);
    });
    expect(mockNavigate).toHaveBeenCalledWith('/produtos?page=5', { replace: true });
  });

  test('mostra apenas os botões básicos quando o modo é basic', async () => {
    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });

    expect(screen.getByRole('button', { name: 'Gerar títulos no básico' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Executar enriquecimento web' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Gerar descrição no básico' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gerar títulos com IA' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Gerar descrição com IA' })).not.toBeInTheDocument();
  });

  test('mantém os atalhos desabilitados quando o produto já está pendente', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      ...richProduct,
      status_enriquecimento_web: 'PENDENTE',
      status_titulo_ia: 'PENDENTE',
      status_descricao_ia: 'PENDENTE',
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });

    expect(screen.getByRole('button', { name: 'Executar enriquecimento web' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Gerar títulos no básico' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Gerar descrição no básico' })).toBeDisabled();
  });

  test('mostra os botões de IA no modo complete', async () => {
    mockEffectiveMode = 'complete';

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });

    expect(screen.getByRole('button', { name: 'Gerar títulos com IA' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Gerar descrição com IA' })).toBeInTheDocument();
  });

  test('dispara geração básica de títulos e descrição na tela dedicada', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });
    await user.click(screen.getByRole('button', { name: 'Gerar títulos no básico' }));
    await waitFor(() => {
      expect(productService.gerarTitulosProdutoModoBasico).toHaveBeenCalledWith(31);
    });

    await user.click(screen.getByRole('button', { name: 'Gerar descrição no básico' }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProdutoModoBasico).toHaveBeenCalledWith(31);
    });

    act(() => {
      jest.runOnlyPendingTimers();
    });
  });

  test('dispara enriquecimento web pelo atalho dedicado', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });
    await user.click(screen.getByRole('button', { name: 'Executar enriquecimento web' }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(31);
    });
  });

  test('mostra sucesso quando o enriquecimento termina com sucesso na tela dedicada', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    productService.getProdutoById
      .mockResolvedValueOnce(richProduct)
      .mockResolvedValueOnce({
        ...richProduct,
        status_enriquecimento_web: 'CONCLUIDO_SUCESSO',
      });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });
    await user.click(screen.getByRole('button', { name: 'Executar enriquecimento web' }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(31);
    });
    await waitFor(() => {
      expect(showSuccessToast).toHaveBeenCalledWith('Enriquecimento web finalizado com sucesso.');
    });
    expect(showWarningToast).not.toHaveBeenCalledWith(
      expect.stringContaining('Enriquecimento web finalizado com pendências')
    );
  });

  test('mostra aviso quando o enriquecimento termina com pendências na tela dedicada', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    productService.getProdutoById
      .mockResolvedValueOnce(richProduct)
      .mockResolvedValueOnce({
        ...richProduct,
        status_enriquecimento_web: 'CONCLUIDO_COM_DADOS_PARCIAIS',
      });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });
    await user.click(screen.getByRole('button', { name: 'Executar enriquecimento web' }));

    await waitFor(() => {
      expect(productService.iniciarEnriquecimentoWebProduto).toHaveBeenCalledWith(31);
    });
    await waitFor(() => {
      expect(showWarningToast).toHaveBeenCalledWith(
        'Enriquecimento web finalizado com pendências (CONCLUIDO_COM_DADOS_PARCIAIS). Revise os dados coletados.'
      );
    });
  });

  test('dispara geração com IA quando o modo complete está ativo', async () => {
    mockEffectiveMode = 'complete';
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await screen.findByRole('heading', { name: 'Reservatório de Ar' });
    await user.click(screen.getByRole('button', { name: 'Gerar títulos com IA' }));
    await waitFor(() => {
      expect(productService.gerarTitulosProduto).toHaveBeenCalledWith(31);
    });

    await user.click(screen.getByRole('button', { name: 'Gerar descrição com IA' }));
    await waitFor(() => {
      expect(productService.gerarDescricaoProduto).toHaveBeenCalledWith(31);
    });

    act(() => {
      jest.runOnlyPendingTimers();
    });
  });

  test('renderiza estado vazio das informações coletadas quando não há dados relevantes', async () => {
    productService.getProdutoById.mockResolvedValueOnce({
      id: 31,
      nome_base: 'Produto limpo',
      titulos_sugeridos: [],
      descricao_chat_api: '',
      dynamic_attributes: {},
      dados_brutos_web: {
        titulos_sugeridos_gerados: ['Ignorar'],
        feedback_conteudo: { valor: 'gostei' },
      },
      status_enriquecimento_web: 'NAO_INICIADO',
      status_titulo_ia: 'NAO_INICIADO',
      status_descricao_ia: 'NAO_INICIADO',
    });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    expect(await screen.findByRole('heading', { name: 'Produto limpo' })).toBeInTheDocument();
    expect(screen.getByText('Nenhuma informação adicional coletada para este produto.')).toBeInTheDocument();
    expect(screen.getByText('Descrição ainda não gerada.')).toBeInTheDocument();
  });

  test('carrega feedback salvo e permite salvar um novo feedback', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    expect(await screen.findByDisplayValue('Muito bom')).toBeInTheDocument();

    const commentField = screen.getByPlaceholderText(/Ex\.: títulos bons/i);
    await user.clear(commentField);
    await user.type(commentField, 'Aprovado');
    await user.click(screen.getByRole('button', { name: 'Gostei' }));

    await waitFor(() => {
      expect(productService.registrarFeedbackConteudoGerado).toHaveBeenCalledWith(31, {
        valor: 'gostei',
        comentario: 'Aprovado',
      });
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Feedback salvo com sucesso.');
  });

  test('exibe erro amigável quando o carregamento falha', async () => {
    productService.getProdutoById.mockRejectedValueOnce(new Error('Falha ao carregar conteúdo.'));

    renderPage({
      pathname: '/produtos/31/conteudo',
      state: { productIds: [31] },
    });

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao carregar conteúdo.');
    });
  });
});


