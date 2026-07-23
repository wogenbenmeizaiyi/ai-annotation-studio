<template>
  <AnnotationScaffold>
    <template #toolbar>
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
            @click="toggleType(type.id)"
          >
            <span
              class="color-dot mr-1"
              :style="{ backgroundColor: currentTypeId === type.id ? '#fff' : type.color }"
            />
            {{ type.label }}
          </v-btn>
        </div>
      </div>

      <v-btn-toggle v-model="mode" mandatory class="mx-4" density="compact" variant="outlined">
        <v-btn value="draw" size="small">手动绘制</v-btn>
        <v-btn value="smart" size="small">智能检测</v-btn>
      </v-btn-toggle>

      <div class="action-buttons">
        <v-btn
          v-if="mode === 'smart'"
          variant="outlined"
          color="warning"
          size="small"
          prepend-icon="mdi-refresh"
          @click="samReset"
        >
          重置
        </v-btn>
        <v-btn
          variant="outlined"
          color="error"
          size="small"
          prepend-icon="mdi-delete-outline"
          @click="clearAll"
        >
          清空
        </v-btn>
        <v-btn color="primary" size="small" prepend-icon="mdi-download" @click="exportData">
          导出
        </v-btn>
      </div>
    </template>

    <template #canvas>
      <!-- 手动绘制模式 -->
      <PolygonLabelComponents
        v-if="mode === 'draw' && imageUrl"
        :image-src="imageUrl"
        :image-alt="imageAlt"
        :type-configs="typeConfigs"
        :current-type-id="currentTypeId"
        :polygons="annotations"
        :min-points="minPoints"
        @polygon-complete="handlePolygonComplete"
        @polygon-update="handlePolygonUpdate"
        @polygon-click="handlePolygonClick"
        @container-resize="handleContainerResize"
        ref="polygonDrawerRef"
      />

      <!-- 智能检测模式 -->
      <div
        v-else-if="imageUrl"
        class="smart-detect-container"
        @click="handleSmartClick"
        ref="smartContainerRef"
      >
        <div class="smart-image-wrapper" ref="smartWrapperRef">
          <img
            :src="imageUrl"
            :alt="imageAlt"
            class="smart-image"
            ref="smartImageEl"
            @load="onSmartImageLoad"
          />
          <canvas ref="smartCanvasRef" class="smart-canvas"></canvas>
        </div>

        <div class="smart-info">
          <v-chip v-if="samStatus === 'disconnected'" size="small" color="grey" variant="flat">
            未连接
          </v-chip>
          <v-chip
            v-else-if="samStatus === 'connecting'"
            size="small"
            color="warning"
            variant="flat"
          >
            连接中...
          </v-chip>
          <v-chip v-else-if="samStatus === 'ready'" size="small" color="success" variant="flat">
            就绪 (点击添加点)
          </v-chip>
          <v-chip v-else-if="samStatus === 'processing'" size="small" color="info" variant="flat">
            分割中...
          </v-chip>

          <v-radio-group
            v-model="samLabel"
            inline
            hide-details
            density="compact"
            class="sam-controls"
          >
            <v-radio :value="1" label="前景" />
            <v-radio :value="0" label="背景" />
          </v-radio-group>
          <v-btn-toggle
            v-model="samResultType"
            mandatory
            density="compact"
            variant="outlined"
            class="sam-controls"
          >
            <v-btn value="mask" size="x-small">多边形</v-btn>
            <v-btn value="bbox" size="x-small">矩形框</v-btn>
          </v-btn-toggle>
          <span class="text-caption" style="opacity: 0.8">已添加 {{ samPoints.length }} 个点</span>
        </div>
      </div>

      <div v-else class="image-loading-placeholder">图片加载中...</div>
    </template>

    <template #right>
      <AnnotationInfoPanel
        :total="annotations.length"
        :current-type-label="getCurrentTypeLabel()"
        :empty="annotations.length === 0"
        empty-hint="在左侧图片上点击绘制多边形标注"
      >
        <template #navigation>
          <v-btn
            variant="outlined"
            size="small"
            prepend-icon="mdi-chevron-left"
            :disabled="isNavigationDisabled"
            @click="prevStep"
          >
            上一页
          </v-btn>
          <v-btn
            variant="outlined"
            size="small"
            append-icon="mdi-chevron-right"
            :disabled="isNavigationDisabled"
            @click="nextStep"
          >
            下一页
          </v-btn>
        </template>

        <template #stats>
          <div>
            <div class="text-caption" style="opacity: 0.9">总点数：</div>
            <div class="text-h6 font-weight-bold">{{ getTotalPoints() }}</div>
          </div>
        </template>

        <v-card
          v-for="(polygon, index) in annotations"
          :key="polygon.id || index"
          variant="outlined"
          class="annotation-card mb-2"
          :style="{ borderLeftColor: getPolygonColor(polygon), borderLeftWidth: '3px' }"
          @click="highlightAnnotation(polygon)"
          :class="{ 'annotation-active': activeAnnotation?.id === polygon.id }"
        >
          <v-card-text class="pa-3">
            <div class="d-flex justify-space-between align-center mb-1">
              <div class="d-flex align-center ga-2">
                <v-chip
                  size="x-small"
                  :color="getPolygonColor(polygon)"
                  variant="flat"
                  text-color="white"
                >
                  {{ getTypeLabel(polygon.typeId) }}
                </v-chip>
                <span class="text-caption text-medium-emphasis">#{{ index + 1 }}</span>
              </div>
              <v-btn
                icon="mdi-close"
                size="x-small"
                variant="text"
                color="error"
                @click.stop="removeAnnotation(polygon.id!)"
              />
            </div>
            <div class="text-caption">
              <div>顶点数：{{ polygon.points.length }} 个点</div>
              <div>
                中心点：({{ getPolygonCenter(polygon).x }}, {{ getPolygonCenter(polygon).y }})
              </div>
            </div>

            <!-- 顶点预览 -->
            <div v-if="polygon.points.length > 0" class="mt-2 pt-2 polygon-points-border">
              <div class="text-caption text-medium-emphasis mb-1">顶点坐标：</div>
              <div class="d-flex flex-wrap ga-1">
                <v-chip
                  v-for="(point, pointIndex) in polygon.points.slice(0, 3)"
                  :key="pointIndex"
                  size="x-small"
                  variant="outlined"
                >
                  ({{ Math.round(point.x) }}, {{ Math.round(point.y) }})
                </v-chip>
                <v-chip v-if="polygon.points.length > 3" size="x-small" variant="tonal">
                  +{{ polygon.points.length - 3 }}个点
                </v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </AnnotationInfoPanel>
    </template>
  </AnnotationScaffold>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import type { CocoAnnotation, CocoDataset, UpdateAnnotationRequest } from '@/types/CocoDataset'
