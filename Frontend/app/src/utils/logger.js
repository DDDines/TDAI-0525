// Determine dev mode. Support environments without import.meta (e.g. Jest)
let isDev = false;
try {
  // eslint-disable-next-line no-new-func
  isDev = new Function(
    'return typeof import.meta !== "undefined" && import.meta.env && import.meta.env.DEV',
  )();
} catch {
  isDev = false;
}
if (!isDev) {
  isDev =
    typeof process !== 'undefined' &&
    process.env &&
    process.env.NODE_ENV !== 'production';
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
