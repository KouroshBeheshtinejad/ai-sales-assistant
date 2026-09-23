import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// FastAPI serves frontend/dist in production (see app/main.py), so the dev server
// mirrors that: API calls are proxied, page navigations stay inside the SPA.
const backend = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'
const apiPrefixes = ['/api']

const proxy = Object.fromEntries(
  apiPrefixes.map((prefix) => [
    prefix,
    {
      target: backend,
      changeOrigin: true,
      // /seller/* is both an SPA route and an API prefix: browser navigations
      // (Accept: text/html) get index.html, fetch() calls reach the backend.
      bypass: (req) => (req.headers.accept?.includes('text/html') ? '/index.html' : undefined),
    },
  ]),
)

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  test: {
    environment: 'jsdom',
  },
})
