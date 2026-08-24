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
          v-if="canManage"
          color="secondary"
          variant="tonal"
          size="small"
          prepend-icon="mdi-image-multiple"
          @click="selectFiles"
        >
          选择图片
        </v-btn>
        <v-btn
          v-if="canManage"
          color="secondary"
          variant="tonal"
          size="small"
          prepend-icon="mdi-folder-open"
          @click="selectFolder"
        >
          选择文件夹
        </v-btn>
        <v-btn
          color="primary"
          variant="flat"
          size="small"
          prepend-icon="mdi-pencil"
          @click="handleStartAnnotation"
        >
          {{ canManage ? '开始标注' : '查看标注' }}
        </v-btn>
      </div>

      <div class="stats-section">
        <v-btn
          v-if="canManage"
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
                  v-if="canManage"
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
                  {{ canManage ? '开始标注' : '查看标注' }}
                </v-btn>
                <v-btn
                  v-if="canManage"
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
            :total-visible="5"
            density="compact"
            rounded
          />
          <div class="page-jump-control">
            <span>跳至</span>
            <v-text-field
              v-model="pageJumpInput"
              class="page-jump-input"
              type="text"
              inputmode="numeric"
              density="compact"
              variant="outlined"
              placeholder="页码"
              aria-label="输入要跳转的页码"
              hide-details
              @keydown.enter.prevent="jumpToPage"
            />
            <span>页</span>
            <v-btn
              class="page-jump-button"
              size="small"
              variant="tonal"
              :disabled="!canSubmitPageJump"
              @click="jumpToPage"
            >
              跳转
            </v-btn>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片上传弹窗 -->
    <v-dialog v-model="showPreview" max-width="760" persistent class="upload-dialog">
      <v-card class="upload-card" elevation="0">
        <header class="upload-header">
          <div class="upload-heading">
            <div class="upload-heading-icon">
              <v-icon :icon="uploading ? 'mdi-cloud-upload' : 'mdi-image-multiple'" size="22" />
            </div>
            <div>
              <div class="upload-eyebrow">{{ uploading ? '正在上传' : '准备上传' }}</div>
              <h2>上传任务图片</h2>
              <p>
                {{
                  uploading
                    ? `正在处理第 ${uploadProgress.currentBatch} / ${uploadProgress.totalBatches} 批`
                    : '确认文件后，图片将保存到当前标注任务'
                }}
              </p>
            </div>
          </div>
          <v-btn
            v-if="!uploading"
            icon="mdi-close"
            variant="text"
            size="small"
            aria-label="关闭上传窗口"
            @click="cancelUpload"
          />
        </header>

        <v-card-text class="upload-body">
          <div v-if="uploading" class="upload-progress-view">
            <div class="upload-progress-panel">
              <div class="upload-progress-heading">
                <div>
                  <span class="upload-progress-label">上传进度</span>
                  <strong>
                    第 {{ uploadProgress.currentBatch }} 批，共
                    {{ uploadProgress.currentBatchFiles }} 张
                  </strong>
                </div>
                <span class="upload-progress-percent">{{ uploadPercent }}%</span>
              </div>

              <v-progress-linear
                :model-value="uploadPercent"
                color="primary"
                bg-color="surface-light"
                height="8"
                rounded
              />

              <div class="upload-progress-meta">
                <span>
                  已完成 {{ uploadProgress.completedFiles }} / {{ uploadProgress.totalFiles }} 张
                </span>
                <span>
                  {{ formatFileSize(uploadProgress.uploadedBytes) }} /
                  {{ formatFileSize(uploadProgress.totalBytes) }}
                </span>
              </div>
            </div>

            <div class="upload-progress-note">
              <v-icon icon="mdi-information-outline" size="18" />
              <div>
                <strong>图片正在写入对象存储</strong>
                <span>上传完成前请保持此页面打开，大文件可能需要稍等片刻。</span>
              </div>
            </div>
          </div>

          <div v-else class="upload-preview-view">
            <div class="upload-summary">
              <div class="upload-summary-item">
                <v-icon icon="mdi-image-outline" size="19" />
                <div>
                  <span>图片数量</span>
                  <strong>{{ filePreviews.length }} 张</strong>
                </div>
              </div>
              <div class="upload-summary-item">
                <v-icon icon="mdi-harddisk" size="19" />
                <div>
                  <span>文件总大小</span>
                  <strong>{{ formatFileSize(selectedTotalBytes) }}</strong>
                </div>
              </div>
              <div class="upload-summary-item">
                <v-icon icon="mdi-layers-triple-outline" size="19" />
                <div>
                  <span>上传批次</span>
                  <strong>{{ plannedBatchCount }} 批</strong>
                </div>
              </div>
            </div>

            <div class="upload-batch-hint">
              <v-icon icon="mdi-auto-fix" size="17" />
              系统将按文件数量和大小自动分批，避免大批量上传中断。
            </div>

            <div class="file-preview-header">
              <span>待上传文件</span>
              <span>{{ filePreviews.length }} 项</span>
            </div>
            <div class="file-preview-list">
              <div
                v-for="(file, index) in filePreviews"
                :key="`${file.name}-${index}`"
                class="file-preview-item"
              >
                <div class="file-preview-icon">
                  <v-icon icon="mdi-file-image-outline" size="19" />
                </div>
                <span class="file-preview-name" :title="file.name">{{ file.name }}</span>
                <span class="file-preview-size">{{ formatFileSize(file.size) }}</span>
              </div>
            </div>
          </div>
        </v-card-text>

        <v-card-actions class="upload-actions">
          <template v-if="uploading">
            <span class="upload-action-status">
              <span class="upload-status-dot"></span>
              正在上传，请勿关闭
            </span>
            <v-spacer />
            <v-btn color="primary" variant="tonal" loading disabled>上传中</v-btn>
          </template>
          <template v-else>
            <v-btn variant="text" @click="cancelUpload">取消</v-btn>
            <v-spacer />
            <v-btn
              color="primary"
              variant="flat"
              prepend-icon="mdi-cloud-upload-outline"
              @click="confirmUpload"
            >
              开始上传
            </v-btn>
          </template>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <AppConfirmDialog />
    <AppSnackbar location="top center" />
  </div>
