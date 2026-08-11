<template>
  <div class="annotation-container">
    <!-- 左侧：图片标注区域 -->
    <div class="left-panel">
      <div class="toolbar">
        <div class="type-selector">
          <span class="text-subtitle-2 mr-3">标注类型：</span>
          <div class="type-buttons">
            <v-btn
              v-for="type in typeConfigs"
              :key="type.id"
              :variant="currentTypeId === type.id ? 'flat' : 'outlined'"
              :color="type.color"
              size="small"
              rounded="pill"
              class="mr-2"
              @click="currentTypeId = type.id"
            >
              <span class="color-dot mr-1" :style="{ backgroundColor: currentTypeId === type.id ? '#fff' : type.color }" />
              {{ type.label }}
            </v-btn>
          </div>
        </div>

        <div class="action-buttons">
          <v-btn variant="outlined" color="error" size="small" prepend-icon="mdi-delete-outline" @click="clearAll">
            清空
          </v-btn>
          <v-btn color="primary" size="small" prepend-icon="mdi-download" @click="exportData">
            导出
          </v-btn>
        </div>
      </div>

      <!-- 标注画布 -->
      <div class="canvas-container">
        <ImageRectDrawer
          :image-src="imageUrl"
          :type-configs="typeConfigs"
          :current-type-id="currentTypeId"
          :rectangles="annotations"
          :editable="true"
          :min-rect-size="10"
          @rect-complete="handleRectComplete"
          @rect-update="handleRectUpdate"
          @rect-click="handleRectClick"
          ref="drawerRef"
        />
      </div>
    </div>

    <!-- 右侧：标注信息面板 -->
    <div class="right-panel">
      <v-card class="info-header" color="deep-purple-accent-4" rounded="0" flat>
        <v-card-text class="text-white">
          <h3 class="text-h6 font-weight-bold mb-2">标注信息</h3>
          <div class="d-flex ga-4">
            <div>
              <div class="text-caption" style="opacity: 0.9">总数：</div>
              <div class="text-h6 font-weight-bold">{{ annotations.length }}</div>
            </div>
            <div>
              <div class="text-caption" style="opacity: 0.9">类型：</div>
              <div class="text-h6 font-weight-bold">{{ getCurrentTypeLabel() }}</div>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <div class="annotations-list">
        <div v-if="annotations.length === 0" class="empty-state">
          <v-icon icon="mdi-clipboard-text-outline" size="48" color="grey-lighten-1" />
          <p class="mt-3">暂无标注</p>
          <p class="text-caption text-medium-emphasis">在左侧图片上拖拽绘制标注框</p>
        </div>

        <div v-else class="annotations-container">
          <v-card
            v-for="(rect, index) in annotations"
            :key="rect.id || index"
            variant="outlined"
            class="annotation-card mb-2"
            :style="{ borderLeftColor: getRectColor(rect), borderLeftWidth: '3px' }"
            @click="highlightAnnotation(rect)"
            :class="{ 'bg-grey-lighten-4': activeAnnotation?.id === rect.id }"
          >
            <v-card-text class="pa-3">
              <div class="d-flex justify-space-between align-center mb-1">
                <div class="d-flex align-center ga-2">
                  <v-chip size="x-small" :color="getRectColor(rect)" variant="flat" text-color="white">
                    {{ getTypeLabel(rect.typeId) }}
                  </v-chip>
                  <span class="text-caption text-medium-emphasis">#{{ index + 1 }}</span>
                </div>
                <v-btn
                  icon="mdi-close"
                  size="x-small"
                  variant="text"
                  color="error"
                  @click.stop="removeAnnotation(rect.id!)"
                />
              </div>
              <div class="text-caption">
                <div>位置：({{ rect.x }}, {{ rect.y }})</div>
                <div>尺寸：{{ rect.width }} x {{ rect.height }}</div>
                <div v-if="rect.label">标签：{{ rect.label }}</div>
              </div>
            </v-card-text>
          </v-card>
        </div>
      </div>
    </div>

    <!-- 确认对话框 -->
    <v-dialog v-model="confirmDialog.isOpen.value" max-width="400">
      <v-card>
        <v-card-title>{{ confirmDialog.title.value }}</v-card-title>
        <v-card-text>{{ confirmDialog.message.value }}</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="confirmDialog.onCancel()">取消</v-btn>
          <v-btn color="error" @click="confirmDialog.onConfirm()">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ImageRectDrawer, {
  type RectAnnotation,
  type TypeConfig,
} from '@/components/common/LabelComponents.vue'
import { useConfirmDialog } from '@/composables/useConfirmDialog'

