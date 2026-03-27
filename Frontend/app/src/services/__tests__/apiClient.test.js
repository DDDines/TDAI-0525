describe('apiClient interceptors', () => {
  let mockClient;
  let requestSuccess;
  let requestFailure;
  let responseSuccess;
  let responseFailure;
  let axiosCreateMock;
  const originalProcess = globalThis.process;

  function loadApiClient() {
    jest.resetModules();
    mockClient = {
      defaults: {
        headers: {
          common: {
            Authorization: 'Bearer old-token',
          },
        },
      },
      interceptors: {
        request: {
          use: jest.fn((onSuccess, onFailure) => {
            requestSuccess = onSuccess;
            requestFailure = onFailure;
          }),
        },
        response: {
          use: jest.fn((onSuccess, onFailure) => {
            responseSuccess = onSuccess;
            responseFailure = onFailure;
          }),
        },
      },
    };

    axiosCreateMock = jest.fn(() => mockClient);

    jest.doMock('axios', () => ({
      __esModule: true,
      default: {
        create: axiosCreateMock,
      },
    }));

    jest.doMock('../../utils/logger', () => ({
      __esModule: true,
      default: {
        log: jest.fn(),
      },
    }));

    let loadedClient;
    jest.isolateModules(() => {
      loadedClient = jest.requireActual('../apiClient').default;
    });
    return loadedClient;
  }

  beforeEach(() => {
    localStorage.clear();
    window.history.pushState({}, '', '/produtos');
    jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
  });

  afterEach(() => {
    window.history.pushState({}, '', '/');
    globalThis.process = originalProcess;
    jest.restoreAllMocks();
  });

  test('request interceptor injects Authorization when an access token exists', () => {
    localStorage.setItem('accessToken', 'token-123');
    const apiClient = loadApiClient();
    const config = { url: '/produtos', headers: {} };

    const updatedConfig = requestSuccess(config);

    expect(apiClient).toBe(mockClient);
    expect(updatedConfig.headers.Authorization).toBe('Bearer token-123');
  });

  test('request interceptor removes Authorization when there is no token', () => {
    loadApiClient();
    const config = { url: '/produtos', headers: { Authorization: 'Bearer stale' } };

    const updatedConfig = requestSuccess(config);

    expect(updatedConfig.headers.Authorization).toBeUndefined();
  });

  test('request interceptor forwards request errors as rejections', async () => {
    loadApiClient();
    const error = new Error('request failed');

    await expect(requestFailure(error)).rejects.toThrow('request failed');
  });

  test('response interceptor returns successful responses untouched', () => {
    loadApiClient();
    const response = { status: 200, data: { ok: true } };

    expect(responseSuccess(response)).toBe(response);
  });

  test('response interceptor clears tokens and redirects on 401 outside the login page', async () => {
    localStorage.setItem('accessToken', 'token-123');
    localStorage.setItem('refreshToken', 'refresh-456');
    loadApiClient();
    const error = {
      config: { url: '/produtos' },
      response: {
        status: 401,
        data: { detail: 'expirou' },
      },
    };

    await expect(responseFailure(error)).rejects.toBe(error);

    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(mockClient.defaults.headers.common.Authorization).toBeUndefined();
    expect(console.warn).toHaveBeenCalled();
  });

  test('response interceptor avoids redirect loops on the login page', async () => {
    window.history.pushState({}, '', '/login');
    localStorage.setItem('accessToken', 'token-123');
    loadApiClient();
    const error = {
      config: { url: '/auth/token' },
      response: {
        status: 401,
        data: { detail: 'credenciais invalidas' },
      },
    };

    await expect(responseFailure(error)).rejects.toBe(error);

    expect(localStorage.getItem('accessToken')).toBe('token-123');
    expect(console.warn).toHaveBeenCalled();
  });

  test('response interceptor does not redirect when skipAuthRedirect is enabled', async () => {
    window.history.pushState({}, '', '/');
    localStorage.setItem('accessToken', 'token-123');
    loadApiClient();
    const error = {
      config: { url: '/auth/users/me', skipAuthRedirect: true },
      response: {
        status: 401,
        data: { detail: 'token expirado' },
      },
    };

    await expect(responseFailure(error)).rejects.toBe(error);

    expect(window.location.pathname).toBe('/');
    expect(localStorage.getItem('accessToken')).toBe('token-123');
    expect(console.warn).toHaveBeenCalled();
  });

  test('response interceptor leaves auth state untouched for non-401 errors', async () => {
    localStorage.setItem('accessToken', 'token-123');
    localStorage.setItem('refreshToken', 'refresh-456');
    loadApiClient();
    const error = {
      config: { url: '/produtos' },
      response: {
        status: 500,
        data: { detail: 'falha interna' },
      },
    };

    await expect(responseFailure(error)).rejects.toBe(error);

    expect(localStorage.getItem('accessToken')).toBe('token-123');
    expect(localStorage.getItem('refreshToken')).toBe('refresh-456');
    expect(mockClient.defaults.headers.common.Authorization).toBe('Bearer old-token');
  });

  test('uses the node environment base url when it is provided', () => {
    globalThis.process = { env: { VITE_API_BASE_URL: 'https://api.example.com/api/v1' } };

    loadApiClient();

    expect(axiosCreateMock).toHaveBeenCalledWith({
      baseURL: 'https://api.example.com/api/v1',
    });
  });

  test('falls back to the relative api path when process env is unavailable', () => {
    globalThis.process = undefined;

    loadApiClient();

    expect(axiosCreateMock).toHaveBeenCalledWith({
      baseURL: '/api/v1',
    });
  });

  test('resolveApiBaseUrl prioritizes import.meta, then node env, then the relative fallback', () => {
    jest.resetModules();
    const { resolveApiBaseUrl } = require('../apiClient');

    expect(
      resolveApiBaseUrl(
        { VITE_API_BASE_URL: 'https://meta.example/api/v1' },
        { VITE_API_BASE_URL: 'https://node.example/api/v1' }
      )
    ).toBe('https://meta.example/api/v1');
    expect(resolveApiBaseUrl(undefined, { VITE_API_BASE_URL: 'https://node.example/api/v1' })).toBe(
      'https://node.example/api/v1'
    );
    expect(resolveApiBaseUrl({}, {})).toBe('/api/v1');
    expect(resolveApiBaseUrl({ VITE_API_BASE_URL: '   ' }, { VITE_API_BASE_URL: '' })).toBe('/api/v1');
  });
});
