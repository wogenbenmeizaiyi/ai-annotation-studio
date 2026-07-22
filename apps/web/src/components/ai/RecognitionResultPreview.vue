<template>
  <div class="recognition-result-preview">
    <div class="preview-stage">
      <div v-if="imageLoadError" class="image-error">图片加载失败，无法绘制识别结果。</div>
      <div v-else class="image-canvas">
        <img
          ref="previewImage"
          :src="result.url"
          :alt="imageInfo.file_name"
          referrerpolicy="no-referrer"
          @error="handleImageError"
          @load="handleImageLoad"
        />
        <svg
          class="annotation-overlay"
          :viewBox="`0 0 ${imageInfo.width} ${imageInfo.height}`"
          aria-label="识别标注预览"
        >
          <g v-for="annotation in visibleAnnotations" :key="annotation.id">
            <polygon
              v-for="(segmentation, index) in getSegmentationPolygons(annotation.segmentation)"
              :key="`${annotation.id}-polygon-${index}`"
              :points="toPolygonPoints(segmentation)"
              :fill="getAnnotationFill(annotation.category_id)"
              :stroke="getAnnotationColor(annotation.category_id)"
              stroke-width="2.5"
              vector-effect="non-scaling-stroke"
              stroke-linejoin="round"
            />
            <rect
              v-if="hasBbox(annotation)"
              :x="annotation.bbox[0]"
              :y="annotation.bbox[1]"
              :width="annotation.bbox[2]"
              :height="annotation.bbox[3]"
              fill="none"
              :stroke="getAnnotationColor(annotation.category_id)"
              stroke-width="2.5"
              vector-effect="non-scaling-stroke"
            />
            <g v-if="hasBbox(annotation)" class="annotation-label">
              <rect
                :x="annotation.bbox[0]"
                :y="getLabelTop(annotation)"
                :width="getLabelWidth(annotation)"
                :height="labelHeight"
                :fill="getAnnotationColor(annotation.category_id)"
                :rx="2 * overlayUnitScale"
              />
              <text
                :x="annotation.bbox[0] + 5 * overlayUnitScale"
                :y="getLabelTextY(annotation)"
                fill="#ffffff"
                :font-size="labelFontSize"
              >
                {{ getCategoryName(annotation.category_id) }} {{ formatScore(annotation.score) }}
              </text>
            </g>
          </g>
        </svg>
      </div>
    </div>

    <aside class="annotation-summary">
      <div class="summary-heading">
        <span>标注结果</span>
        <v-chip size="small" color="primary" variant="tonal"
          >{{ visibleAnnotations.length }} 个目标</v-chip
        >
      </div>
      <div v-if="visibleAnnotations.length" class="annotation-list">
        <div v-for="annotation in visibleAnnotations" :key="annotation.id" class="annotation-item">
          <span
            class="annotation-color"
            :style="{ backgroundColor: getAnnotationColor(annotation.category_id) }"
          />
          <div class="annotation-main">
            <div class="annotation-name">{{ getCategoryName(annotation.category_id) }}</div>
            <div class="annotation-meta">
              置信度 {{ formatScore(annotation.score) }}
              <span v-if="hasBbox(annotation)"> · 框 {{ formatBbox(annotation.bbox) }} </span>
              <span v-if="getSegmentationPolygons(annotation.segmentation).length">
                · 含分割轮廓</span
              >
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty-annotations">该图片未识别到可绘制标注。</div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import type { AiCocoAnnotation, RecognitionResultItem } from '@/types/ai'

interface Props {
  result: RecognitionResultItem
  minimumScore?: number
}

const props = withDefaults(defineProps<Props>(), {
  minimumScore: 0,
})

const imageLoadError = ref(false)
const previewImage = ref<HTMLImageElement | null>(null)
const overlayUnitScale = ref(1)
const colors = ['#2196f3', '#4caf50', '#ff9800', '#e91e63', '#9c27b0', '#00acc1']
let imageResizeObserver: ResizeObserver | null = null

const imageInfo = computed(() => {
  return (
    props.result.images[0] ?? {
      id: -1,
      file_name: '识别图片',
      width: 1,
      height: 1,
    }
  )
})

const visibleAnnotations = computed(() => {
  const imageId = imageInfo.value.id
  return props.result.annotations.filter(
    (annotation) =>
      (imageId < 0 || annotation.image_id === imageId) && annotation.score >= props.minimumScore,
  )
})

const categoryNames = computed(() => {
  return new Map(props.result.categories.map((category) => [category.id, category.name]))
})

const getCategoryName = (categoryId: number) =>
  categoryNames.value.get(categoryId) ?? `类别 ${categoryId}`

