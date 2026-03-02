/**
 * Module backend.
 *
 * Defines responsibilities and integration points for utils.
 */


function getBackendBaseUrl() {
    let metaEnv;
    try {
      metaEnv = new Function(
        'return typeof import.meta !== "undefined" ? import.meta.env : undefined'
      )();
    } catch {
      metaEnv = undefined;
    }
    const nodeEnv =
    typeof globalThis !== 'undefined' &&
    globalThis.process &&
    globalThis.process.env ?
    globalThis.process.env :
    undefined;
    const apiUrl =
    metaEnv && metaEnv.VITE_API_BASE_URL ||
    nodeEnv && nodeEnv.VITE_API_BASE_URL ||
    '/api/v1';
    return apiUrl.replace(/\/api\/v1\/?$/, '');
  }
export { getBackendBaseUrl };

export default getBackendBaseUrl;