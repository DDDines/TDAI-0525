/**
 * Module logger.
 *
 * Implements frontend behavior for utils.
 */

// Determine dev mode. Support environments without import.meta (e.g. Jest)
let isDev = false;
try {
  isDev = new Function(
    'return typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV',
  )();
} catch {
  isDev = false;
}
if (!isDev) {
  const nodeEnv =
    typeof globalThis !== 'undefined' &&
    globalThis.process &&
    globalThis.process.env
      ? globalThis.process.env
      : undefined;
  isDev =
    !!nodeEnv &&
    nodeEnv.NODE_ENV !== 'production';
}

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
