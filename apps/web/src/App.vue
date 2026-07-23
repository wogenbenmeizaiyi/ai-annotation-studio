<template>
  <v-app class="app-shell">
    <div class="app-layout" :class="{ 'is-focus-mode': focusMode }">
      <AppSidebar :focus-mode="focusMode" :mobile-open="mobileNavigationOpen" @close="closeMobileNavigation" />

      <div class="app-workspace">
        <div class="app-topbar">
          <v-btn
            icon="mdi-menu"
            variant="text"
            size="small"
            class="mobile-navigation-trigger"
            aria-label="打开导航"
            @click="mobileNavigationOpen = true"
          />
          <BreadcrumbNav />
        </div>
        <v-main class="app-content">
          <RouterView />
        </v-main>
      </div>

      <button
        v-if="mobileNavigationOpen"
        type="button"
        class="mobile-navigation-scrim"
        aria-label="关闭导航"
        @click="closeMobileNavigation"
      />
    </div>
  </v-app>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/common/AppSidebar.vue'
import BreadcrumbNav from '@/components/common/BreadcrumbNav.vue'

const route = useRoute()
const mobileNavigationOpen = ref(false)

const focusMode = computed(() => Boolean(route.meta.focusMode))

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
}

.app-shell :deep(.v-application__wrap) {
  height: calc(100vh / var(--app-zoom));
  min-height: 0;
}

.app-layout {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  background: var(--studio-canvas);
}

.app-workspace {
  min-width: 0;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.app-topbar {
  height: 40px;
  min-height: 40px;
  display: flex;
  align-items: center;
  background: var(--studio-surface-1);
  border-bottom: 1px solid var(--studio-hairline);
}

.mobile-navigation-trigger {
  display: none;
  margin-left: 6px;
}

.app-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}

.mobile-navigation-scrim {
  position: fixed;
  z-index: 15;
  inset: 0;
  display: none;
  padding: 0;
  background: rgba(0, 0, 0, 0.64);
  border: 0;
}

@media (max-width: 840px) {
  .mobile-navigation-trigger,
  .mobile-navigation-scrim {
    display: inline-flex;
  }
}
</style>