</template>

<script setup lang="ts">
import { getImageList, getTask, uploadImages, deleteImage } from '@/api/services'
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
const canManage = ref(false)
const currentPage = ref(getInitialCurrentPage())
const pageJumpInput = ref<string | number>('')
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
const canSubmitPageJump = computed(() => {
  const rawPage = String(pageJumpInput.value).trim()
  return rawPage.length > 0 && Number.isInteger(Number(rawPage))
})

const jumpToPage = () => {
  const rawPage = String(pageJumpInput.value).trim()
  if (!rawPage) return

  const requestedPage = Number(rawPage)
  if (!Number.isInteger(requestedPage)) return

  const targetPage = Math.min(Math.max(requestedPage, 1), totalPages.value)
  pageJumpInput.value = ''
  if (targetPage !== currentPage.value) {
    currentPage.value = targetPage
  }
}

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
  try {
    canManage.value = (await getTask(taskName.value)).can_manage
  } catch (error) {
    console.error('加载任务权限失败:', error)
  }
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
  pageJumpInput.value = ''
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
const filePreviews = ref<{ name: string; size: number }[]>([])
const uploading = ref(false)
const uploadProgress = ref({
  completedFiles: 0,
  totalFiles: 0,
  uploadedBytes: 0,
  totalBytes: 0,
  currentBatch: 0,
  totalBatches: 0,
  currentBatchFiles: 0,
})
const uploadPercent = computed(() =>
  uploadProgress.value.totalBytes > 0
    ? Math.min(
        100,
        Math.round((uploadProgress.value.uploadedBytes / uploadProgress.value.totalBytes) * 100),
      )
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
  if (fileList.length === 0) {
    snackbar.showSnackbar('没有找到可上传的图片文件', 'warning')
    return
  }
  files.value = fileList
  filePreviews.value = files.value.map((file) => ({ name: file.name, size: file.size }))
  showPreview.value = true
}

const onFolderSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files) {
    showPreviewDialog(Array.from(target.files).filter(isImageFile))
  }
  target.value = ''
}

const onFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files) {
    showPreviewDialog(Array.from(target.files).filter(isImageFile))
  }
  target.value = ''
}

const MAX_BATCH_FILES = 20
const MAX_BATCH_BYTES = 80 * 1024 * 1024

const createUploadBatches = (selectedFiles: File[]) => {
  const batches: File[][] = []
  let currentBatch: File[] = []
  let currentBytes = 0

  selectedFiles.forEach((file) => {
    const exceedsFileCount = currentBatch.length >= MAX_BATCH_FILES
    const exceedsByteLimit = currentBatch.length > 0 && currentBytes + file.size > MAX_BATCH_BYTES

    if (exceedsFileCount || exceedsByteLimit) {
      batches.push(currentBatch)
      currentBatch = []
      currentBytes = 0
    }

    currentBatch.push(file)
    currentBytes += file.size
  })

  if (currentBatch.length > 0) {
    batches.push(currentBatch)
  }

  return batches
}

