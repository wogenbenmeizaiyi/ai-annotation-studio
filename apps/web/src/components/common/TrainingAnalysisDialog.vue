<template>
  <v-dialog v-model="dialogVisible" max-width="860">
    <v-card class="analysis-dialog-card" rounded="lg">
      <v-card-title class="analysis-dialog-title">
        <div>
          <div class="text-h6">训练结果分析</div>
          <div class="text-caption text-medium-emphasis">训练记录 #{{ taskId }}</div>
        </div>
        <div class="d-flex align-center ga-2">
          <v-chip v-if="analysisStatus" :color="analysisStatusColor" size="small" variant="tonal">
            {{ analysisStatusText }}
          </v-chip>
          <v-btn icon="mdi-close" variant="text" size="small" @click="dialogVisible = false" />
        </div>
      </v-card-title>

      <v-card-text class="analysis-dialog-body">
        <div v-if="isLoading && !autoAnalysis" class="analysis-loading">
          <v-progress-circular indeterminate color="primary" size="34" />
          <span>正在分析训练指标...</span>
        </div>

        <v-alert v-else-if="errorMessage && !analysis" type="error" variant="tonal">
          {{ errorMessage }}
        </v-alert>

        <div v-else class="analysis-content">
          <v-alert v-if="errorMessage" type="error" variant="tonal">
            {{ errorMessage }}
          </v-alert>
          <v-alert v-if="isAnalysisPending" type="info" variant="tonal" density="comfortable">
            自动分析正在后台生成，页面会自动刷新，不会重复调用大模型。
          </v-alert>

          <v-alert
            v-if="analysisStatus === 'FAILED'"
            type="warning"
            variant="tonal"
            density="comfortable"
          >
            {{ autoAnalysis?.error_message || '大模型总结生成失败，仍可查看已有的指标分析。' }}
          </v-alert>

          <section v-if="modelReply" class="model-analysis-reply">
            <div class="analysis-section-title">
              <v-icon icon="mdi-auto-fix" color="primary" size="20" />
              智能质量总结
            </div>
            <MarkdownText :content="modelReply" />
          </section>

          <template v-if="analysis">
            <div class="analysis-summary-grid">
              <div v-for="item in summaryItems" :key="item.key" class="analysis-summary-item">
                <div class="analysis-item-label">{{ item.label }}</div>
                <div class="analysis-item-value">{{ item.value }}</div>
              </div>
            </div>

            <section v-if="suggestions.length > 0" class="analysis-suggestions">
              <div class="analysis-section-title">
                <v-icon icon="mdi-lightbulb-on-outline" color="warning" size="20" />
                下一轮建议
              </div>
              <div v-for="(suggestion, index) in suggestions" :key="index" class="suggestion-row">
                <span>{{ index + 1 }}</span>
                <MarkdownText :content="suggestion" />
              </div>
            </section>

            <section
              v-if="!optimizationProposal && !isAnalysisPending"
              class="analysis-optimization-prompt"
            >
              <div class="analysis-section-title">
                <v-icon icon="mdi-message-text-outline" color="primary" size="20" />
                补充下一轮要求
              </div>
              <v-textarea
                v-model="optimizationInstruction"
                label="人工提示词（可选）"
                placeholder="例如：优先提高召回率；保持 batch 不变；减少过拟合并缩短训练轮次"
                hint="系统会同时参考本次训练参数、指标分析和这里填写的要求。"
                persistent-hint
                variant="outlined"
                density="comfortable"
                rows="2"
                auto-grow
                maxlength="5000"
                counter="5000"
              />
            </section>

            <section v-if="optimizationProposal" class="analysis-optimization">
              <div class="analysis-section-title">
                <v-icon icon="mdi-tune-variant" color="primary" size="20" />
                下一轮训练参数草案
              </div>
              <v-alert type="info" variant="tonal" density="compact" class="mb-3">
                该草案以训练记录 #{{ taskId }} 的完整参数为基线，目前尚未启动训练。
              </v-alert>
              <div v-if="optimizationChanges.length" class="optimization-change-list">
                <article
                  v-for="change in optimizationChanges"
                  :key="change.field"
                  class="optimization-change-item"
                >
                  <div class="optimization-change-field">{{ change.field }}</div>
                  <div>{{ formatValue(change.before) }} → {{ formatValue(change.after) }}</div>
                  <div class="text-caption text-medium-emphasis">{{ change.reason }}</div>
                </article>
              </div>
              <v-alert
                v-for="warning in optimizationWarnings"
                :key="warning"
                type="warning"
                variant="tonal"
                density="compact"
                class="mt-2"
              >
                {{ warning }}
              </v-alert>
              <v-alert
                v-for="question in optimizationQuestions"
                :key="question"
                type="info"
                variant="tonal"
                density="compact"
                class="mt-2"
              >
                需要补充：{{ question }}
              </v-alert>
            </section>

            <v-alert v-if="optimizationMessage" type="success" variant="tonal">
              {{ optimizationMessage }}
            </v-alert>

            <section v-if="extraItems.length > 0" class="analysis-extra">
              <div class="analysis-section-title">其他分析</div>
              <div class="analysis-extra-list">
                <article
                  v-for="item in extraItems"
                  :key="item.key"
                  class="analysis-extra-card"
                  :class="{ 'analysis-extra-card--wide': item.wide }"
                >
                  <div class="analysis-extra-label">{{ item.label }}</div>
                  <div v-if="item.parts?.length" class="analysis-detail-grid">
                    <div
                      v-for="(part, partIndex) in item.parts"
                      :key="`${part.label}-${partIndex}`"
                      class="analysis-detail-item"
                    >
                      <span>{{ part.label }}</span>
                      <strong>{{ part.value }}</strong>
                    </div>
                  </div>
                  <div v-else class="analysis-extra-value">{{ item.value }}</div>
                </article>
              </div>
            </section>

            <v-expansion-panels variant="accordion" density="compact">
              <v-expansion-panel title="查看完整分析数据">
                <v-expansion-panel-text>
                  <pre class="analysis-json">{{ JSON.stringify(autoAnalysis, null, 2) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </template>
        </div>
      </v-card-text>

      <v-card-actions class="analysis-dialog-actions">
        <v-btn variant="text" @click="dialogVisible = false">关闭</v-btn>
        <v-spacer />
        <v-btn
          v-if="!optimizationProposal"
          color="primary"
          variant="tonal"
          prepend-icon="mdi-tune-variant"
          :loading="isGeneratingOptimization"
          :disabled="!analysis || isAnalysisPending"
          @click="generateOptimizationProposal"
        >
          基于本次生成下一轮方案
        </v-btn>
        <template v-else-if="!optimizationMessage">
          <v-btn
            color="primary"
            variant="tonal"
            prepend-icon="mdi-pencil-outline"
            :disabled="!optimizationProposal.ready_to_apply || isStartingOptimization"
            @click="confirmAndEditOptimization"
          >
            确认并编辑参数
          </v-btn>
          <v-btn
            color="primary"
            prepend-icon="mdi-play-circle-outline"
            :loading="isStartingOptimization"
            :disabled="!optimizationProposal.ready_to_apply"
            @click="confirmAndStartOptimization"
          >
            确认并开始训练
          </v-btn>
        </template>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import {
  confirmTrainAgentProposal,
  createTrainAgentOptimizationProposal,
  getTrainAgentAnalysis,
  getTrainAgentAutoAnalysis,
  startTrainAgentProposal,
} from '@/api/services'
import MarkdownText from '@/components/common/MarkdownText.vue'
import type {
  TrainAgentAnalysis,
  TrainAgentAutoAnalysis,
  TrainAgentChatResponse,
  TrainAgentConfig,
  TrainOptimizationDraft,
} from '@/types/trainAgent'

interface AnalysisDisplayItem {
  key: string
  label: string
  value: string
  wide?: boolean
  parts?: Array<{ label: string; value: string }>
}

const props = defineProps<{
  modelValue: boolean
  taskId: number
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'started', taskId: number): void
  (event: 'edit', draft: TrainOptimizationDraft): void
}>()

const autoAnalysis = ref<TrainAgentAutoAnalysis | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')
const optimizationProposal = ref<TrainAgentChatResponse | null>(null)
const optimizationInstruction = ref('')
const optimizationMessage = ref('')
const isGeneratingOptimization = ref(false)
const isStartingOptimization = ref(false)
let refreshTimer: number | null = null

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const labelMap: Record<string, string> = {
  best_epoch: '最佳轮次',
  bestEpoch: '最佳轮次',
  convergence_trend: '收敛趋势',
  convergence: '收敛趋势',
  suspected_overfitting: '疑似过拟合',
  is_overfitting: '疑似过拟合',
  overfitting: '过拟合判断',
  precision_recall_balance: '精确率与召回率',
  precision_recall: '精确率与召回率',
}

const suggestionKeys = [
  'next_round_suggestions',
  'next_suggestions',
  'recommendations',
  'suggestions',
  'next_steps',
]

const extraLabelMap: Record<string, string> = {
  analyzer_version: '分析器版本',
  task_id: '训练任务',
  task_type: '任务类型',
  primary_metric: '核心指标',
  status: '任务状态',
  stage: '分析阶段',
  summary: '指标摘要',
  signals: '趋势信号',
  evidence: '判断依据',
  per_class_metrics: '分类指标',
  limitations: '分析限制',
}

const metricLabelMap: Record<string, string> = {
  metric_count: '指标记录数',
  best_epoch: '最佳轮次',
  best_map50_95: '最佳 mAP50-95',
  final_map50_95: '最终 mAP50-95',
  final_map50: '最终 mAP50',
  final_precision: '最终精确率',
  final_recall: '最终召回率',
  peak_decline_ratio: '峰值回落比例',
  final_box_precision: '检测框精确率',
  final_box_recall: '检测框召回率',
  final_box_map50: '检测框 mAP50',
  final_box_map50_95: '检测框 mAP50-95',
  final_mask_precision: '分割精确率',
  final_mask_recall: '分割召回率',
  final_mask_map50: '分割 mAP50',
  final_mask_map50_95: '分割 mAP50-95',
  final_fitness: '最终适应度',
  converged: '是否收敛',
  still_improving: '仍在提升',
  possible_overfitting: '可能过拟合',
  precision_recall_imbalance: '精确率/召回率失衡',
  recent_map_slope: '近期 mAP 趋势',
  recent_train_loss_slope: '近期训练损失趋势',
  recent_val_loss_slope: '近期验证损失趋势',
  class: '类别',
  'Box-P': '检测框精确率',
  'Box-R': '检测框召回率',
  'Box-F1': '检测框 F1',
  mAP50: 'mAP50',
  'mAP50-95': 'mAP50-95',
  Images: '图片数',
  Instances: '实例数',
}

const analysis = computed<TrainAgentAnalysis | null>(() => autoAnalysis.value?.analysis || null)

const analysisStatus = computed(() => String(autoAnalysis.value?.status || '').toUpperCase())
const isAnalysisPending = computed(() => ['PENDING', 'RUNNING'].includes(analysisStatus.value))
const modelReply = computed(() => autoAnalysis.value?.model_result?.reply || '')
const optimizationChanges = computed(() => optimizationProposal.value?.changes || [])
const optimizationWarnings = computed(() => optimizationProposal.value?.warnings || [])
const optimizationQuestions = computed(() => optimizationProposal.value?.questions || [])

const analysisStatusText = computed(() => {
  const statusMap: Record<string, string> = {
    PENDING: '等待分析',
    RUNNING: '分析中',
    COMPLETED: '分析完成',
    FAILED: '总结失败',
  }
  return statusMap[analysisStatus.value] || analysisStatus.value
})

const analysisStatusColor = computed(() => {
  const colorMap: Record<string, string> = {
    PENDING: 'warning',
    RUNNING: 'info',
    COMPLETED: 'success',
    FAILED: 'warning',
  }
  return colorMap[analysisStatus.value] || 'default'
})

const analysisRoot = computed<TrainAgentAnalysis>(() => {
  if (!analysis.value) return {}
  const nested = analysis.value.analysis
  return nested && typeof nested === 'object' && !Array.isArray(nested)
    ? (nested as TrainAgentAnalysis)
    : analysis.value
})

const formatValue = (value: unknown): string => {
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (Array.isArray(value)) {
    return value.length > 0 ? value.map((item) => formatValue(item)).join('；') : '-'
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value)
    if (entries.length === 0) return '-'
    return entries.map(([key, item]) => `${labelMap[key] || key}: ${formatValue(item)}`).join('；')
  }
  if (value === undefined || value === null || value === '') return '-'
  return String(value)
}

