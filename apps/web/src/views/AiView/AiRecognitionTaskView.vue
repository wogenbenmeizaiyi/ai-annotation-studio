<template>
  <div class="ai-page">
    <div class="ai-page-content">
      <div class="page-toolbar">
        <div class="toolbar-title">
          <h2>识别任务</h2>
          <span>查看外部调用提交的识别任务及其结果</span>
        </div>
        <div class="toolbar-actions">
          <v-select
            v-model="statusFilter"
            :items="statusOptions"
            placeholder="任务状态"
            aria-label="任务状态"
            hide-details
            density="compact"
            variant="outlined"
            class="status-filter"
            clearable
          />
          <v-select
            v-model="detectionTypeFilter"
            :items="detectionTypeOptions"
            placeholder="识别类型"
            aria-label="识别类型"
            hide-details
            density="compact"
            variant="outlined"
            class="type-filter"
            clearable
          />
          <v-text-field
            v-model="projectNameFilter"
            placeholder="所属项目"
            aria-label="所属项目"
            hide-details
            density="compact"
            variant="outlined"
            clearable
            class="project-filter"
            @keyup.enter="applyTaskFilters"
          />
          <div class="date-range-filter" role="group" aria-label="创建日期范围">
            <span class="date-range-label">创建日期</span>
            <v-menu
              v-model="startDateMenuOpen"
              :close-on-content-click="false"
              location="bottom start"
            >
              <template #activator="{ props: activatorProps }">
                <v-text-field
                  v-bind="activatorProps"
                  :model-value="createdAtStartFilter"
                  placeholder="开始日期"
                  aria-label="创建开始日期"
                  append-inner-icon="mdi-calendar-blank-outline"
                  hide-details
                  density="compact"
                  variant="outlined"
                  clearable
                  readonly
                  class="date-filter"
                  @click:clear.stop="clearStartDate"
                />
              </template>
              <v-date-picker
                v-model="startDateValue"
                hide-header
                show-adjacent-months
                width="320"
                @update:model-value="handleStartDateSelected"
              />
            </v-menu>
            <span class="date-range-separator">至</span>
            <v-menu
              v-model="endDateMenuOpen"
              :close-on-content-click="false"
              location="bottom start"
            >
              <template #activator="{ props: activatorProps }">
                <v-text-field
                  v-bind="activatorProps"
                  :model-value="createdAtEndFilter"
                  placeholder="结束日期"
                  aria-label="创建结束日期"
                  append-inner-icon="mdi-calendar-blank-outline"
                  hide-details
                  density="compact"
                  variant="outlined"
                  clearable
                  readonly
                  class="date-filter"
                  @click:clear.stop="clearEndDate"
                />
              </template>
              <v-date-picker
                v-model="endDateValue"
                hide-header
                show-adjacent-months
                width="320"
                @update:model-value="handleEndDateSelected"
              />
            </v-menu>
          </div>
          <v-btn
            variant="tonal"
            prepend-icon="mdi-refresh"
            :loading="loading"
            @click="applyTaskFilters"
          >
            刷新
          </v-btn>
        </div>
      </div>

      <div class="table-panel">
        <v-progress-linear v-if="loading" indeterminate color="primary" class="table-loading-bar" />
        <v-table fixed-header class="ai-table">
          <thead>
            <tr>
              <th>任务 ID</th>
              <th>项目</th>
              <th>识别类型</th>
              <th>模型 / 提示词</th>
              <th class="text-center">图片数</th>
              <th>状态</th>
              <th class="text-center">耗时</th>
              <th>创建时间</th>
              <th class="text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.task_id">
              <td>
                <div class="resource-id-row task-id-row">
                  <span class="task-id" :title="task.task_id">{{ formatResourceId(task.task_id) }}</span>
                  <v-tooltip text="复制 ID" location="top">
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        icon="mdi-content-copy"
                        size="x-small"
                        variant="text"
                        class="copy-id-button"
                        @click.stop="copyResourceId(task.task_id, '任务 ID')"
                      />
                    </template>
                  </v-tooltip>
                </div>
              </td>
              <td>{{ task.project_name || '-' }}</td>
              <td>
                <v-chip
                  size="small"
                  variant="tonal"
                  :color="getDetectionTypeColor(task.detection_type)"
                >
                  {{ getDetectionTypeLabel(task.detection_type) }}
                </v-chip>
              </td>
              <td class="text-truncate model-text">{{ task.text || '-' }}</td>
              <td class="text-center">{{ task.image_count }}</td>
              <td>
                <div class="task-status">
                  <v-chip size="small" variant="tonal" :color="getTaskStatusColor(task.status)">
                    {{ getTaskStatusLabel(task.status) }}
                  </v-chip>
                  <v-tooltip v-if="task.status === 'failed'" text="查看错误" location="top">
                    <template #activator="{ props: activatorProps }">
                      <v-btn
                        v-bind="activatorProps"
                        icon="mdi-information-outline"
                        size="x-small"
                        variant="text"
                        color="error"
                        aria-label="查看任务错误"
                        @click="openTaskError(task)"
                      />
                    </template>
                  </v-tooltip>
                </div>
              </td>
              <td class="text-center">{{ formatDuration(task.duration_seconds) }}</td>
              <td>{{ formatDate(task.created_at) }}</td>
              <td class="text-right">
                <v-btn
                  size="small"
                  variant="outlined"
                  color="primary"
                  @click="openTaskResults(task)"
                >
                  查看结果
                </v-btn>
              </td>
            </tr>
            <tr v-if="!loading && tasks.length === 0">
              <td colspan="9" class="empty-cell">暂无识别任务</td>
            </tr>
          </tbody>
        </v-table>
        <div v-if="taskPage.totalPages > 1" class="pagination-bar">
          <v-pagination
            v-model="taskPage.current"
            :length="taskPage.totalPages"
            :total-visible="7"
            density="compact"
          />
        </div>
      </div>
    </div>

    <v-dialog v-model="showResults" max-width="1120" scrollable>
      <v-card class="studio-dialog-card result-dialog">
        <v-card-title class="studio-dialog-header">
          <div class="studio-dialog-heading">
            <div class="studio-dialog-title">识别结果</div>
            <div v-if="selectedTask" class="studio-dialog-subtitle">
              任务 ID：<span class="studio-dialog-context">{{ selectedTask.task_id }}</span>
            </div>
          </div>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            class="studio-dialog-close"
            @click="showResults = false"
          />
        </v-card-title>
        <v-card-text class="studio-dialog-body result-table-content">
          <v-progress-linear
            v-if="resultsLoading"
            indeterminate
            color="primary"
            class="table-loading-bar"
          />
          <v-table fixed-header class="ai-table result-table">
            <thead>
              <tr>
                <th class="text-center">序号</th>
                <th>图片</th>
                <th>服务</th>
                <th>识别类型</th>
                <th class="text-center">目标数</th>
                <th>生成时间</th>
                <th class="text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="result in results" :key="result.image_index">
                <td class="text-center">{{ result.image_index + 1 }}</td>
                <td>
                  <a :href="result.url" target="_blank" rel="noreferrer" class="result-image-link">
                    {{ getFileName(result.url) }}
                  </a>
                </td>
                <td>{{ result.service }}</td>
                <td>{{ result.detection_type }}</td>
                <td class="text-center">{{ result.count }}</td>
                <td>{{ formatDate(result.created_at) }}</td>
                <td class="text-right">
                  <v-btn
                    size="small"
                    variant="text"
                    color="primary"
                    @click="openResultDetail(result)"
                  >
                    查看详情
                  </v-btn>
                </td>
              </tr>
              <tr v-if="!resultsLoading && results.length === 0">
                <td colspan="7" class="empty-cell">该任务暂无可展示的结果</td>
              </tr>
            </tbody>
          </v-table>
          <div v-if="resultPage.totalPages > 1" class="pagination-bar">
            <v-pagination
              v-model="resultPage.current"
              :length="resultPage.totalPages"
              :total-visible="7"
              density="compact"
            />
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showTaskError" max-width="640">
      <v-card class="studio-dialog-card task-error-dialog">
        <v-card-title class="studio-dialog-header">
          <div class="studio-dialog-heading">
            <div class="studio-dialog-title">任务错误详情</div>
            <div v-if="selectedErrorTask" class="studio-dialog-subtitle">
              任务 ID：<span class="studio-dialog-context">{{ selectedErrorTask.task_id }}</span>
            </div>
          </div>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            class="studio-dialog-close"
            @click="showTaskError = false"
          />
        </v-card-title>
        <v-card-text class="studio-dialog-body task-error-body">
          <div class="task-error-label">
            <v-icon icon="mdi-alert-circle-outline" size="18" />
            失败原因
          </div>
          <pre class="task-error-message">{{ selectedErrorMessage }}</pre>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showResultDetail" max-width="1280" scrollable>
      <v-card class="studio-dialog-card result-detail-dialog">
        <v-card-title class="studio-dialog-header">
          <div class="studio-dialog-heading">
            <div class="studio-dialog-title">识别结果详情</div>
            <div class="studio-dialog-subtitle">
              {{ selectedResult ? getFileName(selectedResult.url) : '' }}
            </div>
          </div>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            class="studio-dialog-close"
            @click="showResultDetail = false"
          />
        </v-card-title>
        <v-card-text class="studio-dialog-body result-detail-content">
          <RecognitionResultPreview v-if="selectedResult" :result="selectedResult" />
          <v-expansion-panels v-if="selectedResult" variant="accordion" class="raw-result-panel">
            <v-expansion-panel title="原始 COCO 数据">
              <v-expansion-panel-text>
                <pre class="json-preview">{{ selectedResultJson }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>
      </v-card>
    </v-dialog>

    <AppSnackbar />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getRecognitionTaskResults, getRecognitionTasks } from '@/api/services'
