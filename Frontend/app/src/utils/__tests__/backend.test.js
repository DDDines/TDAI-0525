import getBackendBaseUrl from '../backend';

describe('getBackendBaseUrl', () => {
  const originalValue = globalThis.process?.env?.VITE_API_BASE_URL;

  afterEach(() => {
    if (originalValue === undefined) {
      delete globalThis.process.env.VITE_API_BASE_URL;
    } else {
      globalThis.process.env.VITE_API_BASE_URL = originalValue;
    }
  });

  test('strips the api path suffix from an explicit environment variable', () => {
    globalThis.process.env.VITE_API_BASE_URL = 'https://api.example.com/api/v1';

    expect(getBackendBaseUrl()).toBe('https://api.example.com');
  });

  test('falls back to a relative base url when no environment variable is defined', () => {
    delete globalThis.process.env.VITE_API_BASE_URL;

    expect(getBackendBaseUrl()).toBe('');
  });
});
