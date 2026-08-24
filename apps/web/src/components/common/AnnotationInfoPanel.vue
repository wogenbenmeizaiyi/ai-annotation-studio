<template>
  <div class="pagination-section">
    <slot name="navigation" />
  </div>

  <section class="info-summary">
    <div class="info-summary-heading">
      <div>
        <div class="info-eyebrow">当前图片</div>
        <h3>标注信息</h3>
      </div>
      <div class="annotation-count">
        <strong>{{ total }}</strong>
        <span>个区域</span>
      </div>
    </div>

    <div class="summary-metrics">
      <div class="summary-metric">
        <span>当前类型</span>
        <strong>{{ currentTypeLabel }}</strong>
      </div>
      <slot name="stats" />
    </div>
  </section>

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
  gap: 8px;
  justify-content: center;
  padding: 10px 12px;
  background: var(--studio-surface-1);
  border-bottom: 1px solid var(--studio-hairline);
}

.pagination-section :deep(.v-btn) {
  min-width: 92px;
}

.info-summary {
  padding: 15px 16px 13px;
  background: var(--studio-surface-1);
  border-bottom: 1px solid var(--studio-hairline);
}

.info-summary-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.info-eyebrow {
  margin-bottom: 3px;
  color: var(--studio-ink-tertiary);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.7px;
}

.info-summary h3 {
  margin: 0;
  color: var(--studio-ink);
  font-size: 15px;
  font-weight: 600;
}

.annotation-count {
  min-width: 66px;
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  gap: 4px;
  padding: 6px 9px;
  color: var(--studio-ink-subtle);
  background: var(--studio-surface-2);
  border: 1px solid var(--studio-hairline);
  border-radius: 7px;
  font-size: 11px;
}

.annotation-count strong {
  color: var(--studio-ink);
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
  font-size: 15px;
}

.summary-metrics {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 12px;
}

.summary-metric {
  display: grid;
  gap: 3px;
}

.summary-metric span {
  color: var(--studio-ink-tertiary);
  font-size: 10px;
}

.summary-metric strong {
  color: var(--studio-ink-muted);
  font-size: 12px;
  font-weight: 600;
}

.annotations-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: var(--studio-canvas);
}

.annotations-container {
  display: grid;
  gap: 8px;
}

.annotations-container :deep(.annotation-card) {
  margin: 0 !important;
  background: var(--studio-surface-1);
  border-color: var(--studio-hairline);
  border-radius: 8px;
}

.annotations-container :deep(.annotation-card:hover) {
  background: var(--studio-surface-2);
  border-color: var(--studio-hairline-strong);
}

.annotations-container :deep(.annotation-card.annotation-active) {
  background: linear-gradient(
    90deg,
    rgba(var(--studio-annotation-rgb), 0.27),
    rgba(var(--studio-annotation-rgb), 0.15)
  ) !important;
  border-color: rgba(var(--studio-annotation-rgb), 0.5) !important;
  border-left-color: var(--studio-annotation) !important;
  box-shadow:
    inset 0 0 0 1px rgba(var(--studio-annotation-rgb), 0.18),
    0 4px 12px rgba(0, 0, 0, 0.16);
}

.empty-state {
  text-align: center;
  padding: 42px 16px;
  color: var(--studio-ink-tertiary);
}
</style>
