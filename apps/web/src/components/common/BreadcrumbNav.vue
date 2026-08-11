<template>
  <div class="breadcrumb-bar">
    <v-breadcrumbs :items="breadcrumbItems" density="compact" class="breadcrumb-nav">
      <template #item="{ item }">
        <v-breadcrumbs-item
          v-if="isBreadcrumbLink(item)"
          :to="getBreadcrumbHref(item)"
          class="breadcrumb-link"
        >
          <v-icon v-if="getBreadcrumbIcon(item)" :icon="getBreadcrumbIcon(item)" size="small" />
          <span>{{ getBreadcrumbTitle(item) }}</span>
        </v-breadcrumbs-item>
        <v-breadcrumbs-item v-else disabled class="breadcrumb-current">
          <v-icon v-if="getBreadcrumbIcon(item)" :icon="getBreadcrumbIcon(item)" size="small" />
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
  prependIcon?: string
  disabled?: boolean
}

const route = useRoute()

const toBreadcrumbItem = (item: unknown): BreadcrumbNavItem => item as BreadcrumbNavItem

const isBreadcrumbLink = (item: unknown): boolean => {
  const breadcrumbItem = toBreadcrumbItem(item)
  return !breadcrumbItem.disabled && Boolean(breadcrumbItem.href)
}

const getBreadcrumbHref = (item: unknown): string => toBreadcrumbItem(item).href

const getBreadcrumbIcon = (item: unknown): string | undefined => toBreadcrumbItem(item).prependIcon

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
    return [
      { title: '标注任务', href: path, prependIcon: 'mdi-folder-outline', disabled: true },
    ]
  }

  if (path.startsWith('/ai/')) {
    const currentPage = {
      '/ai/recognition': { title: '识别任务', icon: 'mdi-clipboard-text-outline' },
      '/ai/models': { title: '模型库', icon: 'mdi-cube-outline' },
      '/ai/combinations': { title: '综合检测', icon: 'mdi-vector-combine' },
    }[path]

    return [
      {
        title: currentPage?.title ?? '检测服务管理',
        href: path,
        prependIcon: currentPage?.icon ?? 'mdi-radar',
        disabled: true,
      },
    ]
  }

  if (path === '/model-mraining' || path === '/model-training') {
    return [{ title: '模型训练', href: '/model-mraining', prependIcon: 'mdi-brain' }]
  }

  if (path.startsWith('/task/')) {
    const segments = path.split('/').filter(Boolean)
    const taskName = decodeURIComponent(segments[1] ?? 'unknown')

    if (segments.length === 2) {
      return [
        { title: '标注任务', href: '/task', prependIcon: 'mdi-folder-outline' },
        { title: taskName, href: getTaskHref(taskName), prependIcon: 'mdi-file-document-outline' },
      ]
    }

    if (segments.length === 3 && segments[2] === 'train') {
      return [
        { title: '标注任务', href: '/task', prependIcon: 'mdi-folder-outline' },
      ]
    }

    if (segments.length >= 4) {
      const imageName = decodeURIComponent(segments[2] ?? '')
      const annotationType = segments[3]
      const typeLabel = annotationType === 'segment' ? '分割标注' : '检测标注'
      const typeIcon = annotationType === 'segment' ? 'mdi-target' : 'mdi-cube-outline'
      const displaySize = imageName.length > 20 ? `${imageName.slice(0, 20)}...` : imageName

      return [
        { title: '标注任务', href: '/task', prependIcon: 'mdi-folder-outline' },
        {
          title: taskName,
          href: getTaskHref(taskName, annotationType),
          prependIcon: 'mdi-file-document-outline',
        },
        {
          title: displaySize,
          href: getTaskHref(taskName, annotationType),
          prependIcon: 'mdi-image-outline',
          disabled: true,
        },
        { title: typeLabel, href: path, prependIcon: typeIcon, disabled: true },
      ]
    }
  }

  if (path.startsWith('/train/')) {
    const segments = path.split('/').filter(Boolean)
    const id = segments[1]
    return [
      { title: '模型训练', href: '/model-mraining', prependIcon: 'mdi-brain' },
      { title: `训练任务 #${id}`, href: path, prependIcon: 'mdi-cog-outline' },
    ]
  }

  return [{ title: '首页', href: '/', prependIcon: 'mdi-home-outline' }]
})
</script>

<style scoped>
.breadcrumb-bar {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  height: 40px;
  background: transparent;
}

.breadcrumb-nav {
  --v-breadcrumbs-item-height: auto;
  align-items: center;
  background: transparent;
  display: flex;
  width: 100%;
  height: 40px;
  min-height: 40px;
  padding: 0 16px;
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
  gap: 4px;
  height: 100%;
  line-height: normal;
  text-decoration: none;
  font-size: 12px;
}

.breadcrumb-link {
  cursor: pointer;
}

.breadcrumb-link:hover {
  color: rgb(var(--v-theme-primary));
}

.breadcrumb-current {
  color: var(--studio-ink-subtle);
}

@media (max-width: 640px) {
  .breadcrumb-nav {
    padding-inline: 8px;
  }

  .breadcrumb-nav :deep(.v-breadcrumbs-item:nth-of-type(n + 4)),
  .breadcrumb-nav :deep(.v-breadcrumbs-divider:nth-of-type(n + 4)) {
    display: none;
  }
}
</style>
