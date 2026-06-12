const rawApiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || '';
const devFallbackApiBaseUrl = 'http://127.0.0.1:8010';

export const API_BASE_URL =
  rawApiBaseUrl && rawApiBaseUrl !== '/api'
    ? rawApiBaseUrl
    : import.meta.env.DEV
      ? devFallbackApiBaseUrl
      : rawApiBaseUrl;

export const API_TIMEOUT_MS = 15000;

export function getApiBaseUrlLabel() {
  return API_BASE_URL || 'No configurada. Configure VITE_API_BASE_URL en Vercel.';
}

export function endpointUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}