const summaryItems = computed<AnalysisDisplayItem[]>(() => {
  return Object.entries(analysisRoot.value)
    .filter(([key]) => labelMap[key])
    .map(([key, value]) => ({ key, label: labelMap[key]!, value: formatValue(value) }))
})

const suggestions = computed<string[]>(() => {
  for (const key of suggestionKeys) {
    const value = analysisRoot.value[key]
    if (Array.isArray(value)) return value.map((item) => formatValue(item)).filter(Boolean)
    if (typeof value === 'string' && value.trim()) return [value]
  }
  return []
})

const translateExtraValue = (key: string, value: string) => {
  const valueMap: Record<string, string> = {
    detection: '目标检测',
    segmentation: '实例分割',
    FINISHED: '已完成',
    RUNNING: '训练中',
    ERROR: '失败',
    final: '最终分析',
    true: '是',
    false: '否',
  }
  return valueMap[value] || value
}

const parseAnalysisParts = (value: unknown) => {
  const collectEntries = (source: unknown): Array<readonly [string, unknown]> => {
    if (Array.isArray(source)) return source.flatMap((item) => collectEntries(item))
    if (source && typeof source === 'object') return Object.entries(source)
    if (typeof source !== 'string') return []

    return source
      .split(/[;；]/)
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const separator = part.search(/[:：]/)
        return separator > 0
          ? ([part.slice(0, separator).trim(), part.slice(separator + 1).trim()] as const)
          : null
      })
      .filter((part): part is readonly [string, string] => Boolean(part))
  }

  const entries = collectEntries(value)

  if (entries.length < 2) return undefined
  return entries.map(([key, item]) => ({
    label: metricLabelMap[key] || key.replace(/_/g, ' '),
    value: translateExtraValue(key, formatValue(item)),
  }))
}