import type { CocoCategory } from '@/types/CocoCategory'
import { getAnnotation, getImage, getImageList, getTask, updateAnnotation } from '@/api/services'
import { createWebSocketUrl } from '@/config/env'
import PolygonLabelComponents, {
  type Point,
  type PolygonAnnotation,
  type TypeConfig,
} from '@/components/common/PolygonLabelComponents.vue'
import AnnotationScaffold from '@/components/common/AnnotationScaffold.vue'
import AnnotationInfoPanel from '@/components/common/AnnotationInfoPanel.vue'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()

// 工作模式: draw(手动绘制) | smart(智能检测)
type DetectMode = 'draw' | 'smart'

const mode = ref<DetectMode>('draw')

// WS 地址由 VITE_API_BASE_URL 派生，避免前端源码写死服务地址。
const WS_BASE_URL = createWebSocketUrl('/ws/sam3')

const imageUrl = ref('')
const imageAlt = ref('标注图片')
let imageS3Key = ''

// SAM3 智能检测状态
const samWs = ref<WebSocket | null>(null)
const samStatus = ref<'disconnected' | 'connecting' | 'ready' | 'processing'>('disconnected')
const samPoints = ref<{ x: number; y: number; label: number }[]>([])
const samLabel = ref(1)
const samResultType = ref<'mask' | 'bbox'>('mask')
const samContours = ref<{ contours: number[][]; area: number }[]>([])
const samBboxes = ref<{ bbox: number[]; points: number[][]; area: number }[]>([])
const smartContainerRef = ref<HTMLDivElement | null>(null)
const smartWrapperRef = ref<HTMLDivElement | null>(null)
const smartImageEl = ref<HTMLImageElement | null>(null)
const smartCanvasRef = ref<HTMLCanvasElement | null>(null)

