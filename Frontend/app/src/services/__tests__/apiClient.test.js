describe('apiClient interceptors', () => {
  let mockClient;
  let requestSuccess;
  let requestFailure;
  let responseSuccess;
  let responseFailure;

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

    jest.doMock('axios', () => ({
      __esModule: true,
      default: {
        create: jest.fn(() => mockClient),
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
});
