<template>
  <v-snackbar
    v-model="snackbar.visible.value"
    :timeout="snackbar.timeout.value"
    :location="location"
    class="app-snackbar"
    :class="`app-snackbar--${snackbarTone}`"
  >
    <div class="app-snackbar-content">
      <Icon :name="snackbarIcon" :size="18" class="app-snackbar-icon" />
      <span>{{ snackbar.text.value }}</span>
    </div>
  </v-snackbar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Anchor } from 'vuetify'
import { useSnackbar } from '@/composables/useSnackbar'
import { Icon, type IconName } from '@/components/icons'

withDefaults(
  defineProps<{
    location?: Anchor
  }>(),
  {
    location: 'top center',
  },
)

const snackbar = useSnackbar()

type SnackbarTone = 'success' | 'warning' | 'error' | 'info'

const toneIcons: Record<SnackbarTone, IconName> = {
  success: 'check-circle',
  warning: 'alert',
  error: 'alert-circle',
  info: 'info',
}

const snackbarTone = computed<SnackbarTone>(() => {
  const tone = snackbar.color.value
  return tone === 'success' || tone === 'warning' || tone === 'error' ? tone : 'info'
})

const snackbarIcon = computed<IconName>(() => toneIcons[snackbarTone.value])
</script>

<style scoped>
.app-snackbar {
  --snackbar-accent: var(--text-muted);
}
.app-snackbar--success {
  --snackbar-accent: var(--status-success);
}
.app-snackbar--warning {
  --snackbar-accent: var(--status-warning);
}
.app-snackbar--error {
  --snackbar-accent: var(--status-error);
}

.app-snackbar :deep(.v-snackbar__wrapper) {
  min-width: 320px;
  max-width: min(460px, calc(100vw - 32px));
  color: var(--text) !important;
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-strong) !important;
  border-radius: 0 !important;
  box-shadow:
    inset 3px 0 0 var(--snackbar-accent),
    var(--shadow-card) !important;
}

.app-snackbar :deep(.v-snackbar__content) {
  padding: 14px 16px;
}

.app-snackbar-content {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
}

.app-snackbar-icon {
  flex: 0 0 auto;
  color: var(--snackbar-accent) !important;
}

@media (max-width: 480px) {
  .app-snackbar :deep(.v-snackbar__wrapper) {
    min-width: 0;
  }
}
</style>
