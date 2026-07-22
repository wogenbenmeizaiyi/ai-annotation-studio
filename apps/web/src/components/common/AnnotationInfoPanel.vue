<template>
  <div class="pagination-section">
    <slot name="navigation" />
  </div>

  <v-card class="info-header" color="deep-purple-accent-4" rounded="0" flat>
    <v-card-text class="text-white">
      <h3 class="text-h6 font-weight-bold mb-2">标注信息</h3>
      <div class="d-flex ga-4">
        <div>
          <div class="text-caption" style="opacity: 0.9">总数：</div>
          <div class="text-h6 font-weight-bold">{{ total }}</div>
        </div>
        <div>
          <div class="text-caption" style="opacity: 0.9">类型：</div>
          <div class="text-h6 font-weight-bold">{{ currentTypeLabel }}</div>
        </div>
        <slot name="stats" />
      </div>
    </v-card-text>
  </v-card>

  <div class="annotations-list">
    <div v-if="empty" class="empty-state">
      <v-icon icon="mdi-clipboard-text-outline" size="48" color="grey-lighten-1" />
      <p class="mt-3">暂无标注</p>
      <p class="text-caption text-medium-emphasis">{{ emptyHint }}</p>
    </div>

    <div v-else class="annotations-container">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  total: number
  currentTypeLabel: string
  empty: boolean
  emptyHint: string
}>()
</script>

<style scoped>
.pagination-section {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 16px;
}

.annotations-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.empty-state {
  text-align: center;
  padding: 48px 16px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}
</style>
