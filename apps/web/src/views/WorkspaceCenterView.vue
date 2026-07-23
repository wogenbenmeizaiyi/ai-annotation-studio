<template>
  <main class="workspace-center">
    <section class="workspace-content">
      <PageHeader title="工作中心" description="选择工作区，继续数据标注、模型训练或检测服务管理。" />

      <div class="workspace-options">
        <v-card class="workspace-option" hover variant="flat" @click="goTo('taskList')">
          <v-card-text>
            <div class="workspace-option-icon">
              <v-icon icon="mdi-folder-outline" color="primary" size="24" />
            </div>
            <h2>标注任务</h2>
            <p>管理数据集图片，完成检测与分割标注，并配置模型训练。</p>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" variant="text" append-icon="mdi-arrow-right">进入标注任务</v-btn>
          </v-card-actions>
        </v-card>

        <v-card class="workspace-option" hover variant="flat" @click="goTo('aiRecognition')">
          <v-card-text>
            <div class="workspace-option-icon">
              <v-icon icon="mdi-radar" color="primary" size="24" />
            </div>
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
import PageHeader from '@/components/common/PageHeader.vue'

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
  max-width: 1040px;
  margin: 0 auto;
  padding: 36px 28px;
}

.workspace-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-top: 24px;
}

.workspace-option {
  min-height: 196px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.workspace-option:hover {
  background: var(--studio-surface-2);
  transform: translateY(-1px);
}

.workspace-option :deep(.v-card-text) {
  flex: 1;
}

.workspace-option h2 {
  margin: 14px 0 7px;
  color: rgb(var(--v-theme-on-surface));
  font-size: 18px;
  font-weight: 600;
}

.workspace-option-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  background: rgba(var(--v-theme-primary), 0.12);
  border: 1px solid rgba(var(--v-theme-primary), 0.2);
  border-radius: 10px;
}

.workspace-option p {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.65);
  font-size: 14px;
  line-height: 1.7;
}

@media (max-width: 640px) {
  .workspace-content {
    padding: 24px 16px;
  }

  .workspace-options {
    grid-template-columns: 1fr;
  }
}
</style>
