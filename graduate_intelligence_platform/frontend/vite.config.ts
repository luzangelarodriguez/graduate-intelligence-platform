import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_BASE_URL || 'https://graduate-intelligence-platform-production.up.railway.app';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/auth': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/health': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/metrics': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/emerging-skills': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/curriculum-gaps': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/recommendations': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/company-intelligence': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/semantic-roles': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/career-paths': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/market-forecast': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/observatory-status': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
    preview: {
      port: 4173,
      host: '0.0.0.0',
    },
    build: {
      sourcemap: mode !== 'production',
      rollupOptions: {
        output: {
          manualChunks: {
            react: ['react', 'react-dom', 'react-router-dom'],
            charts: ['recharts'],
            http: ['axios'],
          },
        },
      },
    },
  };
});
