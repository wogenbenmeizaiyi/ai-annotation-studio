<template>
  <div class="ai-management-nav">
    <div class="ai-management-title">
      <div>
        <h1>检测服务管理</h1>
        <p>管理外部识别任务、模型与综合检测配置</p>
      </div>
    </div>

    <v-tabs :model-value="route.path" color="primary" density="compact" class="ai-management-tabs">
      <v-tab
        value="/ai/recognition"
        prepend-icon="mdi-clipboard-text-outline"
        @click="goTo('aiRecognition')"
      >
        识别任务
      </v-tab>
      <v-tab value="/ai/models" prepend-icon="mdi-cube-outline" @click="goTo('aiModels')">
        模型库
      </v-tab>
      <v-tab
        value="/ai/combinations"
        prepend-icon="mdi-vector-combine"
        @click="goTo('aiCombinations')"
      >
        综合检测
      </v-tab>
    </v-tabs>
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const goTo = (name: 'aiRecognition' | 'aiModels' | 'aiCombinations') => {
  if (route.name !== name) {
    void router.push({ name })
  }
}
</script>

<style scoped>
.ai-management-nav {
  flex: 0 0 auto;
  background: rgb(var(--v-theme-surface));
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.ai-management-title {
  padding: 18px 24px 10px;
}

.ai-management-title h1 {
  margin: 0;
  color: rgb(var(--v-theme-on-surface));
  font-size: 24px;
  font-weight: 600;
}

.ai-management-title p {
  margin: 4px 0 0;
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 14px;
}

.ai-management-tabs {
  padding: 0 16px;
}

@media (max-width: 640px) {
  .ai-management-title {
    padding: 14px 16px 8px;
  }

  .ai-management-tabs {
    padding: 0 8px;
  }
}
</style>
