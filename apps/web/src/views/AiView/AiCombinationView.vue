<template>
  <div class="ai-page">
    <div class="ai-page-content">
      <div class="page-toolbar">
        <div class="toolbar-title">
          <h2>综合检测</h2>
          <span>将多个模型组合为可复用的检测配置</span>
        </div>
        <div class="toolbar-actions">
          <v-text-field
            v-model="projectNameFilter"
            placeholder="所属项目"
            aria-label="所属项目"
            clearable
            hide-details
            density="compact"
            variant="outlined"
            class="project-filter"
          />
          <v-btn
            variant="tonal"
            prepend-icon="mdi-refresh"
            :loading="loading"
            @click="loadCombinations"
          >
            刷新
          </v-btn>
          <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">新建组合</v-btn>
        </div>
      </div>

      <div class="table-panel">
        <v-progress-linear v-if="loading" indeterminate color="primary" class="table-loading-bar" />
        <v-table fixed-header class="ai-table">
          <thead>
            <tr>
              <th>组合名称</th>
              <th>所属项目</th>
              <th>包含模型</th>
              <th>说明</th>
              <th>更新时间</th>
              <th class="text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="combination in combinations" :key="combination.uuid">
              <td>
                <div class="font-weight-medium">{{ combination.name }}</div>
                <div class="resource-id-row">
                  <span class="combination-uuid" :title="combination.uuid">
                    {{ formatResourceId(combination.uuid) }}
                  </span>
                  <v-tooltip text="复制 ID" location="top">
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        icon="mdi-content-copy"
                        size="x-small"
                        variant="text"
                        class="copy-id-button"
                        @click.stop="copyResourceId(combination.uuid, '组合 ID')"
                      />
                    </template>
                  </v-tooltip>
                </div>
              </td>
              <td>{{ combination.project_name || '-' }}</td>
              <td>
                <div class="model-chips">
                  <v-chip
                    v-for="model in combination.models.slice(0, 3)"
                    :key="model.uuid"
                    size="x-small"
                    variant="tonal"
                    :color="getDetectionTypeColor(model.detection_type)"
                  >
                    {{ model.name }}
                  </v-chip>
                  <v-chip v-if="combination.models.length > 3" size="x-small" variant="outlined">
                    +{{ combination.models.length - 3 }}
                  </v-chip>
                  <span v-if="combination.models.length === 0" class="text-medium-emphasis">-</span>
                </div>
              </td>
              <td class="text-truncate description-text">{{ combination.description || '-' }}</td>
              <td>{{ formatDate(combination.updated_at) }}</td>
              <td class="text-right">
                <v-btn
                  size="small"
                  variant="text"
                  color="primary"
                  @click="openDetailDialog(combination)"
                >
                  详情
                </v-btn>
                <v-btn
                  v-if="combination.can_manage"
                  size="small"
                  variant="text"
                  color="primary"
                  @click="openEditDialog(combination)"
                >
                  编辑
                </v-btn>
                <v-btn
                  v-if="combination.can_manage"
                  size="small"
                  variant="text"
                  color="error"
                  @click="handleDeleteCombination(combination)"
                >
                  删除
                </v-btn>
              </td>
            </tr>
            <tr v-if="!loading && combinations.length === 0">
              <td colspan="6" class="empty-cell">暂无综合检测配置</td>
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

    <v-dialog v-model="showCombinationDialog" max-width="720" persistent>
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <span>{{ editingCombination ? '编辑综合检测' : '新建综合检测' }}</span>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            @click="showCombinationDialog = false"
          />
        </v-card-title>
        <v-divider />
        <v-card-text class="pt-5">
          <v-text-field
            v-model="combinationForm.name"
            label="组合名称 *"
            variant="outlined"
            density="comfortable"
          />
          <v-text-field
            v-model="combinationForm.projectName"
            label="所属项目"
            variant="outlined"
            density="comfortable"
          />
          <v-select
            v-model="modelTypeFilter"
            :items="modelTypeFilterOptions"
            label="模型类型"
            variant="outlined"
            density="comfortable"
            hide-details
            class="model-type-filter mb-4"
          />
          <v-select
            v-model="selectedModelUuids"
            :items="modelOptions"
            :loading="modelsLoading"
            label="选择模型 *"
            multiple
            chips
            closable-chips
            variant="outlined"
            density="comfortable"
            hide-details
            class="model-selector"
          >
            <template #chip="{ props, item }">
              <v-chip v-bind="props" :text="getSelectedModelTitle(item)" />
            </template>
          </v-select>
          <div class="model-selection-hint">模型顺序会按当前选择顺序保存</div>
          <v-textarea
            v-model="combinationForm.description"
            label="组合说明"
            rows="3"
            variant="outlined"
            density="comfortable"
            hide-details
          />
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="text" @click="showCombinationDialog = false">取消</v-btn>
          <v-spacer />
          <v-btn color="primary" :loading="saving" @click="saveCombination">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showDetailDialog" max-width="760">
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <span>综合检测详情</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="showDetailDialog = false" />
        </v-card-title>
        <v-divider />
        <v-card-text v-if="detailCombination" class="pt-5">
          <div class="detail-row">
            <span>组合名称</span><strong>{{ detailCombination.name }}</strong>
          </div>
          <div class="detail-row">
            <span>所属项目</span><strong>{{ detailCombination.project_name || '-' }}</strong>
          </div>
          <div class="detail-row description-row">
            <span>组合说明</span><strong>{{ detailCombination.description || '-' }}</strong>
          </div>
          <div class="text-subtitle-2 mt-5 mb-2">包含模型</div>
          <v-table density="comfortable" class="detail-model-table">
            <thead>
              <tr>
                <th>模型名称</th>
                <th>类型</th>
                <th>模型文件</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="model in detailCombination.models" :key="model.uuid">
                <td>{{ model.name }}</td>
                <td>
                  <v-chip
                    size="x-small"
                    variant="tonal"
                    :color="getDetectionTypeColor(model.detection_type)"
                  >
                    {{ getDetectionTypeLabel(model.detection_type) }}
                  </v-chip>
                </td>
                <td>{{ model.model_file || '-' }}</td>
                <td>{{ model.description || '-' }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card-text>
      </v-card>
    </v-dialog>

    <AppConfirmDialog />
    <AppSnackbar />
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  createAiCombination,
  deleteAiCombination,
  getAiCombination,
  getAiCombinations,
  getAiModels,
  updateAiCombination,
} from '@/api/services'
import AppConfirmDialog from '@/components/common/AppConfirmDialog.vue'
import AppSnackbar from '@/components/common/AppSnackbar.vue'
import { copyText } from '@/composables/useClipboard'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'
import type { AiCombination, AiDetectionType, AiModel } from '@/types/ai'

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()
const loading = ref(false)
const modelsLoading = ref(false)
const saving = ref(false)
const combinations = ref<AiCombination[]>([])
const availableModels = ref<AiModel[]>([])
const projectNameFilter = ref('')
const showCombinationDialog = ref(false)
const showDetailDialog = ref(false)
const editingCombination = ref<AiCombination | null>(null)
const detailCombination = ref<AiCombination | null>(null)
const selectedModelUuids = ref<string[]>([])
const page = ref({ current: 1, totalPages: 1 })
const modelTypeFilter = ref<'all' | AiDetectionType>('all')

