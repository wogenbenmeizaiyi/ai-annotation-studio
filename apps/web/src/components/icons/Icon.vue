<script setup lang="ts">
/* AI Studio 自绘图标组件 — Paper + Ink + Cinnabar 设计语言
 * 用法: <Icon name="folder" :size="19" /> 颜色由 CSS color 控制 (currentColor)
 */
import { computed } from 'vue'
import { icons, type IconShape, type IconName } from './icons-data'

const props = withDefaults(
  defineProps<{
    name: IconName | (string & {})
    size?: number | string
    strokeWidth?: number
  }>(),
  { size: 19, strokeWidth: 1.5 },
)

const shapes = computed<IconShape[]>(() => icons[props.name] ?? [])
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    class="ai-icon"
    role="img"
  >
    <template v-for="(s, i) in shapes" :key="i">
      <path v-if="s.t === 'p'" :d="s.d" :fill="s.fill ? 'currentColor' : 'none'" />
      <circle
        v-else-if="s.t === 'c'"
        :cx="s.cx"
        :cy="s.cy"
        :r="s.r"
        :fill="s.fill ? 'currentColor' : 'none'"
      />
      <rect
        v-else-if="s.t === 'r'"
        :x="s.x"
        :y="s.y"
        :width="s.w"
        :height="s.h"
        :fill="s.fill ? 'currentColor' : 'none'"
      />
      <line v-else-if="s.t === 'l'" :x1="s.x1" :y1="s.y1" :x2="s.x2" :y2="s.y2" />
    </template>
  </svg>
</template>

<style scoped>
.ai-icon {
  display: inline-block;
  flex: 0 0 auto;
  vertical-align: middle;
}
</style>
