<template>
  <main class="workspace-center">
    <section class="workspace-content">
      <PageHeader title="工作中心" description="选择工作区，继续数据标注、模型训练或检测服务管理。" />

      <div class="workspace-options">
        <article class="workspace-option" @click="goTo('taskList')">
          <div class="workspace-option-icon is-cinnabar">
            <Icon name="folder" :size="22" />
          </div>
          <h2>标注任务</h2>
          <p>管理数据集图片，完成检测与分割标注，并配置模型训练。</p>
          <span class="workspace-option-cta">进入标注任务
            <Icon name="arrow-right" :size="16" />
          </span>
        </article>

        <article class="workspace-option" @click="goTo('aiRecognition')">
          <div class="workspace-option-icon is-sage">
            <Icon name="radar" :size="22" />
          </div>
          <h2>检测服务管理</h2>
          <p>查看识别任务，维护模型与提示词，并管理综合检测配置。</p>
          <span class="workspace-option-cta">进入检测服务
            <Icon name="arrow-right" :size="16" />
          </span>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import PageHeader from '@/components/common/PageHeader.vue'
import { Icon } from '@/components/icons'

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
  background: var(--bg-app);
}

.workspace-content {
  max-width: 1040px;
  margin: 0 auto;
  padding: 36px 28px;
}

.workspace-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
  margin-top: 28px;
}

.workspace-option {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  padding: 32px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  cursor: pointer;
  transition:
    transform 0.18s,
    border-color 0.18s,
    box-shadow 0.18s;
  box-shadow: var(--shadow-card);
}
.workspace-option:hover {
  transform: translateY(-2px);
  border-color: var(--ink);
}
.workspace-option h2 {
  margin: 22px 0 10px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 500;
  letter-spacing: -0.04em;
}
.workspace-option p {
  margin: 0;
  flex: 1;
  color: var(--text-muted);
  font-size: 14px;
  line-height: 1.7;
}
.workspace-option-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border: 1px solid var(--ink);
}
.workspace-option-icon.is-cinnabar {
  background: var(--accent);
  color: var(--paper);
  border-color: var(--accent);
}
.workspace-option-icon.is-sage {
  background: var(--sage);
  color: var(--paper);
  border-color: var(--sage);
}
.workspace-option-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
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
