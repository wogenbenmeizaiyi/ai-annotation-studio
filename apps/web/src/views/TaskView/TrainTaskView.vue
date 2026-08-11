<template>
  <TrainingConfig />
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import TrainingConfig from '@/components/common/TrainingConfig.vue'
import { provide } from 'vue'

const route = useRoute()
const taskName = route.params.id as string
const detectionType = route.query.type as string

provide('taskId', taskName)
provide('detectionType', detectionType)
</script>
