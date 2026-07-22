<template>
  <main class="workspace-center">
    <section class="workspace-content">
      <header class="workspace-header">
        <h1>工作中心</h1>
        <p>选择要进入的工作区</p>
      </header>

      <div class="workspace-options">
        <v-card class="workspace-option" hover @click="goTo('taskList')">
          <v-card-text>
            <v-icon icon="mdi-folder-outline" color="primary" size="32" />
            <h2>标注任务</h2>
            <p>管理数据集图片，完成检测与分割标注，并配置模型训练。</p>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" variant="text" append-icon="mdi-arrow-right">进入标注任务</v-btn>
          </v-card-actions>
        </v-card>

        <v-card class="workspace-option" hover @click="goTo('aiRecognition')">
          <v-card-text>
            <v-icon icon="mdi-radar" color="secondary" size="32" />
            <h2>检测服务管理</h2>
            <p>查看识别任务，维护模型与提示词，并管理综合检测配置。</p>
          </v-card-text>
          <v-card-actions>
            <v-btn color="secondary" variant="text" append-icon="mdi-arrow-right"
              >进入检测服务</v-btn
            >
          </v-card-actions>
        </v-card>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goTo = (name: 'taskList' | 'aiRecognition') => {
  void router.push({ name })
}
</script>

<style scoped>
.workspace-center {
  height: 100%;
  min-height: 0;
  overflow: auto;
  background: rgb(var(--v-theme-background));
}

.workspace-content {
  max-width: 880px;
  margin: 0 auto;
  padding: 48px 24px;
}

.workspace-header h1 {
  margin: 0;
  color: rgb(var(--v-theme-on-background));
  font-size: 24px;
  font-weight: 600;
}

.workspace-header p {
  margin: 8px 0 0;
  color: rgba(var(--v-theme-on-background), 0.65);
}

.workspace-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-top: 28px;
}

.workspace-option {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.workspace-option :deep(.v-card-text) {
  flex: 1;
}

.workspace-option h2 {
  margin: 16px 0 8px;
  color: rgb(var(--v-theme-on-surface));
  font-size: 18px;
  font-weight: 600;
}

.workspace-option p {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 14px;
  line-height: 1.7;
}

@media (max-width: 640px) {
  .workspace-content {
    padding: 28px 16px;
  }

  .workspace-options {
    grid-template-columns: 1fr;
  }
}
</style>
