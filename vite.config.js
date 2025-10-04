import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/upload': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      },
      '/rgba': {
        target: 'http://localhost:5050',
        changeOrigin: true,
      }
    }
  }
})
