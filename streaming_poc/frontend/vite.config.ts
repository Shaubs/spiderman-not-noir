import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API requests to FastAPI backend
      '/video': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        // Handle proxy errors gracefully
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.log('WebSocket proxy error:', err.message);
          });
        },
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
