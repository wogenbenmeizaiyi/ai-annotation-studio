/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_AI_SERVICE_BASE_URL?: string
  readonly VITE_AUTH_SERVICE_BASE_URL?: string
  readonly VITE_APP_BASE_PATH?: string
  readonly VITE_ANNOTATION_PROXY_TARGET?: string
  readonly VITE_RECOGNITION_PROXY_TARGET?: string
  readonly VITE_AUTH_PROXY_TARGET?: string
  readonly VITE_SAM3_PROXY_TARGET?: string
}
