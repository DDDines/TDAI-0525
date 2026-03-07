import getBackendBaseUrl from '../backend';

describe('getBackendBaseUrl', () => {
  const originalValue = globalThis.process?.env?.VITE_API_BASE_URL;
  const originalProcess = globalThis.process;

  afterEach(() => {
    if (!globalThis.process) {
      globalThis.process = originalProcess;
    }

    if (originalValue === undefined) {
      delete globalThis.process.env.VITE_API_BASE_URL;
    } else {
      globalThis.process.env.VITE_API_BASE_URL = originalValue;
    }
    globalThis.process = originalProcess;
  });

  test('strips the api path suffix from an explicit environment variable', () => {
    globalThis.process.env.VITE_API_BASE_URL = 'https://api.example.com/api/v1';

    expect(getBackendBaseUrl()).toBe('https://api.example.com');
  });

  test('falls back to a relative base url when no environment variable is defined', () => {
    delete globalThis.process.env.VITE_API_BASE_URL;

    expect(getBackendBaseUrl()).toBe('');
  });

  test('falls back cleanly when process env is unavailable', () => {
    globalThis.process = undefined;

    expect(getBackendBaseUrl()).toBe('');
  });
});
