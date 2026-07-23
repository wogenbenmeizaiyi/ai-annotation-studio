<template>
  <div
    class="img-wrapper"
    @mousemove="handleMouseMove"
    @mousedown="startDrawing"
    @mouseup="stopDrawing"
    @mouseleave="cancelDrawing"
    ref="wrapperRef"
  >
    <img ref="imgRef" :src="props.imageSrc" @mousemove="handleMouseMove" />
    <!-- 绘制中的矩形 - 使用transform优化 -->
    <div
      v-if="isDrawing"
      class="drawing-rect"
      :style="{
        transform: `translate(${currentRect.x}px, ${currentRect.y}px)`,
        width: currentRect.width + 'px',
        height: currentRect.height + 'px',
        borderColor: currentColor,
      }"
    ></div>

    <!-- 已绘制的矩形 - 使用transform优化 -->
    <div
      v-for="(rect, index) in props.rectangles"
      :key="rect.id || index"
      class="drawn-rect"
      :style="{
        transform: `translate(${rect.x}px, ${rect.y}px)`,
        width: rect.width + 'px',
        height: rect.height + 'px',
        borderColor: getRectColor(rect),
        backgroundColor: getRectColor(rect) + '20',
      }"
      @click.stop="handleRectClick(rect, $event)"
    >
      <span
        class="rect-label"
        :style="{
          backgroundColor: getRectColor(rect),
          transform: 'translateY(-100%)',
        }"
      >
        {{ rect.label || getTypeLabel(rect.typeId) || `标注${index + 1}` }}
      </span>
    </div>
  </div>

  <div class="info" aria-label="画布状态">
    <div class="info-item">
      <span class="info-label">鼠标坐标</span>
      <span class="info-value">
        <b>X</b> {{ Math.round(x) }}
        <i />
        <b>Y</b> {{ Math.round(y) }}
      </span>
    </div>
    <div v-if="currentRect.width > 0" class="info-item current-rect-info">
      <span class="info-label">当前框</span>
      <span class="info-value">
        {{ Math.round(currentRect.width) }} × {{ Math.round(currentRect.height) }}
      </span>
      <span class="info-position">
        @ {{ Math.round(currentRect.x) }}, {{ Math.round(currentRect.y) }}
      </span>
    </div>
    <div class="info-item annotation-total">
      <span class="info-label">已标注</span>
      <strong>{{ props.rectangles?.length || 0 }}</strong>
      <span class="info-unit">个区域</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

export interface RectAnnotation {
  id?: string | number
  x: number
  y: number
  width: number
  height: number
  typeId: string | number
  label?: string
  data?: any // 自定义数据
}

export interface TypeConfig {
  id: string | number
  label: string
  color: string
  description?: string
}

interface Props {
  // 图片相关
  imageSrc: string
  imageAlt?: string

  // 标注配置
  typeConfigs: TypeConfig[]
  currentTypeId?: string | number

  // 数据
  rectangles?: RectAnnotation[]

  // 交互配置
  minRectSize?: number // 最小矩形尺寸
  editable?: boolean // 是否可编辑

  // 样式
  rectBorderWidth?: number
  showLabels?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  imageAlt: '标注图片',
  currentTypeId: undefined,
  rectangles: () => [],
  minRectSize: 10,
  editable: true,
  rectBorderWidth: 2,
  showLabels: true,
})

interface Emits {
  (e: 'rect-complete', rect: RectAnnotation): void
  (e: 'rect-update', rects: RectAnnotation[]): void
  (e: 'rect-click', rect: RectAnnotation, event: MouseEvent): void
  (e: 'rect-delete', rect: RectAnnotation): void
  (e: 'error', error: Error): void
  (e: 'wrapper-resize', size: { width: number; height: number }): void
}

const emit = defineEmits<Emits>()

// 使用浮点数存储坐标，避免整数抖动
const x = ref(0)
const y = ref(0)
const isDrawing = ref(false)
const startX = ref(0)
const startY = ref(0)
const wrapperRef = ref<HTMLElement | null>(null)
const imgRef = ref<HTMLImageElement | null>(null)

const currentRect = ref({
  x: 0,
  y: 0,
  width: 0,
  height: 0,
})