const confirmDialog = useConfirmDialog()

const imageUrl = ref()

const typeConfigs = ref<TypeConfig[]>([
  { id: 'person', label: '人物', color: '#ff4757' },
  { id: 'vehicle', label: '车辆', color: '#2ed573' },
  { id: 'building', label: '建筑', color: '#1e90ff' },
  { id: 'animal', label: '动物', color: '#ffa502' },
  { id: 'other', label: '其他', color: '#9c88ff' },
])

const currentTypeId = ref(typeConfigs.value[0]?.id)

const annotations = ref<RectAnnotation[]>([])

const activeAnnotation = ref<RectAnnotation | null>(null)

const drawerRef = ref<InstanceType<typeof ImageRectDrawer>>()

const getCurrentTypeLabel = (): string => {
  const type = typeConfigs.value.find((t) => t.id === currentTypeId.value)
  return type?.label || '未知'
}

const getRectColor = (rect: RectAnnotation): string => {
  const type = typeConfigs.value.find((t) => t.id === rect.typeId)
  return type?.color || '#ff4757'
}

const getTypeLabel = (typeId: string | number): string => {
  const type = typeConfigs.value.find((t) => t.id === typeId)
  return type?.label || String(typeId)
}

const handleRectComplete = (rect: RectAnnotation) => {
  rect.id = rect.id || `rect_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

const handleRectUpdate = (rects: RectAnnotation[]) => {
  annotations.value = rects
}

const handleRectClick = (rect: RectAnnotation, event: MouseEvent) => {
  activeAnnotation.value = rect
}

const highlightAnnotation = (rect: RectAnnotation) => {
  activeAnnotation.value = rect
}

const removeAnnotation = (id: string | number) => {
  const index = annotations.value.findIndex((r) => r.id === id)
  if (index !== -1) {
    annotations.value.splice(index, 1)
    if (activeAnnotation.value?.id === id) {
      activeAnnotation.value = null
    }
  }
}

const clearAll = async () => {
  const confirmed = await confirmDialog.showConfirm('确认清空', '确定要清空所有标注吗？')
  if (confirmed) {
    annotations.value = []
    activeAnnotation.value = null
  }
}

const exportData = () => {
  const data = {
    image: imageUrl.value,
    annotations: annotations.value,
    exportTime: new Date().toISOString(),
    typeConfigs: typeConfigs.value,
  }

  const dataStr = JSON.stringify(data, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const a = document.createElement('a')
  a.href = url
  a.download = `annotations_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.annotation-container {
  display: flex;
  height: 100%;
  background: rgb(var(--v-theme-background));
}

.left-panel {
  flex: 3;
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: rgb(var(--v-theme-surface));
  border-right: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.type-selector {
  display: flex;
  align-items: center;
  flex: 1;
}

.type-buttons {
  display: flex;
  flex-wrap: wrap;
}

.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.canvas-container {
  flex: 1;
  overflow: auto;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-background));
}

.right-panel {
  flex: 1.2;
  min-width: 320px;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  background: rgb(var(--v-theme-surface));
}

.annotations-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.empty-state {
  text-align: center;
  padding: 48px 16px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.annotation-card {
  cursor: pointer;
  transition: transform 0.15s ease;
}

.annotation-card:hover {
  transform: translateX(2px);
}
</style>
