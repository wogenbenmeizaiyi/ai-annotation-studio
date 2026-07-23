const stripTrailingSlash = (value: string): string => value.replace(/\/+$/, '')

const getEnvUrl = (key: keyof ImportMetaEnv, fallback: string): string => {
  return stripTrailingSlash(import.meta.env[key] || fallback)
}

export const API_BASE_URL = getEnvUrl('VITE_API_BASE_URL', '/api/annotation')

export const AI_SERVICE_BASE_URL = getEnvUrl('VITE_AI_SERVICE_BASE_URL', '/api/ai')

export const AUTH_SERVICE_BASE_URL = getEnvUrl('VITE_AUTH_SERVICE_BASE_URL', '/api/auth')

export const createWebSocketUrl = (path: string): string => {
  const apiUrl = new URL(API_BASE_URL, window.location.origin)
  apiUrl.protocol = apiUrl.protocol === 'https:' ? 'wss:' : 'ws:'
  apiUrl.pathname = path.startsWith('/') ? path : `/${path}`
  apiUrl.search = ''
  apiUrl.hash = ''

  return apiUrl.toString()
}
