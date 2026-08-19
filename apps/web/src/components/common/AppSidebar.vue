<template>
  <aside class="app-sidebar" :class="{ 'is-focus-mode': focusMode, 'is-mobile-open': mobileOpen }">
    <RouterLink to="/task" class="sidebar-brand" aria-label="返回标注任务">
      <div class="sidebar-brand-mark">
        <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
          <rect x="1" y="1" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.5" />
          <rect x="12" y="12" width="7" height="7" fill="var(--accent, #cf4a36)" />
        </svg>
      </div>
      <div class="sidebar-brand-copy">
        <strong>AI Studio</strong>
        <span>标注与检测平台</span>
      </div>
      <button
        type="button"
        class="sidebar-mobile-close"
        aria-label="关闭导航"
        @click="emit('close')"
      >
        <Icon name="close" :size="18" />
      </button>
    </RouterLink>

    <nav class="sidebar-navigation" aria-label="主导航">
      <div v-for="group in navigationGroups" :key="group.label" class="sidebar-group">
        <div class="sidebar-group-label">{{ group.label }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="sidebar-link"
          :class="{ 'is-active': isActive(item) }"
          :title="focusMode ? item.label : undefined"
          @click="emit('close')"
        >
          <Icon :name="item.icon" :size="19" class="sidebar-link-icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-user">
        <span class="sidebar-avatar">{{ userInitial }}</span>
        <div class="sidebar-user-copy">
          <strong>{{ auth.user?.display_name }}</strong>
          <span>{{ roleText }}</span>
        </div>
      </div>
      <button
        type="button"
        class="sidebar-logout"
        title="退出登录"
        aria-label="退出登录"
        @click="handleLogout"
      >
        <Icon name="logout" :size="18" />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Icon, type IconName } from '@/components/icons'

type NavigationItem = {
  label: string
  to: string
  icon: IconName
  match: (path: string) => boolean
}

type NavigationGroup = {
  label: string
  items: NavigationItem[]
}

defineProps<{
  focusMode: boolean
  mobileOpen: boolean
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const userInitial = computed(() =>
  (auth.user?.display_name || auth.user?.username || 'U').slice(0, 1),
)
const roleText = computed(() => {
  if (auth.isPlatformOwner) return '平台所有者'
  return auth.isSuperAdmin ? '超级管理员' : '普通用户'
})

const handleLogout = async () => {
  await auth.logout()
  await router.replace({ name: 'login' })
}

const navigationGroups = computed<NavigationGroup[]>(() => {
  const groups: NavigationGroup[] = [
    {
      label: '标注与训练',
      items: [
        {
          label: '标注任务',
          to: '/task',
          icon: 'folder',
          match: (path) => path.startsWith('/task'),
        },
      ],
    },
    {
      label: '检测服务',
      items: [
        {
          label: '识别任务',
          to: '/ai/recognition',
          icon: 'clipboard',
          match: (path) => path === '/ai/recognition',
        },
        {
          label: '模型库',
          to: '/ai/models',
          icon: 'cube',
          match: (path) => path === '/ai/models',
        },
        {
          label: '综合检测',
          to: '/ai/combinations',
          icon: 'vector-combine',
          match: (path) => path === '/ai/combinations',
        },
      ],
    },
  ]

  if (auth.isSuperAdmin) {
    groups.push({
      label: '系统管理',
      items: [
        {
          label: '用户管理',
          to: '/admin/users',
          icon: 'users',
          match: (path) => path === '/admin/users',
        },
      ],
    })
  }

  return groups
})

const isActive = (item: NavigationItem): boolean => item.match(route.path)
</script>

<style scoped>
.app-sidebar {
  position: relative;
  z-index: 20;
  width: 232px;
  min-width: 232px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-elevated);
  border-right: 1px solid var(--border);
  transition:
    width 0.18s ease,
    min-width 0.18s ease,
    transform 0.18s ease;
}

/* Brand — 64px 高, 跟 topbar 齐高 */
.sidebar-brand {
  height: 64px;
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
  color: var(--ink);
  text-decoration: none;
}
.sidebar-brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--ink);
}
.sidebar-brand-copy {
  min-width: 0;
  display: grid;
  gap: 1px;
  white-space: nowrap;
}
.sidebar-brand-copy strong {
  color: var(--ink);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.2px;
}
.sidebar-brand-copy span {
  color: var(--text-subtle);
  font-size: 11px;
}
.sidebar-mobile-close {
  display: none;
  margin-left: auto;
  width: 32px;
  height: 32px;
  padding: 0;
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--border);
  cursor: pointer;
  align-items: center;
  justify-content: center;
}
.sidebar-mobile-close:hover {
  background: var(--bg-sunken);
  border-color: var(--ink);
}

