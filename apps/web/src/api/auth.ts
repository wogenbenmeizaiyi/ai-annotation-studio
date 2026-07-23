import type { AxiosError } from 'axios'
import { authTransport } from '@/api/session'

export type UserRole = 'super_admin' | 'user'
export type UserStatus = 'pending' | 'active' | 'disabled'

export interface StudioUser {
  id: string
  username: string
  display_name: string
  role: UserRole
  status: UserStatus
  must_change_password: boolean
  created_at: string
  approved_at: string | null
}

export interface UserPage {
  items: StudioUser[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

interface AuthEnvelope<T> {
  code: number
  message: string
  data: T
}

const unwrap = <T>(response: { data: AuthEnvelope<T> }): T => response.data.data

export const getAuthErrorMessage = (error: unknown, fallback: string): string => {
  const axiosError = error as AxiosError<AuthEnvelope<unknown>>
  return axiosError.response?.data?.message || axiosError.message || fallback
}

export const login = async (username: string, password: string): Promise<StudioUser> =>
  unwrap(await authTransport.post('/login', { username, password }))

export const register = async (
  username: string,
  displayName: string,
  password: string,
): Promise<StudioUser> =>
  unwrap(
    await authTransport.post('/register', {
      username,
      display_name: displayName,
      password,
    }),
  )

export const getCurrentUser = async (): Promise<StudioUser> =>
  unwrap(await authTransport.get('/me'))

export const logout = async (): Promise<void> => {
  await authTransport.post('/logout')
}

export const changePassword = async (
  currentPassword: string,
  newPassword: string,
): Promise<void> => {
  await authTransport.patch('/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export const getUsers = async (page = 1, status?: UserStatus): Promise<UserPage> =>
  unwrap(
    await authTransport.get('/admin/users', {
      params: { page, pageSize: 20, status },
    }),
  )

export const approveUser = async (id: string): Promise<StudioUser> =>
  unwrap(await authTransport.post(`/admin/users/${id}/approve`))

export const disableUser = async (id: string): Promise<StudioUser> =>
  unwrap(await authTransport.post(`/admin/users/${id}/disable`))

export const enableUser = async (id: string): Promise<StudioUser> =>
  unwrap(await authTransport.post(`/admin/users/${id}/enable`))

export const updateUserRole = async (id: string, role: UserRole): Promise<StudioUser> =>
  unwrap(await authTransport.put(`/admin/users/${id}/role`, { role }))

export const resetUserPassword = async (id: string, newPassword: string): Promise<void> => {
  await authTransport.post(`/admin/users/${id}/reset-password`, { new_password: newPassword })
}
