import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ResetSenhaPage from '../ResetSenhaPage.jsx';
import authService from '../../services/authService';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';

jest.mock('../../services/authService', () => ({
  __esModule: true,
  default: {
    resetPassword: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
}));

function renderPage(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/resetar-senha" element={<ResetSenhaPage />} />
      </Routes>
    </MemoryRouter>
  );
}

function fillPasswords(password, confirmPassword = password) {
  fireEvent.change(screen.getByLabelText(/^Nova senha \(/i), {
    target: { value: password },
  });
  fireEvent.change(screen.getByLabelText(/^Confirmar nova senha$/i), {
    target: { value: confirmPassword },
  });
}

describe('ResetSenhaPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('blocks submission when passwords do not match', () => {
    renderPage('/resetar-senha?token=abc123');

    fillPasswords('12345678', '87654321');
    fireEvent.click(screen.getByRole('button', { name: /Alterar Senha/i }));

    expect(showErrorToast).toHaveBeenCalledWith('A senha e a confirmação não coincidem.');
    expect(authService.resetPassword).not.toHaveBeenCalled();
  });

  test('blocks submission when the reset token is missing', () => {
    renderPage('/resetar-senha');

    fillPasswords('12345678');
    fireEvent.click(screen.getByRole('button', { name: /Alterar Senha/i }));

    expect(showErrorToast).toHaveBeenCalledWith('Token inválido.');
  });

  test('submits the new password when the token is valid', async () => {
    authService.resetPassword.mockResolvedValueOnce({ ok: true });

    renderPage('/resetar-senha?token=abc123');

    fillPasswords('12345678');
    fireEvent.click(screen.getByRole('button', { name: /Alterar Senha/i }));

    await waitFor(() => {
      expect(authService.resetPassword).toHaveBeenCalledWith('abc123', '12345678');
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Senha alterada com sucesso. Faça login.');
  });

  test('shows submitting state and uses the default error fallback on unknown failures', async () => {
    let rejectRequest;
    authService.resetPassword.mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectRequest = reject;
        })
    );

    renderPage('/resetar-senha?token=abc123');

    fillPasswords('12345678');
    fireEvent.click(screen.getByRole('button', { name: /Alterar Senha/i }));

    expect(screen.getByRole('button', { name: /Salvando/i })).toBeDisabled();

    rejectRequest({});

    await waitFor(() => {
      expect(showErrorToast).toHaveBeenCalledWith('Falha ao redefinir senha.');
    });
    expect(screen.getByRole('button', { name: /Alterar Senha/i })).toBeEnabled();
  });
});
