<template>
  <div class="model-training-view">
    <TaskListView />
  </div>
</template>
<script lang="ts" setup>
import TaskListView from './TaskView/TaskListView.vue'
</script>

<style scoped>
.model-training-view {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
}
</style>
