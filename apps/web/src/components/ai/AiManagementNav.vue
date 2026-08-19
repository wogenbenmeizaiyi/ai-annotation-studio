<template>
  <div class="ai-management-nav">
    <div class="ai-management-title">
      <div class="eyebrow">检测服务</div>
      <h1>检测服务管理</h1>
      <p>管理外部识别任务、模型与综合检测配置</p>
    </div>

    <nav class="ai-management-tabs" aria-label="检测服务子导航">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="ai-management-tab"
        :class="{ 'is-active': route.path === tab.value }"
        @click="goTo(tab.routeName)"
      >
        <Icon :name="tab.icon" :size="18" />
        <span>{{ tab.label }}</span>
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { Icon, type IconName } from '@/components/icons'

const route = useRoute()
const router = useRouter()

const tabs: Array<{ value: string; label: string; routeName: 'aiRecognition' | 'aiModels' | 'aiCombinations'; icon: IconName }> = [
  { value: '/ai/recognition', label: '识别任务', routeName: 'aiRecognition', icon: 'clipboard' },
  { value: '/ai/models', label: '模型库', routeName: 'aiModels', icon: 'cube' },
  { value: '/ai/combinations', label: '综合检测', routeName: 'aiCombinations', icon: 'vector-combine' },
]

const goTo = (name: 'aiRecognition' | 'aiModels' | 'aiCombinations') => {
  if (route.name !== name) {
    void router.push({ name })
  }
}
</script>

<style scoped>
.ai-management-nav {
  flex: 0 0 auto;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}

.ai-management-title {
  padding: 22px 24px 14px;
}
.eyebrow {
  color: var(--accent);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.ai-management-title h1 {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 500;
  letter-spacing: -0.04em;
}
.ai-management-title p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 14px;
}

.ai-management-tabs {
  display: flex;
  gap: 0;
  padding: 0 16px;
  border-top: 1px solid var(--border);
}
.ai-management-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 50px;
  padding: 0 18px;
  background: transparent;
  color: var(--text-muted);
  border: 0;
  border-bottom: 2px solid transparent;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.ai-management-tab:hover {
  color: var(--ink);
  background: var(--bg-sunken);
}
.ai-management-tab.is-active {
  color: var(--ink);
  border-bottom-color: var(--accent);
}

@media (max-width: 640px) {
  .ai-management-title {
    padding: 16px 16px 10px;
  }
  .ai-management-tabs {
    padding: 0 8px;
    overflow-x: auto;
  }
  .ai-management-tab {
    padding: 0 12px;
    font-size: 13px;
  }
}
</style>
