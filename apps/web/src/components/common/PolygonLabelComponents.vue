<template>
  <div
    class="polygon-container"
    @mousemove="handleMouseMove"
    @mousedown="handleMouseDown"
    @contextmenu.prevent="handleRightClick"
    ref="containerRef"
  >
    <!-- 背景图片 -->
    <img
      :src="props.imageSrc"
      :alt="props.imageAlt"
      ref="imageRef"
      @load="handleImageLoad"
      @error="handleImageError"
      class="background-image"
    />

    <!-- SVG 绘制层 -->
    <svg class="drawing-layer" :width="containerSize.width" :height="containerSize.height">
      <!-- 已完成的标注 -->
      <g v-for="(polygon, index) in completedPolygons" :key="polygon.id">
        <polygon
          :points="formatPoints(polygon.points)"
          :fill="getColor(polygon.typeId) + '40'"
          :stroke="getColor(polygon.typeId)"
          stroke-width="2"
          class="completed-polygon"
          @click="handlePolygonClick(polygon, $event)"
        />

        <!-- 标注标签 -->
        <text
          v-if="showLabel(polygon)"
          :x="getCenter(polygon.points).x"
          :y="getCenter(polygon.points).y"
          class="polygon-label"
          :fill="getColor(polygon.typeId)"
          font-size="12"
          font-weight="bold"
          text-anchor="middle"
          dominant-baseline="middle"
        >
          {{ getLabel(polygon) }}
        </text>
      </g>

      <!-- 当前正在绘制的多边形 -->
      <g v-if="currentPoints.length > 0">
        <!-- 已确定的线段 -->
        <polyline
          v-if="currentPoints.length >= 2"
          :points="formatPoints(currentPoints)"
          :stroke="currentColor"
          stroke-width="2"
          fill="none"
          class="drawing-line"
        />

        <!-- 从最后一点到鼠标的虚线 -->
        <line
          v-if="mousePosition && currentPoints.length >= 1"
          :x1="currentPoints[currentPoints.length - 1]?.x"
          :y1="currentPoints[currentPoints.length - 1]?.y"
          :x2="mousePosition.x"
          :y2="mousePosition.y"
          :stroke="currentColor"
          stroke-width="2"
          stroke-dasharray="5,5"
          class="guide-line"
        />

        <!-- 从鼠标到第一点的虚线（形成闭合预览） -->
        <line
          v-if="mousePosition && currentPoints.length >= 3"
          :x1="mousePosition.x"
          :y1="mousePosition.y"
          :x2="currentPoints[0]?.x"
          :y2="currentPoints[0]?.y"
          :stroke="currentColor"
          stroke-width="2"
          stroke-dasharray="5,5"
          class="close-guide-line"
        />

        <!-- 已确定的点 -->
        <circle
          v-for="(point, index) in currentPoints"
          :key="`point-${index}`"
          :cx="point.x"
          :cy="point.y"
          r="4"
          :fill="currentColor"
          stroke="none"
          class="drawing-point"
          @click.stop="removePoint(index)"
        />

        <!-- 闭合预览区域（3个点以上） -->
        <polygon
          v-if="mousePosition && currentPoints.length >= 3"
          :points="getPreviewPoints()"
          fill="rgba(255, 71, 87, 0.1)"
          :stroke="currentColor"
          stroke-width="2"
          stroke-dasharray="5,5"
          class="preview-polygon"
        />
      </g>
    </svg>

    <!-- 操作提示 -->
    <div class="hint-box" v-if="currentPoints.length > 0">
      <div class="hint-title">绘制中...</div>
      <div class="hint-item">已添加 {{ currentPoints.length }} 个点</div>
      <div class="hint-item">点击点可删除</div>
      <div v-if="currentPoints.length >= 3" class="hint-item success">✓ 右键点击完成绘制</div>
    </div>
  </div>

  <!-- 状态栏 -->
  <div class="status-bar">
    <div class="status-item">
      <span class="status-label">坐标:</span>
      <span class="status-value">{{
        mousePosition ? `(${mousePosition.x}, ${mousePosition.y})` : '(0, 0)'
      }}</span>
    </div>
    <div class="status-item">
      <span class="status-label">状态:</span>
      <span class="status-value" :class="{ drawing: currentPoints.length > 0 }">
        {{ currentPoints.length > 0 ? '绘制中' : '就绪' }}
      </span>
    </div>
    <div class="status-item">
      <span class="status-label">标注:</span>
      <span class="status-value">{{ completedPolygons.length }} 个</span>
    </div>
    <div class="status-item" v-if="currentPoints.length > 0">
      <button @click="cancelCurrentDrawing" class="cancel-btn" title="取消当前绘制">取消</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'

// 类型定义
export interface Point {
  x: number
  y: number
}

