describe('logger', () => {
  const originalProcess = globalThis.process;

  afterEach(() => {
    jest.resetModules();
    globalThis.process = originalProcess;
    jest.restoreAllMocks();
  });

  test('writes to console outside production', () => {
    globalThis.process = { env: { NODE_ENV: 'test' } };
    const logSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    const logger = require('../logger').default;
    logger.log('alpha');
    logger.warn('beta');
    logger.error('gamma');

    expect(logSpy).toHaveBeenCalledWith('alpha');
    expect(warnSpy).toHaveBeenCalledWith('beta');
    expect(errorSpy).toHaveBeenCalledWith('gamma');
  });

  test('stays silent in production', () => {
    globalThis.process = { env: { NODE_ENV: 'production' } };
    const logSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    const logger = require('../logger').default;
    logger.log('alpha');
    logger.warn('beta');
    logger.error('gamma');

    expect(logSpy).not.toHaveBeenCalled();
    expect(warnSpy).not.toHaveBeenCalled();
    expect(errorSpy).not.toHaveBeenCalled();
  });

  test('stays silent when process env is unavailable', () => {
    globalThis.process = undefined;
    const logSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    const logger = require('../logger').default;
    logger.log('alpha');
    logger.warn('beta');
    logger.error('gamma');

    expect(logSpy).not.toHaveBeenCalled();
    expect(warnSpy).not.toHaveBeenCalled();
    expect(errorSpy).not.toHaveBeenCalled();
  });

  test('resolveIsDev honors the import.meta flag before the node environment', () => {
    const { resolveIsDev } = require('../logger');

    expect(resolveIsDev(true, { NODE_ENV: 'production' })).toBe(true);
    expect(resolveIsDev(false, { NODE_ENV: 'production' })).toBe(false);
    expect(resolveIsDev(false, { NODE_ENV: 'test' })).toBe(true);
  });
});
