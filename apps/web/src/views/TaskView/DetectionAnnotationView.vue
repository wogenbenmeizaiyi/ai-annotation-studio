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
            :disabled="!canManage"
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
        <v-btn value="smart" size="small" :disabled="!canManage">智能检测</v-btn>
      </v-btn-toggle>

      <div class="action-buttons">
        <v-btn
          v-if="canManage && mode === 'smart'"
          variant="outlined"
          color="warning"
          size="small"
          prepend-icon="mdi-refresh"
          @click="samReset"
        >
          重置
        </v-btn>
        <v-btn
          v-if="canManage"
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
      <ImageRectDrawer
        v-if="mode === 'draw' && imageUrl"
        :image-src="imageUrl"
        :type-configs="typeConfigs"
        :current-type-id="currentTypeId"
        :rectangles="annotations"
        :editable="canManage && isAnnotationLoaded && !isAnnotationLoading && !isSwitchingImage"
        :min-rect-size="10"
        @rect-complete="handleRectComplete"
        @rect-update="handleRectUpdate"
        @rect-click="handleRectClick"
        @wrapper-resize="handleWrapperResize"
        ref="drawerRef"
      />

      <div v-else-if="imageUrl" class="smart-detect-container" @click="handleSmartClick">
        <div class="smart-image-wrapper" ref="smartWrapperRef">
          <img
            :src="imageUrl"
            alt="标注图片"
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
            就绪 (点击生成检测框)
          </v-chip>
          <v-chip v-else-if="samStatus === 'processing'" size="small" color="info" variant="flat">
            检测中...
          </v-chip>

          <span class="text-caption" style="opacity: 0.8">
            已生成 {{ samBboxes.length }} 个框
          </span>
        </div>
      </div>

      <div v-else class="image-loading-placeholder">图片加载中...</div>
    </template>

    <template #right>
      <AnnotationInfoPanel
        :total="annotations.length"
        :current-type-label="getCurrentTypeLabel()"
        :empty="annotations.length === 0"
        empty-hint="在左侧图片上拖拽绘制标注框"
      >
        <template #navigation>
          <v-btn
            variant="outlined"
            size="small"
            prepend-icon="mdi-chevron-left"
            :loading="isNavigationLoading"
            :disabled="isNavigationDisabled"
            @click="prevStep"
          >
            上一页
          </v-btn>
          <v-btn
            variant="outlined"
            size="small"
            append-icon="mdi-chevron-right"
            :loading="isNavigationLoading"
            :disabled="isNavigationDisabled"
            @click="nextStep"
          >
            下一页
          </v-btn>
        </template>

        <v-card
          v-for="(rect, index) in annotations"
          :key="rect.id || index"
          variant="outlined"
          class="annotation-card mb-2"
          :style="{ borderLeftColor: getRectColor(rect), borderLeftWidth: '3px' }"
          @click="highlightAnnotation(rect)"
          :class="{ 'annotation-active': activeAnnotation?.id === rect.id }"
        >
          <v-card-text class="annotation-card-content">
            <div class="annotation-card-heading">
              <div class="d-flex align-center ga-2">
                <v-chip
                  size="x-small"
                  :color="getRectColor(rect)"
                  variant="flat"
                  text-color="white"
                >
                  {{ getTypeLabel(rect.typeId) }}
                </v-chip>
                <span class="annotation-index">#{{ index + 1 }}</span>
              </div>
              <v-btn
                v-if="canManage"
                icon="mdi-close"
                size="x-small"
                variant="text"
                color="error"
                @click.stop="removeAnnotation(rect.id!)"
              />
            </div>
            <div class="annotation-details">
              <div class="annotation-detail-item">
                <span>坐标</span>
                <code>{{ formatRectValue(rect.x) }}, {{ formatRectValue(rect.y) }}</code>
              </div>
              <div class="annotation-detail-item">
                <span>尺寸</span>
                <code>
                  {{ formatRectValue(rect.width) }} × {{ formatRectValue(rect.height) }}
                </code>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </AnnotationInfoPanel>
    </template>
  </AnnotationScaffold>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import ImageRectDrawer, {
  type RectAnnotation,
  type TypeConfig,
} from '@/components/common/LabelComponents.vue'
import AnnotationScaffold from '@/components/common/AnnotationScaffold.vue'
import AnnotationInfoPanel from '@/components/common/AnnotationInfoPanel.vue'
import { useRoute } from 'vue-router'
import type { CocoAnnotation, CocoDataset, UpdateAnnotationRequest } from '@/types/CocoDataset'
import { getAnnotation, getImage, getImageList, getTask, updateAnnotation } from '@/api/services'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'
import { ANNOTATION_COLOR } from '@/config/annotation'
import { createWebSocketUrl } from '@/config/env'

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()

