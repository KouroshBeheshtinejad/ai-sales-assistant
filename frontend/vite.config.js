import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: Object.fromEntries(['/api', '/public', '/cart', '/orders', '/auth', '/stores', '/products', '/seller', '/dashboard'].map((path) => [path, { target: process.env.VITE_BACKEND_URL || 'http://127.0.0.1:18080', changeOrigin: true }])) },
})
