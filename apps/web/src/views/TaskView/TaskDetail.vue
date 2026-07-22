<template>
  <div class="task-detail-view">
    <!-- 顶部操作区域 -->
    <div class="task-detail-top">
      <div class="operation-section">
        <input
          type="file"
          accept="image/*"
          multiple
          ref="fileInput"
          style="display: none"
          @change="onFileSelect"
        />
        <input
          type="file"
          webkitdirectory
          multiple
          ref="folderInput"
          style="display: none"
          @change="onFolderSelect"
        />

        <v-btn
          color="success"
          variant="flat"
          size="small"
          prepend-icon="mdi-image-multiple"
          @click="selectFiles"
        >
          选择图片
        </v-btn>
        <v-btn
          color="success"
          variant="flat"
          size="small"
          prepend-icon="mdi-folder-open"
          @click="selectFolder"
        >
          选择文件夹
        </v-btn>
        <v-btn
          color="success"
          variant="flat"
          size="small"
          prepend-icon="mdi-pencil"
          @click="handleStartAnnotation"
        >
          开始标注
        </v-btn>
      </div>

      <div class="stats-section">
        <v-btn
          color="error"
          variant="tonal"
          size="small"
          prepend-icon="mdi-delete"
          :disabled="selectedImageIds.length === 0"
          @click="handleBatchDeleteImages"
        >
          批量删除
          <span v-if="selectedImageIds.length > 0">({{ selectedImageIds.length }})</span>
        </v-btn>
        <v-chip variant="tonal" color="primary" class="mx-1">
          <v-icon start icon="mdi-image" size="small" />
          {{ totalImages }} 图片总数
        </v-chip>
        <v-chip variant="tonal" color="success" class="mx-1">
          <v-icon start icon="mdi-check-circle" size="small" />
          {{ annotatedCount }} 已标注
        </v-chip>
        <v-chip variant="tonal" color="warning" class="mx-1">
          <v-icon start icon="mdi-clock-outline" size="small" />
          {{ pendingCount }} 未标注
        </v-chip>
      </div>
    </div>

    <!-- 底部表格区域 -->
    <div class="task-detail-bottom">
      <div
        ref="tableWrapperRef"
        class="table-wrapper"
        tabindex="0"
        @click="handleTableWrapperClick"
      >
        <v-table>
          <thead>
            <tr>
              <th class="col-select"></th>
              <th class="col-index">序号</th>
              <th class="col-preview">图片预览</th>
              <th class="col-name">文件名</th>
              <th class="col-size">大小</th>
              <th class="col-status">状态</th>
              <th class="col-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(item, index) in paginatedImages"
              :key="item.id"
              :class="{
                'row-annotated': item.annotated,
                'row-selected': isImageSelected(item.id),
              }"
              @click.stop="handleImageRowClick($event, item, index)"
            >
              <td class="col-select text-center">
                <v-checkbox-btn
                  :model-value="isImageSelected(item.id)"
                  density="compact"
                  color="primary"
                  @click.stop="handleImageRowClick($event, item, index)"
                />
              </td>
              <td class="col-index text-center">{{ (currentPage - 1) * pageSize + index + 1 }}</td>
              <td class="col-preview">
                <div class="image-preview">
                  <img
                    :src="item.url"
                    :alt="item.fileName"
                    class="preview-img"
                    @error="onImageError(item)"
                    @load="onImageLoad(item)"
                  />
                  <div v-if="!item.loaded" class="preview-placeholder">加载中...</div>
                </div>
              </td>
              <td class="col-name">{{ item.fileName }}</td>
              <td class="col-size text-medium-emphasis">
                <div>尺寸：{{ item.width }}x{{ item.height }}</div>
                <div>大小：{{ item.fileSize }}</div>
              </td>
              <td class="col-status">
                <v-chip
                  size="small"
                  :color="item.annotated ? 'success' : 'warning'"
                  variant="tonal"
                >
                  {{ item.annotated ? '已标注' : '未标注' }}
                </v-chip>
              </td>
              <td class="col-actions">
                <v-btn
                  variant="outlined"
                  color="primary"
                  size="x-small"
                  class="mr-2"
                  @click.stop="startAnnotation(item)"
                >
                  开始标注
                </v-btn>
                <v-btn
                  variant="outlined"
                  color="error"
                  size="x-small"
                  @click.stop="handleDeleteImage(item)"
                >
                  删除
                </v-btn>
              </td>
            </tr>
          </tbody>
        </v-table>

        <!-- 分页组件 -->
        <div v-if="totalPages > 1" class="pagination-wrapper">
          <v-pagination
            v-model="currentPage"
            :length="totalPages"
            :total-visible="7"
            density="comfortable"
            rounded
          />
        </div>
      </div>
    </div>

    <!-- 文件预览弹窗 -->
    <v-dialog v-model="showPreview" max-width="800" persistent>
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <span v-if="uploading">
            上传中 {{ uploadProgress.done }} / {{ uploadProgress.total }}
          </span>
          <span v-else>选中 {{ filePreviews.length }} 张图片，确认上传？</span>
          <v-btn
            v-if="!uploading"
            icon="mdi-close"
            variant="text"
            size="small"
            @click="cancelUpload"
          />
        </v-card-title>

        <v-divider />

        <v-card-text>
          <div v-if="uploading" class="text-center py-4">
            <v-progress-linear :model-value="uploadPercent" color="success" height="12" rounded />
            <div class="text-body-2 text-medium-emphasis mt-2">
              {{ uploadPercent }}% ({{ uploadProgress.done }} / {{ uploadProgress.total }})
            </div>
          </div>
          <div v-else class="file-preview-list">
            <div v-for="(file, index) in filePreviews" :key="index" class="file-preview-item">
              <v-icon icon="mdi-file-image" size="small" class="mr-2" />
              {{ file.name }}
            </div>
          </div>
        </v-card-text>

        <v-divider />

        <v-card-actions class="pa-4">
          <v-btn variant="outlined" :disabled="uploading" @click="cancelUpload">取消</v-btn>
          <v-spacer />
          <v-btn color="success" :disabled="uploading" :loading="uploading" @click="confirmUpload">
            {{ uploading ? '上传中...' : '确认上传' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <AppConfirmDialog />
    <AppSnackbar location="top center" />
  </div>
</template>

<script setup lang="ts">
import { getImageList, uploadImages, deleteImage } from '@/api/services'
import { ref, computed, nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'
import AppConfirmDialog from '@/components/common/AppConfirmDialog.vue'
import AppSnackbar from '@/components/common/AppSnackbar.vue'

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()

const route = useRoute()
const router = useRouter()

interface Props {
  id: string
}
const props = defineProps<Props>()
const taskName = computed(() => decodeURIComponent(props.id))
const detectionType = computed(() => {
  const type = Array.isArray(route.query.type) ? route.query.type[0] : route.query.type
  return type === 'segmentation' ? 'segmentation' : 'detection'
})

const pageStorageKey = computed(() => `task-detail-page:${taskName.value}`)

const getPositiveQueryNumber = (value: unknown, fallback: number) => {
  const rawValue = Array.isArray(value) ? value[0] : value
  const parsed = Number(rawValue)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback
}

const getStoredCurrentPage = () => {
  const storedPage = sessionStorage.getItem(pageStorageKey.value)
  return getPositiveQueryNumber(storedPage, 1)
}

const getInitialCurrentPage = () => {
  return getPositiveQueryNumber(route.query.page, getStoredCurrentPage())
}

const TABLE_HEADER_HEIGHT = 40
const TABLE_ROW_HEIGHT = 76
const PAGINATION_HEIGHT = 56
const TABLE_LAYOUT_BUFFER = 8

const pageSize = ref(7)
const currentPage = ref(getInitialCurrentPage())
const totalImagesCount = ref(0)
const annotatedImagesCount = ref(0)
const tableWrapperRef = ref<HTMLElement | null>(null)
let resizeObserver: ResizeObserver | null = null

interface ImageNamePage {
  list: ServerImageItem[]
  page: number
  page_size: number
  total: number
  annotated_count: number
  total_pages: number
}

interface ServerImageItem {
  id: number
  file_name: string
  url: string
  is_annotated: boolean
  width: number
  height: number
  file_size: number
}

interface ImageItem {
  id: string
  url: string
  annotated: boolean
  fileName: string
  fileSize: string
  width: number
  height: number
  loaded?: boolean
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const source = ref<ImageItem[]>([])
const selectedImageIds = ref<string[]>([])
const lastSelectedImageId = ref<string | null>(null)

const isImageSelected = (id: string) => selectedImageIds.value.includes(id)

const setImageSelected = (id: string, selected: boolean) => {
  if (selected) {
    if (!selectedImageIds.value.includes(id)) {
      selectedImageIds.value = [...selectedImageIds.value, id]
    }
    return
  }

  selectedImageIds.value = selectedImageIds.value.filter((selectedId) => selectedId !== id)
}

const clearImageSelection = () => {
  selectedImageIds.value = []
  lastSelectedImageId.value = null
}

const handleImageRowClick = (event: MouseEvent, item: ImageItem, index: number) => {
  const currentPageItems = paginatedImages.value

  if (event.shiftKey && lastSelectedImageId.value) {
    const startIndex = currentPageItems.findIndex((image) => image.id === lastSelectedImageId.value)
    if (startIndex >= 0) {
      const from = Math.min(startIndex, index)
      const to = Math.max(startIndex, index)
      const rangeIds = currentPageItems.slice(from, to + 1).map((image) => image.id)
      selectedImageIds.value = rangeIds
      return
    }
  }

  setImageSelected(item.id, !isImageSelected(item.id))
  lastSelectedImageId.value = item.id
}

const handleTableWrapperClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement | null
  if (target?.closest('tbody tr')) return
  clearImageSelection()
}

const refreshImagesAfterDelete = async () => {
  await loadImageStats()

  if (currentPage.value > totalPages.value) {
    currentPage.value = Math.max(1, totalPages.value)
    await syncCurrentPageToRoute()
  }

  await loadCurrentPageData()
}

const getImagesByPage = async (name: string, page: number, pageSizeNum: number) => {
  try {
    const response = (await getImageList(name, { page, page_size: pageSizeNum })) as ImageNamePage
    if (!response) return []
    totalImagesCount.value = response.total
    annotatedImagesCount.value = response.annotated_count

    return response.list.map((item: ServerImageItem) => ({
      id: String(item.id),
      url: item.url,
      annotated: item.is_annotated,
      fileName: item.file_name,
      fileSize: formatFileSize(item.file_size),
      width: item.width,
      height: item.height,
    }))
  } catch (error) {
    console.log('报错')
    return []
  }
}

const totalImages = computed(() => totalImagesCount.value)
const annotatedCount = computed(() => annotatedImagesCount.value)
const pendingCount = computed(() =>
  Math.max(0, totalImagesCount.value - annotatedImagesCount.value),
)
const totalPages = computed(() => Math.ceil(totalImagesCount.value / pageSize.value))
const paginatedImages = computed(() => source.value)

const loadCurrentPageData = async () => {
  source.value = await getImagesByPage(taskName.value, currentPage.value, pageSize.value)
  const visibleImageIds = new Set(source.value.map((item) => item.id))
  selectedImageIds.value = selectedImageIds.value.filter((id) => visibleImageIds.has(id))
  if (lastSelectedImageId.value && !visibleImageIds.has(lastSelectedImageId.value)) {
    lastSelectedImageId.value = null
  }
}

const syncCurrentPageToRoute = async () => {
  sessionStorage.setItem(pageStorageKey.value, String(currentPage.value))

  if (String(route.query.page ?? '') === String(currentPage.value)) return

  await router.replace({
    name: 'taskDetail',
    params: {
      id: props.id,
    },
    query: {
      ...route.query,
      page: String(currentPage.value),
    },
  })
}

const loadImageStats = async () => {
  try {
    const response = (await getImageList(taskName.value, {
      page: 1,
      page_size: 1,
    })) as ImageNamePage
    totalImagesCount.value = response.total
    annotatedImagesCount.value = response.annotated_count
  } catch (error) {
    console.error('加载图片统计失败:', error)
  }
}

const calculatePageSize = () => {
  const wrapperHeight = tableWrapperRef.value?.clientHeight ?? 0
  if (!wrapperHeight) return pageSize.value

  const availableRowsHeight =
    wrapperHeight - TABLE_HEADER_HEIGHT - PAGINATION_HEIGHT - TABLE_LAYOUT_BUFFER
  const rows = Math.floor(availableRowsHeight / TABLE_ROW_HEIGHT)
  return rows > 0 ? rows : 1
}

const updatePageSizeByLayout = async () => {
  await nextTick()

  const nextPageSize = calculatePageSize()
  if (nextPageSize === pageSize.value) return false

  pageSize.value = nextPageSize

  await loadCurrentPageData()
  return true
}

onMounted(async () => {
  await syncCurrentPageToRoute()

  await Promise.all([
    (async () => {
      const loadedByLayout = await updatePageSizeByLayout()
      if (!loadedByLayout) {
        await loadCurrentPageData()
      }
    })(),
    loadImageStats(),
  ])

  if (tableWrapperRef.value) {
    resizeObserver = new ResizeObserver(() => {
      void updatePageSizeByLayout()
    })
    resizeObserver.observe(tableWrapperRef.value)
  }
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
})

watch(currentPage, () => {
  loadCurrentPageData()
  void syncCurrentPageToRoute()
})

watch(
  () => route.query.page,
  (page) => {
    const nextPage = getPositiveQueryNumber(page, currentPage.value)
    if (nextPage !== currentPage.value) {
      currentPage.value = nextPage
    }
  },
)

const files = ref<File[]>([])
const folderInput = ref<HTMLInputElement | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const showPreview = ref(false)
const filePreviews = ref<{ name: string }[]>([])
const uploading = ref(false)
const uploadProgress = ref({ done: 0, total: 0 })
const uploadPercent = computed(() =>
  uploadProgress.value.total > 0
    ? Math.round((uploadProgress.value.done / uploadProgress.value.total) * 100)
    : 0,
)

const selectFolder = () => {
  folderInput.value?.click()
}

const selectFiles = () => {
  fileInput.value?.click()
}

const isImageFile = (file: File) => {
  const ext = file.name.toLowerCase().split('.').pop()
  return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'tiff', 'tif'].includes(ext || '')
}

const showPreviewDialog = (fileList: File[]) => {
  files.value = fileList
  filePreviews.value = files.value.map((f) => ({ name: f.name }))
  showPreview.value = true
}

const onFolderSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files) {
    showPreviewDialog(Array.from(target.files).filter(isImageFile))
  }
}

const onFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files) {
    showPreviewDialog(Array.from(target.files))
  }
}

const BATCH_SIZE = 50

const confirmUpload = async () => {
  if (!files.value.length) return
  uploading.value = true
  uploadProgress.value = { done: 0, total: files.value.length }
  console.log(`[上传] 开始上传，共 ${files.value.length} 张图片，每批 ${BATCH_SIZE} 张`)

  let failedCount = 0
  for (let i = 0; i < files.value.length; i += BATCH_SIZE) {
    const batch = files.value.slice(i, i + BATCH_SIZE)
    const batchNum = Math.floor(i / BATCH_SIZE) + 1
    const totalBatches = Math.ceil(files.value.length / BATCH_SIZE)
    console.log(`[上传] 第 ${batchNum}/${totalBatches} 批，${batch.length} 张`)
    try {
      await uploadImages(taskName.value, batch)
    } catch (error) {
      failedCount++
      console.error(`[上传] 第 ${batchNum} 批上传失败:`, error)
    }
    uploadProgress.value.done = Math.min(i + BATCH_SIZE, files.value.length)
  }

  uploading.value = false
  showPreview.value = false

  if (failedCount > 0) {
    console.error(`[上传] 完成，${failedCount} 批失败`)
  } else {
    console.log('[上传] 全部上传成功')
  }

  currentPage.value = 1
  await Promise.all([loadCurrentPageData(), loadImageStats()])
}

