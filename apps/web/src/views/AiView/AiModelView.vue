<template>
  <div class="ai-page">
    <AiManagementNav />

    <div class="ai-page-content">
      <div class="page-toolbar">
        <div class="toolbar-title">
          <h2>模型库</h2>
          <span>维护检测模型及多模态识别提示词</span>
        </div>
        <div class="toolbar-actions">
          <v-select
            v-model="detectionTypeFilter"
            :items="detectionTypeOptions"
            label="模型类型"
            clearable
            hide-details
            density="compact"
            variant="outlined"
            class="type-filter"
          />
          <v-btn variant="tonal" prepend-icon="mdi-plus" @click="openCreateConfigDialog">
            新增模型配置
          </v-btn>
          <v-btn color="primary" prepend-icon="mdi-upload" @click="openUploadDialog"
            >上传模型</v-btn
          >
        </div>
      </div>

      <div class="table-panel">
        <v-progress-linear v-if="loading" indeterminate color="primary" class="table-loading-bar" />
        <v-table fixed-header class="ai-table">
          <thead>
            <tr>
              <th>模型名称</th>
              <th>类型</th>
              <th>所属项目</th>
              <th>提示词</th>
              <th>说明</th>
              <th>更新时间</th>
              <th class="text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in models" :key="model.uuid">
              <td>
                <div class="font-weight-medium">{{ model.name }}</div>
                <div class="resource-id-row">
                  <span class="model-uuid">{{ model.uuid }}</span>
                  <v-tooltip text="复制 ID" location="top">
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        icon="mdi-content-copy"
                        size="x-small"
                        variant="text"
                        class="copy-id-button"
                        @click.stop="copyResourceId(model.uuid, '模型 ID')"
                      />
                    </template>
                  </v-tooltip>
                </div>
              </td>
              <td>
                <v-chip
                  size="small"
                  variant="tonal"
                  :color="getDetectionTypeColor(model.detection_type)"
                >
                  {{ getDetectionTypeLabel(model.detection_type) }}
                </v-chip>
              </td>
              <td>{{ model.project_name || '-' }}</td>
              <td class="text-truncate prompt-text">{{ model.prompt || '-' }}</td>
              <td class="text-truncate description-text">{{ model.description || '-' }}</td>
              <td>{{ formatDate(model.updated_at) }}</td>
              <td class="text-right">
                <v-btn size="small" variant="text" color="primary" @click="openTestDialog(model)">
                  试跑
                </v-btn>
                <v-btn size="small" variant="text" color="primary" @click="openEditDialog(model)">
                  编辑
                </v-btn>
                <v-btn size="small" variant="text" color="error" @click="handleDeleteModel(model)">
                  删除
                </v-btn>
              </td>
            </tr>
            <tr v-if="!loading && models.length === 0">
              <td colspan="7" class="empty-cell">暂无模型配置</td>
            </tr>
          </tbody>
        </v-table>
        <div v-if="page.totalPages > 1" class="pagination-bar">
          <v-pagination
            v-model="page.current"
            :length="page.totalPages"
            :total-visible="7"
            density="compact"
          />
        </div>
      </div>
    </div>

    <v-dialog v-model="showModelDialog" max-width="680" persistent>
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <span>{{ modelDialogTitle }}</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="showModelDialog = false" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-5">
          <v-select
            v-model="modelForm.detectionType"
            :items="dialogDetectionTypeOptions"
            label="识别类型 *"
            variant="outlined"
            density="comfortable"
            :disabled="modelDialogMode === 'edit'"
          />
          <v-file-input
            v-if="modelDialogMode === 'upload' && requiresModelFile"
            v-model="modelFile"
            label="模型文件 *"
            accept=".pt,.pth,.onnx,.engine,.bin"
            prepend-icon="mdi-file-upload-outline"
            variant="outlined"
            density="comfortable"
          />
          <v-text-field
            v-model="modelForm.name"
            label="模型名称 *"
            variant="outlined"
            density="comfortable"
          />
          <v-text-field
            v-if="modelDialogMode !== 'upload' && modelDialogMode !== 'edit' && requiresModelFile"
            v-model="modelForm.modelFile"
            label="模型文件名"
            variant="outlined"
            density="comfortable"
          />
          <v-text-field
            v-if="modelDialogMode !== 'upload' && modelDialogMode !== 'edit' && requiresModelFile"
            v-model="modelForm.storageKey"
            label="S3 存储 Key"
            variant="outlined"
            density="comfortable"
          />
          <v-textarea
            v-if="usesPrompt"
            v-model="modelForm.prompt"
            label="提示词"
            hint="多模态识别时用于描述需要识别的目标"
            variant="outlined"
            density="comfortable"
            rows="2"
          />
          <v-text-field
            v-model="modelForm.projectName"
            label="所属项目"
            variant="outlined"
            density="comfortable"
          />
          <v-textarea
            v-model="modelForm.description"
            label="模型说明"
            rows="3"
            variant="outlined"
            density="comfortable"
            hide-details
          />
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="text" @click="showModelDialog = false">取消</v-btn>
          <v-spacer />
          <v-btn color="primary" :loading="saving" @click="saveModel">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showTestDialog" :max-width="testPreview ? 1280 : 640" persistent scrollable>
      <v-card :class="{ 'test-result-card': testPreview }">
        <v-card-title class="d-flex align-center justify-space-between">
          <span>试跑模型</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="closeTestDialog" />
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-5">
          <div v-if="testModel" class="test-model-summary mb-4">
            <span class="text-medium-emphasis">当前模型：</span>{{ testModel.name }}
          </div>
          <v-file-input
            v-model="testFile"
            label="测试图片 *"
            accept="image/*"
            prepend-icon="mdi-image-outline"
            variant="outlined"
            density="comfortable"
            @update:model-value="handleTestFileChange"
          />
          <v-text-field
            v-model.number="testConfidence"
            label="置信度"
            type="number"
            min="0"
            max="1"
            step="0.05"
            variant="outlined"
            density="comfortable"
            hide-details
          />
          <v-alert v-if="testResult" type="success" variant="tonal" class="mt-4">
            {{
              testPreview ? '识别完成，标注已绘制在测试图片上。' : '请求完成，可查看接口返回结果。'
            }}
          </v-alert>
          <div v-if="testPreview" class="test-preview mt-4">
            <RecognitionResultPreview
              :result="testPreview"
              :minimum-score="effectiveTestConfidence"
            />
            <v-expansion-panels variant="accordion" class="mt-3">
              <v-expansion-panel title="原始 COCO 数据">
                <v-expansion-panel-text>
                  <pre class="json-preview">{{ testResult }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
          <pre v-else-if="testResult" class="json-preview mt-3">{{ testResult }}</pre>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="text" @click="closeTestDialog">关闭</v-btn>
          <v-spacer />
          <v-btn color="primary" :loading="testing" @click="runModelTest">开始试跑</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <AppConfirmDialog />
    <AppSnackbar />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import axios from 'axios'
import {
  createAiModel,
  deleteAiModel,
  getAiModels,
  recognizeModelDirectly,
  updateAiModel,
  uploadAiModel,
} from '@/api/services'
import AiManagementNav from '@/components/ai/AiManagementNav.vue'
import RecognitionResultPreview from '@/components/ai/RecognitionResultPreview.vue'
import AppConfirmDialog from '@/components/common/AppConfirmDialog.vue'
import AppSnackbar from '@/components/common/AppSnackbar.vue'
import { copyText } from '@/composables/useClipboard'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'
import type {
  AiCocoAnnotation,
  AiCocoCategory,
  AiCocoImage,
  AiDetectionType,
  AiModel,
  RecognitionResultItem,
} from '@/types/ai'

type ModelDialogMode = 'create' | 'upload' | 'edit'

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const models = ref<AiModel[]>([])
const detectionTypeFilter = ref<AiDetectionType | null>(null)
const showModelDialog = ref(false)
const showTestDialog = ref(false)
const modelDialogMode = ref<ModelDialogMode>('upload')
const editingModel = ref<AiModel | null>(null)
const modelFile = ref<File | null>(null)
const testModel = ref<AiModel | null>(null)
const testFile = ref<File | null>(null)
const testConfidence = ref(0.5)
const testResult = ref('')
const testPreview = ref<RecognitionResultItem | null>(null)
const testImageUrl = ref('')

const effectiveTestConfidence = computed(() => {
  return Math.min(1, Math.max(0, Number(testConfidence.value) || 0.5))
})
const page = ref({ current: 1, totalPages: 1 })

const detectionTypeOptions = [
  { title: 'YOLO 目标检测', value: 1 },
  { title: 'YOLO 实例分割', value: 2 },
  { title: 'SAM 分割', value: 3 },
  { title: '多模态识别', value: 4 },
]

const uploadModelTypeOptions = [
  { title: 'YOLO 目标检测模型', value: 1 },
  { title: 'YOLO 实例分割模型', value: 2 },
]

const configTypeOptions = [
  { title: 'SAM 智能分割模型', value: 3 },
  { title: '多模态提示词识别', value: 4 },
]

const editableModelTypeOptions = [...uploadModelTypeOptions, ...configTypeOptions]

const createEmptyModelForm = () => ({
  name: '',
  detectionType: 4 as AiDetectionType,
  modelFile: '',
  storageKey: '',
  prompt: '',
  projectName: '通用',
  description: '',
})

const modelForm = reactive(createEmptyModelForm())

const dialogDetectionTypeOptions = computed(() => {
  if (modelDialogMode.value === 'upload') return uploadModelTypeOptions
  return modelDialogMode.value === 'create' ? configTypeOptions : editableModelTypeOptions
})

const requiresModelFile = computed(() => {
  return modelForm.detectionType === 1 || modelForm.detectionType === 2
})

const usesPrompt = computed(() => {
  return modelForm.detectionType === 3 || modelForm.detectionType === 4
})

const modelDialogTitle = computed(() => {
  if (modelDialogMode.value === 'upload') return '上传模型'
  return modelDialogMode.value === 'edit' ? '编辑模型配置' : '新增模型配置'
})

const getErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === 'string') return error
  if (axios.isAxiosError(error)) {
    const responseData = error.response?.data
    if (
      responseData &&
      typeof responseData === 'object' &&
      'message' in responseData &&
      typeof responseData.message === 'string'
    ) {
      return responseData.message
    }
  }
  if (error instanceof Error && error.message) return error.message
  return fallback
}

