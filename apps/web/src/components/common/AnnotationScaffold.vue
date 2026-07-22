<template>
  <div class="annotation-container">
    <div class="left-panel">
      <div class="toolbar">
        <slot name="toolbar" />
      </div>

      <div class="canvas-container">
        <slot name="canvas" />
      </div>
    </div>

    <div class="right-panel">
      <slot name="right" />
    </div>

    <AppConfirmDialog />
    <AppSnackbar />
  </div>
</template>

<script setup lang="ts">
import AppConfirmDialog from '@/components/common/AppConfirmDialog.vue'
import AppSnackbar from '@/components/common/AppSnackbar.vue'
</script>

<style scoped>
.annotation-container {
  display: flex;
  height: 100%;
  background: rgb(var(--v-theme-background));
}

.left-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: rgb(var(--v-theme-surface));
  border-right: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.canvas-container {
  flex: 1;
  overflow: auto;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-background));
}

.right-panel {
  flex: 1.2;
  min-width: 320px;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  background: rgb(var(--v-theme-surface));
}
</style>
