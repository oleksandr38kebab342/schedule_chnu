import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Дев-сервер проксує /api на FastAPI, щоб у розробці не вмикати CORS і
// не прописувати абсолютні адреси в коді.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
})