import RecognitionResultPreview from '@/components/ai/RecognitionResultPreview.vue'
import AppSnackbar from '@/components/common/AppSnackbar.vue'
import { useSnackbar } from '@/composables/useSnackbar'
import { copyText } from '@/composables/useClipboard'
import type {
  AiDetectionType,
  RecognitionResultItem,
  RecognitionTask,
  RecognitionTaskStatus,
} from '@/types/ai'

const snackbar = useSnackbar()
const loading = ref(false)
const resultsLoading = ref(false)
const tasks = ref<RecognitionTask[]>([])
const results = ref<RecognitionResultItem[]>([])
const statusFilter = ref<RecognitionTaskStatus | null>(null)
const detectionTypeFilter = ref<AiDetectionType | null>(null)
const projectNameFilter = ref<string | null>(null)
const createdAtStartFilter = ref<string | null>(null)
const createdAtEndFilter = ref<string | null>(null)
const startDateMenuOpen = ref(false)
const endDateMenuOpen = ref(false)
const startDateValue = ref<unknown>(null)
const endDateValue = ref<unknown>(null)
const selectedTask = ref<RecognitionTask | null>(null)
const selectedErrorTask = ref<RecognitionTask | null>(null)
const selectedResult = ref<RecognitionResultItem | null>(null)
const selectedResultJson = ref('')
const showResults = ref(false)
const showTaskError = ref(false)
const showResultDetail = ref(false)