const cancelUpload = () => {
  if (uploading.value) return
  showPreview.value = false
  files.value = []
  filePreviews.value = []
}

const handleStartAnnotation = () => {
  const firstPending = source.value.find((img) => !img.annotated)
  if (firstPending) {
    startAnnotation(firstPending)
  } else {
    snackbar.showSnackbar('当前页所有图片都已标注完成', 'info')
  }
}

const startAnnotation = async (item: ImageItem) => {
  await syncCurrentPageToRoute()

  const routeName =
    detectionType.value === 'segmentation' ? 'segmentationAnnotation' : 'detectionAnnotation'
  router.push({
    name: routeName,
    params: {
      taskId: taskName.value,
      imageName: item.fileName,
    },
    query: {
      type: detectionType.value,
      page: String(currentPage.value),
    },
  })
}

const handleDeleteImage = async (item: ImageItem) => {
  const confirmed = await confirmDialog.showConfirm('确认删除', '确定要删除这张图片吗？')
  if (confirmed) {
    try {
      await deleteImage(Number(item.id))
      setImageSelected(item.id, false)
      await refreshImagesAfterDelete()
    } catch (error) {
      console.error(error)
    }
  }
}

const handleBatchDeleteImages = async () => {
  if (selectedImageIds.value.length === 0) return

  const deleteIds = [...selectedImageIds.value]
  const confirmed = await confirmDialog.showConfirm(
    '批量删除',
    `确定要删除选中的 ${deleteIds.length} 张图片吗？`,
  )
  if (!confirmed) return

  try {
    await Promise.all(deleteIds.map((id) => deleteImage(Number(id))))
    clearImageSelection()
    await refreshImagesAfterDelete()
    snackbar.showSnackbar(`已删除 ${deleteIds.length} 张图片`, 'success')
  } catch (error) {
    console.error(error)
    snackbar.showSnackbar('批量删除失败', 'error')
    await refreshImagesAfterDelete()
  }
}