/* Navigation */
.sidebar-navigation {
  flex: 1;
  min-height: 0;
  padding: 18px 12px;
  overflow-y: auto;
}
.sidebar-group + .sidebar-group {
  margin-top: 22px;
}
.sidebar-group-label {
  height: 24px;
  padding: 0 12px 8px;
  color: var(--text-label);
  font-size: 11px;
  font-weight: 600;
  line-height: 24px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  white-space: nowrap;
}
.sidebar-link {
  position: relative;
  height: 38px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 2px 0;
  padding: 0 12px;
  overflow: hidden;
  color: var(--text-muted);
  text-decoration: none;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
  transition:
    color 0.15s ease,
    background-color 0.15s ease;
}
.sidebar-link:hover {
  color: var(--ink);
  background: var(--bg-sunken);
}
.sidebar-link.is-active {
  color: var(--ink);
  background: var(--bg-sunken);
}
.sidebar-link.is-active::before {
  position: absolute;
  inset: 8px auto 8px 0;
  width: 2px;
  content: '';
  background: var(--accent);
}
.sidebar-link-icon {
  color: inherit;
  flex: 0 0 auto;
}

/* Footer */
.sidebar-footer {
  height: 60px;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 14px;
  color: var(--text-subtle);
  border-top: 1px solid var(--border);
  font-size: 11px;
  white-space: nowrap;
}
.sidebar-user {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.sidebar-avatar {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: var(--paper);
  background: var(--ink);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.sidebar-user-copy {
  min-width: 0;
  display: grid;
}
.sidebar-user-copy strong {
  overflow: hidden;
  color: var(--ink);
  font-size: 12px;
  font-weight: 600;
  text-overflow: ellipsis;
}
.sidebar-user-copy span {
  color: var(--text-subtle);
  font-size: 10px;
}
.sidebar-logout {
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-subtle);
  border: 1px solid var(--border);
  cursor: pointer;
  transition:
    color 0.15s,
    background 0.15s,
    border-color 0.15s;
}
.sidebar-logout:hover {
  color: var(--ink);
  background: var(--bg-sunken);
  border-color: var(--ink);
}

/* Focus mode — 收起成窄条 */
.app-sidebar.is-focus-mode {
  width: 60px;
  min-width: 60px;
}
.is-focus-mode .sidebar-brand {
  justify-content: center;
  padding: 0;
}
.is-focus-mode .sidebar-brand-copy,
.is-focus-mode .sidebar-group-label,
.is-focus-mode .sidebar-link span,
.is-focus-mode .sidebar-footer .sidebar-user-copy,
.is-focus-mode .sidebar-footer .sidebar-logout {
  display: none;
}
.is-focus-mode .sidebar-navigation {
  padding-inline: 8px;
}
.is-focus-mode .sidebar-link {
  justify-content: center;
  padding: 0;
}
.is-focus-mode .sidebar-footer {
  justify-content: center;
  padding: 0;
}

@media (max-width: 840px) {
  .app-sidebar,
  .app-sidebar.is-focus-mode {
    position: fixed;
    inset: 0 auto 0 0;
    width: min(280px, calc(100vw - 48px));
    min-width: min(280px, calc(100vw - 48px));
    transform: translateX(-105%);
  }
  .app-sidebar.is-mobile-open {
    transform: translateX(0);
  }
  .is-focus-mode .sidebar-brand {
    justify-content: flex-start;
    padding: 0 20px;
  }
  .is-focus-mode .sidebar-brand-copy,
  .is-focus-mode .sidebar-group-label,
  .is-focus-mode .sidebar-link span,
  .is-focus-mode .sidebar-footer .sidebar-user-copy,
  .is-focus-mode .sidebar-footer .sidebar-logout {
    display: initial;
  }
  .is-focus-mode .sidebar-link {
    justify-content: flex-start;
    padding: 0 12px;
  }
  .is-focus-mode .sidebar-footer {
    justify-content: flex-start;
    padding: 0 14px;
  }
  .sidebar-mobile-close {
    display: inline-flex;
  }
}
</style>