// 添加防抖控制
let animationFrameId: number | null = null
let lastMouseX = 0
let lastMouseY = 0

// 计算属性
const currentType = computed(() => {
  if (!props.currentTypeId || props.typeConfigs.length === 0) {
    return props.typeConfigs[0] || null
  }
  return props.typeConfigs.find((t) => t.id === props.currentTypeId) || props.typeConfigs[0]
})

const currentColor = computed(() => {
  return currentType.value?.color || '#ff4757'
})

// 方法
const getRectColor = (rect: RectAnnotation): string => {
  const config = props.typeConfigs.find((t) => t.id === rect.typeId)
  return config?.color || currentColor.value
}

const getTypeLabel = (typeId: string | number): string => {
  const config = props.typeConfigs.find((t) => t.id === typeId)
  return config?.label || String(typeId)
}

const handleMouseMove = (e: MouseEvent) => {
  if (!wrapperRef.value) return

  const rect = wrapperRef.value.getBoundingClientRect()
  // 🔥 关键：保留浮点数，不取整！
  const currentX = e.clientX - rect.left
  const currentY = e.clientY - rect.top

  x.value = currentX
  y.value = currentY

  if (isDrawing.value) {
    // 🔥 关键：使用requestAnimationFrame避免频繁更新
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId)
    }

    animationFrameId = requestAnimationFrame(() => {
      // 计算矩形位置和大小（保留浮点数）
      currentRect.value.x = Math.min(startX.value, currentX)
      currentRect.value.y = Math.min(startY.value, currentY)
      currentRect.value.width = Math.abs(currentX - startX.value)
      currentRect.value.height = Math.abs(currentY - startY.value)
      animationFrameId = null
    })
  }
}

const startDrawing = (e: MouseEvent) => {
  if (!props.editable || !wrapperRef.value || !currentType.value) return

  const rect = wrapperRef.value.getBoundingClientRect()
  // 🔥 关键：保留浮点数
  startX.value = e.clientX - rect.left
  startY.value = e.clientY - rect.top

  isDrawing.value = true
  currentRect.value = {
    x: startX.value,
    y: startY.value,
    width: 0,
    height: 0,
  }
}

const stopDrawing = (e: MouseEvent) => {
  if (!isDrawing.value || !wrapperRef.value || !currentType.value) return

  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }

  const rect = wrapperRef.value.getBoundingClientRect()
  const endX = e.clientX - rect.left
  const endY = e.clientY - rect.top

  const width = Math.abs(endX - startX.value)
  const height = Math.abs(endY - startY.value)

  // 检查最小尺寸
  if (width >= props.minRectSize && height >= props.minRectSize) {
    const newRect: RectAnnotation = {
      x: Math.min(startX.value, endX),
      y: Math.min(startY.value, endY),
      width,
      height,
      typeId: currentType.value.id,
      label: currentType.value.label,
    }

    // 生成唯一ID
    newRect.id = Date.now() + '-' + Math.random().toString(36).substr(2, 9)

    // 创建新的数组并通知父组件
    const updatedRects = [...(props.rectangles || []), newRect]
    emit('rect-complete', newRect)
    emit('rect-update', updatedRects)
  }

  isDrawing.value = false
  currentRect.value = { x: 0, y: 0, width: 0, height: 0 }
}

const cancelDrawing = () => {
  if (isDrawing.value) {
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
    isDrawing.value = false
    currentRect.value = { x: 0, y: 0, width: 0, height: 0 }
  }
}

const handleRectClick = (rect: RectAnnotation, event: MouseEvent) => {
  emit('rect-click', rect, event)
}

const wrapperSize = ref({
  width: 0,
  height: 0,
})

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  initResizeObserver()
})

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId)
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})

const initResizeObserver = () => {
  if (!wrapperRef.value) return

  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const { width, height } = entry.contentRect
      const newSize = {
        width: Math.round(width),
        height: Math.round(height),
      }
      wrapperSize.value = newSize
      emit('wrapper-resize', newSize)
    }
  })

  resizeObserver.observe(wrapperRef.value)
}