const typeConfigs = ref<TypeConfig[]>([])

const minPoints = ref(3)

const route = useRoute()
const taskName = computed(() => decodeURIComponent(route.params.taskId as string))
let imageName = route.params.imageName as string
let imageId: string | null = null
let annotation: CocoDataset

const imageListCache = ref<import('@/types/ImageItem').ImageItem[]>([])

const loadImageList = async () => {
  if (imageListCache.value.length > 0) return
  imageListCache.value = (await getImageList(
    taskName.value,
  )) as import('@/types/ImageItem').ImageItem[]
}

const resolveImageId = async () => {
  await loadImageList()
  const match = imageListCache.value.find((img) => img.file_name === imageName)
  if (match) {
    imageId = String(match.id)
  } else {
    throw new Error(`Image not found: ${imageName}`)
  }
}

const currentTypeId = ref<string | number | undefined>(typeConfigs.value[0]?.id)

const toggleType = (id: string | number) => {
  if (currentTypeId.value === id) {
    currentTypeId.value = undefined
  } else {
    currentTypeId.value = id
  }
}

const annotations = ref<PolygonAnnotation[]>([])
const activeAnnotation = ref<PolygonAnnotation | null>(null)
const isSwitchingImage = ref(false)
const isAnnotationLoading = ref(false)
const isAnnotationLoaded = ref(false)
const isAnnotationSaving = ref(false)
const hasUserEditedCurrentImage = ref(false)
const annotationChangeVersion = ref(0)
let annotationSaveQueue = Promise.resolve()
const isNavigationDisabled = computed(
  () =>
    isSwitchingImage.value ||
    isAnnotationLoading.value ||
    isAnnotationSaving.value ||
    !isAnnotationLoaded.value,
)
const wrapperSize = ref({ width: 500, height: 500 })
const OriginalImageSize = ref({ width: 0, height: 0 })
const polygonDrawerRef = ref<InstanceType<typeof PolygonLabelComponents>>()

onMounted(async () => {
  await resolveImageId()
  await loadImage()
  await getTaskDimensionType()
  await reloadCurrentImageAnnotation()
})

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const getCurrentDisplaySize = () => {
  if (mode.value === 'draw') {
    return polygonDrawerRef.value?.getContainerSize()
  }

  const img = smartImageEl.value
  if (!img?.naturalWidth || !img.width || !img.height) return undefined
  return {
    width: Math.round(img.width),
    height: Math.round(img.height),
  }
}

const waitForDrawableWrapperSize = async () => {
  for (let index = 0; index < 60; index++) {
    await nextTick()

    const size = getCurrentDisplaySize()
    if (size?.width && size.height) {
      wrapperSize.value = size
      lastWrapperSize.value = { ...size }
      return
    }

    await sleep(30)
  }
}

const getCurrentTypeLabel = (): string => {
  const type = typeConfigs.value.find((t) => t.id === currentTypeId.value)
  return type?.label || '未知'
}

const getPolygonColor = (polygon: PolygonAnnotation): string => {
  const type = typeConfigs.value.find((t) => t.id === polygon.typeId)
  return type?.color || '#ff4757'
}

const getTypeLabel = (typeId: string | number): string => {
  const type = typeConfigs.value.find((t) => t.id === typeId)
  return type?.label || String(typeId)
}

const getTotalPoints = (): number => {
  return annotations.value.reduce((sum, polygon) => sum + polygon.points.length, 0)
}

const getPolygonCenter = (polygon: PolygonAnnotation): Point => {
  if (polygon.points.length === 0) return { x: 0, y: 0 }
  const sum = polygon.points.reduce((acc, point) => ({ x: acc.x + point.x, y: acc.y + point.y }), {
    x: 0,
    y: 0,
  })
  return {
    x: Math.round(sum.x / polygon.points.length),
    y: Math.round(sum.y / polygon.points.length),
  }
}

const getTaskDimensionType = async () => {
  const res = await getTask(taskName.value)
  typeConfigs.value = categoriesToTypeConfigs(res.categories)
  if (typeConfigs.value.length > 0) {
    currentTypeId.value = typeConfigs.value[0]?.id
  }
}