const getAnnotationColor = (categoryId: number) => {
  const color = colors[Math.abs(categoryId) % colors.length] ?? '#2196f3'
  return color
}

const getAnnotationFill = (categoryId: number) => `${getAnnotationColor(categoryId)}40`

const updateOverlayUnitScale = () => {
  const image = previewImage.value
  if (!image || image.clientWidth === 0) return

  overlayUnitScale.value = imageInfo.value.width / image.clientWidth
}

const handleImageLoad = () => {
  imageLoadError.value = false
  imageResizeObserver?.disconnect()
  imageResizeObserver = new ResizeObserver(updateOverlayUnitScale)
  if (previewImage.value) imageResizeObserver.observe(previewImage.value)
  updateOverlayUnitScale()
}

const handleImageError = () => {
  imageResizeObserver?.disconnect()
  imageLoadError.value = true
}

const hasBbox = (annotation: AiCocoAnnotation) => {
  return annotation.bbox.length === 4 && annotation.bbox[2] > 0 && annotation.bbox[3] > 0
}

const getSegmentationPolygons = (segmentation: unknown): number[][] => {
  const collectPolygons = (value: unknown): number[][] => {
    if (!Array.isArray(value)) return []
    if (value.every((point) => typeof point === 'number')) return [value as number[]]
    return value.flatMap(collectPolygons)
  }

  return collectPolygons(segmentation).filter(
    (polygon) =>
      polygon.length >= 6 &&
      polygon.length % 2 === 0 &&
      polygon.every((point) => Number.isFinite(point)),
  )
}

const toPolygonPoints = (segmentation: number[]) => {
  return segmentation
    .reduce<string[]>((points, value, index) => {
      if (index % 2 === 0 && segmentation[index + 1] !== undefined) {
        points.push(`${value},${segmentation[index + 1]}`)
      }
      return points
    }, [])
    .join(' ')
}

const formatScore = (score: number) => `${Math.round(score * 100)}%`

const formatBbox = (bbox: AiCocoAnnotation['bbox']) => {
  return `${Math.round(bbox[0])}, ${Math.round(bbox[1])}, ${Math.round(bbox[2])} x ${Math.round(bbox[3])}`
}

const labelHeight = computed(() => 22 * overlayUnitScale.value)
const labelFontSize = computed(() => 13 * overlayUnitScale.value)

const getLabelWidth = (annotation: AiCocoAnnotation) =>
  Math.max(72, getCategoryName(annotation.category_id).length * 13 + 46) * overlayUnitScale.value

const getLabelTop = (annotation: AiCocoAnnotation) =>
  Math.max(0, annotation.bbox[1] - labelHeight.value)

const getLabelTextY = (annotation: AiCocoAnnotation) =>
  getLabelTop(annotation) + labelHeight.value * 0.7

watch(
  () => props.result.url,
  () => {
    imageResizeObserver?.disconnect()
    overlayUnitScale.value = 1
    imageLoadError.value = false
  },
)

onUnmounted(() => imageResizeObserver?.disconnect())
</script>

<style scoped>
.recognition-result-preview {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  background: rgb(var(--v-theme-surface));
}

.preview-stage {
  min-width: 0;
  min-height: 440px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  overflow: auto;
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.image-canvas {
  position: relative;
  flex: 0 0 auto;
  max-width: 100%;
  line-height: 0;
}

.image-canvas img {
  display: block;
  max-width: 100%;
  max-height: min(66vh, 680px);
  object-fit: contain;
}

.annotation-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}

.annotation-label text {
  font-weight: 600;
}

.annotation-summary {
  min-height: 0;
  padding: 16px;
  overflow-y: auto;
  border-left: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.summary-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: 600;
}

.annotation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.annotation-item {
  display: flex;
  gap: 9px;
  padding: 9px;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
}

.annotation-color {
  width: 4px;
  flex: 0 0 4px;
  border-radius: 2px;
}

.annotation-main {
  min-width: 0;
}

.annotation-name {
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.annotation-meta {
  margin-top: 3px;
  color: rgba(var(--v-theme-on-surface), 0.62);
  font-size: 12px;
  line-height: 1.5;
}

.empty-annotations,
.image-error {
  color: rgba(var(--v-theme-on-surface), 0.62);
  font-size: 14px;
}

@media (max-width: 800px) {
  .recognition-result-preview {
    grid-template-columns: 1fr;
  }

  .preview-stage {
    min-height: 300px;
  }

  .annotation-summary {
    max-height: 260px;
    border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-left: 0;
  }
}
</style>
