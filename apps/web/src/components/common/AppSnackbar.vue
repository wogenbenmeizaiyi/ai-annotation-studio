<template>
  <v-snackbar
    v-model="snackbar.visible.value"
    color="surface"
    :timeout="snackbar.timeout.value"
    :location="location"
    class="app-snackbar"
    :class="`app-snackbar--${snackbarTone}`"
  >
    <div class="app-snackbar-content">
      <v-icon :icon="snackbarIcon" size="18" class="app-snackbar-icon" />
      <span>{{ snackbar.text.value }}</span>
    </div>
  </v-snackbar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Anchor } from 'vuetify'
import { useSnackbar } from '@/composables/useSnackbar'

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

const toneIcons: Record<SnackbarTone, string> = {
  success: 'mdi-check-circle-outline',
  warning: 'mdi-alert-outline',
  error: 'mdi-alert-circle-outline',
  info: 'mdi-information-outline',
}

const snackbarTone = computed<SnackbarTone>(() => {
  const tone = snackbar.color.value
  return tone === 'success' || tone === 'warning' || tone === 'error' ? tone : 'info'
})

const snackbarIcon = computed(() => toneIcons[snackbarTone.value])
</script>

<style scoped>
.app-snackbar {
  --snackbar-accent: 94, 106, 210;
}

.app-snackbar--success {
  --snackbar-accent: 54, 179, 90;
}

.app-snackbar--warning {
  --snackbar-accent: 210, 153, 34;
}

.app-snackbar--error {
  --snackbar-accent: 232, 79, 79;
}

.app-snackbar :deep(.v-snackbar__wrapper) {
  min-width: 320px;
  max-width: min(460px, calc(100vw - 32px));
  color: var(--studio-ink-muted) !important;
  background: var(--studio-surface-2) !important;
  border: 1px solid var(--studio-hairline-strong);
  border-radius: 8px;
  box-shadow:
    inset 2px 0 0 rgb(var(--snackbar-accent)),
    0 12px 32px rgba(0, 0, 0, 0.34) !important;
}

.app-snackbar :deep(.v-snackbar__content) {
  padding: 12px 14px;
}

.app-snackbar-content {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.45;
}

.app-snackbar-icon {
  flex: 0 0 auto;
  color: rgb(var(--snackbar-accent)) !important;
}

@media (max-width: 480px) {
  .app-snackbar :deep(.v-snackbar__wrapper) {
    min-width: 0;
  }
}
</style>
