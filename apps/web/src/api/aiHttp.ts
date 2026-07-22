import axios from 'axios'
import { AI_SERVICE_BASE_URL } from '@/config/env'

interface AiApiResponse<T> {
  code: number
  message: string
  data: T
}

const aiHttp = axios.create({
  baseURL: AI_SERVICE_BASE_URL,
})

aiHttp.interceptors.response.use(
  (response) => {
    const res = response.data as AiApiResponse<unknown>

    if (res.code !== 0 && res.code !== 200) {
      return Promise.reject(res.message)
    }

    return res.data as any
  },
  (error) => Promise.reject(error),
)

export default aiHttp as {
  get<T>(url: string, config?: any): Promise<T>
  post<T>(url: string, data?: any, config?: any): Promise<T>
  delete<T>(url: string, config?: any): Promise<T>
  put<T>(url: string, data?: any, config?: any): Promise<T>
}