const modelTypeFilterOptions = [
  { title: '全部类型', value: 'all' },
  { title: '目标检测', value: 1 },
  { title: '实例分割', value: 2 },
  { title: 'SAM 分割', value: 3 },
  { title: '多模态识别', value: 4 },
]

const combinationForm = reactive({
  name: '',
  projectName: '通用',
  description: '',
})

const getModelOptionTitle = (modelUuid: string) => {
  const model = availableModels.value.find((item) => item.uuid === modelUuid)
  if (!model) return modelUuid

  const description = model.description?.trim()
  const detail = description
    ? `${getDetectionTypeLabel(model.detection_type)}，${description}`
    : getDetectionTypeLabel(model.detection_type)
  return `${model.name}（${detail}）`
}

const getSelectedModelTitle = (item: unknown) => {
  if (typeof item === 'string') return getModelOptionTitle(item)
  if (!item || typeof item !== 'object') return '未知模型'

  const selectedItem = item as { value?: unknown; raw?: unknown; title?: unknown }
  const value = selectedItem.value ?? selectedItem.raw ?? selectedItem.title
  if (typeof value === 'string') return getModelOptionTitle(value)
  if (value && typeof value === 'object' && 'uuid' in value && typeof value.uuid === 'string') {
    return getModelOptionTitle(value.uuid)
  }
  return '未知模型'
}

const modelOptions = computed(() =>
  availableModels.value
    .filter((model) => {
      return modelTypeFilter.value === 'all' || model.detection_type === modelTypeFilter.value
    })
    .map((model) => ({
      title: getModelOptionTitle(model.uuid),
      value: model.uuid,
    })),
)

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

