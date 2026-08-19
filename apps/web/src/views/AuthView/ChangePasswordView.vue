<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="auth-brand">
        <span class="auth-brand-mark">
          <svg viewBox="0 0 24 24" width="32" height="32" aria-hidden="true">
            <rect x="1" y="1" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.5" />
            <rect x="12" y="12" width="7" height="7" fill="var(--accent, #cf4a36)" />
          </svg>
        </span>
        <span class="auth-brand-text">AI Studio<small>标注与检测平台</small></span>
      </div>
      <div>
        <h1>修改密码</h1>
        <p>管理员重置了你的密码。设置新密码后请重新登录。</p>
      </div>
      <v-alert v-if="error" type="error" variant="tonal" density="compact">{{ error }}</v-alert>
      <v-form @submit.prevent="submit">
        <v-text-field v-model="currentPassword" label="当前密码" type="password" />
        <v-text-field v-model="newPassword" label="新密码（至少 12 位）" type="password" />
        <v-text-field v-model="confirmation" label="确认新密码" type="password" />
        <v-btn type="submit" color="primary" block :loading="loading">保存并重新登录</v-btn>
      </v-form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { getAuthErrorMessage } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const currentPassword = ref('')
const newPassword = ref('')
const confirmation = ref('')
const loading = ref(false)
const error = ref('')

const submit = async () => {
  if (newPassword.value !== confirmation.value) {
    error.value = '两次输入的新密码不一致'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await auth.changePassword(currentPassword.value, newPassword.value)
    await router.replace({ name: 'login' })
  } catch (reason) {
    error.value = getAuthErrorMessage(reason, '密码修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="./auth-page.css"></style>
