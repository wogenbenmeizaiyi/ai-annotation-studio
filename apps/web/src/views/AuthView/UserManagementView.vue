<template>
  <div class="management-page">
    <header class="management-header">
      <div>
        <h1>用户管理</h1>
        <p>审批注册申请、调整角色并管理账号状态。</p>
      </div>
      <v-select
        v-model="statusFilter"
        :items="statusOptions"
        item-title="title"
        item-value="value"
        label="账号状态"
        clearable
        hide-details
        class="status-filter"
        @update:model-value="loadUsers(1)"
      />
    </header>

    <v-alert v-if="error" type="error" variant="tonal" density="compact">{{ error }}</v-alert>
    <section class="users-panel">
      <v-data-table
        :headers="headers"
        :items="users"
        :loading="loading"
        item-value="id"
        no-data-text="暂无符合当前状态的用户"
        hide-default-footer
      >
        <template #item.identity="{ item }">
          <div class="identity-cell">
            <strong>{{ item.display_name }}</strong>
            <span>@{{ item.username }}</span>
          </div>
        </template>
        <template #item.role="{ item }">
          <div class="role-cell">
            <span
              v-if="item.is_platform_owner"
              class="role-pill is-owner"
              :title="`平台所有者 — 不可变更`"
            >
              平台所有者
            </span>
            <span
              v-else-if="item.role === 'super_admin'"
              class="role-pill is-admin"
            >
              超级管理员
            </span>
            <span v-else class="role-pill is-user">
              普通用户
            </span>
            <button
              v-if="!item.is_platform_owner && auth.isPlatformOwner"
              type="button"
              class="role-toggle"
              :class="item.role === 'super_admin' ? 'is-demote' : 'is-promote'"
              :disabled="busyId === item.id"
              :title="item.role === 'super_admin' ? '降级为普通用户' : '提升为超级管理员'"
              @click="toggleRole(item)"
            >
              <Icon
                :name="item.role === 'super_admin' ? 'arrow-down' : 'arrow-up'"
                :size="14"
              />
            </button>
          </div>
        </template>
        <template #item.status="{ item }">
          <span class="status-pill" :class="`is-${item.status}`">{{ statusText[item.status] }}</span>
        </template>
        <template #item.created_at="{ item }">{{ formatDate(item.created_at) }}</template>
        <template #item.actions="{ item }">
          <div class="row-actions">
            <span
              v-if="!canManageAccount(item)"
              class="protected-note"
              :title="item.is_platform_owner ? '所有者账号受保护' : '仅所有者可管理'"
            >
              {{ item.is_platform_owner ? '受保护' : '仅所有者' }}
            </span>
            <v-btn
              v-else-if="item.status === 'pending'"
              size="small"
              color="primary"
              variant="tonal"
              @click="runAction(item.id, 'approve')"
              >批准</v-btn
            >
            <v-btn
              v-else-if="item.status === 'disabled'"
              size="small"
              variant="tonal"
              @click="runAction(item.id, 'enable')"
              >启用</v-btn
            >
            <v-btn
              v-else
              size="small"
              color="error"
              variant="text"
              @click="runAction(item.id, 'disable')"
              >禁用</v-btn
            >
            <v-btn
              v-if="canManageAccount(item)"
              size="small"
              variant="text"
              :title="`重置 ${item.display_name} 的密码`"
              @click="openReset(item)"
            >
              重置
            </v-btn>
          </div>
        </template>
      </v-data-table>
      <div class="pagination-bar">
        <span>共 {{ total }} 个用户</span>
        <v-pagination
          v-model="page"
          :length="totalPages"
          density="compact"
          @update:model-value="loadUsers"
        />
      </div>
    </section>

    <v-dialog v-model="resetDialog" max-width="560">
      <v-card class="studio-dialog-card reset-password-card">
        <v-card-title class="reset-password-title">
          重置「{{ resetTarget?.display_name }}」的密码
        </v-card-title>
        <v-card-text class="studio-dialog-body reset-password-body">
          <p class="dialog-note">重置后该用户的现有会话立即失效，下次登录必须再次修改密码。</p>
          <v-text-field
            v-model="newPassword"
            label="临时密码（至少 12 位）"
            type="password"
            autocomplete="new-password"
            class="reset-password-field"
            autofocus
          />
        </v-card-text>
        <v-card-actions class="studio-dialog-actions reset-password-actions">
          <v-spacer />
          <v-btn variant="text" @click="resetDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="busyId === resetTarget?.id" @click="submitReset"
            >确认重置</v-btn
          >
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { Icon } from '@/components/icons'
import {
  approveUser,
  disableUser,
  enableUser,
  getAuthErrorMessage,
  getUsers,
  resetUserPassword,
  updateUserRole,
  type StudioUser,
  type UserRole,
  type UserStatus,
} from '@/api/auth'

