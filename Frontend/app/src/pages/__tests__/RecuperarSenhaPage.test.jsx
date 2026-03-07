import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import RecuperarSenhaPage from '../RecuperarSenhaPage.jsx';
import authService from '../../services/authService';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';

jest.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    requestPasswordRecovery: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
}));

describe('RecuperarSenhaPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('requests password recovery and shows the success message', async () => {
    authService.requestPasswordRecovery.mockResolvedValueOnce({ ok: true });

    render(
      <MemoryRouter>
        <RecuperarSenhaPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText('Email cadastrado'), {
      target: { value: 'julio@example.com' },
    });
    fireEvent.click(screen.getByText('Enviar link'));

    await waitFor(() => {
      expect(authService.requestPasswordRecovery).toHaveBeenCalledWith('julio@example.com');
    });
    expect(showSuccessToast).toHaveBeenCalledWith(
      'Se o email existir, enviaremos instruções para redefinição.'
    );
  });

  test('shows the backend error when password recovery fails', async () => {
    authService.requestPasswordRecovery.mockRejectedValueOnce(new Error('email inválido'));

    render(
      <MemoryRouter>
        <RecuperarSenhaPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText('Email cadastrado'), {
      target: { value: 'bad@example.com' },
    });
    fireEvent.click(screen.getByText('Enviar link'));

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('email inválido');
    });
  });
});
