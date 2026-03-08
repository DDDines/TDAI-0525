import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';

const nodeEnv = globalThis.process?.env || {};

function resolveProxyTarget() {
  const explicitApiBaseUrl = String(nodeEnv.VITE_API_BASE_URL || '').trim();
  if (explicitApiBaseUrl) {
    try {
      return new URL(explicitApiBaseUrl).origin;
    } catch {
      // Ignore malformed overrides and fall back to host/port defaults.
    }
  }

  const backendHost = String(nodeEnv.BACKEND_HOST || '127.0.0.1').trim() || '127.0.0.1';
  const backendPort =
    String(
      nodeEnv.PLAYWRIGHT_BACKEND_PORT ||
        nodeEnv.BACKEND_PORT ||
        '8000'
    ).trim() || '8000';
  return `http://${backendHost}:${backendPort}`;
}

const proxyTarget = resolveProxyTarget();

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 2500,
    rollupOptions: {
      onwarn(warning, warn) {
        if (
          warning?.code === 'EVAL' &&
          typeof warning?.id === 'string' &&
          warning.id.includes('pdfjs-dist/legacy/build/pdf.js')
        ) {
          return;
        }
        warn(warning);
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api/v1': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
});