const formatUploadSize = (bytes: number) => `${(bytes / 1024 / 1024).toFixed(1)} MiB`
const selectedTotalBytes = computed(() => files.value.reduce((total, file) => total + file.size, 0))
const plannedBatchCount = computed(() => createUploadBatches(files.value).length)

const confirmUpload = async () => {
  if (!files.value.length) return
  uploading.value = true
  const batches = createUploadBatches(files.value)
  const totalBytes = files.value.reduce((total, file) => total + file.size, 0)
  uploadProgress.value = {
    completedFiles: 0,
    totalFiles: files.value.length,
    uploadedBytes: 0,
    totalBytes,
    currentBatch: 1,
    totalBatches: batches.length,
    currentBatchFiles: batches[0]?.length ?? 0,
  }
  console.log(`[上传] 开始上传，共 ${files.value.length} 张图片，拆分为 ${batches.length} 批`)

  let failedCount = 0
  let completedCount = 0
  let completedBytes = 0
  for (const [batchIndex, batch] of batches.entries()) {
    const batchNum = batchIndex + 1
    const batchBytes = batch.reduce((total, file) => total + file.size, 0)
    const completedBytesBeforeBatch = completedBytes
    uploadProgress.value.currentBatch = batchNum
    uploadProgress.value.currentBatchFiles = batch.length
    console.log(
      `[上传] 第 ${batchNum}/${batches.length} 批，${batch.length} 张，${formatUploadSize(batchBytes)}`,
    )
    try {
      await uploadImages(taskName.value, batch, (loaded, requestTotal) => {
        const batchRatio =
          requestTotal && requestTotal > 0 ? loaded / requestTotal : loaded / batchBytes
        const uploadedBatchBytes = Math.min(batchBytes, batchBytes * batchRatio)
        uploadProgress.value.uploadedBytes = Math.min(
          totalBytes,
          completedBytesBeforeBatch + uploadedBatchBytes,
        )
      })
    } catch (error) {
      failedCount++
      console.error(`[上传] 第 ${batchNum} 批上传失败:`, error)
    }
    completedCount += batch.length
    completedBytes += batchBytes
    uploadProgress.value.completedFiles = completedCount
    uploadProgress.value.uploadedBytes = completedBytes
  }

  uploading.value = false
  showPreview.value = false

  if (failedCount > 0) {
    console.error(`[上传] 完成，${failedCount} 批失败`)
    snackbar.showSnackbar(`上传完成，但有 ${failedCount} 批失败，请检查后重试`, 'error')
  } else {
    console.log('[上传] 全部上传成功')
    snackbar.showSnackbar(`已成功上传 ${files.value.length} 张图片`, 'success')
  }

  files.value = []
  filePreviews.value = []
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
  gap: 12px;
  padding: 14px;
}

.task-detail-top {
  flex: 0 0 auto;
  background: rgb(var(--v-theme-surface));
  padding: 10px 12px;
  border: 1px solid var(--studio-hairline);
  border-radius: 10px;
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
  border: 1px solid var(--studio-hairline);
  border-radius: 10px;
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
  background: rgba(var(--v-theme-success), 0.045);
}

.row-selected {
  background: rgba(var(--v-theme-primary), 0.14) !important;
}

.row-selected.row-annotated {
  background: rgba(var(--v-theme-primary), 0.17) !important;
}

.pagination-wrapper {
  flex: 0 0 auto;
  padding: 6px 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.page-jump-control {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 6px;
  color: rgba(var(--v-theme-on-surface), 0.68);
  font-size: 13px;
  white-space: nowrap;
}

.page-jump-input {
  width: 84px;
  flex: 0 0 84px;
}

.page-jump-input :deep(.v-field),
.page-jump-input :deep(.v-field__input) {
  min-height: 34px;
}

.page-jump-input :deep(.v-field__input) {
  padding-inline: 10px;
  padding-top: 0;
  padding-bottom: 0;
  text-align: center;
}

.page-jump-button {
  min-width: 52px;
}

.upload-card {
  overflow: hidden;
  color: var(--studio-ink);
  background: var(--studio-surface-1) !important;
  border: 1px solid var(--studio-hairline-strong);
  border-radius: 14px !important;
}

.upload-header {
  min-height: 88px;
  padding: 18px 20px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  background: var(--studio-surface-1);
  border-bottom: 1px solid var(--studio-hairline);
}

.upload-heading {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  gap: 13px;
}

.upload-heading-icon {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  display: grid;
  place-items: center;
  color: var(--studio-primary-hover);
  background: rgba(94, 106, 210, 0.12);
  border: 1px solid rgba(94, 106, 210, 0.24);
  border-radius: 10px;
}

.upload-eyebrow {
  margin-bottom: 2px;
  color: var(--studio-primary-hover);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.upload-heading h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 650;
  line-height: 1.35;
}

.upload-heading p {
  margin: 4px 0 0;
  color: var(--studio-ink-subtle);
  font-size: 12px;
}

.upload-body {
  padding: 18px 20px 20px !important;
}

.upload-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.upload-summary-item {
  min-width: 0;
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--studio-ink-subtle);
  background: var(--studio-surface-2);
  border: 1px solid var(--studio-hairline);
  border-radius: 9px;
}