const route = useRoute()

const imageUrl = ref('')
let imageS3Key = ''

type DetectMode = 'draw' | 'smart'
type SamStatus = 'disconnected' | 'connecting' | 'ready' | 'processing'
type SamBbox = { bbox: number[]; points?: number[][]; area?: number }

const WS_BASE_URL = createWebSocketUrl('/ws/sam3')
const mode = ref<DetectMode>('draw')
const canManage = ref(false)
const samWs = ref<WebSocket | null>(null)
const samStatus = ref<SamStatus>('disconnected')
const samPoints = ref<{ x: number; y: number; label: number }[]>([])
const samBboxes = ref<SamBbox[]>([])
const smartWrapperRef = ref<HTMLDivElement | null>(null)
const smartImageEl = ref<HTMLImageElement | null>(null)
const smartCanvasRef = ref<HTMLCanvasElement | null>(null)

const taskName = computed(() => decodeURIComponent(route.params.taskId as string))

const typeConfigs = ref<TypeConfig[]>([])

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

const annotations = ref<RectAnnotation[]>([])

const activeAnnotation = ref<RectAnnotation | null>(null)

const isSwitchingImage = ref(false)
const isAnnotationLoading = ref(false)
const isAnnotationLoaded = ref(false)
const isAnnotationSaving = ref(false)
const hasUserEditedCurrentImage = ref(false)
const annotationChangeVersion = ref(0)
let annotationSaveQueue = Promise.resolve()
const isNavigationLoading = computed(
  () => isSwitchingImage.value || isAnnotationLoading.value || isAnnotationSaving.value,
)
const isNavigationDisabled = computed(
  () =>
    isSwitchingImage.value ||
    isAnnotationLoading.value ||
    isAnnotationSaving.value ||
    !isAnnotationLoaded.value,
)

const wrapperSize = ref({ width: 500, height: 500 })

const OriginalImageSize = ref({ width: 0, height: 0 })

const drawerRef = ref<InstanceType<typeof ImageRectDrawer>>()

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const waitForDrawableWrapperSize = async () => {
  for (let index = 0; index < 10; index++) {
    await nextTick()

    const size = drawerRef.value?.getWrapperSize()
    if (size?.width && size.height) {
      wrapperSize.value = size
      lastWrapperSize.value = { ...size }
      return
    }

    await sleep(30)
  }
}

const getTaskDimensionType = async () => {
  const res = await getTask(taskName.value)
  canManage.value = res.can_manage
  typeConfigs.value = res.categories.map((c) => ({
    id: c.id,
    label: c.name,
    color: ANNOTATION_COLOR,
    description: c.supercategory ?? '',
  }))
  if (currentTypeId.value === undefined && typeConfigs.value.length > 0) {
    currentTypeId.value = typeConfigs.value[0]!.id
  }
}

const getCurrentTypeLabel = (): string => {
  if (currentTypeId.value === undefined) return '未选择'
  const type = typeConfigs.value.find((t) => t.id === currentTypeId.value)
  return type?.label || '未知'
}

const toggleType = (id: string | number) => {
  if (currentTypeId.value === id) {
    currentTypeId.value = undefined
  } else {
    currentTypeId.value = id
  }
}

const getRectColor = (rect: RectAnnotation): string => {
  const type = typeConfigs.value.find((t) => t.id === rect.typeId)
  return type?.color || ANNOTATION_COLOR
}

const getTypeLabel = (typeId: string | number): string => {
  const type = typeConfigs.value.find((t) => t.id === typeId)
  return type?.label || String(typeId)
}

const formatRectValue = (value: number): number => Math.round(value)

