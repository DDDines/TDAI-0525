export function getBackendBaseUrl() {
  const metaEnv = typeof import.meta !== 'undefined' ? import.meta.env : undefined;
  const apiUrl =
    (metaEnv && metaEnv.VITE_API_BASE_URL) ||
    (typeof process !== 'undefined' && process.env && process.env.VITE_API_BASE_URL) ||
    '/api/v1';
  return apiUrl.replace(/\/api\/v1\/?$/, '');
}

export default getBackendBaseUrl;