const copyResourceId = async (id: string, label: string) => {
  try {
    await copyText(id)
    snackbar.showSnackbar(`${label} 已复制`, 'success')
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, `${label} 复制失败`), 'error')
  }
}

const getDetectionTypeLabel = (type: AiDetectionType) => {
  return { 1: '目标检测', 2: '实例分割', 3: 'SAM 分割', 4: '多模态识别' }[type]
}

const getDetectionTypeColor = (type: AiDetectionType) => {
  return { 1: 'primary', 2: 'success', 3: 'secondary', 4: 'warning' }[type]
}

const formatDate = (value: string) => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

const resetModelForm = () => {
  Object.assign(modelForm, createEmptyModelForm())
  modelFile.value = null
  editingModel.value = null
}

const loadModels = async () => {
  loading.value = true
  try {
    const response = await getAiModels({
      page: page.value.current,
      pageSize: 10,
      detection_type: detectionTypeFilter.value ?? undefined,
    })
    models.value = response.items
    page.value.totalPages = Math.max(1, response.totalPages)
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '加载模型列表失败'), 'error')
  } finally {
    loading.value = false
  }
}

const openUploadDialog = () => {
  resetModelForm()
  modelDialogMode.value = 'upload'
  modelForm.detectionType = 1
  showModelDialog.value = true
}