const formatResourceId = (id: string): string => {
  if (id.length <= 16) return id
  return `${id.slice(0, 8)}…${id.slice(-5)}`
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

const loadCombinations = async () => {
  loading.value = true
  try {
    const response = await getAiCombinations({
      page: page.value.current,
      pageSize: 10,
      projectName: projectNameFilter.value.trim() || undefined,
    })
    combinations.value = response.items
    page.value.totalPages = Math.max(1, response.totalPages)
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '加载综合检测配置失败'), 'error')
  } finally {
    loading.value = false
  }
}

const loadModelOptions = async () => {
  modelsLoading.value = true
  try {
    const response = await getAiModels({ page: 1, pageSize: 100 })
    availableModels.value = response.items
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '加载模型选项失败'), 'error')
  } finally {
    modelsLoading.value = false
  }
}

const resetCombinationForm = () => {
  combinationForm.name = ''
  combinationForm.projectName = '通用'
  combinationForm.description = ''
  selectedModelUuids.value = []
  modelTypeFilter.value = 'all'
  editingCombination.value = null
}

const openCreateDialog = async () => {
  resetCombinationForm()
  showCombinationDialog.value = true
  await loadModelOptions()
}

const openEditDialog = async (combination: AiCombination) => {
  editingCombination.value = combination
  combinationForm.name = combination.name
  combinationForm.projectName = combination.project_name || '通用'
  combinationForm.description = combination.description || ''
  selectedModelUuids.value = combination.models.map((model) => model.uuid)
  showCombinationDialog.value = true
  await loadModelOptions()
}

const openDetailDialog = async (combination: AiCombination) => {
  try {
    detailCombination.value = await getAiCombination(combination.uuid)
    showDetailDialog.value = true
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '加载组合详情失败'), 'error')
  }
}

const saveCombination = async () => {
  if (!combinationForm.name.trim()) {
    snackbar.showSnackbar('请输入组合名称', 'warning')
    return
  }

  if (selectedModelUuids.value.length === 0) {
    snackbar.showSnackbar('请至少选择一个模型', 'warning')
    return
  }

  const modelUuids = [...new Set(selectedModelUuids.value)]
  selectedModelUuids.value = modelUuids

  saving.value = true
  const data = {
    name: combinationForm.name.trim(),
    model_uuids: modelUuids,
    project_name: combinationForm.projectName.trim() || undefined,
    description: combinationForm.description.trim() || undefined,
  }

  try {
    if (editingCombination.value) {
      await updateAiCombination(editingCombination.value.uuid, data)
    } else {
      await createAiCombination(data)
    }
    showCombinationDialog.value = false
    snackbar.showSnackbar('综合检测配置已保存', 'success')
    await loadCombinations()
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '保存综合检测配置失败'), 'error')
  } finally {
    saving.value = false
  }
}

const handleDeleteCombination = async (combination: AiCombination) => {
  const confirmed = await confirmDialog.showConfirm(
    '删除综合检测',
    `确定要删除“${combination.name}”吗？`,
  )
  if (!confirmed) return

  try {
    await deleteAiCombination(combination.uuid)
    snackbar.showSnackbar('综合检测配置已删除', 'success')
    await loadCombinations()
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '删除综合检测配置失败'), 'error')
  }
}

watch(projectNameFilter, () => {
  page.value.current = 1
  void loadCombinations()
})

watch(
  () => page.value.current,
  () => void loadCombinations(),
)

onMounted(() => {
  document.title = '综合检测 - 检测服务管理'
  void loadCombinations()
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

.project-filter {
  width: 160px;
}

.model-selection-hint {
  margin: 6px 0 16px;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-size: 12px;
  line-height: 1.2;
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
  width: 22%;
}

.ai-table :deep(th:nth-child(4)) {
  width: 20%;
}

.ai-table :deep(th:nth-child(5)) {
  width: 16%;
  white-space: nowrap;
}

.ai-table :deep(th:nth-child(6)) {
  width: 12%;
  white-space: nowrap;
}

.resource-id-row {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 0;
  margin-top: 3px;
  opacity: 0.72;
  transition: opacity 0.15s ease;
}

.resource-id-row:hover {
  opacity: 1;
}

.combination-uuid {
  max-width: 132px;
  overflow: hidden;
  color: rgba(var(--v-theme-on-surface), 0.55);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
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

.model-chips {
  max-width: 280px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.description-text {
  max-width: 240px;
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

.detail-row {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 16px;
  margin-bottom: 12px;
}

.detail-row > span {
  color: rgba(var(--v-theme-on-surface), 0.65);
}

.detail-row > strong {
  font-weight: 500;
}

.description-row strong {
  white-space: pre-wrap;
}

.detail-model-table {
  border: 1px solid var(--studio-hairline);
  border-radius: 8px;
  overflow: hidden;
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