const initSam3 = () => {
  if (samWs.value) {
    samWs.value.close()
  }

  samPoints.value = []
  samBboxes.value = []
  samStatus.value = 'connecting'
  samWs.value = new WebSocket(WS_BASE_URL)

  samWs.value.onopen = () => {
    if (!imageS3Key || !samWs.value) return
    samWs.value.send(
      JSON.stringify({
        action: 'init',
        s3_key: imageS3Key,
      }),
    )
  }

  samWs.value.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.status === 'loading' || msg.status === 'predicting') {
      samStatus.value = 'processing'
      return
    }

    if (msg.action === 'init') {
      if (msg.success) {
        samStatus.value = 'ready'
        console.log('[检测标注] SAM3 初始化成功:', imageS3Key)
      } else {
        console.error('[检测标注] SAM3 初始化失败:', msg.message)
        samStatus.value = 'disconnected'
      }
      return
    }

    if (msg.action === 'reset') {
      samPoints.value = []
      samBboxes.value = []
      samStatus.value = 'ready'
      drawSmartOverlay()
      return
    }

    if (msg.bboxes) {
      samBboxes.value = msg.bboxes
      samStatus.value = 'ready'
      drawSmartOverlay()
      void applySamBboxes('sam-bbox')
    }
  }

  samWs.value.onerror = (error) => {
    console.error('[检测标注] SAM3 WebSocket 错误:', error)
    samStatus.value = 'disconnected'
  }

  samWs.value.onclose = () => {
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

  if (!OriginalImageSize.value.width || !OriginalImageSize.value.height) {
    clearSmartOverlay()
    return
  }

  const scaleX = img.width / OriginalImageSize.value.width
  const scaleY = img.height / OriginalImageSize.value.height
  ctx.clearRect(0, 0, canvas.width, canvas.height)

  for (const rect of annotations.value) {
    ctx.beginPath()
    ctx.strokeStyle = getRectColor(rect)
    ctx.lineWidth = 2
    ctx.setLineDash([])
    ctx.rect(rect.x, rect.y, rect.width, rect.height)
    ctx.fillStyle = `${getRectColor(rect)}20`
    ctx.fill()
    ctx.stroke()
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

  for (const point of samPoints.value) {
    ctx.beginPath()
    ctx.arc(point.x * scaleX, point.y * scaleY, 6, 0, Math.PI * 2)
    ctx.fillStyle = '#ff0000'
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

const handleSmartClick = (event: MouseEvent) => {
  if (samStatus.value !== 'ready' || !samWs.value) return

  const img = smartImageEl.value
  if (!img) return

  const target = event.target as HTMLElement
  if (target.closest('.smart-info')) return

  const rect = img.getBoundingClientRect()
  const imgX = event.clientX - rect.left
  const imgY = event.clientY - rect.top

  if (imgX < 0 || imgX > img.width || imgY < 0 || imgY > img.height) return

  const scaleX = OriginalImageSize.value.width / img.width
  const scaleY = OriginalImageSize.value.height / img.height
  const origX = imgX * scaleX
  const origY = imgY * scaleY

  samPoints.value.push({ x: origX, y: origY, label: 1 })
  samStatus.value = 'processing'
  samWs.value.send(
    JSON.stringify({
      action: 'bbox',
      x: origX,
      y: origY,
      label: 1,
    }),
  )
}

const samReset = () => {
  if (samWs.value && samStatus.value !== 'disconnected') {
    samWs.value.send(JSON.stringify({ action: 'reset' }))
    return
  }

  samPoints.value = []
  samBboxes.value = []
  drawSmartOverlay()
}

const applySamBboxes = async (reason = 'sam-bbox'): Promise<boolean> => {
  if (samBboxes.value.length === 0 || currentTypeId.value === undefined) return false
  if (!OriginalImageSize.value.width || !OriginalImageSize.value.height) return false

  const img = smartImageEl.value
  const displayWidth = img?.width || wrapperSize.value.width
  const displayHeight = img?.height || wrapperSize.value.height
  if (!displayWidth || !displayHeight) return false

  const displayScaleX = displayWidth / OriginalImageSize.value.width
  const displayScaleY = displayHeight / OriginalImageSize.value.height

  const newRects = samBboxes.value
    .map((box): RectAnnotation | null => {
      const [x, y, width, height] = box.bbox as [number, number, number, number]
      if (!width || !height) return null
      return {
        id: `sam_box_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        x: x * displayScaleX,
        y: y * displayScaleY,
        width: width * displayScaleX,
        height: height * displayScaleY,
        typeId: currentTypeId.value!,
        label: getCurrentTypeLabel(),
      }
    })
    .filter((rect): rect is RectAnnotation => rect !== null)

  if (newRects.length === 0) return false

  annotations.value = [...annotations.value, ...newRects]
  markCurrentImageEdited()
  await queueSaveCurrentAnnotation(reason)
  samReset()
  await nextTick()
  drawSmartOverlay()
  return true
}

const onSmartImageLoad = () => {
  const img = smartImageEl.value
  if (img?.width && img.height) {
    handleWrapperResize({ width: img.width, height: img.height })
  }
  nextTick(() => drawSmartOverlay())
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

const loadAnnotation = async () => {
  try {
    const res = await getAnnotation(Number(imageId))
    annotation = res
    const height = res.images[0]?.height
    const width = res.images[0]?.width
    OriginalImageSize.value = {
      width: width ?? 0,
      height: height ?? 0,
    }
    const parsedAnnotations = res.annotations
      .map(cocoToRectAnnotation)
      .filter((a): a is RectAnnotation => a !== null)
    annotations.value = parsedAnnotations
    console.log(
      `[检测标注] 查询标注完成 imageId=${imageId}, 接口数量=${res.annotations.length}, 可显示数量=${parsedAnnotations.length}`,
    )
    if (res.annotations.length > 0 && parsedAnnotations.length === 0) {
      console.warn('[检测标注] 接口返回了标注，但前端未能转换成可显示标注', {
        imageId,
        annotations: res.annotations,
        wrapperSize: wrapperSize.value,
        originalImageSize: OriginalImageSize.value,
        typeConfigs: typeConfigs.value,
      })
    }
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
    isAnnotationLoaded.value = true
  } finally {
    isAnnotationLoading.value = false
  }
}

const markCurrentImageEdited = () => {
  hasUserEditedCurrentImage.value = true
  annotationChangeVersion.value += 1
}

const UpDateAnnotation = async (reason = 'manual') => {
  if (!isAnnotationLoaded.value) {
    throw new Error('ANNOTATION_NOT_LOADED')
  }

  if (!hasUserEditedCurrentImage.value) {
    console.log(`[检测标注] 当前图片未修改，跳过保存 imageId=${imageId}`)
    return
  }

  const image_id = Number(imageId)
  const cocoAnnotations: CocoAnnotation[] = annotations.value.map((rect, index) =>
    rectToCocoAnnotation(rect, image_id, index),
  )
  const savedVersion = annotationChangeVersion.value
  console.log(
    `[检测标注] 保存标注 reason=${reason}, imageId=${image_id}, 数量=${cocoAnnotations.length}`,
  )
  const updatePayload: UpdateAnnotationRequest = {
    image_id,
    cocoAnnotations,
  }
  await updateAnnotation(updatePayload)
  if (annotationChangeVersion.value === savedVersion) {
    hasUserEditedCurrentImage.value = false
  }
  console.log(`[检测标注] 标注更新成功 reason=${reason}, imageId=${image_id}`)
}

const queueSaveCurrentAnnotation = (reason: string) => {
  annotationSaveQueue = annotationSaveQueue
    .catch(() => undefined)
    .then(async () => {
      isAnnotationSaving.value = true
      try {
        await UpDateAnnotation(reason)
      } catch (error) {
        console.error(`[检测标注] 自动保存失败 reason=${reason}:`, error)
        snackbar.showSnackbar('自动保存标注失败，请稍后重试', 'error')
      } finally {
        isAnnotationSaving.value = false
      }
    })

  return annotationSaveQueue
}

const cocoToRectAnnotation = (annotation: CocoAnnotation): RectAnnotation | null => {
  const bbox = annotation.bbox
  if (!bbox || bbox.length !== 4) return null

  const [imgX, imgY, imgW, imgH] = bbox as [number, number, number, number]
  const wrapperWidth = wrapperSize.value.width
  const wrapperHeight = wrapperSize.value.height
  const originalWidth = OriginalImageSize.value.width
  const originalHeight = OriginalImageSize.value.height

  if (!wrapperWidth || !wrapperHeight || !originalWidth || !originalHeight) {
    return null
  }

  const scaleX = wrapperWidth / originalWidth
  const scaleY = wrapperHeight / originalHeight

  const x = imgX * scaleX
  const y = imgY * scaleY
  const width = imgW * scaleX
  const height = imgH * scaleY

  const typeConfig =
    typeConfigs.value.find((config) => Number(config.id) === annotation.category_id) ??
    typeConfigs.value[annotation.category_id]
  if (!typeConfig) return null
  return {
    id: annotation.id,
    x,
    y,
    width,
    height,
    typeId: typeConfig.id,
    label: typeConfig.label,
  }
}

const rectToCocoAnnotation = (
  rect: RectAnnotation,
  imageIdNum: number,
  index: number,
): CocoAnnotation => {
  const { x, y, width, height, typeId } = rect
  const wrapperWidth = wrapperSize.value.width
  const wrapperHeight = wrapperSize.value.height
  const originalWidth = OriginalImageSize.value.width
  const originalHeight = OriginalImageSize.value.height

  if (!wrapperWidth || !wrapperHeight || !originalWidth || !originalHeight) {
    return {
      id: index,
      image_id: imageIdNum,
      category_id: -1,
      bbox: [0, 0, 0, 0],
      iscrowd: 0,
      area: 0,
    }
  }

  const scaleX = originalWidth / wrapperWidth
  const scaleY = originalHeight / wrapperHeight
  const imgX = x * scaleX
  const imgY = y * scaleY
  const imgW = width * scaleX
  const imgH = height * scaleY
  const category_id = Number(typeId)

  return {
    id: index,
    image_id: imageIdNum,
    category_id,
    bbox: [imgX, imgY, imgW, imgH],
    iscrowd: 0,
    area: imgW * imgH,
  }
}

const handleRectComplete = (rect: RectAnnotation) => {
  console.log('新标注完成:', rect)
  rect.id = rect.id || `rect_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

const handleRectUpdate = (rects: RectAnnotation[]) => {
  annotations.value = rects
  markCurrentImageEdited()
  void queueSaveCurrentAnnotation('draw')
}

const handleRectClick = (rect: RectAnnotation, event: MouseEvent) => {
  activeAnnotation.value = rect
  console.log('点击标注:', rect)
}

const highlightAnnotation = (rect: RectAnnotation) => {
  activeAnnotation.value = rect
}

const removeAnnotation = (id: string | number) => {
  const index = annotations.value.findIndex((r) => r.id === id)
  if (index !== -1) {
    annotations.value = annotations.value.filter((r) => r.id !== id)
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
      await applySamBboxes('sam-bbox-before-switch')
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
    annotations.value = []
    activeAnnotation.value = null
    samPoints.value = []
    samBboxes.value = []

    const image = await getImage(targetImage.id)
    imageUrl.value = image.url
    imageS3Key = image.s3_key
    await reloadCurrentImageAnnotation()
    if (mode.value === 'smart') {
      initSam3()
      nextTick(() => drawSmartOverlay())
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

const handleWrapperResize = (size: { width: number; height: number }) => {
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

  annotations.value = annotations.value.map((a) => ({
    ...a,
    x: a.x * scaleX,
    y: a.y * scaleY,
    width: a.width * scaleX,
    height: a.height * scaleY,
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
  a.download = `annotations_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)

  console.log('标注数据已导出', data)
}

onMounted(async () => {
  await resolveImageId()
  await loadImage()
  await getTaskDimensionType()
  await reloadCurrentImageAnnotation()
})

watch(mode, async (newMode, oldMode) => {
  if (newMode === 'smart') {
    initSam3()
    nextTick(() => drawSmartOverlay())
    return
  }

  if (oldMode === 'smart') {
    await applySamBboxes('sam-bbox-before-draw')
    if (samWs.value) samWs.value.close()
    samStatus.value = 'disconnected'
  }
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
  min-height: 75vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-size: 14px;
}

.smart-detect-container {
  position: relative;
  min-height: 100%;
  overflow: auto;
  cursor: crosshair;
}

.smart-image-wrapper {
  position: relative;
  display: inline-block;
  overflow: hidden;
}

.smart-image {
  display: block;
  height: 75vh;
  max-width: 100%;
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
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  color: white;
  background: rgba(0, 0, 0, 0.65);
  border-radius: 999px;
  transform: translateX(-50%);
}

.annotation-card {
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease;
}

.annotation-card-content {
  padding: 10px 11px !important;
}

.annotation-card-heading {
  min-height: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.annotation-index {
  color: var(--studio-ink-tertiary);
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
  font-size: 11px;
}

.annotation-details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}

.annotation-detail-item {
  min-width: 0;
  display: grid;
  gap: 3px;
  padding: 7px 8px;
  background: var(--studio-canvas);
  border: 1px solid var(--studio-hairline);
  border-radius: 6px;
}

.annotation-detail-item span {
  color: var(--studio-ink-tertiary);
  font-size: 10px;
}

.annotation-detail-item code {
  overflow: hidden;
  color: var(--studio-ink-muted);
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
