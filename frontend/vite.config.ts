import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  worker: {
    format: 'es',
  },
  optimizeDeps: {
    include: [
      '@monaco-editor/react',
      '@monaco-editor/loader',
      'monaco-editor',
      'monaco-editor/languages/definitions/yaml/yaml.js',
    ],
  },
  resolve: {
    dedupe: ['@monaco-editor/loader'],
  },
  server: {
    host: true,
    port: 3000,
    strictPort: true,
    // App is opened via nginx gateway on :8080; keeps generated asset URLs consistent.
    origin: process.env.VITE_DEV_SERVER_ORIGIN ?? 'http://localhost:8080',
    hmr: {
      host: 'localhost',
      clientPort: 8080,
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
      manualChunks: {
        'monaco': ['@monaco-editor/react', 'monaco-editor'],
          'vendor': ['react', 'react-dom', 'react-router-dom'],
          'query': ['@tanstack/react-query'],
        },
      },
    },
  },
})
