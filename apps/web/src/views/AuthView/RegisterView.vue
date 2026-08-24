<template>
  <main class="auth-page">
    <section class="auth-card">
      <div class="auth-brand"><img src="/favicon-48.png" alt="" /> AI Studio</div>
      <div v-if="submitted" class="pending-panel">
        <v-icon icon="mdi-clock-check-outline" size="36" color="primary" />
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
        <v-form ref="formRef" @submit.prevent="submit">
          <v-text-field
            v-model="username"
            label="用户名"
            autocomplete="username"
            hint="3–64 位，仅支持字母、数字、下划线和连字符"
            persistent-hint
            :rules="usernameRules"
            autofocus
          />
          <v-text-field
            v-model="displayName"
            label="显示名称"
            autocomplete="name"
            hint="用于界面展示，最多 100 个字符"
            persistent-hint
            :rules="displayNameRules"
          />
          <v-text-field
            v-model="password"
            label="密码"
            type="password"
            autocomplete="new-password"
            hint="请输入 12–128 位密码"
            persistent-hint
            :rules="passwordRules"
          />
          <v-text-field
            v-model="confirmPassword"
            label="确认密码"
            type="password"
            autocomplete="new-password"
            :rules="confirmPasswordRules"
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

const auth = useAuthStore()
const username = ref('')
const displayName = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const submitted = ref(false)
const error = ref('')

interface ValidatableForm {
  validate: () => Promise<{ valid: boolean }>
}

const formRef = ref<ValidatableForm | null>(null)

const usernameRules = [
  (value: string) => !!value.trim() || '请输入用户名',
  (value: string) => value.trim().length >= 3 || '用户名至少需要 3 位',
  (value: string) => value.trim().length <= 64 || '用户名不能超过 64 位',
  (value: string) =>
    /^[\p{L}\p{N}_-]+$/u.test(value.trim()) || '用户名只能包含字母、数字、下划线和连字符',
]

const displayNameRules = [
  (value: string) => !!value.trim() || '请输入显示名称',
  (value: string) => value.trim().length <= 100 || '显示名称不能超过 100 个字符',
]

const passwordRules = [
  (value: string) => !!value || '请输入密码',
  (value: string) => value.length >= 12 || '密码至少需要 12 位',
  (value: string) => value.length <= 128 || '密码不能超过 128 位',
]

const confirmPasswordRules = [
  (value: string) => !!value || '请再次输入密码',
  (value: string) => value === password.value || '两次输入的密码不一致',
]

const submit = async () => {
  const validation = await formRef.value?.validate()
  if (!validation?.valid) {
    error.value = '请检查下方标红的注册信息'
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