const taskPage = ref({ current: 1, totalPages: 1 })
const resultPage = ref({ current: 1, totalPages: 1 })

const statusOptions = [
  { title: '等待中', value: 'pending' },
  { title: '处理中', value: 'processing' },
  { title: '成功', value: 'success' },
  { title: '失败', value: 'failed' },
]

const detectionTypeOptions = [
  { title: 'YOLO 目标检测', value: 1 },
  { title: 'YOLO 实例分割', value: 2 },
  { title: 'SAM 分割', value: 3 },
  { title: '多模态识别', value: 4 },
]

const getErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === 'string') return error
  if (error instanceof Error && error.message) return error.message
  return fallback
}

const getDetectionTypeLabel = (type: AiDetectionType) => {
  return { 1: '目标检测', 2: '实例分割', 3: 'SAM 分割', 4: '多模态识别' }[type]
}

const getDetectionTypeColor = (type: AiDetectionType) => {
  return { 1: 'primary', 2: 'success', 3: 'secondary', 4: 'warning' }[type]
}

const getTaskStatusLabel = (status: RecognitionTaskStatus) => {
  return { pending: '等待中', processing: '处理中', success: '成功', failed: '失败' }[status]
}

const getTaskStatusColor = (status: RecognitionTaskStatus) => {
  return { pending: 'warning', processing: 'primary', success: 'success', failed: 'error' }[status]
}

const formatDate = (value: string | null) => {
  if (!value) return '-'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

const formatResourceId = (id: string): string => {
  if (id.length <= 16) return id
  return `${id.slice(0, 8)}…${id.slice(-5)}`
}

const copyResourceId = async (id: string, label: string) => {
  try {
    await copyText(id)
    snackbar.showSnackbar(`${label} 已复制`, 'success')
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, `${label} 复制失败`), 'error')
  }
}