.upload-summary-item div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.upload-summary-item span {
  font-size: 11px;
}

.upload-summary-item strong {
  overflow: hidden;
  color: var(--studio-ink);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-batch-hint {
  margin: 12px 0 16px;
  padding: 9px 11px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--studio-ink-subtle);
  font-size: 12px;
  background: rgba(94, 106, 210, 0.07);
  border: 1px solid rgba(94, 106, 210, 0.16);
  border-radius: 8px;
}

.file-preview-header {
  margin-bottom: 7px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--studio-ink-subtle);
  font-size: 11px;
  font-weight: 600;
}

.file-preview-list {
  max-height: 280px;
  overflow-y: auto;
  background: var(--studio-canvas);
  border: 1px solid var(--studio-hairline);
  border-radius: 9px;
}

.file-preview-item {
  min-height: 44px;
  padding: 7px 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  border-bottom: 1px solid var(--studio-hairline);
}

.file-preview-item:last-child {
  border-bottom: 0;
}

.file-preview-item:hover {
  background: var(--studio-surface-2);
}

.file-preview-icon {
  width: 30px;
  height: 30px;
  flex: 0 0 30px;
  display: grid;
  place-items: center;
  color: var(--studio-primary-hover);
  background: rgba(94, 106, 210, 0.1);
  border-radius: 7px;
}

.file-preview-name {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: var(--studio-ink-muted);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-preview-size {
  flex: 0 0 auto;
  color: var(--studio-ink-tertiary);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.upload-progress-view {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 14px;
}

.upload-progress-panel {
  padding: 18px;
  background: var(--studio-surface-2);
  border: 1px solid var(--studio-hairline-strong);
  border-radius: 11px;
}

.upload-progress-heading {
  margin-bottom: 14px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.upload-progress-heading > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.upload-progress-label {
  color: var(--studio-ink-tertiary);
  font-size: 11px;
}

.upload-progress-heading strong {
  color: var(--studio-ink-muted);
  font-size: 13px;
  font-weight: 600;
}

.upload-progress-percent {
  color: var(--studio-ink);
  font-size: 24px;
  font-weight: 650;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.upload-progress-panel :deep(.v-progress-linear__determinate) {
  transition: width 180ms ease;
}

.upload-progress-meta {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--studio-ink-subtle);
  font-size: 11px;
  font-variant-numeric: tabular-nums;
}

.upload-progress-note {
  padding: 12px 14px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: var(--studio-ink-subtle);
  background: var(--studio-canvas);
  border: 1px solid var(--studio-hairline);
  border-radius: 9px;
}

.upload-progress-note div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.upload-progress-note strong {
  color: var(--studio-ink-muted);
  font-size: 12px;
  font-weight: 600;
}

.upload-progress-note span {
  font-size: 11px;
}

.upload-actions {
  min-height: 62px;
  padding: 12px 20px !important;
  background: var(--studio-surface-1);
  border-top: 1px solid var(--studio-hairline);
}

.upload-action-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--studio-ink-subtle);
  font-size: 12px;
}

.upload-status-dot {
  width: 7px;
  height: 7px;
  background: var(--studio-primary-hover);
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(94, 106, 210, 0.12);
  animation: upload-pulse 1.4s ease-in-out infinite;
}

@keyframes upload-pulse {
  50% {
    opacity: 0.45;
  }
}

@media (max-width: 600px) {
  .upload-header,
  .upload-body {
    padding-right: 14px !important;
    padding-left: 14px !important;
  }

  .upload-summary {
    grid-template-columns: 1fr;
  }

  .upload-progress-meta {
    flex-direction: column;
    gap: 3px;
  }
}
</style>