const extraItems = computed<AnalysisDisplayItem[]>(() => {
  return Object.entries(analysisRoot.value)
    .filter(([key]) => !labelMap[key] && !suggestionKeys.includes(key) && key !== 'analysis')
    .map(([key, value]) => {
      const formattedValue = formatValue(value)
      const parts = parseAnalysisParts(value)
      return {
        key,
        label: extraLabelMap[key] || key.replace(/_/g, ' '),
        value:
          key === 'limitations' && formattedValue === '-'
            ? '暂无明确限制'
            : translateExtraValue(key, formattedValue),
        wide:
          Boolean(parts?.length) ||
          ['summary', 'signals', 'evidence', 'per_class_metrics'].includes(key),
        parts,
      }
    })
})

const getErrorMessage = (error: unknown) => {
  if (typeof error === 'string' && error) return error
  if (error instanceof Error && error.message) return error.message
  if (error && typeof error === 'object') {
    const response = (error as { response?: { data?: { message?: string; detail?: string } } })
      .response
    return response?.data?.message || response?.data?.detail || '训练分析加载失败'
  }
  return '训练分析加载失败'
}

const getHttpStatus = (error: unknown) => {
  if (!error || typeof error !== 'object') return null
  return (error as { response?: { status?: number } }).response?.status ?? null
}

