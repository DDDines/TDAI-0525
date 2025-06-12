export function getBackendBaseUrl() {
  const apiUrl = process.env.VITE_API_BASE_URL || '/api/v1';
  return apiUrl.replace(/\/api\/v1\/?$/, '');
}

export default getBackendBaseUrl;
