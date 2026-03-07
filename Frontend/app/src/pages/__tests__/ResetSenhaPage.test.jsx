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

describe('ResetSenhaPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('blocks submission when passwords do not match', () => {
    renderPage('/resetar-senha?token=abc123');

    fireEvent.change(screen.getByLabelText('Nova senha (mín. 8 caracteres)'), {
      target: { value: '12345678' },
    });
    fireEvent.change(screen.getByLabelText('Confirmar nova senha'), {
      target: { value: '87654321' },
    });
    fireEvent.click(screen.getByText('Alterar Senha'));

    expect(showErrorToast).toHaveBeenCalledWith('A senha e a confirmação não coincidem.');
    expect(authService.resetPassword).not.toHaveBeenCalled();
  });

  test('blocks submission when the reset token is missing', () => {
    renderPage('/resetar-senha');

    fireEvent.change(screen.getByLabelText('Nova senha (mín. 8 caracteres)'), {
      target: { value: '12345678' },
    });
    fireEvent.change(screen.getByLabelText('Confirmar nova senha'), {
      target: { value: '12345678' },
    });
    fireEvent.click(screen.getByText('Alterar Senha'));

    expect(showErrorToast).toHaveBeenCalledWith('Token inválido.');
  });

  test('submits the new password when the token is valid', async () => {
    authService.resetPassword.mockResolvedValueOnce({ ok: true });

    renderPage('/resetar-senha?token=abc123');

    fireEvent.change(screen.getByLabelText('Nova senha (mín. 8 caracteres)'), {
      target: { value: '12345678' },
    });
    fireEvent.change(screen.getByLabelText('Confirmar nova senha'), {
      target: { value: '12345678' },
    });
    fireEvent.click(screen.getByText('Alterar Senha'));

    await waitFor(() => {
      expect(authService.resetPassword).toHaveBeenCalledWith('abc123', '12345678');
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Senha alterada com sucesso. Faça login.');
  });
});
