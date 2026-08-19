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
  background: var(--bg-app);
  gap: 10px;
  padding: 10px;
}

.left-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.canvas-container {
  flex: 1;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 0;
  background: var(--bg-app);
}

.right-panel {
  flex: 1.2;
  min-width: 320px;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 0;
  overflow: hidden;
}

@media (max-width: 900px) {
  .annotation-container {
    flex-direction: column;
    overflow-y: auto;
  }

  .left-panel {
    min-height: 620px;
  }

  .right-panel {
    width: 100%;
    min-width: 0;
    max-width: none;
    min-height: 280px;
  }
}
</style>
