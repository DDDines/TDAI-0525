import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import PlanoPage from '../PlanoPage.jsx';
import authService from '../../services/authService';
import dashboardService from '../../services/dashboardService';
import planosService from '../../services/planosService';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { showErrorToast, showInfoToast } from '../../utils/notifications';

jest.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    getCurrentUser: jest.fn(),
  },
}));

jest.mock('../../services/dashboardService', () => ({
  __esModule: true,
  default: {
    getMyDashboard: jest.fn(),
  },
}));

jest.mock('../../services/planosService', () => ({
  __esModule: true,
  default: {
    listarPlanos: jest.fn(),
    mudarPlano: jest.fn(),
    criarCheckout: jest.fn(),
    abrirPortal: jest.fn(),
  },
}));

jest.mock('../../contexts/WorkspaceContext', () => ({
  useWorkspace: jest.fn(),
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showInfoToast: jest.fn(),
}));

describe('PlanoPage', () => {
  const renderPage = () =>
    render(
      <MemoryRouter>
        <PlanoPage />
      </MemoryRouter>
    );

  beforeEach(() => {
    jest.clearAllMocks();
    useWorkspace.mockReturnValue({
      workspace: { nome: 'Dines' },
    });
    planosService.listarPlanos.mockResolvedValue([]);
    dashboardService.getMyDashboard.mockResolvedValue({
      plano_nome: 'Pro',
      product_experience_mode: 'complete',
      limites: {
        produtos: 1500,
        enriquecimento_web: 999999,
        geracao_ia: 400,
      },
      uso_mes_atual: {
        enriquecimento_web: 18,
        geracao_ia: 42,
      },
      totais: {
        produtos: 210,
        fornecedores: 9,
      },
    });
  });

  test('renders the plan overview with capacity, coverage and action shortcuts', async () => {
    authService.getCurrentUser.mockResolvedValueOnce({
      id: 8,
      product_experience_mode: 'complete',
      plano: {
        nome: 'Pro',
        limite_produtos: 1500,
        limite_enriquecimento_web: 999999,
        limite_geracao_ia: 400,
        permite_api_externa: true,
        suporte_prioritario: true,
      },
    });

    renderPage();

    expect(await screen.findByRole('heading', { name: 'Pro' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Capacidade do plano/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Cobertura incluída/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Ações financeiras/i })).toBeInTheDocument();
    expect(screen.getByText(/Credenciais do cliente liberadas/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Ilimitado/).length).toBeGreaterThan(0);
    expect(screen.getByRole('link', { name: /Abrir monitoramento/i })).toHaveAttribute('href', '/monitoramento');
    expect(screen.getByRole('link', { name: /Configurar credenciais/i })).toHaveAttribute('href', '/configuracoes');
    expect(screen.getByRole('button', { name: /Mudar de plano/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Falar com suporte/i }));

    expect(showInfoToast).toHaveBeenNthCalledWith(
      1,
      expect.stringMatching(/suporte comercial ainda não foi conectado/i)
    );
  });

  test('shows an inline loading state before data resolves', () => {
    authService.getCurrentUser.mockReturnValueOnce(new Promise(() => {}));
    dashboardService.getMyDashboard.mockReturnValueOnce(new Promise(() => {}));

    renderPage();

    expect(screen.getByText(/Preparando a leitura financeira da empresa/i)).toBeInTheDocument();
  });

  test('shows an error state when user data fails to load', async () => {
    authService.getCurrentUser.mockRejectedValueOnce(new Error('plano indisponivel'));

    renderPage();

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('plano indisponivel');
    });
    expect(screen.getByText(/Não foi possível montar a tela do seu plano/i)).toBeInTheDocument();
  });

  test('uses the generic load error fallback when the request fails without a message', async () => {
    authService.getCurrentUser.mockRejectedValueOnce({});

    renderPage();

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        expect.stringMatching(/Falha ao carregar dados do usuario e plano/i)
      );
    });
    expect(screen.getByText(/Não foi possível montar a tela do seu plano/i)).toBeInTheDocument();
  });

  test('falls back to a gratuito baseline when the account has no nested plan payload', async () => {
    authService.getCurrentUser.mockResolvedValueOnce({ id: 8, plano: null });
    dashboardService.getMyDashboard.mockResolvedValueOnce(null);

    renderPage();

    expect(await screen.findByRole('heading', { name: 'Gratuito' })).toBeInTheDocument();
    expect(screen.getByText(/sem busca web incluída/i)).toBeInTheDocument();
  });

  test('renders the plan from dashboard limits when the current user payload has no nested plan object', async () => {
    authService.getCurrentUser.mockResolvedValueOnce({
      id: 8,
      plano: null,
      product_experience_mode: 'basic',
      limite_produtos: 50,
      limite_enriquecimento_web: 10,
      limite_geracao_ia: 0,
    });
    dashboardService.getMyDashboard.mockResolvedValueOnce({
      plano_nome: 'Gratuito',
      product_experience_mode: 'basic',
      limites: {
        produtos: 50,
        enriquecimento_web: 10,
        geracao_ia: 0,
      },
      uso_mes_atual: {
        enriquecimento_web: 3,
        geracao_ia: 0,
      },
      totais: {
        produtos: 12,
        fornecedores: 2,
      },
    });

    renderPage();

    expect(await screen.findByRole('heading', { name: 'Gratuito' })).toBeInTheDocument();
    expect(screen.getByText(/Fluxo enxuto com geração básica como padrão/i)).toBeInTheDocument();
    expect(screen.getAllByText(/38 espaços livres/i).length).toBeGreaterThan(0);
  });

  test('renders fallback plan labels when the current plan has no friendly name', async () => {
    authService.getCurrentUser.mockResolvedValueOnce({
      id: 8,
      product_experience_mode: 'basic',
      plano: {
        nome: '',
        limite_produtos: 10,
        limite_enriquecimento_web: 20,
        limite_geracao_ia: 30,
      },
    });

    renderPage();

    expect(await screen.findByRole('heading', { name: 'N/D' })).toBeInTheDocument();
    expect(screen.queryByText(/Fila de suporte com atendimento prioritário/i)).not.toBeInTheDocument();
  });
});
