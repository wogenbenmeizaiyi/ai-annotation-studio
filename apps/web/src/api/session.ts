import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { AUTH_SERVICE_BASE_URL } from '@/config/env'

type RetryRequestConfig = InternalAxiosRequestConfig & { _sessionRetry?: boolean }

export const readCookie = (name: string): string => {
  const prefix = `${encodeURIComponent(name)}=`
  const item = document.cookie.split('; ').find((value) => value.startsWith(prefix))
  return item ? decodeURIComponent(item.slice(prefix.length)) : ''
}

export const authTransport = axios.create({
  baseURL: AUTH_SERVICE_BASE_URL,
  withCredentials: true,
})

authTransport.interceptors.request.use((request) => {
  const method = request.method?.toUpperCase() || 'GET'
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = readCookie('studio_csrf')
    if (csrf) request.headers.set('X-CSRF-Token', csrf)
  }
  return request
})

let refreshPromise: Promise<void> | null = null

export const refreshSession = async (): Promise<void> => {
  if (!refreshPromise) {
    refreshPromise = authTransport
      .post('/refresh')
      .then(() => undefined)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

authTransport.interceptors.response.use(undefined, async (error: AxiosError) => {
  const request = error.config as RetryRequestConfig | undefined
  const path = request?.url || ''
  const cannotRefresh = ['/login', '/register', '/refresh'].some((item) => path.endsWith(item))
  if (error.response?.status !== 401 || !request || request._sessionRetry || cannotRefresh) {
    return Promise.reject(error)
  }
  request._sessionRetry = true
  try {
    await refreshSession()
    return authTransport.request(request)
  } catch {
    window.dispatchEvent(new CustomEvent('studio:session-expired'))
    return Promise.reject(error)
  }
})

export const configureSessionClient = (client: AxiosInstance): void => {
  client.defaults.withCredentials = true
  client.interceptors.request.use((request) => {
    const method = request.method?.toUpperCase() || 'GET'
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const csrf = readCookie('studio_csrf')
      if (csrf) request.headers.set('X-CSRF-Token', csrf)
    }
    return request
  })
  client.interceptors.response.use(undefined, async (error: AxiosError) => {
    const request = error.config as RetryRequestConfig | undefined
    if (error.response?.status !== 401 || !request || request._sessionRetry) {
      return Promise.reject(error)
    }
    request._sessionRetry = true
    try {
      await refreshSession()
      return client.request(request)
    } catch {
      window.dispatchEvent(new CustomEvent('studio:session-expired'))
      return Promise.reject(error)
    }
  })
}