export interface PolygonAnnotation {
  id?: string | number
  points: Point[]
  typeId: string | number
  label?: string
  data?: any
}

export interface TypeConfig {
  id: string | number
  label: string
  color: string
  description?: string
}

// Props
interface Props {
  // 图片相关
  imageSrc: string
  imageAlt?: string

  // 标注配置
  typeConfigs: TypeConfig[]
  currentTypeId?: string | number

  // 数据
  polygons?: PolygonAnnotation[]

  // 配置
  minPoints?: number
  showLabels?: boolean
  showGuides?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  imageAlt: '标注图片',
  currentTypeId: undefined,
  polygons: () => [],
  minPoints: 3,
  showLabels: true,
  showGuides: true,
})

// Emits
interface Emits {
  (e: 'polygon-complete', polygon: PolygonAnnotation): void
  (e: 'polygon-update', polygons: PolygonAnnotation[]): void
  (e: 'polygon-click', polygon: PolygonAnnotation, event: MouseEvent): void
  (e: 'container-resize', size: { width: number; height: number }): void
}

const emit = defineEmits<Emits>()

// Refs
const containerRef = ref<HTMLElement | null>(null)
const imageRef = ref<HTMLImageElement | null>(null)
const mousePosition = ref<Point | null>(null)
const currentPoints = ref<Point[]>([])
const containerSize = ref({ width: 0, height: 0 })

// 计算属性
const currentType = computed(() => {
  if (!props.currentTypeId || props.typeConfigs.length === 0) {
    return props.typeConfigs[0]
  }
  return props.typeConfigs.find((t) => t.id === props.currentTypeId) || props.typeConfigs[0]
})

const currentColor = computed(() => {
  return currentType.value?.color || '#ff4757'
})

const completedPolygons = computed(() => {
  return props.polygons || []
})

// 方法
const getRelativePosition = (event: MouseEvent): Point | null => {
  if (!containerRef.value) return null

  const rect = containerRef.value.getBoundingClientRect()
  return {
    x: Math.max(0, Math.min(Math.round(event.clientX - rect.left), containerSize.value.width)),
    y: Math.max(0, Math.min(Math.round(event.clientY - rect.top), containerSize.value.height)),
  }
}

const handleMouseMove = (event: MouseEvent) => {
  const pos = getRelativePosition(event)
  if (!pos) return

  mousePosition.value = pos
}

const handleMouseDown = (event: MouseEvent) => {
  const pos = getRelativePosition(event)
  if (!pos) return

  // 只处理左键点击添加点
  if (event.button === 0) {
    currentPoints.value.push({ ...pos })
  }
}

const handleRightClick = (event: MouseEvent) => {
  event.preventDefault()

  // 如果点数不足，不能完成
  if (currentPoints.value.length < props.minPoints) {
    console.warn(
      `需要至少 ${props.minPoints} 个点才能完成多边形，当前有 ${currentPoints.value.length} 个点`,
    )
    return
  }

  // 如果当前没有选中类型，使用第一个
  if (!currentType.value) {
    console.warn('请先选择标注类型')
    return
  }

  // 创建多边形
  const polygon: PolygonAnnotation = {
    id: Math.random().toString(36).substring(2, 9),
    points: [...currentPoints.value],
    typeId: currentType.value.id,
    label: currentType.value.label,
  }

  // 添加到完成列表
  const updatedPolygons = [...completedPolygons.value, polygon]
  emit('polygon-complete', polygon)
  emit('polygon-update', updatedPolygons)

  // 清空当前绘制，准备下一个多边形
  currentPoints.value = []

  console.log('完成了一个多边形，准备绘制下一个')
}

const removePoint = (index: number) => {
  if (currentPoints.value.length <= 1) {
    currentPoints.value = []
    return
  }

  currentPoints.value.splice(index, 1)
}

const cancelCurrentDrawing = () => {
  currentPoints.value = []
}

const formatPoints = (points: Point[]): string => {
  return points.map((p) => `${p.x},${p.y}`).join(' ')
}

const getPreviewPoints = (): string => {
  if (!mousePosition.value || currentPoints.value.length < 3) return ''

  const points = [...currentPoints.value.map((p) => `${p.x},${p.y}`)]
  points.push(`${mousePosition.value.x},${mousePosition.value.y}`)
  return points.join(' ')
}

const getColor = (typeId: string | number): string => {
  const type = props.typeConfigs.find((t) => t.id === typeId)
  return type?.color || currentColor.value
}

const getLabel = (polygon: PolygonAnnotation): string => {
  if (polygon.label) return polygon.label

  const type = props.typeConfigs.find((t) => t.id === polygon.typeId)
  return type?.label || `类型 ${polygon.typeId}`
}

const showLabel = (polygon: PolygonAnnotation): boolean => {
  return props.showLabels && polygon.points.length > 0
}

