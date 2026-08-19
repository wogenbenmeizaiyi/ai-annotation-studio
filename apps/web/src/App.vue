<template>
  <div class="app-shell">
    <!-- 公开页 (login / register / change-password / pending) — 整页居中, 不带侧栏 -->
    <template v-if="publicLayout">
      <RouterView />
    </template>

    <!-- 主界面: 侧栏 + workspace -->
    <div v-else class="app-layout" :class="{ 'is-focus-mode': focusMode }">
      <AppSidebar
        :focus-mode="focusMode"
        :mobile-open="mobileNavigationOpen"
        @close="closeMobileNavigation"
      />

      <div class="app-workspace">
        <div class="app-topbar">
          <button
            type="button"
            class="mobile-navigation-trigger"
            aria-label="打开导航"
            @click="mobileNavigationOpen = true"
          >
            <Icon name="menu" :size="20" />
          </button>
          <BreadcrumbNav />
        </div>
        <main class="app-content">
          <RouterView />
        </main>
      </div>

      <button
        v-if="mobileNavigationOpen"
        type="button"
        class="mobile-navigation-scrim"
        aria-label="关闭导航"
        @click="closeMobileNavigation"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/common/AppSidebar.vue'
import BreadcrumbNav from '@/components/common/BreadcrumbNav.vue'
import { Icon } from '@/components/icons'

const route = useRoute()
const mobileNavigationOpen = ref(false)

const focusMode = computed(() => Boolean(route.meta.focusMode))
const publicLayout = computed(() => Boolean(route.meta.publicLayout))

const closeMobileNavigation = () => {
  mobileNavigationOpen.value = false
}

watch(
  () => route.fullPath,
  () => closeMobileNavigation(),
)
</script>

<style scoped>
.app-shell {
  position: fixed;
  inset: 0;
  width: calc(100vw / var(--app-zoom));
  height: calc(100vh / var(--app-zoom));
  overflow: hidden;
  zoom: var(--app-zoom);
  background: var(--bg-app);
}

.app-layout {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  background: var(--bg-app);
}

.app-workspace {
  min-width: 0;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 纸墨系统的 topbar — 82px 高 (来自设计语言), 1px 描边分隔 */
.app-topbar {
  height: 64px;
  min-height: 64px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 28px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}

.mobile-navigation-trigger {
  display: none;
  width: 36px;
  height: 36px;
  margin: 0;
  padding: 0;
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--border);
  cursor: pointer;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, border-color 0.15s;
}
.mobile-navigation-trigger:hover {
  background: var(--bg-sunken);
  border-color: var(--ink);
}

.app-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  background: var(--bg-app);
}

.mobile-navigation-scrim {
  position: fixed;
  z-index: 25;
  inset: 0;
  display: none;
  padding: 0;
  background: var(--ink);
  border: 0;
  opacity: 0.4;
  cursor: pointer;
}

@media (max-width: 840px) {
  .app-topbar {
    padding: 0 16px;
  }
  .mobile-navigation-trigger,
  .mobile-navigation-scrim {
    display: inline-flex;
  }
  .mobile-navigation-scrim {
    display: block;
  }
}
</style>
