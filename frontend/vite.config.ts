import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // Tests never talk to the real backend
    env: { VITE_USE_MOCK: 'false' },
    // The default 5s is too tight for the heavy render tests (AboutPage lists ~100 checks,
    // the App scan flow walks three pages) when the machine/CI runner is busy: they pass in
    // ~1s alone but timed out under load. 20s is headroom, not a licence for slow tests.
    testTimeout: 20000,
  },
})
