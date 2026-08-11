import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  // 非 VITE_ 前缀，仅构建期读取，不注入 import.meta.env 产物
  const env = loadEnv(mode, process.cwd(), '')
  // 默认 /（含 Cloudflare Workers 部署）；Nginx 挂 /admin/ 时用 BUILD_BASE=/admin/
  const base = mode === 'production' ? (env.BUILD_BASE ?? '/') : '/'

  return {
    plugins: [vue()],
    base,
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