function categoriesToTypeConfigs(categories: CocoCategory[]): TypeConfig[] {
  return categories.map((c) => ({
    id: c.id,
    label: c.name,
    color: getColorById(c.id),
    description: c.supercategory ?? '',
  }))
}

const COLOR_MAP: Record<number, string> = {
  1: '#ff4d4f',
  2: '#faad14',
  3: '#52c41a',
  4: '#1890ff',
}

const DEFAULT_COLORS = ['#722ed1', '#eb2f96', '#13c2c2']

function getColorById(id: number): string {
  return COLOR_MAP[id] ?? DEFAULT_COLORS[id % DEFAULT_COLORS.length]!
}

const loadImage = async () => {
  try {
    const image = await getImage(Number(imageId))
    imageUrl.value = image.url
    imageS3Key = image.s3_key
  } catch (error) {
    console.error('加载图片失败:', error)
  }
}

// ---- SAM3 智能检测 ----

const initSam3 = () => {
  if (samWs.value) {
    samWs.value.close()
  }
  samPoints.value = []
  samContours.value = []
  samBboxes.value = []
  samStatus.value = 'connecting'

  samWs.value = new WebSocket(WS_BASE_URL)

  samWs.value.onopen = () => {
    if (!imageS3Key) return
    samWs.value!.send(
      JSON.stringify({
        action: 'init',
        s3_key: imageS3Key,
      }),
    )
  }

  samWs.value.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (msg.status === 'loading' || msg.status === 'predicting') {
      samStatus.value = 'processing'
      return
    }

    if (msg.action === 'init') {
      if (msg.success) {
        samStatus.value = 'ready'
        console.log('SAM3 初始化成功:', imageS3Key)
      } else {
        console.error('SAM3 初始化失败:', msg.message)
        samStatus.value = 'disconnected'
      }
    } else if (msg.action === 'reset') {
      samPoints.value = []
      samContours.value = []
      samBboxes.value = []
      samStatus.value = 'ready'
      drawSmartOverlay()
    } else if (msg.bboxes) {
      samContours.value = []
      samBboxes.value = msg.bboxes
      samStatus.value = 'ready'
      drawSmartOverlay()
      void applySamResults('sam-result')
    } else if (msg.contours !== undefined || msg.masks) {
      const masks = msg.masks || [{ contours: msg.contours || [], area: msg.area || 0 }]
      samContours.value = masks
      samBboxes.value = []
      samStatus.value = 'ready'
      drawSmartOverlay()
      void applySamResults('sam-result')
    }
  }

  samWs.value.onerror = (err) => {
    console.error('SAM3 WebSocket 错误:', err)
    samStatus.value = 'disconnected'
  }

  samWs.value.onclose = () => {
    console.log('SAM3 WebSocket 已关闭')
    samStatus.value = 'disconnected'
  }
}

const drawSmartOverlay = () => {
  const canvas = smartCanvasRef.value
  const wrapper = smartWrapperRef.value
  const img = smartImageEl.value
  if (!canvas) return
  if (!wrapper || !img || !img.naturalWidth) {
    clearSmartOverlay()
    return
  }

  canvas.width = wrapper.clientWidth
  canvas.height = wrapper.clientHeight

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const scaleX = img.width / OriginalImageSize.value.width
  const scaleY = img.height / OriginalImageSize.value.height

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  for (const ann of annotations.value) {
    const color = getColorById(ann.typeId as number)
    ctx.beginPath()
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.setLineDash([])
    for (let i = 0; i < ann.points.length; i++) {
      const sx = ann.points[i]!.x
      const sy = ann.points[i]!.y
      if (i === 0) ctx.moveTo(sx, sy)
      else ctx.lineTo(sx, sy)
    }
    ctx.closePath()
    ctx.fillStyle = color + '20'
    ctx.fill()
    ctx.stroke()
  }

  for (const mask of samContours.value) {
    for (const contour of mask.contours) {
      ctx.beginPath()
      ctx.strokeStyle = '#00ff00'
      ctx.lineWidth = 2
      ctx.setLineDash([])
      for (let i = 0; i < contour.length - 1; i += 2) {
        const sx = contour[i]! * scaleX
        const sy = contour[i + 1]! * scaleY
        if (i === 0) ctx.moveTo(sx, sy)
        else ctx.lineTo(sx, sy)
      }
      ctx.closePath()
      ctx.fillStyle = 'rgba(0, 255, 0, 0.15)'
      ctx.fill()
      ctx.stroke()
    }
  }

  for (const box of samBboxes.value) {
    const [x, y, width, height] = box.bbox as [number, number, number, number]
    ctx.beginPath()
    ctx.strokeStyle = '#00ff00'
    ctx.lineWidth = 2
    ctx.setLineDash([])
    ctx.rect(x * scaleX, y * scaleY, width * scaleX, height * scaleY)
    ctx.fillStyle = 'rgba(0, 255, 0, 0.12)'
    ctx.fill()
    ctx.stroke()
  }

  for (const pt of samPoints.value) {
    const sx = pt.x * scaleX
    const sy = pt.y * scaleY
    ctx.beginPath()
    ctx.arc(sx, sy, 6, 0, Math.PI * 2)
    ctx.fillStyle = pt.label === 1 ? '#ff0000' : '#0000ff'
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
  }
}