const getCenter = (points: Point[]): Point => {
  if (points.length === 0) return { x: 0, y: 0 }

  const sum = points.reduce(
    (acc, point) => ({
      x: acc.x + point.x,
      y: acc.y + point.y,
    }),
    { x: 0, y: 0 },
  )

  return {
    x: Math.round(sum.x / points.length),
    y: Math.round(sum.y / points.length),
  }
}

const handleImageLoad = () => {
  updateContainerSize()
}

const handleImageError = (event: Event) => {
  console.error('图片加载失败:', props.imageSrc, event)
}

const updateContainerSize = () => {
  if (!containerRef.value) return

  const rect = containerRef.value.getBoundingClientRect()
  containerSize.value = {
    width: Math.round(rect.width),
    height: Math.round(rect.height),
  }

  emit('container-resize', containerSize.value)
}

const handlePolygonClick = (polygon: PolygonAnnotation, event: MouseEvent) => {
  emit('polygon-click', polygon, event)
}

// 初始化
onMounted(() => {
  updateContainerSize()

  // 监听窗口大小变化
  window.addEventListener('resize', updateContainerSize)
})

// 暴露的方法
defineExpose({
  // 添加多边形
  addPolygon: (points: Point[], typeId: string | number, label?: string) => {
    const polygon: PolygonAnnotation = {
      id: Math.random().toString(36).substring(2, 9),
      points,
      typeId,
      label,
    }

    const updatedPolygons = [...completedPolygons.value, polygon]
    emit('polygon-update', updatedPolygons)
    return polygon
  },

  // 清除所有标注
  clearAll: () => {
    emit('polygon-update', [])
  },

  // 删除指定标注
  removePolygon: (id: string | number) => {
    const updatedPolygons = completedPolygons.value.filter((p) => p.id !== id)
    emit('polygon-update', updatedPolygons)
  },

  // 获取容器信息
  getContainerSize: () => containerSize.value,

  // 取消当前绘制
  cancelDrawing: () => {
    cancelCurrentDrawing()
  },

  // 手动完成当前多边形
  completeCurrentPolygon: () => {
    if (currentPoints.value.length < props.minPoints) {
      console.warn(`需要至少 ${props.minPoints} 个点才能完成多边形`)
      return null
    }

    if (!currentType.value) {
      console.warn('请先选择标注类型')
      return null
    }

    const polygon: PolygonAnnotation = {
      id: Math.random().toString(36).substring(2, 9),
      points: [...currentPoints.value],
      typeId: currentType.value.id,
      label: currentType.value.label,
    }

    const updatedPolygons = [...completedPolygons.value, polygon]
    emit('polygon-complete', polygon)
    emit('polygon-update', updatedPolygons)

    currentPoints.value = []
    return polygon
  },
})
</script>

<style scoped>
.polygon-container {
  position: relative;
  display: inline-block;
  cursor: crosshair;
  user-select: none;
  overflow: hidden;
  background-color: transparent;
}

.background-image {
  display: block;
  max-width: 100%;
  max-height: 70vh;
  pointer-events: none;
}

.drawing-layer {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.completed-polygon {
  pointer-events: all;
  cursor: pointer;
  transition:
    stroke-width 0.2s,
    filter 0.2s;
}

.completed-polygon:hover {
  stroke-width: 3;
  filter: drop-shadow(0 0 3px rgba(0, 0, 0, 0.3));
}

.polygon-label {
  pointer-events: none;
  user-select: none;
}

.drawing-point {
  pointer-events: all;
  cursor: pointer;
  transition: r 0.2s;
}

.drawing-point:hover {
  r: 6;
  fill: #ff6b81;
}

.drawing-line {
  pointer-events: none;
}

.guide-line,
.close-guide-line {
  pointer-events: none;
  opacity: 0.7;
}

.preview-polygon {
  pointer-events: none;
  opacity: 0.5;
}

.hint-box {
  position: absolute;
  top: 10px;
  left: 10px;
  background-color: rgba(0, 0, 0, 0.85);
  color: white;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  min-width: 200px;
}

.hint-title {
  font-weight: bold;
  margin-bottom: 8px;
  color: #ffdd59;
}

.hint-item {
  padding: 2px 0;
  line-height: 1.4;
}

.hint-item.success {
  color: #2ed573;
  font-weight: bold;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 10px;
  padding: 10px 15px;
  background-color: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 13px;
  flex-wrap: wrap;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-label {
  font-weight: bold;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.status-value {
  color: rgb(var(--v-theme-on-surface));
  min-width: 60px;
}

.status-value.drawing {
  color: #ff4757;
  font-weight: bold;
}

.cancel-btn {
  padding: 4px 12px;
  background-color: #ff6b81;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.2s;
}

.cancel-btn:hover {
  background-color: #ff4757;
}
</style>
