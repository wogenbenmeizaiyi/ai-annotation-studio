<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="auth-brand"><img src="/favicon-48.png" alt="" /> AI Studio</div>
      <div>
        <h1>登录平台</h1>
        <p>进入标注、训练与检测服务管理工作区。</p>
      </div>
      <v-alert v-if="error" type="error" variant="tonal" density="compact">{{ error }}</v-alert>
      <v-form @submit.prevent="submit">
        <v-text-field v-model="username" label="用户名" autocomplete="username" autofocus />
        <v-text-field
          v-model="password"
          label="密码"
          type="password"
          autocomplete="current-password"
        />
        <v-btn type="submit" color="primary" block :loading="loading">登录</v-btn>
      </v-form>
      <div class="auth-footnote">还没有账号？<RouterLink to="/register">申请注册</RouterLink></div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAuthErrorMessage } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const submit = async () => {
  error.value = ''
  loading.value = true
  try {
    const user = await auth.login(username.value.trim(), password.value)
    if (user.must_change_password) {
      await router.replace({ name: 'changePassword' })
      return
    }
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/task'
    await router.replace(redirect.startsWith('/') ? redirect : '/task')
  } catch (reason) {
    error.value = getAuthErrorMessage(reason, '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="./auth-page.css"></style>
