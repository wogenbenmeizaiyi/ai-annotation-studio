<template>
  <v-app class="app-shell">
    <BreadcrumbNav />
    <v-main class="app-content">
      <RouterView />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import BreadcrumbNav from '@/components/common/BreadcrumbNav.vue'
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
  height: 100vh;
  min-height: 0;
}

.app-content {
  flex: 1 1 auto;
  min-height: 0;
  overflow: hidden;
}
</style>