const openCreateConfigDialog = () => {
  resetModelForm()
  modelDialogMode.value = 'create'
  modelForm.detectionType = 4
  showModelDialog.value = true
}

const openEditDialog = (model: AiModel) => {
  editingModel.value = model
  modelDialogMode.value = 'edit'
  modelFile.value = null
  Object.assign(modelForm, {
    name: model.name,
    detectionType: model.detection_type,
    modelFile: model.model_file ?? '',
    storageKey: model.storage_key ?? '',
    prompt: model.prompt ?? '',
    projectName: model.project_name ?? '通用',
    description: model.description ?? '',
  })
  showModelDialog.value = true
}

const saveModel = async () => {
  if (!modelForm.name.trim()) {
    snackbar.showSnackbar('请输入模型名称', 'warning')
    return
  }

  if (modelDialogMode.value === 'upload' && !modelFile.value) {
    snackbar.showSnackbar('请选择模型文件', 'warning')
    return
  }

  saving.value = true
  try {
    const baseData = {
      name: modelForm.name.trim(),
      detection_type: modelForm.detectionType,
      project_name: modelForm.projectName.trim() || undefined,
      description: modelForm.description.trim() || undefined,
    }
    const modelStorageData =
      modelDialogMode.value !== 'edit' && requiresModelFile.value
        ? {
            model_file: modelForm.modelFile.trim() || undefined,
            storage_key: modelForm.storageKey.trim() || undefined,
          }
        : {}
    const promptData = usesPrompt.value ? { prompt: modelForm.prompt.trim() || undefined } : {}

    if (modelDialogMode.value === 'upload' && modelFile.value) {
      await uploadAiModel({ file: modelFile.value, ...baseData })
    } else if (modelDialogMode.value === 'edit' && editingModel.value) {
      await updateAiModel(editingModel.value.uuid, {
        ...baseData,
        ...modelStorageData,
        ...promptData,
      })
    } else {
      await createAiModel({
        ...baseData,
        ...modelStorageData,
        ...promptData,
      })
    }

    showModelDialog.value = false
    snackbar.showSnackbar('模型配置已保存', 'success')
    await loadModels()
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '保存模型配置失败'), 'error')
  } finally {
    saving.value = false
  }
}