const formatDuration = (seconds: number | null) => {
  if (seconds === null || seconds === undefined) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)} 秒`
  const minutes = Math.floor(seconds / 60)
  const restSeconds = Math.round(seconds % 60)
  if (minutes < 60) return `${minutes} 分 ${restSeconds} 秒`
  const hours = Math.floor(minutes / 60)
  const restMinutes = minutes % 60
  return `${hours} 时 ${restMinutes} 分`
}

const getFileName = (url: string) => {
  try {
    return decodeURIComponent(new URL(url).pathname.split('/').pop() || url)
  } catch {
    return url
  }
}

const toIsoDateTime = (value: string | null, isEndOfDay = false) => {
  if (!value) return undefined
  const date = new Date(`${value}T${isEndOfDay ? '23:59:59.999' : '00:00:00'}`)
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString()
}

const formatSelectedDate = (value: unknown): string | null => {
  const selectedValue = Array.isArray(value) ? value[0] : value
  if (!selectedValue) return null

  if (typeof selectedValue === 'string') {
    const datePart = selectedValue.match(/^\d{4}-\d{2}-\d{2}/)?.[0]
    if (datePart) return datePart
  }

  const date = selectedValue instanceof Date ? selectedValue : new Date(String(selectedValue))
  if (Number.isNaN(date.getTime())) return null

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const handleStartDateSelected = (value: unknown) => {
  const selectedDate = formatSelectedDate(value)
  if (!selectedDate) return
  createdAtStartFilter.value = selectedDate
  startDateMenuOpen.value = false
}

const handleEndDateSelected = (value: unknown) => {
  const selectedDate = formatSelectedDate(value)
  if (!selectedDate) return
  createdAtEndFilter.value = selectedDate
  endDateMenuOpen.value = false
}

const clearStartDate = () => {
  createdAtStartFilter.value = null
  startDateValue.value = null
  startDateMenuOpen.value = false
}

const clearEndDate = () => {
  createdAtEndFilter.value = null
  endDateValue.value = null
  endDateMenuOpen.value = false
}

const applyTaskFilters = () => {
  if (taskPage.value.current === 1) {
    void loadTasks()
    return
  }
  taskPage.value.current = 1
}

const loadTasks = async () => {
  loading.value = true
  try {
    const response = await getRecognitionTasks({
      page: taskPage.value.current,
      pageSize: 10,
      status: statusFilter.value ?? undefined,
      detectionType: detectionTypeFilter.value ?? undefined,
      projectName: projectNameFilter.value?.trim() || undefined,
      createdAtStart: toIsoDateTime(createdAtStartFilter.value),
      createdAtEnd: toIsoDateTime(createdAtEndFilter.value, true),
    })
    tasks.value = response.items
    taskPage.value.totalPages = Math.max(1, response.totalPages)
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '加载识别任务失败'), 'error')
  } finally {
    loading.value = false
  }
}

const loadTaskResults = async () => {
  if (!selectedTask.value) return

  resultsLoading.value = true
  try {
    const response = await getRecognitionTaskResults(selectedTask.value.task_id, {
      page: resultPage.value.current,
      pageSize: 10,
    })
    results.value = response.items
    resultPage.value.totalPages = Math.max(1, response.totalPages)
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '加载识别结果失败'), 'error')
  } finally {
    resultsLoading.value = false
  }
}

const openTaskResults = async (task: RecognitionTask) => {
  selectedTask.value = task
  resultPage.value.current = 1
  results.value = []
  showResults.value = true
  await loadTaskResults()
}

const openTaskError = (task: RecognitionTask) => {
  selectedErrorTask.value = task
  showTaskError.value = true
}

const selectedErrorMessage = computed(
  () => selectedErrorTask.value?.error?.trim() || '该历史任务未记录详细错误信息。',
)

const openResultDetail = (result: RecognitionResultItem) => {
  selectedResult.value = result
  selectedResultJson.value = JSON.stringify(result, null, 2)
  showResultDetail.value = true
}

watch(
  [statusFilter, detectionTypeFilter, createdAtStartFilter, createdAtEndFilter],
  applyTaskFilters,
)

watch(
  () => taskPage.value.current,
  () => void loadTasks(),
)

watch(
  () => resultPage.value.current,
  () => void loadTaskResults(),
)

onMounted(() => {
  document.title = '识别任务 - 检测服务管理'
  void loadTasks()
})
</script>

<style scoped>
.ai-page {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--studio-canvas);
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
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.status-filter {
  width: 150px;
}

.type-filter {
  width: 160px;
}

.project-filter {
  width: 160px;
}

.date-filter {
  width: 156px;
}

.date-range-filter {
  display: flex;
  align-items: center;
  gap: 6px;
}

.date-range-label,
.date-range-separator {
  flex: 0 0 auto;
  color: var(--studio-ink-subtle);
  font-size: 12px;
  white-space: nowrap;
}

.date-range-filter :deep(.v-field) {
  background: var(--studio-surface-1);
}

.table-panel {
  position: relative;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--studio-surface-1);
  border: 1px solid var(--studio-hairline);
  border-radius: 10px;
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

.ai-table:not(.result-table) :deep(th:nth-child(1)) {
  width: 18%;
}

.ai-table:not(.result-table) :deep(th:nth-child(2)) {
  width: 10%;
}

.ai-table:not(.result-table) :deep(th:nth-child(3)) {
  width: 13%;
}

.ai-table:not(.result-table) :deep(th:nth-child(4)) {
  width: 18%;
}

.ai-table:not(.result-table) :deep(th:nth-child(5)) {
  width: 8%;
}

.ai-table:not(.result-table) :deep(th:nth-child(6)) {
  width: 10%;
}

.ai-table:not(.result-table) :deep(th:nth-child(7)) {
  width: 10%;
  white-space: nowrap;
}

.ai-table:not(.result-table) :deep(th:nth-child(8)) {
  width: 14%;
  white-space: nowrap;
}

.ai-table:not(.result-table) :deep(th:nth-child(9)) {
  width: 8%;
  white-space: nowrap;
}

.result-table :deep(th:nth-child(1)) {
  width: 8%;
}

.result-table :deep(th:nth-child(2)) {
  width: 25%;
}

.result-table :deep(th:nth-child(3)),
.result-table :deep(th:nth-child(4)) {
  width: 15%;
}

.result-table :deep(th:nth-child(5)) {
  width: 8%;
}

.result-table :deep(th:nth-child(6)) {
  width: 18%;
  white-space: nowrap;
}

.result-table :deep(th:nth-child(7)) {
  width: 11%;
  white-space: nowrap;
}

.task-id-row {
  margin-top: 0;
}

.task-id {
  max-width: 140px;
  overflow: hidden;
  color: rgba(var(--v-theme-on-surface), 0.55);
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
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

.model-text {
  max-width: 220px;
}

.task-status {
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.empty-cell {
  padding: 56px !important;
  color: rgba(var(--v-theme-on-surface), 0.6);
  text-align: center;
}

.pagination-bar {
  flex: 0 0 auto;
  padding: 8px;
  border-top: 1px solid var(--studio-hairline);
}

.result-dialog {
  height: min(760px, calc(100vh - 80px));
  display: flex;
  flex-direction: column;
}

.task-error-dialog {
  overflow: hidden;
}

.task-error-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-error-label {
  display: flex;
  align-items: center;
  gap: 7px;
  color: rgb(var(--v-theme-error));
  font-size: 13px;
  font-weight: 600;
}

.task-error-message {
  max-height: min(360px, 50vh);
  margin: 0;
  padding: 14px 16px;
  overflow: auto;
  border: 1px solid rgba(var(--v-theme-error), 0.2);
  border-radius: 8px;
  background: rgba(var(--v-theme-error), 0.06);
  color: rgba(var(--v-theme-on-surface), 0.86);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

.result-table-content {
  position: relative;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.result-table {
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--studio-hairline);
  border-radius: 8px;
}

.result-image-link {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}

.result-image-link:hover {
  text-decoration: underline;
}

.json-preview {
  margin: 0;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}

.result-detail-dialog {
  max-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
}

.result-detail-content {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.raw-result-panel {
  flex: 0 0 auto;
}

.raw-result-panel :deep(.v-expansion-panel) {
  border: 1px solid var(--studio-hairline);
  border-radius: 8px;
}

.raw-result-panel :deep(.v-expansion-panel-text__wrapper) {
  max-height: 260px;
  overflow: auto;
}

@media (max-width: 800px) {
  .ai-page-content {
    padding: 12px 16px 16px;
  }

  .page-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-actions {
    width: 100%;
  }

  .status-filter {
    flex: 1;
  }

  .date-range-filter {
    width: 100%;
  }

  .date-filter {
    min-width: 132px;
    flex: 1;
  }
}
</style>
