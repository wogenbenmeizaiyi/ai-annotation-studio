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
      <div v-if="submitted" class="pending-panel">
        <Icon name="clock-check" :size="36" class="pending-icon" />
        <h1>申请已提交</h1>
        <p>超级管理员批准后即可登录。当前不需要重复注册。</p>
        <v-btn to="/login" variant="tonal" color="primary">返回登录</v-btn>
      </div>
      <template v-else>
        <div>
          <h1>申请账号</h1>
          <p>注册后需要超级管理员审批，密码至少 12 位。</p>
        </div>
        <v-alert v-if="error" type="error" variant="tonal" density="compact">{{ error }}</v-alert>
        <v-form @submit.prevent="submit">
          <v-text-field v-model="username" label="用户名" autocomplete="username" autofocus />
          <v-text-field v-model="displayName" label="显示名称" autocomplete="name" />
          <v-text-field
            v-model="password"
            label="密码"
            type="password"
            autocomplete="new-password"
          />
          <v-text-field
            v-model="confirmPassword"
            label="确认密码"
            type="password"
            autocomplete="new-password"
          />
          <v-btn type="submit" color="primary" block :loading="loading">提交注册申请</v-btn>
        </v-form>
        <div class="auth-footnote">已有账号？<RouterLink to="/login">返回登录</RouterLink></div>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { getAuthErrorMessage } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import { Icon } from '@/components/icons'

const auth = useAuthStore()
const username = ref('')
const displayName = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const submitted = ref(false)
const error = ref('')

const submit = async () => {
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  error.value = ''
  loading.value = true
  try {
    await auth.register(username.value.trim(), displayName.value.trim(), password.value)
    submitted.value = true
  } catch (reason) {
    error.value = getAuthErrorMessage(reason, '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped src="./auth-page.css"></style>

<style scoped>
.pending-icon {
  color: var(--accent);
}
</style>
