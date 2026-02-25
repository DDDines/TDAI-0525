import authService from '../authService';
import apiClient from '../apiClient';

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
  },
}));

jest.mock('../../utils/notifications', () => ({
  showSuccessToast: jest.fn(),
  showErrorToast: jest.fn(),
}));

describe('authService.login', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  test('returns token payload on success', async () => {
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
  });

  test('maps network errors to temporary auth message', async () => {
    apiClient.post.mockRejectedValue({ code: 'ERR_NETWORK', message: 'Network Error' });

    await expect(authService.login('admin@example.com', 'secret')).rejects.toThrow(
      'Não foi possível autenticar agora. Tente novamente em alguns instantes.'
    );
  });

  test('keeps backend detail for invalid credentials', async () => {
    apiClient.post.mockRejectedValue({
      response: { status: 401, data: { detail: 'Credenciais invalidas.' } },
    });

    await expect(authService.login('admin@example.com', 'wrong')).rejects.toThrow(
      'Credenciais invalidas.'
    );
  });

  test('uses default invalid credential message for 401 without detail', async () => {
    apiClient.post.mockRejectedValue({
      response: { status: 401, data: {} },
    });

    await expect(authService.login('admin@example.com', 'wrong')).rejects.toThrow(
      'Email ou senha invalidos.'
    );
  });

  test('maps server errors to temporary auth message', async () => {
    apiClient.post.mockRejectedValue({
      response: { status: 503, data: { detail: 'Service Unavailable' } },
    });

    await expect(authService.login('admin@example.com', 'secret')).rejects.toThrow(
      'Não foi possível autenticar agora. Tente novamente em alguns instantes.'
    );
  });
});
