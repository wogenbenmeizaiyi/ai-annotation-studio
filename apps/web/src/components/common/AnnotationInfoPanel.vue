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
      <Icon name="clipboard" :size="48" class="empty-icon" />
      <p class="empty-title">暂无标注</p>
      <p class="empty-hint">{{ emptyHint }}</p>
    </div>

    <div v-else class="annotations-container">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@/components/icons'

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
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}

.pagination-section :deep(.v-btn) {
  min-width: 92px;
}

.info-summary {
  padding: 15px 16px 13px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}

.info-summary-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.info-eyebrow {
  margin-bottom: 3px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.info-summary h3 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: -0.02em;
}

.annotation-count {
  min-width: 66px;
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  gap: 4px;
  padding: 6px 9px;
  color: var(--text-muted);
  background: var(--bg-sunken);
  border: 1px solid var(--border);
  font-size: 11px;
}

.annotation-count strong {
  color: var(--ink);
  font-family: var(--font-mono);
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
  color: var(--text-label);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.summary-metric strong {
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
}

.annotations-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: var(--bg-app);
}

.annotations-container {
  display: grid;
  gap: 8px;
}

.annotations-container :deep(.annotation-card) {
  margin: 0 !important;
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border) !important;
  border-radius: 0 !important;
  box-shadow: var(--shadow-card-xs) !important;
}

.annotations-container :deep(.annotation-card:hover) {
  background: var(--bg-card-hover) !important;
  border-color: var(--ink) !important;
}

.annotations-container :deep(.annotation-card.annotation-active) {
  background: var(--accent-soft) !important;
  border-color: var(--accent) !important;
}

.empty-state {
  text-align: center;
  padding: 42px 16px;
  color: var(--text-subtle);
  display: grid;
  justify-items: center;
  gap: 8px;
}
.empty-icon {
  color: var(--text-subtle);
  opacity: 0.5;
}
.empty-title {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 500;
}
.empty-hint {
  margin: 0;
  color: var(--text-subtle);
  font-size: 12px;
}
</style>
