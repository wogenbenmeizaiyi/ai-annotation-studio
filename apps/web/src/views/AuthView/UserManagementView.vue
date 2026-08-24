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
            <strong>{{ item.display_name }}</strong
            ><span>@{{ item.username }}</span>
          </div>
        </template>
        <template #item.role="{ item }">
          <div class="role-cell">
            <span
              class="role-pill"
              :class="
                item.is_platform_owner
                  ? 'is-owner'
                  : item.role === 'super_admin'
                    ? 'is-super-admin'
                    : 'is-user'
              "
            >
              <v-icon :icon="getRoleIcon(item)" size="14" />
              {{ getRoleText(item) }}
            </span>
            <v-tooltip
              v-if="canChangeRole(item)"
              :text="item.role === 'user' ? '晋升为超级管理员' : '降级为普通用户'"
              location="top"
            >
              <template #activator="{ props: tooltipProps }">
                <v-btn
                  v-bind="tooltipProps"
                  :icon="item.role === 'user' ? 'mdi-chevron-double-up' : 'mdi-chevron-double-down'"
                  size="x-small"
                  variant="tonal"
                  :color="item.role === 'user' ? 'warning' : 'error'"
                  :loading="busyId === item.id"
                  :disabled="busyId !== ''"
                  class="role-change-btn"
                  :aria-label="`${item.role === 'user' ? '晋升' : '降级'}用户 ${item.display_name}`"
                  @click="toggleRole(item)"
                />
              </template>
            </v-tooltip>
          </div>
        </template>
        <template #item.status="{ item }">
          <span class="status-pill" :class="`is-${item.status}`">{{
            statusText[item.status]
          }}</span>
        </template>
        <template #item.created_at="{ item }">{{ formatDate(item.created_at) }}</template>
        <template #item.actions="{ item }">
          <div class="row-actions">
            <span v-if="!canManageAccount(item)" class="protected-note">
              <v-icon icon="mdi-lock-outline" size="14" />
              {{ item.is_platform_owner ? '所有者账号受保护' : '仅所有者可管理' }}
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
              @click="openReset(item)"
              >重置密码</v-btn
            >
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

const getRoleRank = (user: StudioUser): number => {
  if (user.is_platform_owner) return 0
  return user.role === 'super_admin' ? 1 : 2
}

const compareUserRole = (first: StudioUser, second: StudioUser): number =>
  getRoleRank(first) - getRoleRank(second)

const headers = [
  { title: '用户', key: 'identity' },
  { title: '角色', key: 'role', width: 220, sortRaw: compareUserRole },
  { title: '状态', key: 'status', width: 120 },
  { title: '注册时间', key: 'created_at', width: 190 },
  { title: '', key: 'actions', sortable: false, align: 'end' as const, width: 250 },
]
const statusOptions = [
  { title: '待审批', value: 'pending' },
  { title: '已启用', value: 'active' },
  { title: '已禁用', value: 'disabled' },
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
const canChangeRole = (user: StudioUser): boolean => auth.isPlatformOwner && !user.is_platform_owner
const getRoleText = (user: StudioUser): string => {
  if (user.is_platform_owner) return '平台所有者'
  return user.role === 'super_admin' ? '超级管理员' : '普通用户'
}
const getRoleIcon = (user: StudioUser): string => {
  if (user.is_platform_owner) return 'mdi-shield-crown-outline'
  return user.role === 'super_admin' ? 'mdi-shield-star-outline' : 'mdi-account-outline'
}

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
  error.value = ''
  try {
    await updateUserRole(user.id, role)
    await loadUsers()
  } catch (reason) {
    error.value = getAuthErrorMessage(reason, '角色更新失败')
  } finally {
    busyId.value = ''
  }
}

const toggleRole = (user: StudioUser) => {
  const nextRole: UserRole = user.role === 'user' ? 'super_admin' : 'user'
  void changeRole(user, nextRole)
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
}
.management-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
}
.management-header p,
.dialog-note {
  margin: 0;
  color: var(--studio-ink-subtle);
}
.reset-password-title {
  padding: 24px 24px 12px;
  font-size: 20px;
  line-height: 1.4;
  white-space: normal;
}
.reset-password-body {
  padding: 8px 24px 12px;
}
.dialog-note {
  margin-bottom: 24px;
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
  overflow: hidden;
  background: var(--studio-surface-1);
  border: 1px solid var(--studio-border);
  border-radius: 10px;
}
.users-panel :deep(.v-data-table) {
  min-height: 0;
  flex: 1;
}
.identity-cell {
  display: grid;
  gap: 2px;
}
.identity-cell span {
  color: var(--studio-ink-subtle);
  font-size: 12px;
}
.role-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.role-pill,
.protected-note {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
}
.role-pill {
  width: 98px;
  justify-content: center;
  padding: 5px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  white-space: nowrap;
}
.role-pill.is-user {
  color: var(--studio-ink-subtle);
  background: var(--studio-surface-3);
  border-color: var(--studio-hairline);
}
.role-pill.is-super-admin {
  color: rgb(var(--v-theme-warning));
  background: rgba(var(--v-theme-warning), 0.1);
  border-color: rgba(var(--v-theme-warning), 0.2);
}
.role-pill.is-owner {
  color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.1);
  border-color: rgba(var(--v-theme-primary), 0.2);
}
.protected-note {
  color: var(--studio-ink-subtle);
}
.role-change-btn {
  flex: 0 0 auto;
}
.status-pill {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--studio-surface-3);
  color: var(--studio-ink-subtle);
}
.status-pill.is-active {
  color: rgb(var(--v-theme-success));
  background: rgba(var(--v-theme-success), 0.1);
}
.status-pill.is-pending {
  color: rgb(var(--v-theme-warning));
  background: rgba(var(--v-theme-warning), 0.1);
}
.row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}
.pagination-bar {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  color: var(--studio-ink-subtle);
  border-top: 1px solid var(--studio-hairline);
}
</style>
