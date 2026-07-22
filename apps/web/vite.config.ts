import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import vueDevTools from 'vite-plugin-vue-devtools'
import vuetify from 'vite-plugin-vuetify'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const annotationProxyTarget =
    env.VITE_ANNOTATION_PROXY_TARGET || 'http://127.0.0.1:8811'
  const recognitionProxyTarget =
    env.VITE_RECOGNITION_PROXY_TARGET || 'http://127.0.0.1:7987'
  const sam3ProxyTarget = env.VITE_SAM3_PROXY_TARGET || 'ws://127.0.0.1:8811'

  return {
    base: command === 'serve' ? '/' : env.VITE_APP_BASE_PATH || '/web/',
    plugins: [vue(), vueJsx(), vueDevTools(), vuetify({ autoImport: true })],
    server: {
      host: true,
      port: 5173,
      proxy: {
        '/api/annotation': {
          target: annotationProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/annotation/, '/api'),
        },
        '/api/ai': {
          target: recognitionProxyTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/ai/, '/api'),
        },
        '/ws/sam3': {
          target: sam3ProxyTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
  }
})
