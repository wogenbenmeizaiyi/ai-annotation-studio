<template>
  <v-dialog v-model="confirmDialog.isOpen.value" max-width="400">
    <v-card>
      <v-card-title>{{ confirmDialog.title.value }}</v-card-title>
      <v-card-text>{{ confirmDialog.message.value }}</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="confirmDialog.onCancel()">取消</v-btn>
        <v-btn color="error" @click="confirmDialog.onConfirm()">确定</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const confirmDialog = useConfirmDialog()
</script>