// 暴露给父组件的方法
defineExpose({
  // 获取 wrapper 尺寸
  getWrapperSize: () => wrapperSize.value,

  // 获取 wrapper 元素本身（如果需要直接访问元素）
  getWrapperElement: () => wrapperRef.value,

  // 计算相对坐标（相对于图片）
  getRelativePosition: (clientX: number, clientY: number) => {
    if (!wrapperRef.value) return null
    const rect = wrapperRef.value.getBoundingClientRect()
    return {
      x: clientX - rect.left, // 🔥 保留浮点数
      y: clientY - rect.top,
    }
  },

  // 添加矩形（编程式）
  addRectangle: (rect: RectAnnotation) => {
    const newRect = { ...rect }
    if (!newRect.id) {
      newRect.id = Date.now() + '-' + Math.random().toString(36).substr(2, 9)
    }
    const updatedRects = [...(props.rectangles || []), newRect]
    emit('rect-update', updatedRects)
    return newRect
  },

  // 清除所有矩形
  clearRectangles: () => {
    emit('rect-update', [])
  },

  // 删除指定矩形
  removeRectangle: (id: string | number) => {
    const updatedRects = (props.rectangles || []).filter((r) => r.id !== id)
    emit('rect-update', updatedRects)
  },
})
</script>

<style scoped>
.img-wrapper {
  position: relative;
  display: inline-block;
  cursor: crosshair;
  user-select: none;
  /* 🔥 添加硬件加速 */
  transform: translateZ(0);
  backface-visibility: hidden;
  perspective: 1000;
}

.img-wrapper img {
  display: block;
  height: 75vh;
  max-width: 100%;
  pointer-events: none;
}

.drawing-rect {
  position: absolute;
  top: 0;
  left: 0;
  border: 2px dashed;
  pointer-events: none;
  z-index: 10;
  /* 🔥 优化性能 */
  will-change: transform, width, height;
  /* 🔥 使用border-box确保尺寸准确 */
  box-sizing: border-box;
}

.drawn-rect {
  position: absolute;
  top: 0;
  left: 0;
  border: 2px solid;
  cursor: pointer;
  transition: box-shadow 0.2s;
  z-index: 5;
  /* 🔥 优化性能 */
  will-change: transform;
  box-sizing: border-box;
}

.drawn-rect:hover {
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
}

.rect-label {
  position: absolute;
  top: 0;
  left: 0;
  padding: 2px 6px;
  color: white;
  font-size: 12px;
  border-radius: 3px;
  white-space: nowrap;
  /* 🔥 确保标签位置正确 */
  pointer-events: none;
}

.info {
  position: sticky;
  bottom: 0;
  z-index: 20;
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 0;
  margin: 0;
  padding: 0 12px;
  color: var(--studio-ink-subtle);
  background: rgba(15, 16, 17, 0.94);
  border-top: 1px solid var(--studio-hairline);
  backdrop-filter: blur(10px);
}

.info-item {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 11px;
}

.info-item + .info-item {
  margin-left: 14px;
  padding-left: 14px;
  border-left: 1px solid var(--studio-hairline);
}

.info-label {
  color: var(--studio-ink-tertiary);
  font-size: 10px;
  white-space: nowrap;
}

.info-value,
.info-position {
  color: var(--studio-ink-muted);
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
  white-space: nowrap;
}

.info-value b {
  color: var(--studio-ink-tertiary);
  font-size: 9px;
  font-weight: 600;
}

.info-value i {
  display: inline-block;
  width: 1px;
  height: 10px;
  margin: 0 4px;
  vertical-align: -1px;
  background: var(--studio-hairline-strong);
}

.info-position {
  color: var(--studio-ink-tertiary);
}

.annotation-total {
  margin-left: auto !important;
}

.annotation-total strong {
  min-width: 24px;
  padding: 2px 7px;
  color: var(--studio-ink);
  background: rgba(94, 106, 210, 0.16);
  border: 1px solid rgba(94, 106, 210, 0.28);
  border-radius: 999px;
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
  font-size: 11px;
  text-align: center;
}

.info-unit {
  color: var(--studio-ink-tertiary);
  white-space: nowrap;
}

@media (max-width: 700px) {
  .info {
    flex-wrap: wrap;
    gap: 6px 0;
    padding-block: 7px;
  }

  .annotation-total {
    width: auto;
  }
}
</style>