const onImageError = (item: ImageItem) => {
  console.error('图片加载失败:', item.url)
  item.loaded = false
}

const onImageLoad = (item: ImageItem) => {
  item.loaded = true
}
</script>

<style scoped>
.task-detail-view {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: rgb(var(--v-theme-background));
}

.task-detail-top {
  flex: 0 0 auto;
  background: rgb(var(--v-theme-surface));
  padding: 10px 16px;
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.operation-section {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stats-section {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.task-detail-bottom {
  flex: 1;
  min-height: 0;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.table-wrapper {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.table-wrapper :deep(.v-table) {
  flex: 1 1 auto;
  min-height: 0;
}

.table-wrapper :deep(.v-table__wrapper) {
  height: 100%;
  overflow: auto;
}

.table-wrapper :deep(.v-table__wrapper > table) {
  table-layout: fixed;
}

.table-wrapper :deep(tbody tr) {
  cursor: pointer;
  user-select: none;
}

.table-wrapper :deep(tbody tr:hover) {
  background: rgba(var(--v-theme-primary), 0.06);
}

.table-wrapper :deep(th) {
  height: 40px !important;
}

.table-wrapper :deep(td) {
  height: 76px !important;
}

.col-select {
  width: 44px;
}

.col-index {
  width: 60px;
}

.col-preview {
  width: 120px;
  padding: 4px 12px !important;
}

.col-name {
  min-width: 200px;
}

.col-size {
  width: 140px;
  font-size: 13px;
}

.col-status {
  width: 100px;
}

.col-actions {
  width: 180px;
}

.image-preview {
  width: 112px;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  background: rgb(var(--v-theme-background));
}

.preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.preview-placeholder {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.row-annotated {
  background: rgba(var(--v-theme-success), 0.08);
}

.row-selected {
  background: rgba(var(--v-theme-primary), 0.14) !important;
}

.row-selected.row-annotated {
  background: linear-gradient(
    90deg,
    rgba(var(--v-theme-primary), 0.18),
    rgba(var(--v-theme-success), 0.08)
  ) !important;
}

.pagination-wrapper {
  flex: 0 0 auto;
  padding: 6px 12px;
  display: flex;
  justify-content: center;
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.file-preview-list {
  max-height: 300px;
  overflow-y: auto;
}

.file-preview-item {
  display: flex;
  align-items: center;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