const headers = [
  { title: '用户', key: 'identity' },
  { title: '角色', key: 'role', width: 200 },
  { title: '状态', key: 'status', width: 100 },
  { title: '注册时间', key: 'created_at', width: 150 },
  { title: '', key: 'actions', sortable: false, align: 'end' as const, width: 260 },
]
const statusOptions = [
  { title: '待审批', value: 'pending' },
  { title: '已启用', value: 'active' },
  { title: '已禁用', value: 'disabled' },
]
const roleOptions = [
  { title: '普通用户', value: 'user' },
  { title: '超级管理员', value: 'super_admin' },
]
const statusText: Record<UserStatus, string> = {
  pending: '待审批',
  active: '已启用',
  disabled: '已禁用',
}

const users = ref<StudioUser[]>([])
const auth = useAuthStore()
const statusFilter = ref<UserStatus | undefined>()
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
const loading = ref(false)
const busyId = ref('')
const error = ref('')
const resetDialog = ref(false)
const resetTarget = ref<StudioUser | null>(null)
const newPassword = ref('')

const formatDate = (value: string) => new Date(value).toLocaleString('zh-CN', { hour12: false })
const canManageAccount = (user: StudioUser): boolean =>
  !user.is_platform_owner && (auth.isPlatformOwner || user.role !== 'super_admin')

const loadUsers = async (targetPage = page.value) => {
  loading.value = true
  error.value = ''
  try {
    const result = await getUsers(targetPage, statusFilter.value)
    users.value = result.items
    page.value = result.page
    total.value = result.total
    totalPages.value = Math.max(result.total_pages, 1)
  } catch (reason) {
    error.value = getAuthErrorMessage(reason, '用户列表加载失败')
  } finally {
    loading.value = false
  }
}

const runAction = async (id: string, action: 'approve' | 'enable' | 'disable') => {
  busyId.value = id
  error.value = ''
  try {
    if (action === 'approve') await approveUser(id)
    else if (action === 'enable') await enableUser(id)
    else await disableUser(id)
    await loadUsers()
  } catch (reason) {
    error.value = getAuthErrorMessage(reason, '账号状态更新失败')
  } finally {
    busyId.value = ''
  }
}

const changeRole = async (user: StudioUser, role: UserRole) => {
  if (role === user.role || !auth.isPlatformOwner || user.is_platform_owner) return
  busyId.value = user.id
  // 乐观更新 — 直接改本地那行，避免 loadUsers() 触发整表 loading 闪一下
  const idx = users.value.findIndex((u) => u.id === user.id)
  const current = idx >= 0 ? users.value[idx] : undefined
  if (!current) {
    busyId.value = ''
    return
  }
  const previousRole: UserRole = current.role
  const applyRole = (next: UserRole) => {
    const at = users.value.findIndex((u) => u.id === user.id)
    if (at < 0) return
    const row = users.value[at]
    if (!row) return
    users.value[at] = { ...row, role: next }
  }
  applyRole(role)
  try {
    await updateUserRole(user.id, role)
  } catch (reason) {
    applyRole(previousRole)
    error.value = getAuthErrorMessage(reason, '角色更新失败')
  } finally {
    busyId.value = ''
  }
}

