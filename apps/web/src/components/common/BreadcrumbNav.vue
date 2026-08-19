<template>
  <div class="breadcrumb-bar">
    <v-breadcrumbs :items="breadcrumbItems" density="compact" class="breadcrumb-nav">
      <template #item="{ item }">
        <v-breadcrumbs-item
          v-if="isBreadcrumbLink(item)"
          :to="getBreadcrumbHref(item)"
          class="breadcrumb-link"
        >
          <span>{{ getBreadcrumbTitle(item) }}</span>
        </v-breadcrumbs-item>
        <v-breadcrumbs-item v-else disabled class="breadcrumb-current">
          <span>{{ getBreadcrumbTitle(item) }}</span>
        </v-breadcrumbs-item>
      </template>
    </v-breadcrumbs>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

type BreadcrumbNavItem = {
  title: string
  href: string
  disabled?: boolean
}

const route = useRoute()

const toBreadcrumbItem = (item: unknown): BreadcrumbNavItem => item as BreadcrumbNavItem

const isBreadcrumbLink = (item: unknown): boolean => {
  const breadcrumbItem = toBreadcrumbItem(item)
  return !breadcrumbItem.disabled && Boolean(breadcrumbItem.href)
}

const getBreadcrumbHref = (item: unknown): string => toBreadcrumbItem(item).href

const getBreadcrumbTitle = (item: unknown): string => toBreadcrumbItem(item).title

const getTaskType = (annotationType?: string): string | undefined => {
  if (typeof route.query.type === 'string') return route.query.type
  if (annotationType === 'segment') return 'segmentation'
  if (annotationType === 'detect') return 'detection'
  return undefined
}

const getTaskHref = (taskName: string, annotationType?: string): string => {
  const taskType = getTaskType(annotationType)
  const href = `/task/${encodeURIComponent(taskName)}`
  return taskType ? `${href}?type=${encodeURIComponent(taskType)}` : href
}

const breadcrumbItems = computed<BreadcrumbNavItem[]>(() => {
  const path = route.path

  if (path === '/' || path === '/task') {
    return [{ title: '标注任务', href: path, disabled: true }]
  }

  if (path.startsWith('/ai/')) {
    const currentTitle: Record<string, string> = {
      '/ai/recognition': '识别任务',
      '/ai/models': '模型库',
      '/ai/combinations': '综合检测',
    }

    return [
      {
        title: currentTitle[path] ?? '检测服务管理',
        href: path,
        disabled: true,
      },
    ]
  }

  if (path === '/model-mraining' || path === '/model-training') {
    return [{ title: '模型训练', href: '/model-mraining' }]
  }

  if (path.startsWith('/task/')) {
    const segments = path.split('/').filter(Boolean)
    const taskName = decodeURIComponent(segments[1] ?? 'unknown')

    if (segments.length === 2) {
      return [
        { title: '标注任务', href: '/task' },
        { title: taskName, href: getTaskHref(taskName) },
      ]
    }

    if (segments.length === 3 && segments[2] === 'train') {
      return [{ title: '标注任务', href: '/task' }]
    }

    if (segments.length >= 4) {
      const imageName = decodeURIComponent(segments[2] ?? '')
      const annotationType = segments[3]
      const typeLabel = annotationType === 'segment' ? '分割标注' : '检测标注'
      const displaySize = imageName.length > 20 ? `${imageName.slice(0, 20)}...` : imageName

      return [
        { title: '标注任务', href: '/task' },
        {
          title: taskName,
          href: getTaskHref(taskName, annotationType),
        },
        {
          title: displaySize,
          href: getTaskHref(taskName, annotationType),
          disabled: true,
        },
        { title: typeLabel, href: path, disabled: true },
      ]
    }
  }

  if (path.startsWith('/train/')) {
    const segments = path.split('/').filter(Boolean)
    const id = segments[1]
    return [
      { title: '模型训练', href: '/model-mraining' },
      { title: `训练任务 #${id}`, href: path },
    ]
  }

  return [{ title: '首页', href: '/' }]
})
</script>

<style scoped>
.breadcrumb-bar {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  height: 64px;
  background: transparent;
}

.breadcrumb-nav {
  --v-breadcrumbs-item-height: auto;
  align-items: center;
  background: transparent;
  display: flex;
  width: 100%;
  height: 64px;
  min-height: 64px;
  padding: 0;
  line-height: normal;
}

.breadcrumb-nav :deep(.v-breadcrumbs-item),
.breadcrumb-nav :deep(.v-breadcrumbs-divider) {
  align-items: center;
  display: inline-flex;
  height: auto;
  padding: 0 4px;
  line-height: normal;
}

.breadcrumb-link,
.breadcrumb-current {
  align-items: center;
  color: inherit;
  height: 100%;
  line-height: normal;
  text-decoration: none;
  font-size: 12px;
}

.breadcrumb-link {
  cursor: pointer;
  color: var(--text-muted);
}

.breadcrumb-link:hover {
  color: var(--accent);
}

.breadcrumb-current {
  color: var(--ink);
  font-weight: 500;
}

@media (max-width: 640px) {
  .breadcrumb-nav :deep(.v-breadcrumbs-item:nth-of-type(n + 4)),
  .breadcrumb-nav :deep(.v-breadcrumbs-divider:nth-of-type(n + 4)) {
    display: none;
  }
}
</style>
