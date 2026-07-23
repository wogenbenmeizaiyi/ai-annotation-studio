import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  changePassword as changePasswordRequest,
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  type StudioUser,
} from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<StudioUser | null>(null)
  const initialized = ref(false)
  const loading = ref(false)

  const isAuthenticated = computed(() => user.value?.status === 'active')
  const isSuperAdmin = computed(() => user.value?.role === 'super_admin')

  const loadCurrentUser = async (): Promise<void> => {
    if (loading.value) return
    loading.value = true
    try {
      user.value = await getCurrentUser()
    } catch {
      user.value = null
    } finally {
      initialized.value = true
      loading.value = false
    }
  }

  const login = async (username: string, password: string): Promise<StudioUser> => {
    user.value = await loginRequest(username, password)
    initialized.value = true
    return user.value
  }

  const register = (username: string, displayName: string, password: string) =>
    registerRequest(username, displayName, password)

  const logout = async (): Promise<void> => {
    try {
      await logoutRequest()
    } finally {
      user.value = null
      initialized.value = true
    }
  }

  const changePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
    await changePasswordRequest(currentPassword, newPassword)
    user.value = null
  }

  const clear = (): void => {
    user.value = null
    initialized.value = true
  }

  return {
    user,
    initialized,
    loading,
    isAuthenticated,
    isSuperAdmin,
    loadCurrentUser,
    login,
    register,
    logout,
    changePassword,
    clear,
  }
})