const handleDeleteModel = async (model: AiModel) => {
  const confirmed = await confirmDialog.showConfirm('删除模型', `确定要删除“${model.name}”吗？`)
  if (!confirmed) return

  try {
    await deleteAiModel(model.uuid)
    snackbar.showSnackbar('模型已删除', 'success')
    await loadModels()
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '删除模型失败'), 'error')
  }
}

const openTestDialog = (model: AiModel) => {
  releaseTestImageUrl()
  testModel.value = model
  testFile.value = null
  testConfidence.value = 0.5
  testResult.value = ''
  testPreview.value = null
  showTestDialog.value = true
}

const closeTestDialog = () => {
  showTestDialog.value = false
  testResult.value = ''
  testPreview.value = null
  releaseTestImageUrl()
}

const releaseTestImageUrl = () => {
  if (testImageUrl.value) {
    URL.revokeObjectURL(testImageUrl.value)
    testImageUrl.value = ''
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === 'object' && value !== null
}

const getCocoPayload = (result: unknown) => {
  const root = isRecord(result) ? result : null
  const directCandidates = [result, root?.data, root?.result, root?.coco]
  const candidates = directCandidates.flatMap((candidate) => {
    if (!isRecord(candidate) || !Array.isArray(candidate.results)) return [candidate]
    return [candidate, ...candidate.results]
  })
  return candidates.find((candidate) => {
    if (!isRecord(candidate)) return false
    return Array.isArray(candidate.annotations) && Array.isArray(candidate.categories)
  }) as Record<string, unknown> | undefined
}

const getTestImageInfo = (file: File) => {
  return new Promise<{ url: string; width: number; height: number }>((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => {
      resolve({ url, width: image.naturalWidth, height: image.naturalHeight })
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('测试图片无法读取'))
    }
    image.src = url
  })
}

const buildTestPreview = (
  file: File,
  imageInfo: Awaited<ReturnType<typeof getTestImageInfo>>,
  payload?: Record<string, unknown>,
) => {
  const images = Array.isArray(payload?.images) ? (payload.images as AiCocoImage[]) : []
  const annotations = (payload?.annotations as AiCocoAnnotation[] | undefined) ?? []
  const categories = (payload?.categories as AiCocoCategory[] | undefined) ?? []
  const fallbackImageId = annotations[0]?.image_id ?? 1
  return {
    image_index: 0,
    url: imageInfo.url,
    service: '',
    detection_type: '',
    count: annotations.length,
    image_key: '',
    coco_key: '',
    images:
      images.length > 0
        ? images
        : [
            {
              id: fallbackImageId,
              file_name: file.name,
              width: imageInfo.width,
              height: imageInfo.height,
            },
          ],
    annotations,
    categories,
    created_at: '',
  } satisfies RecognitionResultItem
}

const handleTestFileChange = async (value: File | File[] | null) => {
  const file = Array.isArray(value) ? (value[0] ?? null) : value
  testFile.value = file
  testResult.value = ''
  testPreview.value = null
  releaseTestImageUrl()
  if (!file) return

  try {
    const imageInfo = await getTestImageInfo(file)
    if (testFile.value !== file) {
      URL.revokeObjectURL(imageInfo.url)
      return
    }

    testImageUrl.value = imageInfo.url
    testPreview.value = buildTestPreview(file, imageInfo)
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '测试图片无法读取'), 'error')
  }
}