const clearSmartOverlay = () => {
  const canvas = smartCanvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)
}

const handleSmartClick = (e: MouseEvent) => {
  if (samStatus.value !== 'ready' || !samWs.value) return

  const img = smartImageEl.value
  if (!img) return

  const target = e.target as HTMLElement
  if (target.closest('.smart-info')) return

  const rect = img.getBoundingClientRect()
  const imgX = e.clientX - rect.left
  const imgY = e.clientY - rect.top

  if (imgX < 0 || imgX > img.width || imgY < 0 || imgY > img.height) return

  const scaleX = OriginalImageSize.value.width / img.width
  const scaleY = OriginalImageSize.value.height / img.height

  const origX = imgX * scaleX
  const origY = imgY * scaleY

  samPoints.value.push({ x: origX, y: origY, label: samLabel.value })
  samStatus.value = 'processing'

  samWs.value.send(
    JSON.stringify({
      action: samResultType.value === 'bbox' ? 'bbox' : 'point',
      x: origX,
      y: origY,
      label: samLabel.value,
    }),
  )
}

const samReset = () => {
  if (samWs.value && samStatus.value !== 'disconnected') {
    samWs.value.send(JSON.stringify({ action: 'reset' }))
  } else {
    samPoints.value = []
    samContours.value = []
    samBboxes.value = []
    drawSmartOverlay()
  }
}