const loadAnalysis = async () => {
  if (isLoading.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    autoAnalysis.value = await getTrainAgentAutoAnalysis(props.taskId)
  } catch (autoAnalysisError) {
    if (getHttpStatus(autoAnalysisError) !== 404) {
      console.warn('加载自动训练分析失败，尝试读取规则分析:', autoAnalysisError)
    }
    try {
      const deterministicAnalysis = await getTrainAgentAnalysis(props.taskId)
      autoAnalysis.value = {
        status: 'FAILED',
        analysis: deterministicAnalysis,
        error_message: '该训练暂无自动总结，当前展示指标规则分析。',
      }
    } catch (deterministicAnalysisError) {
      console.error('加载训练指标规则分析失败:', deterministicAnalysisError)
      errorMessage.value = getErrorMessage(deterministicAnalysisError)
    }
  } finally {
    isLoading.value = false
    scheduleRefresh()
  }
}

const generateOptimizationProposal = async () => {
  if (isGeneratingOptimization.value) return
  isGeneratingOptimization.value = true
  errorMessage.value = ''
  optimizationMessage.value = ''
  try {
    const customInstruction = optimizationInstruction.value.trim()
    const instruction = customInstruction
      ? `基于本次训练报告生成下一轮优化训练参数草案。用户补充要求：${customInstruction}`
      : '基于本次训练报告生成下一轮优化训练参数草案'
    optimizationProposal.value = await createTrainAgentOptimizationProposal(
      props.taskId,
      instruction,
    )
  } catch (error) {
    console.error('生成下一轮优化训练草案失败:', error)
    errorMessage.value = getErrorMessage(error)
  } finally {
    isGeneratingOptimization.value = false
  }
}

