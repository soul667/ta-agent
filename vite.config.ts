import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 10102,
    strictPort: true, // 如果端口被占用,自动尝试下一个可用端口
  },
  optimizeDeps: {
    include: ['xlsx'],
  },
})
