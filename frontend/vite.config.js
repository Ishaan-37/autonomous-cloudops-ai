import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/runs':       { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health':     { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/trigger':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/approve':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/reject':     { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/metrics':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/monitoring': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/logs':       { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/kubernetes': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/costs':      { target: 'http://127.0.0.1:8000', changeOrigin: true },
    }
  }
})