const confirmAndEditOptimization = () => {
  const config = optimizationProposal.value?.config
  if (!config || !optimizationProposal.value?.ready_to_apply) return

  dialogVisible.value = false
  emit('edit', {
    config: config as TrainAgentConfig,
    sourceTrainTaskId: props.taskId,
  })
}

const confirmAndStartOptimization = async () => {
  const proposalId = optimizationProposal.value?.proposal_id
  const config = optimizationProposal.value?.config
  if (!proposalId || !config || isStartingOptimization.value) return
  isStartingOptimization.value = true
  errorMessage.value = ''
  try {
    const confirmation = await confirmTrainAgentProposal(proposalId, config as TrainAgentConfig)
    if (!confirmation.confirmation_token) {
      throw new Error('后端没有返回训练确认令牌')
    }
    const started = await startTrainAgentProposal(proposalId, confirmation.confirmation_token)
    if (typeof started.train_task_id !== 'number') {
      throw new Error('后端没有返回新训练任务 ID')
    }
    optimizationMessage.value = `下一轮训练任务 #${started.train_task_id} 已进入队列。`
    dialogVisible.value = false
    emit('started', started.train_task_id)
  } catch (error) {
    console.error('启动下一轮优化训练失败:', error)
    errorMessage.value = getErrorMessage(error)
  } finally {
    isStartingOptimization.value = false
  }
}

const clearRefreshTimer = () => {
  if (refreshTimer !== null) {
    window.clearTimeout(refreshTimer)
    refreshTimer = null
  }
}

const scheduleRefresh = () => {
  clearRefreshTimer()
  if (props.modelValue && isAnalysisPending.value) {
    refreshTimer = window.setTimeout(loadAnalysis, 3000)
  }
}

watch(
  () => [props.modelValue, props.taskId] as const,
  ([visible], previous) => {
    if (visible && (!autoAnalysis.value || previous?.[1] !== props.taskId)) {
      autoAnalysis.value = null
      optimizationProposal.value = null
      optimizationInstruction.value = ''
      optimizationMessage.value = ''
      loadAnalysis()
    } else if (!visible) {
      clearRefreshTimer()
    }
  },
)

onUnmounted(clearRefreshTimer)
</script>

<style scoped>
.analysis-dialog-card {
  display: flex;
  max-height: calc(100vh - 80px);
  flex-direction: column;
  overflow: hidden;
  background: var(--studio-surface-1) !important;
  border-color: var(--studio-hairline) !important;
}

.analysis-dialog-title {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  background: var(--studio-surface-1);
  border-bottom: 1px solid var(--studio-hairline);
}

.analysis-dialog-body {
  min-height: 360px;
  overflow-y: auto;
  padding: 18px 20px 20px;
  background: var(--studio-canvas);
}

