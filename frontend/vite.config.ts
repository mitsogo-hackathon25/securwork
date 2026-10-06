import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Dedicated port — avoids conflict with other Vite projects (default 5173)
    host: '127.0.0.1',
    port: 5180,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // Django admin at /django-admin/ — /admin/* is the React product panel.
      '/django-admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/sitemap.xml': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
