import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://your-dify-server:port',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, '/v1'),
      },
    },
  },
})
