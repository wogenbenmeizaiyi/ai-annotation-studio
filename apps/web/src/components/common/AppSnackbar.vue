<template>
  <v-snackbar
    v-model="snackbar.visible.value"
    :color="snackbar.color.value"
    :timeout="snackbar.timeout.value"
    :location="location"
  >
    {{ snackbar.text.value }}
  </v-snackbar>
</template>

<script setup lang="ts">
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
</script>
