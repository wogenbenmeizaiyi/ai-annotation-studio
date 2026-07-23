<template>
  <aside class="app-sidebar" :class="{ 'is-focus-mode': focusMode, 'is-mobile-open': mobileOpen }">
    <RouterLink to="/task" class="sidebar-brand" aria-label="返回标注任务">
      <img src="/favicon-32.png?v=20260722b" alt="" class="sidebar-logo" />
      <div class="sidebar-brand-copy">
        <strong>AI Studio</strong>
        <span>标注与检测平台</span>
      </div>
      <v-btn
        icon="mdi-close"
        variant="text"
        size="small"
        class="sidebar-mobile-close"
        aria-label="关闭导航"
        @click="emit('close')"
      />
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
          <v-icon :icon="item.icon" size="19" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-user">
        <span class="sidebar-avatar">{{ userInitial }}</span>
        <div class="sidebar-user-copy">
          <strong>{{ auth.user?.display_name }}</strong
          ><span>{{ roleText }}</span>
        </div>
      </div>
      <v-btn
        icon="mdi-logout"
        variant="text"
        size="x-small"
        title="退出登录"
        @click="handleLogout"
      />
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

type NavigationItem = {
  label: string
  to: string
  icon: string
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
const roleText = computed(() => (auth.isSuperAdmin ? '超级管理员' : '普通用户'))

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
          icon: 'mdi-folder-outline',
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
          icon: 'mdi-clipboard-text-outline',
          match: (path) => path === '/ai/recognition',
        },
        {
          label: '模型库',
          to: '/ai/models',
          icon: 'mdi-cube-outline',
          match: (path) => path === '/ai/models',
        },
        {
          label: '综合检测',
          to: '/ai/combinations',
          icon: 'mdi-vector-combine',
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
          icon: 'mdi-account-group-outline',
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
  width: 216px;
  min-width: 216px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--studio-canvas);
  border-right: 1px solid var(--studio-hairline);
  transition:
    width 0.18s ease,
    min-width 0.18s ease,
    transform 0.18s ease;
}

.sidebar-brand {
  height: 52px;
  min-height: 52px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  border-bottom: 1px solid var(--studio-hairline);
  color: inherit;
  text-decoration: none;
}

.sidebar-logo {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  object-fit: contain;
}

.sidebar-brand-copy {
  min-width: 0;
  display: grid;
  gap: 1px;
  white-space: nowrap;
}

.sidebar-brand-copy strong {
  color: var(--studio-ink);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.2px;
}

.sidebar-brand-copy span {
  color: var(--studio-ink-subtle);
  font-size: 11px;
}

.sidebar-mobile-close {
  display: none;
  margin-left: auto;
}

.sidebar-navigation {
  flex: 1;
  min-height: 0;
  padding: 12px 8px;
  overflow-y: auto;
}

.sidebar-group + .sidebar-group {
  margin-top: 18px;
}

.sidebar-group-label {
  height: 22px;
  padding: 0 10px;
  color: var(--studio-ink-tertiary);
  font-size: 11px;
  font-weight: 500;
  line-height: 22px;
  letter-spacing: 0.4px;
  white-space: nowrap;
}

.sidebar-link {
  position: relative;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 2px 0;
  padding: 0 10px;
  overflow: hidden;
  color: var(--studio-ink-subtle);
  border-radius: 8px;
  text-decoration: none;
  white-space: nowrap;
  transition:
    color 0.15s ease,
    background-color 0.15s ease;
}

.sidebar-link:hover {
  color: var(--studio-ink-muted);
  background: var(--studio-surface-1);
}

.sidebar-link.is-active {
  color: var(--studio-ink);
  background: var(--studio-surface-2);
}

.sidebar-link.is-active::before {
  position: absolute;
  inset: 8px auto 8px 0;
  width: 2px;
  content: '';
  background: var(--studio-primary);
  border-radius: 2px;
}

.sidebar-footer {
  height: 54px;
  min-height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 0 10px;
  color: var(--studio-ink-tertiary);
  border-top: 1px solid var(--studio-hairline);
  font-size: 11px;
  white-space: nowrap;
}
.sidebar-user {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sidebar-avatar {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #fff;
  background: var(--studio-primary);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 650;
}
.sidebar-user-copy {
  min-width: 0;
  display: grid;
}
.sidebar-user-copy strong {
  overflow: hidden;
  color: var(--studio-ink);
  font-size: 12px;
  font-weight: 550;
  text-overflow: ellipsis;
}
.sidebar-user-copy span {
  color: var(--studio-ink-tertiary);
  font-size: 10px;
}

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
.is-focus-mode .sidebar-footer .v-btn {
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
    box-shadow: 16px 0 48px rgba(0, 0, 0, 0.45);
    transform: translateX(-105%);
  }

  .app-sidebar.is-mobile-open {
    transform: translateX(0);
  }

  .is-focus-mode .sidebar-brand {
    justify-content: flex-start;
    padding: 0 14px;
  }

  .is-focus-mode .sidebar-brand-copy,
  .is-focus-mode .sidebar-group-label,
  .is-focus-mode .sidebar-link span,
  .is-focus-mode .sidebar-footer span:not(.sidebar-status-dot) {
    display: initial;
  }

  .is-focus-mode .sidebar-link {
    justify-content: flex-start;
    padding: 0 10px;
  }

  .is-focus-mode .sidebar-footer {
    justify-content: flex-start;
    padding: 0 18px;
  }

  .sidebar-mobile-close {
    display: inline-flex;
  }
}
</style>
