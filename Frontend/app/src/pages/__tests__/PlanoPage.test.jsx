import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PlanoPage from '../PlanoPage.jsx';
import authService from '../../services/authService';
import { showErrorToast, showInfoToast } from '../../utils/notifications';

jest.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    getCurrentUser: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showErrorToast: jest.fn(),
  showInfoToast: jest.fn(),
}));

jest.mock('../../components/common/LoadingPopup.jsx', () => ({
  __esModule: true,
  default: ({ isOpen, message }) => (isOpen ? <div>{message}</div> : null),
}));

describe('PlanoPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('loads the current plan and exposes the management actions', async () => {
    authService.getCurrentUser.mockResolvedValueOnce({
      id: 8,
      plano: {
        nome: 'Pro',
        limite_produtos: 1500,
        limite_enriquecimento_web: 999999,
        limite_geracao_ia: 400,
      },
    });

    render(<PlanoPage />);

    expect(await screen.findByText('Plano atual')).toBeInTheDocument();
    expect(screen.getByText(/Ilimitado/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Upgrade de Plano'));
    fireEvent.click(screen.getByText('Cancelar Assinatura'));
    fireEvent.click(screen.getByText(/Ver Historico de Cobranca|Ver Hist.rico de Cobran.a/i));

    expect(showInfoToast).toHaveBeenNthCalledWith(
      1,
      expect.stringMatching(/upgrade ainda n.o disponivel/i)
    );
    expect(showInfoToast).toHaveBeenNthCalledWith(
      2,
      expect.stringMatching(/cancelamento ainda n.o disponivel/i)
    );
    expect(showInfoToast).toHaveBeenNthCalledWith(
      3,
      expect.stringMatching(/historico de cobranca ainda n.o disponivel/i)
    );
  });

  test('shows an error state when user data fails to load', async () => {
    authService.getCurrentUser.mockRejectedValueOnce(new Error('plano indisponivel'));

    render(<PlanoPage />);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('plano indisponivel');
    });
    expect(screen.getByText(/Erro ao carregar dados/)).toBeInTheDocument();
  });

  test('uses the generic load error fallback when the request fails without a message', async () => {
    authService.getCurrentUser.mockRejectedValueOnce({});

    render(<PlanoPage />);

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith(
        expect.stringMatching(/Falha ao carregar dados do usu.rio e plano/i)
      );
    });
    expect(screen.getByText(/Erro ao carregar dados/)).toBeInTheDocument();
  });

  test('shows a no-plan fallback when the user has no active subscription', async () => {
    authService.getCurrentUser.mockResolvedValueOnce({ id: 8, plano: null });

    render(<PlanoPage />);

    expect(
      await screen.findByText(
        /Nao foi possivel carregar as informacoes do seu plano|N.o foi poss.vel carregar as informa..es do seu plano/i
      )
    ).toBeInTheDocument();
  });

  test('renders fallback plan labels when the current plan has no friendly name', async () => {
    authService.getCurrentUser.mockResolvedValueOnce({
      id: 8,
      plano: {
        nome: '',
        limite_produtos: 10,
        limite_enriquecimento_web: 20,
        limite_geracao_ia: 30,
      },
    });

    render(<PlanoPage />);

    expect(await screen.findByText('Plano atual')).toBeInTheDocument();
    expect(screen.getByText('N/D')).toBeInTheDocument();
    expect(screen.queryByText(/Suporte priorit/i)).not.toBeInTheDocument();
  });
});
