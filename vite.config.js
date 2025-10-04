import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    // Bind to all interfaces for LAN access. Use VITE_HOST env var to tell the HMR client
    // which host/IP to connect to (set this to your Mac's LAN IP before starting dev).
    host: true,
    port: 5173,
    allowedHosts: ["a6578988c619.ngrok-free.app"],
    hmr: {
      host: process.env.VITE_HOST || undefined,
      port: 5173,
    },
    proxy: {
      '/upload': {
        target: 'http://localhost:5054',
        changeOrigin: true,
      },
      '/all_images': {
        target: 'http://localhost:5054',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://localhost:5054',
        changeOrigin: true,
      },
      '/rgba': {
        target: 'http://localhost:5054',
        changeOrigin: true,
      }
    }
  }
})