const toggleRole = (user: StudioUser) => {
  if (!auth.isPlatformOwner || user.is_platform_owner) return
  const nextRole: UserRole = user.role === 'super_admin' ? 'user' : 'super_admin'
  return changeRole(user, nextRole)
}

const openReset = (user: StudioUser) => {
  if (!canManageAccount(user)) return
  resetTarget.value = user
  newPassword.value = ''
  resetDialog.value = true
}

const submitReset = async () => {
  if (!resetTarget.value) return
  busyId.value = resetTarget.value.id
  try {
    await resetUserPassword(resetTarget.value.id, newPassword.value)
    resetDialog.value = false
  } catch (reason) {
    error.value = getAuthErrorMessage(reason, '密码重置失败')
  } finally {
    busyId.value = ''
  }
}

onMounted(() => loadUsers())
</script>

<style scoped>
.management-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 24px;
  overflow: hidden;
}
.management-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border);
}
.management-header h1 {
  margin: 0 0 4px;
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 500;
  color: var(--ink);
  letter-spacing: -0.04em;
}
.management-header p,
.dialog-note {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.5;
}
.reset-password-title {
  padding: 20px 20px 12px;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.4;
  white-space: normal;
}
.reset-password-body {
  padding: 8px 20px 12px;
}
.dialog-note {
  margin-bottom: 20px;
  line-height: 1.65;
}
.reset-password-field {
  margin-top: 4px;
}
.reset-password-actions {
  padding: 8px 16px 16px;
}
.status-filter {
  max-width: 220px;
}
.users-panel {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-x: auto;
  overflow-y: hidden;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 0;
}
.users-panel :deep(.v-data-table) {
  min-width: 760px;
  flex: 1;
}
.identity-cell {
  display: grid;
  gap: 2px;
}
.identity-cell strong {
  color: var(--ink);
  font-weight: 600;
}
.identity-cell span {
  color: var(--text-subtle);
  font-size: 12px;
  font-family: var(--font-mono);
}
.role-select {
  width: 150px;
}

/* 角色等级 pill — 跟平台所有者同款结构, 用背景色分层级 */
.role-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
}
.role-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 120px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  white-space: nowrap;
  flex-shrink: 0;
  border: 1px solid transparent;
}
.role-pill.is-owner {
  color: var(--accent);
  background: var(--accent-soft);
  border-color: rgba(207, 74, 54, 0.32);
}
.role-pill.is-admin {
  color: var(--sage);
  background: rgba(94, 107, 85, 0.12);
  border-color: rgba(94, 107, 85, 0.32);
}
.role-pill.is-user {
  color: var(--text-muted);
  background: var(--bg-sunken);
  border-color: var(--border);
}

/* 升级 / 降级按钮 — 纯图标方形, 弱描边 */
.role-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border);
  flex-shrink: 0;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.role-toggle.is-promote:hover:not(:disabled) {
  color: var(--sage);
  border-color: var(--sage);
  background: rgba(94, 107, 85, 0.08);
}
.role-toggle.is-demote:hover:not(:disabled) {
  color: var(--status-error);
  border-color: var(--status-error);
  background: var(--status-error-bg);
}
.role-toggle:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.protected-note {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-subtle);
  font-size: 12px;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  background: var(--bg-sunken);
  color: var(--text-muted);
}
.status-pill.is-active {
  color: var(--status-success);
  background: var(--status-success-bg);
}
.status-pill.is-pending {
  color: var(--status-warning);
  background: var(--status-warning-bg);
}
.status-pill.is-disabled {
  color: var(--status-error);
  background: var(--status-error-bg);
}
.row-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 6px;
}
.pagination-bar {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  color: var(--text-subtle);
  background: var(--bg-elevated);
  border-top: 1px solid var(--border);
  font-size: 13px;
}
</style>
