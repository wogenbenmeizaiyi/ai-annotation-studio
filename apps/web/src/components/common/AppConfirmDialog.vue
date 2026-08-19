<template>
  <v-dialog v-model="confirmDialog.isOpen.value" max-width="440">
    <v-card class="app-confirm-card">
      <v-card-title class="app-confirm-title">{{ confirmDialog.title.value }}</v-card-title>
      <v-card-text class="app-confirm-text">{{ confirmDialog.message.value }}</v-card-text>
      <v-card-actions class="app-confirm-actions">
        <v-spacer />
        <v-btn variant="text" @click="confirmDialog.onCancel()">取消</v-btn>
        <v-btn color="primary" @click="confirmDialog.onConfirm()">确定</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const confirmDialog = useConfirmDialog()
</script>

<style scoped>
.app-confirm-card {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-strong) !important;
  border-radius: 0 !important;
  box-shadow: var(--shadow-card) !important;
}
.app-confirm-title {
  padding: 20px 22px 8px !important;
  font-family: var(--font-serif) !important;
  font-size: 20px !important;
  font-weight: 500 !important;
  letter-spacing: -0.04em !important;
  color: var(--ink) !important;
}
.app-confirm-text {
  padding: 4px 22px 18px !important;
  color: var(--text-muted) !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
}
.app-confirm-actions {
  padding: 8px 14px 14px !important;
  background: var(--bg-elevated) !important;
  border-top: 1px solid var(--border) !important;
  min-height: 60px !important;
}
</style>