const createTestPreview = async (result: unknown, file: File) => {
  const payload = getCocoPayload(result)
  if (!payload) return null

  releaseTestImageUrl()
  const imageInfo = await getTestImageInfo(file)
  testImageUrl.value = imageInfo.url
  return buildTestPreview(file, imageInfo, payload)
}

const runModelTest = async () => {
  if (!testModel.value || !testFile.value) {
    snackbar.showSnackbar('请选择测试图片', 'warning')
    return
  }

  const model = testModel.value
  const file = testFile.value
  testing.value = true
  try {
    const result = await recognizeModelDirectly({
      file,
      model_uuid: model.uuid,
      confidence: effectiveTestConfidence.value,
    })
    if (testFile.value !== file || testModel.value?.uuid !== model.uuid) return

    testResult.value = JSON.stringify(result, null, 2)
    testPreview.value = await createTestPreview(result, file)
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '模型试跑失败'), 'error')
  } finally {
    testing.value = false
  }
}

watch(detectionTypeFilter, () => {
  page.value.current = 1
  void loadModels()
})

watch(
  () => page.value.current,
  () => void loadModels(),
)

onMounted(() => {
  document.title = '模型库 - 检测服务管理'
  void loadModels()
})

onUnmounted(() => {
  releaseTestImageUrl()
})
</script>

<style scoped>
.ai-page {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: rgb(var(--v-theme-background));
}

.ai-page-content {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 24px 24px;
  gap: 14px;
}

.page-toolbar {
  flex: 0 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.toolbar-title h2 {
  margin: 0;
  color: rgb(var(--v-theme-on-background));
  font-size: 18px;
  font-weight: 600;
}

.toolbar-title span {
  color: rgba(var(--v-theme-on-background), 0.65);
  font-size: 13px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-filter {
  width: 160px;
}

.table-panel {
  position: relative;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgb(var(--v-theme-surface));
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
}

.table-loading-bar {
  position: absolute;
  inset: 0 0 auto;
  z-index: 2;
}

.ai-table {
  min-height: 0;
  flex: 1;
}

.ai-table :deep(.v-table__wrapper) {
  height: 100%;
}

.ai-table :deep(table) {
  width: 100%;
  table-layout: fixed;
}

.ai-table :deep(th:nth-child(1)) {
  width: 18%;
}

.ai-table :deep(th:nth-child(2)) {
  width: 12%;
}

.ai-table :deep(th:nth-child(3)) {
  width: 12%;
}

.ai-table :deep(th:nth-child(4)),
.ai-table :deep(th:nth-child(5)) {
  width: 16%;
}

.ai-table :deep(th:nth-child(6)) {
  width: 16%;
  white-space: nowrap;
}

.ai-table :deep(th:nth-child(7)) {
  width: 10%;
  white-space: nowrap;
}

.resource-id-row {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
}

.model-uuid {
  max-width: 180px;
  overflow: hidden;
  color: rgba(var(--v-theme-on-surface), 0.55);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.copy-id-button {
  flex: 0 0 auto;
  width: 14px;
  min-width: 14px;
  height: 14px;
  min-height: 14px;
  padding: 0;
  --v-btn-height: 14px;
}

.copy-id-button :deep(.v-icon) {
  font-size: 11px;
}

.prompt-text {
  max-width: 280px;
}

.description-text {
  max-width: 220px;
}

.empty-cell {
  padding: 56px !important;
  color: rgba(var(--v-theme-on-surface), 0.6);
  text-align: center;
}

.pagination-bar {
  flex: 0 0 auto;
  padding: 8px;
  border-top: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.test-model-summary {
  padding: 10px 12px;
  background: rgba(var(--v-theme-primary), 0.08);
  border-radius: 4px;
}

.json-preview {
  max-height: 300px;
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}

.test-result-card {
  max-height: calc(100vh - 64px);
}

.test-preview :deep(.preview-stage) {
  min-height: 360px;
}

.test-preview :deep(.annotation-summary) {
  max-height: 620px;
}

.test-preview :deep(.v-expansion-panel-text__wrapper) {
  max-height: 240px;
  overflow: auto;
}

@media (max-width: 860px) {
  .ai-page-content {
    padding: 12px 16px 16px;
  }

  .page-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-actions {
    flex-wrap: wrap;
  }
}
</style>