.analysis-loading {
  display: flex;
  min-height: 320px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: rgba(var(--v-theme-on-surface), 0.62);
}

.analysis-content {
  display: grid;
  gap: 14px;
}

.analysis-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.analysis-summary-item,
.analysis-suggestions,
.analysis-extra,
.analysis-optimization,
.analysis-optimization-prompt,
.model-analysis-reply {
  padding: 16px;
  border: 1px solid var(--studio-hairline);
  border-radius: 9px;
  background: var(--studio-surface-1);
}

.analysis-optimization-prompt :deep(.v-field) {
  background: var(--studio-surface-2);
}

.optimization-change-list {
  display: grid;
  gap: 8px;
}

.optimization-change-item {
  display: grid;
  grid-template-columns: minmax(100px, 0.5fr) minmax(150px, 1fr) minmax(220px, 1.5fr);
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid rgba(var(--v-border-color), 0.16);
  border-radius: 6px;
}

.optimization-change-field {
  font-weight: 700;
}

.model-analysis-reply {
  padding: 18px 20px;
  background: var(--studio-surface-2);
  line-height: 1.72;
}

.model-analysis-reply :deep(.markdown-text) {
  gap: 10px;
  color: var(--studio-ink-muted);
  font-size: 13px;
  line-height: 1.72;
}

.model-analysis-reply :deep(.markdown-heading) {
  margin-top: 4px;
  color: var(--studio-ink);
  font-size: 14px;
  font-weight: 600;
}

.model-analysis-reply :deep(.markdown-paragraph),
.model-analysis-reply :deep(.markdown-list-item p) {
  color: var(--studio-ink-muted);
  font-weight: 400;
}

.model-analysis-reply :deep(strong) {
  color: var(--studio-ink);
  font-weight: 600;
}

.analysis-item-label {
  margin-bottom: 6px;
  color: rgba(var(--v-theme-on-surface), 0.58);
  font-size: 12px;
}

.analysis-item-value {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
}

.analysis-section-title {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 12px;
  color: var(--studio-ink);
  font-weight: 600;
}

.suggestion-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 8px;
  padding: 7px 0;
  line-height: 1.5;
}

.suggestion-row > span {
  display: flex;
  width: 22px;
  height: 22px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(var(--v-theme-warning), 0.16);
  color: rgb(var(--v-theme-warning));
  font-size: 12px;
  font-weight: 700;
}

.analysis-extra-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.analysis-extra-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(var(--v-border-color), 0.16);
  border-radius: 6px;
  background: rgba(var(--v-theme-surface), 0.34);
}

.analysis-extra-card--wide {
  grid-column: 1 / -1;
}

.analysis-extra-label {
  margin-bottom: 8px;
  color: rgba(var(--v-theme-on-surface), 0.58);
  font-size: 12px;
  font-weight: 600;
}

.analysis-extra-value {
  font-weight: 600;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.analysis-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  overflow: hidden;
  border: 1px solid rgba(var(--v-border-color), 0.14);
  border-radius: 5px;
  background: rgba(var(--v-border-color), 0.14);
}

.analysis-detail-item {
  display: grid;
  grid-template-columns: minmax(110px, 0.9fr) minmax(0, 1.1fr);
  gap: 8px;
  padding: 8px 10px;
  background: rgb(var(--v-theme-surface));
}

.analysis-detail-item span {
  color: rgba(var(--v-theme-on-surface), 0.58);
  font-size: 12px;
}

.analysis-detail-item strong {
  font-size: 13px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.analysis-json {
  max-height: 300px;
  margin: 0;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  white-space: pre-wrap;
}

.analysis-dialog-actions {
  flex: 0 0 auto;
  padding: 12px 20px;
  background: var(--studio-surface-1);
  border-top: 1px solid var(--studio-hairline);
}

@media (max-width: 620px) {
  .analysis-summary-grid {
    grid-template-columns: 1fr;
  }

  .analysis-extra-list,
  .analysis-detail-grid {
    grid-template-columns: 1fr;
  }

  .analysis-detail-item {
    grid-template-columns: 1fr;
    gap: 3px;
  }

  .optimization-change-item {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>
