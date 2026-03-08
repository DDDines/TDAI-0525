/**
 * Module logger.
 *
 * Defines responsibilities and integration points for utils.
 */

// Determine dev mode. Support environments without import.meta (e.g. Jest)
function readMetaDevFlag() {
  try {
    return Boolean(
      new Function(
        'return typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV',
      )()
    );
  } catch {
    return false;
  }
}

function readNodeEnv() {
  return typeof globalThis !== 'undefined' &&
    globalThis.process &&
    globalThis.process.env
    ? globalThis.process.env
    : undefined;
}

export function resolveIsDev(metaDev = readMetaDevFlag(), nodeEnv = readNodeEnv()) {
  if (metaDev) {
    return true;
  }
  return Boolean(nodeEnv && nodeEnv.NODE_ENV !== 'production');
}

const isDev = resolveIsDev();

const logger = {
  log: (...args) => {
    if (isDev) {
      console.log(...args);
    }
  },
  warn: (...args) => {
    if (isDev) {
      console.warn(...args);
    }
  },
  error: (...args) => {
    if (isDev) {
      console.error(...args);
    }
  }
};

export default logger;