const applySamResults = async (reason = 'sam-result'): Promise<boolean> => {
  const hasContours = samContours.value.some((m) => m.contours.length > 0)
  const hasBboxes = samBboxes.value.length > 0
  if (!hasContours && !hasBboxes) return false

  const img = smartImageEl.value
  const displayScaleX = img ? img.width / OriginalImageSize.value.width : 1
  const displayScaleY = img ? img.height / OriginalImageSize.value.height : 1
  let addedCount = 0

  for (const mask of samContours.value) {
    for (const contour of mask.contours) {
      const pts: Point[] = []
      for (let i = 0; i < contour.length - 1; i += 2) {
        const imgX = contour[i]!
        const imgY = contour[i + 1]!
        pts.push({ x: imgX * displayScaleX, y: imgY * displayScaleY })
      }
      if (pts.length >= 3 && currentTypeId.value !== undefined) {
        annotations.value.push({
          id: `sam_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
          points: pts,
          typeId: currentTypeId.value,
          label: getCurrentTypeLabel(),
        })
        addedCount += 1
      }
    }
  }

  for (const box of samBboxes.value) {
    const points = box.points.length
      ? box.points
      : [
          [box.bbox[0]!, box.bbox[1]!],
          [box.bbox[0]! + box.bbox[2]!, box.bbox[1]!],
          [box.bbox[0]! + box.bbox[2]!, box.bbox[1]! + box.bbox[3]!],
          [box.bbox[0]!, box.bbox[1]! + box.bbox[3]!],
        ]
    const pts = points.map((point) => ({
      x: point[0]! * displayScaleX,
      y: point[1]! * displayScaleY,
    }))
    if (pts.length >= 3 && currentTypeId.value !== undefined) {
      annotations.value.push({
        id: `sam_box_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        points: pts,
        typeId: currentTypeId.value,
        label: getCurrentTypeLabel(),
      })
      addedCount += 1
    }
  }

  if (addedCount === 0) return false

  markCurrentImageEdited()
  await queueSaveCurrentAnnotation(reason)
  samReset()
  return true
}

const onSmartImageLoad = () => {
  const size = getCurrentDisplaySize()
  if (size?.width && size.height) {
    wrapperSize.value = size
    lastWrapperSize.value = { ...size }
  }
  nextTick(() => drawSmartOverlay())
}

watch(mode, async (newMode) => {
  if (newMode === 'smart') {
    initSam3()
    nextTick(() => drawSmartOverlay())
  } else {
    await applySamResults('sam-result-before-draw')
    if (samWs.value) samWs.value.close()
    samStatus.value = 'disconnected'
  }
})

watch(samContours, () => {
  nextTick(() => drawSmartOverlay())
})

watch(samBboxes, () => {
  nextTick(() => drawSmartOverlay())
})

watch(samPoints, () => {
  nextTick(() => drawSmartOverlay())
})

watch(
  annotations,
  () => {
    if (mode.value === 'smart') {
      nextTick(() => drawSmartOverlay())
    }
  },
  { deep: true },
)

onUnmounted(() => {
  if (samWs.value) samWs.value.close()
})

const loadAnnotation = async () => {
  try {
    let res = await getAnnotation(Number(imageId))
    annotation = res
    let height = res.images[0]?.height
    let width = res.images[0]?.width

    OriginalImageSize.value = {
      width: width ?? 0,
      height: height ?? 0,
    }

    annotations.value = res.annotations
      .map(cocoToPolygonAnnotation)
      .filter((annotation): annotation is PolygonAnnotation => annotation !== null)
    console.log(
      `[分割标注] 查询标注完成 imageId=${imageId}, 接口数量=${res.annotations.length}, 可显示数量=${annotations.value.length}`,
    )
  } catch (error) {
    console.error('加载标注失败:', error)
    throw error
  }
}

const reloadCurrentImageAnnotation = async () => {
  isAnnotationLoaded.value = false
  isAnnotationLoading.value = true
  hasUserEditedCurrentImage.value = false
  annotationChangeVersion.value = 0
  annotations.value = []
  activeAnnotation.value = null
  try {
    await waitForDrawableWrapperSize()
    await loadAnnotation()
    if (mode.value === 'smart') {
      await nextTick()
      drawSmartOverlay()
    }
    isAnnotationLoaded.value = true
  } finally {
    isAnnotationLoading.value = false
  }
}

const markCurrentImageEdited = () => {
  hasUserEditedCurrentImage.value = true
  annotationChangeVersion.value += 1
}

const cocoToPolygonAnnotation = (annotation: CocoAnnotation): PolygonAnnotation | null => {
  if (!annotation.segmentation) return null

  let points: number[] = []

  if (Array.isArray(annotation.segmentation) && annotation.segmentation.length > 0) {
    points = annotation.segmentation[0] as number[]
  }

  if (points.length === 0 || points.length % 2 !== 0) return null

  const polygonPoints: Point[] = []
  for (let i = 0; i < points.length; i += 2) {
    const imgX = points[i]!
    const imgY = points[i + 1]!

    const wrapperWidth = wrapperSize.value.width
    const wrapperHeight = wrapperSize.value.height
    const originalWidth = OriginalImageSize.value.width
    const originalHeight = OriginalImageSize.value.height

    if (!wrapperWidth || !wrapperHeight || !originalWidth || !originalHeight) {
      continue
    }

    const scaleX = wrapperWidth / originalWidth
    const scaleY = wrapperHeight / originalHeight

    polygonPoints.push({
      x: imgX * scaleX,
      y: imgY * scaleY,
    })
  }

  if (polygonPoints.length < minPoints.value) return null

  const typeConfig =
    typeConfigs.value.find((config) => Number(config.id) === annotation.category_id) ??
    typeConfigs.value[annotation.category_id]
  if (!typeConfig) return null

  return {
    id: annotation.id,
    points: polygonPoints,
    typeId: typeConfig.id,
    label: typeConfig.label,
  }
}

const polygonToCocoAnnotation = (
  polygon: PolygonAnnotation,
  imageId: number,
  index: number,
): CocoAnnotation => {
  const wrapperWidth = wrapperSize.value.width
  const wrapperHeight = wrapperSize.value.height
  const originalWidth = OriginalImageSize.value.width
  const originalHeight = OriginalImageSize.value.height

  if (!wrapperWidth || !wrapperHeight || !originalWidth || !originalHeight) {
    return {
      id: index,
      image_id: imageId,
      category_id: -1,
      bbox: [0, 0, 0, 0],
      iscrowd: 0,
      area: 0,
    }
  }

  const scaleX = originalWidth / wrapperWidth
  const scaleY = originalHeight / wrapperHeight

  const segmentation: number[] = []
  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity,
    maxY = -Infinity

  polygon.points.forEach((point) => {
    const imgX = point.x * scaleX
    const imgY = point.y * scaleY

    segmentation.push(imgX, imgY)

    minX = Math.min(minX, imgX)
    minY = Math.min(minY, imgY)
    maxX = Math.max(maxX, imgX)
    maxY = Math.max(maxY, imgY)
  })

  const width = maxX - minX
  const height = maxY - minY

  const category_id = Number(polygon.typeId)

  return {
    id: index,
    image_id: imageId,
    category_id,
    segmentation: [segmentation],
    bbox: [minX, minY, width, height],
    iscrowd: 0,
    area: width * height,
  }
}

const UpDateAnnotation = async (reason = 'manual') => {
  if (!isAnnotationLoaded.value) {
    throw new Error('ANNOTATION_NOT_LOADED')
  }

  if (!hasUserEditedCurrentImage.value) {
    console.log(`[分割标注] 当前图片未修改，跳过保存 imageId=${imageId}`)
    return
  }

  const image_id = Number(imageId)

  const cocoAnnotations: CocoAnnotation[] = annotations.value.map((polygon, index) =>
    polygonToCocoAnnotation(polygon, image_id, index),
  )

  const updatePayload: UpdateAnnotationRequest = {
    image_id,
    cocoAnnotations,
  }

  const savedVersion = annotationChangeVersion.value
  console.log(
    `[分割标注] 保存标注 reason=${reason}, imageId=${image_id}, 数量=${cocoAnnotations.length}`,
  )
  await updateAnnotation(updatePayload)
  if (annotationChangeVersion.value === savedVersion) {
    hasUserEditedCurrentImage.value = false
  }
  console.log(`[分割标注] 标注更新成功 reason=${reason}, imageId=${image_id}`)
}

const queueSaveCurrentAnnotation = (reason: string) => {
  annotationSaveQueue = annotationSaveQueue
    .catch(() => undefined)
    .then(async () => {
      isAnnotationSaving.value = true
      try {
        await UpDateAnnotation(reason)
      } catch (error) {
        console.error(`[分割标注] 自动保存失败 reason=${reason}:`, error)
        snackbar.showSnackbar('自动保存标注失败，请稍后重试', 'error')
      } finally {
        isAnnotationSaving.value = false
      }
    })

  return annotationSaveQueue
}

const handlePolygonComplete = (polygon: PolygonAnnotation) => {
  polygon.id = polygon.id || `polygon_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

const handlePolygonUpdate = (polygons: PolygonAnnotation[]) => {
  annotations.value = polygons
  markCurrentImageEdited()
  void queueSaveCurrentAnnotation('draw')
}

const handlePolygonClick = (polygon: PolygonAnnotation, event: MouseEvent) => {
  activeAnnotation.value = polygon
}

const highlightAnnotation = (polygon: PolygonAnnotation) => {
  activeAnnotation.value = polygon
}

const removeAnnotation = (id: string | number) => {
  const index = annotations.value.findIndex((p) => p.id === id)
  if (index !== -1) {
    annotations.value = annotations.value.filter((p) => p.id !== id)
    markCurrentImageEdited()
    if (activeAnnotation.value?.id === id) {
      activeAnnotation.value = null
    }
    clearSmartOverlay()
    void nextTick(() => drawSmartOverlay())
    void queueSaveCurrentAnnotation('delete')
  }
}

const switchAnnotation = async (increment: number) => {
  if (isNavigationDisabled.value) return

  isSwitchingImage.value = true

  try {
    if (mode.value === 'smart') {
      await applySamResults('sam-result-before-switch')
    }

    const allImages = imageListCache.value
    const currentIndex = allImages.findIndex((img) => img.file_name === imageName)
    const newIndex = currentIndex + increment
    if (newIndex < 0 || newIndex >= allImages.length) {
      throw new Error('IMAGE_NOT_FOUND')
    }
    const targetImage = allImages[newIndex]!
    imageName = targetImage.file_name
    imageId = String(targetImage.id)

    imageUrl.value = ''
    lastWrapperSize.value = null
    annotations.value = []
    activeAnnotation.value = null
    samPoints.value = []
    samContours.value = []
    samBboxes.value = []

    const image = await getImage(targetImage.id)
    imageUrl.value = image.url
    imageS3Key = image.s3_key
    await reloadCurrentImageAnnotation()

    if (mode.value === 'smart') {
      if (samWs.value) {
        samWs.value.send(
          JSON.stringify({
            action: 'init',
            s3_key: imageS3Key,
          }),
        )
      }
    }
  } catch (error) {
    if (error instanceof Error && error.message !== 'IMAGE_NOT_FOUND') {
      console.error('切换图片失败:', error)
      snackbar.showSnackbar('保存或加载标注失败，请稍后重试', 'error')
      return
    }

    const direction = increment > 0 ? '最后一' : '第一'
    snackbar.showSnackbar(`已经是${direction}张图片了`, 'info')
  } finally {
    isSwitchingImage.value = false
  }
}

const lastWrapperSize = ref<{ width: number; height: number } | null>(null)

const handleContainerResize = (size: { width: number; height: number }) => {
  const lastSize = lastWrapperSize.value

  if (!lastSize) {
    lastWrapperSize.value = { ...size }
    wrapperSize.value = size
    return
  }

  if (!lastSize.width || !lastSize.height || !size.width || !size.height) {
    lastWrapperSize.value = { ...size }
    wrapperSize.value = size
    return
  }

  const scaleX = size.width / lastSize.width
  const scaleY = size.height / lastSize.height

  annotations.value = annotations.value.map((polygon) => ({
    ...polygon,
    points: polygon.points.map((point) => ({
      x: point.x * scaleX,
      y: point.y * scaleY,
    })),
  }))

  wrapperSize.value = size
  lastWrapperSize.value = { ...size }
}

const nextStep = async () => {
  await switchAnnotation(1)
}

const prevStep = async () => {
  await switchAnnotation(-1)
}

const clearAll = async () => {
  const confirmed = await confirmDialog.showConfirm('确认清空', '确定要清空所有标注吗？')
  if (confirmed) {
    annotations.value = []
    activeAnnotation.value = null
    samReset()
    markCurrentImageEdited()
    clearSmartOverlay()
    void nextTick(() => drawSmartOverlay())
    void queueSaveCurrentAnnotation('clear')
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
  a.download = `polygon_annotations_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
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

.image-loading-placeholder {
  min-height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-size: 14px;
}

.annotation-card {
  cursor: pointer;
  transition: transform 0.15s ease;
}

.annotation-card:hover {
  transform: translateX(2px);
}

/* ---- 智能检测模式样式 ---- */
.smart-detect-container {
  position: relative;
  overflow: auto;
  background: rgb(var(--v-theme-background));
  cursor: crosshair;
}

.smart-image-wrapper {
  position: relative;
  display: inline-block;
  overflow: hidden;
}

.smart-image {
  display: block;
  max-width: 100%;
  max-height: 70vh;
  pointer-events: none;
  user-select: none;
}

.smart-canvas {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.smart-info {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  background: rgba(0, 0, 0, 0.75);
  border-radius: 8px;
  color: #fff;
  font-size: 13px;
  pointer-events: auto;
  z-index: 10;
}

.sam-controls {
  flex-direction: row !important;
}

.sam-controls :deep(.v-label) {
  color: white;
  opacity: 1;
}

.polygon-points-border {
  border-top: 1px dashed rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
