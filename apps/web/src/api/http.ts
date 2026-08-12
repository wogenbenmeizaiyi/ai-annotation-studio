import axios from 'axios'
import { API_BASE_URL } from '@/config/env'
import { configureSessionClient } from '@/api/session'

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

const http = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
})

configureSessionClient(http)

http.interceptors.response.use(
  (response) => {
    const res = response.data as ApiResponse<any>

    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code !== 0 && res.code !== 200) {
        return Promise.reject(res.message)
      }
      return res.data
    }

    return res
  },
  (error) => Promise.reject(error),
)

export default http as {
  get<T>(url: string, config?: any): Promise<T>
  post<T>(url: string, data?: any, config?: any): Promise<T>
  delete<T>(url: string, config?: any): Promise<T>
  put<T>(url: string, data?: any, config?: any): Promise<T>
}
