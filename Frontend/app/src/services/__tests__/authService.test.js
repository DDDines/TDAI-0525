import authService from '../authService';
import apiClient from '../apiClient';
import logger from '../../utils/logger';
import { showErrorToast, showSuccessToast } from '../../utils/notifications';

jest.mock('../apiClient', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
    get: jest.fn(),
    put: jest.fn(),
  },
}));

jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    log: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
}));

describe('authService', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('login returns token payload on success', async () => {
    apiClient.post.mockResolvedValue({ data: { access_token: 'abc' } });

    const result = await authService.login('admin@example.com', 'secret');

    expect(result).toEqual({ access_token: 'abc' });
    expect(apiClient.post).toHaveBeenCalledTimes(1);
    const [url, formData, config] = apiClient.post.mock.calls[0];
    expect(url).toBe('/auth/token');
    expect(formData).toBeInstanceOf(URLSearchParams);
    expect(formData.get('username')).toBe('admin@example.com');
    expect(formData.get('password')).toBe('secret');
    expect(config.headers['Content-Type']).toBe('application/x-www-form-urlencoded');
    expect(logger.log).toHaveBeenCalled();
  });

  test('login surfaces normalized error messages for network, auth and generic failures', async () => {
    apiClient.post.mockRejectedValueOnce({ code: 'ERR_NETWORK', message: 'Network Error' });
    await expect(authService.login('admin@example.com', 'secret')).rejects.toThrow(
      /autenticar agora/i
    );

    apiClient.post.mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Credenciais invalidas.' } },
    });
    await expect(authService.login('admin@example.com', 'wrong')).rejects.toThrow(
      'Credenciais invalidas.'
    );

    apiClient.post.mockRejectedValueOnce({
      response: { status: 401, data: {} },
    });
    await expect(authService.login('admin@example.com', 'wrong')).rejects.toThrow(
      'Email ou senha invalidos.'
    );

    apiClient.post.mockRejectedValueOnce({
      response: { status: 503, data: { detail: 'Service Unavailable' } },
    });
    await expect(authService.login('admin@example.com', 'secret')).rejects.toThrow(
      /autenticar agora/i
    );

    apiClient.post.mockRejectedValueOnce({
      response: { status: 400, data: {} },
    });
    await expect(authService.login('admin@example.com', 'secret')).rejects.toThrow(
      'Falha no login.'
    );

    expect(logger.warn).toHaveBeenCalled();
  });

  test('login trims backend validation details on non-auth errors', async () => {
    apiClient.post.mockRejectedValueOnce({
      response: { status: 400, data: { detail: '  detalhe validado  ' } },
    });

    await expect(authService.login('admin@example.com', 'secret')).rejects.toThrow(
      'detalhe validado'
    );
  });

  test('getCurrentUser returns current user data', async () => {
    apiClient.get.mockResolvedValue({ data: { id: 7, email: 'admin@example.com' } });

    await expect(authService.getCurrentUser()).resolves.toEqual({
      id: 7,
      email: 'admin@example.com',
    });
    expect(apiClient.get).toHaveBeenCalledWith('/auth/users/me', { skipAuthRedirect: true });
  });

  test('getCurrentUser rethrows backend payload or generic error', async () => {
    apiClient.get.mockRejectedValueOnce({ response: { data: { detail: 'Sessao expirada' } } });
    await expect(authService.getCurrentUser()).rejects.toEqual({
      detail: 'Sessao expirada',
    });

    apiClient.get.mockRejectedValueOnce(new Error('offline'));
    await expect(authService.getCurrentUser()).rejects.toThrow(
      'Falha ao buscar usuario atual.'
    );
  });

  test('register returns payload and success toast', async () => {
    apiClient.post.mockResolvedValue({ data: { id: 15 } });

    await expect(authService.register({ email: 'novo@example.com' })).resolves.toEqual({ id: 15 });
    expect(apiClient.post).toHaveBeenCalledWith('/users/', { email: 'novo@example.com' });
    expect(showSuccessToast).toHaveBeenCalledWith('Registro bem-sucedido! Faca login para continuar.');
  });

  test('register surfaces backend or generic errors', async () => {
    apiClient.post.mockRejectedValueOnce({ response: { data: { detail: 'Email duplicado' } } });
    await expect(authService.register({ email: 'duplicado@example.com' })).rejects.toEqual({
      detail: 'Email duplicado',
    });
    expect(showErrorToast).toHaveBeenCalledWith('Email duplicado');

    apiClient.post.mockRejectedValueOnce(new Error('offline'));
    await expect(authService.register({ email: 'novo@example.com' })).rejects.toThrow(
      'Falha no registro.'
    );
    expect(showErrorToast).toHaveBeenCalledWith('Falha no registro.');
  });

  test('update user endpoints return payload and show success toasts', async () => {
    apiClient.put
      .mockResolvedValueOnce({ data: { id: 11, nome_completo: 'Admin' } })
      .mockResolvedValueOnce({ data: { id: 11, nome_completo: 'Admin Atualizado' } })
      .mockResolvedValueOnce({ data: { ok: true } });

    await expect(authService.updateUser(11, { nome_completo: 'Admin' })).resolves.toEqual({
      id: 11,
      nome_completo: 'Admin',
    });
    await expect(authService.updateCurrentUser({ nome_completo: 'Admin Atualizado' })).resolves.toEqual({
      id: 11,
      nome_completo: 'Admin Atualizado',
    });
    await expect(
      authService.changePassword(11, { current_password: 'a', new_password: 'b' })
    ).resolves.toEqual({ ok: true });

    expect(apiClient.put).toHaveBeenNthCalledWith(1, '/auth/users/11', { nome_completo: 'Admin' });
    expect(apiClient.put).toHaveBeenNthCalledWith(2, '/auth/users/me', {
      nome_completo: 'Admin Atualizado',
    });
    expect(apiClient.put).toHaveBeenNthCalledWith(3, '/auth/users/me/change-password', {
      current_password: 'a',
      new_password: 'b',
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Perfil atualizado com sucesso!');
    expect(showSuccessToast).toHaveBeenCalledWith('Senha alterada com sucesso!');
  });

  test('update user endpoints surface backend and generic errors', async () => {
    apiClient.put
      .mockRejectedValueOnce({ response: { data: { detail: 'Sem permissao' } } })
      .mockRejectedValueOnce(new Error('offline'))
      .mockRejectedValueOnce({ response: { data: { detail: 'Senha atual invalida' } } });

    await expect(authService.updateUser(11, { nome_completo: 'Admin' })).rejects.toEqual({
      detail: 'Sem permissao',
    });
    expect(showErrorToast).toHaveBeenCalledWith('Sem permissao');

    await expect(authService.updateCurrentUser({ nome_completo: 'Admin' })).rejects.toThrow(
      'Falha ao atualizar perfil.'
    );
    expect(showErrorToast).toHaveBeenCalledWith('Falha ao atualizar perfil.');

    await expect(
      authService.changePassword(11, { current_password: 'x', new_password: 'y' })
    ).rejects.toEqual({
      detail: 'Senha atual invalida',
    });
    expect(showErrorToast).toHaveBeenCalledWith('Senha atual invalida');
  });

  test('update user endpoints fall back to generic messages when there is no backend payload', async () => {
    apiClient.put
      .mockRejectedValueOnce(new Error('offline user'))
      .mockRejectedValueOnce(new Error('offline current user'))
      .mockRejectedValueOnce(new Error('offline password'));

    await expect(authService.updateUser(11, { nome_completo: 'Admin' })).rejects.toThrow(
      'Falha ao atualizar perfil.'
    );
    await expect(authService.updateCurrentUser({ nome_completo: 'Admin' })).rejects.toThrow(
      'Falha ao atualizar perfil.'
    );
    await expect(
      authService.changePassword(11, { current_password: 'x', new_password: 'y' })
    ).rejects.toThrow('Falha ao alterar senha.');
  });

  test('password recovery and reset encode inputs and surface success', async () => {
    apiClient.post
      .mockResolvedValueOnce({ data: { sent: true } })
      .mockResolvedValueOnce({ data: { reset: true } });

    await expect(authService.requestPasswordRecovery('admin+teste@example.com')).resolves.toEqual({
      sent: true,
    });
    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/auth/password-recovery/admin%2Bteste%40example.com'
    );
    expect(showSuccessToast).toHaveBeenCalledWith(
      'Se o email existir, um link de redefinicao sera enviado.'
    );

    await expect(authService.resetPassword('token-1', 'nova-senha')).resolves.toEqual({
      reset: true,
    });
    expect(apiClient.post).toHaveBeenNthCalledWith(2, '/auth/reset-password/', {
      token: 'token-1',
      new_password: 'nova-senha',
    });
    expect(showSuccessToast).toHaveBeenCalledWith('Senha redefinida com sucesso!');
  });

  test('password recovery and reset surface backend and generic errors', async () => {
    apiClient.post
      .mockRejectedValueOnce({ response: { data: { detail: 'Email invalido' } } })
      .mockRejectedValueOnce(new Error('offline'));

    await expect(authService.requestPasswordRecovery('falha@example.com')).rejects.toEqual({
      detail: 'Email invalido',
    });
    expect(showErrorToast).toHaveBeenCalledWith('Email invalido');

    await expect(authService.resetPassword('token-2', 'outra-senha')).rejects.toThrow(
      'Falha ao redefinir senha.'
    );
    expect(showErrorToast).toHaveBeenCalledWith('Falha ao redefinir senha.');
  });

  test('password recovery and reset cover the opposite error branches as well', async () => {
    apiClient.post
      .mockRejectedValueOnce(new Error('offline recovery'))
      .mockRejectedValueOnce({ response: { data: { detail: 'Token expirado' } } });

    await expect(authService.requestPasswordRecovery('falha@example.com')).rejects.toThrow(
      'Falha ao solicitar recuperacao de senha.'
    );
    expect(showErrorToast).toHaveBeenCalledWith('Falha ao solicitar recuperacao de senha.');

    await expect(authService.resetPassword('token-2', 'outra-senha')).rejects.toEqual({
      detail: 'Token expirado',
    });
    expect(showErrorToast).toHaveBeenCalledWith('Token expirado');
  });
});
