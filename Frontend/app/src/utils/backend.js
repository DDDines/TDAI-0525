export function getBackendBaseUrl() {
  let metaEnv;
  try {
    // eslint-disable-next-line no-new-func
    metaEnv = new Function(
      'return typeof import.meta !== "undefined" ? import.meta.env : undefined',
    )();
  } catch {
    metaEnv = undefined;
  }
  const apiUrl =
    (metaEnv && metaEnv.VITE_API_BASE_URL) ||
    (typeof process !== 'undefined' && process.env && process.env.VITE_API_BASE_URL) ||
    '/api/v1';
  return apiUrl.replace(/\/api\/v1\/?$/, '');
}

export default getBackendBaseUrl;
