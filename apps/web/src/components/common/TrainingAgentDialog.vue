<template>
  <v-dialog v-model="dialogVisible" max-width="980" persistent>
    <v-card class="agent-dialog-card" rounded="lg">
      <v-card-title class="agent-dialog-title">
        <div>
          <div class="agent-dialog-heading">智能训练建议</div>
          <div class="agent-dialog-subtitle">结合当前数据集和参数生成训练草案</div>
        </div>
        <v-btn icon="mdi-close" variant="text" size="small" @click="closeDialog" />
      </v-card-title>

      <div class="agent-dialog-separator" />

      <v-card-text class="agent-dialog-body pa-0">
        <aside class="agent-context-panel">
          <div class="agent-section-title">
            <span>数据集画像</span>
            <v-btn
              icon="mdi-refresh"
              variant="text"
              size="x-small"
              :loading="isLoadingContext"
              title="刷新数据集画像"
              @click="loadContext"
            />
          </div>

          <div v-if="isLoadingContext" class="agent-loading">
            <v-progress-circular indeterminate size="22" />
            <span>正在分析数据集...</span>
          </div>
          <v-alert v-else-if="contextError" type="warning" variant="tonal" density="compact">
            {{ contextError }}
          </v-alert>
          <div v-else-if="datasetContext" class="context-content">
            <div class="context-stats">
              <div v-for="item in contextStats" :key="item.label" class="context-stat">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>

            <div v-for="item in contextDetails" :key="item.label" class="context-detail">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }}</strong>
            </div>

            <v-expansion-panels
              variant="accordion"
              density="compact"
              class="context-raw agent-expansion-panels"
            >
              <v-expansion-panel title="查看完整画像">
                <v-expansion-panel-text>
                  <pre>{{ formatJson(datasetContext) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
          <div v-else class="agent-empty-small">打开面板后会自动读取当前任务的数据集信息。</div>

          <div class="context-separator" />

          <div class="agent-section-title">训练目标</div>
          <v-textarea
            v-model="userMessage"
            variant="outlined"
            rows="5"
            auto-grow
            hide-details
            placeholder="例如：小目标较多，希望准确率优先，训练时间可以长一些。"
          />
          <div class="quick-prompts">
            <v-chip
              v-for="prompt in quickPrompts"
              :key="prompt"
              size="small"
              variant="tonal"
              class="quick-prompt-chip"
              @click="userMessage = prompt"
            >
              {{ prompt }}
            </v-chip>
          </div>

          <v-btn
            block
            color="primary"
            prepend-icon="mdi-auto-fix"
            :loading="isGenerating"
            :disabled="!userMessage.trim()"
            @click="generateProposal"
          >
            生成训练建议
          </v-btn>
        </aside>

        <main class="agent-proposal-panel">
          <div class="agent-section-title">
            <span>参数草案</span>
            <v-chip v-if="proposalConfig" size="small" color="success" variant="tonal">
              {{ proposalEntries.length }} 项参数
            </v-chip>
          </div>

          <div v-if="isGenerating" class="agent-proposal-empty">
            <v-progress-circular indeterminate color="primary" size="32" />
            <div>Agent 正在整理数据集和训练参数...</div>
          </div>
          <div v-else-if="proposalConfig" class="proposal-content">
            <v-alert v-if="agentReply" color="primary" variant="tonal" density="comfortable">
              <MarkdownText :content="agentReply" />
            </v-alert>

            <div class="proposal-table-wrap">
              <table class="proposal-table">
                <thead>
                  <tr>
                    <th>参数</th>
                    <th>当前值</th>
                    <th>建议值</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="item in proposalEntries"
                    :key="item.key"
                    :class="{ changed: item.changed }"
                  >
                    <td>{{ item.key }}</td>
                    <td>{{ item.currentValue }}</td>
                    <td>{{ item.proposedValue }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <v-expansion-panels
              variant="accordion"
              density="compact"
              class="agent-expansion-panels"
            >
              <v-expansion-panel title="查看草案 JSON">
                <v-expansion-panel-text>
                  <pre class="proposal-json">{{ formatJson(proposalConfig) }}</pre>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>
          <div v-else class="agent-proposal-empty">
            <v-icon icon="mdi-lightbulb-on-outline" size="48" color="grey" />
            <div class="text-body-1">还没有生成参数建议</div>
            <div class="text-caption text-medium-emphasis">
              在左侧描述训练目标，Agent 只会生成草案，不会自动启动训练。
            </div>
          </div>
        </main>
      </v-card-text>

      <v-card-actions class="agent-dialog-actions">
        <v-btn variant="text" @click="closeDialog">关闭</v-btn>
        <v-spacer />
        <v-btn variant="tonal" color="primary" :disabled="!proposalConfig" @click="applyProposal">
          应用到参数
        </v-btn>
        <v-btn
          color="primary"
          :loading="isStarting"
          :disabled="!canStartProposal"
          @click="confirmAndStart"
        >
          确认并按建议启动
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  chatWithTrainAgent,
  confirmTrainAgentProposal,
  getTrainAgentContext,
  startTrainAgentProposal,
} from '@/api/services'
import type { TrainAgentConfig, TrainAgentContext } from '@/types/trainAgent'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'
import MarkdownText from '@/components/common/MarkdownText.vue'

const props = defineProps<{
  modelValue: boolean
  taskName: string
  currentConfig: TrainAgentConfig
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'apply', config: TrainAgentConfig): void
  (event: 'started', taskId?: number): void
}>()

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()
const datasetContext = ref<TrainAgentContext | null>(null)
const contextError = ref('')
const isLoadingContext = ref(false)
const isGenerating = ref(false)
const isStarting = ref(false)
const userMessage = ref('')
const sessionId = ref<string | null>(null)
const proposalId = ref('')
const proposalConfig = ref<TrainAgentConfig | null>(null)
const agentReply = ref('')

const quickPrompts = ['准确率优先', '小目标较多', '训练速度优先']

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const pickNumber = (source: TrainAgentContext, keys: string[]) => {
  for (const key of keys) {
    const value = source[key]
    if (typeof value === 'number') return value
  }
  return null
}

const collectionSize = (value: unknown) => {
  if (Array.isArray(value)) return value.length
  if (value && typeof value === 'object') return Object.keys(value).length
  return null
}

const contextStats = computed(() => {
  if (!datasetContext.value) return []
  const context = datasetContext.value
  const images = pickNumber(context, ['image_count', 'total_images', 'images_count'])
  const annotations = pickNumber(context, [
    'annotation_count',
    'total_annotations',
    'annotations_count',
  ])
  const categories = collectionSize(
    context.category_distribution ?? context.categories ?? context.class_distribution,
  )

  return [
    { label: '图片', value: images ?? '-' },
    { label: '标注', value: annotations ?? '-' },
    { label: '类别', value: categories ?? '-' },
  ]
})

const summarizeValue = (value: unknown) => {
  if (Array.isArray(value)) return value.map(String).join('、') || '-'
  if (value && typeof value === 'object') {
    return Object.entries(value)
      .slice(0, 4)
      .map(([key, item]) => `${key}: ${String(item)}`)
      .join('；')
  }
  return value === undefined || value === null || value === '' ? '-' : String(value)
}

const contextDetails = computed(() => {
  if (!datasetContext.value) return []
  const context = datasetContext.value
  return [
    {
      label: '目标尺寸',
      value: summarizeValue(context.object_size_distribution ?? context.size_distribution),
    },
    {
      label: '可用模型',
      value: summarizeValue(context.available_models ?? context.models),
    },
  ]
})

const formatValue = (value: unknown) => {
  if (value === undefined) return '未设置'
  if (typeof value === 'string') return value
  return JSON.stringify(value)
}

const proposalEntries = computed(() => {
  if (!proposalConfig.value) return []
  return Object.entries(proposalConfig.value).map(([key, value]) => {
    const current = props.currentConfig[key]
    return {
      key,
      currentValue: formatValue(current),
      proposedValue: formatValue(value),
      changed: JSON.stringify(current) !== JSON.stringify(value),
    }
  })
})

const canStartProposal = computed(
  () => Boolean(proposalConfig.value && proposalId.value) && !isStarting.value,
)

const formatJson = (value: unknown) => JSON.stringify(value, null, 2)

const getErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === 'string' && error) return error
  if (error instanceof Error && error.message) return error.message
  if (error && typeof error === 'object') {
    const response = (error as { response?: { data?: { message?: string; detail?: string } } })
      .response
    return response?.data?.message || response?.data?.detail || fallback
  }
  return fallback
}

const loadContext = async () => {
  if (!props.taskName || isLoadingContext.value) return
  isLoadingContext.value = true
  contextError.value = ''
  try {
    datasetContext.value = await getTrainAgentContext(props.taskName)
  } catch (error) {
    console.error('加载训练 Agent 数据集画像失败:', error)
    contextError.value = getErrorMessage(error, '数据集画像加载失败')
  } finally {
    isLoadingContext.value = false
  }
}

const generateProposal = async () => {
  const message = userMessage.value.trim()
  if (!message || isGenerating.value) return
  isGenerating.value = true
  try {
    const response = await chatWithTrainAgent({
      session_id: sessionId.value,
      task_name: props.taskName,
      message,
      current_config: props.currentConfig,
      train_task_id: null,
    })
    sessionId.value = response.session_id ?? sessionId.value
    proposalId.value = typeof response.proposal_id === 'string' ? response.proposal_id : ''
    proposalConfig.value =
      response.config && typeof response.config === 'object' ? response.config : null
    agentReply.value = String(response.message ?? response.reply ?? response.content ?? '')

    if (!proposalConfig.value) {
      throw new Error('Agent 没有返回可用的训练参数草案')
    }
  } catch (error) {
    console.error('生成训练参数建议失败:', error)
    snackbar.showSnackbar(getErrorMessage(error, '生成训练建议失败'), 'error')
  } finally {
    isGenerating.value = false
  }
}

const applyProposal = () => {
  if (!proposalConfig.value) return
  emit('apply', proposalConfig.value)
  snackbar.showSnackbar('Agent 参数已同步到训练配置', 'success')
}

const confirmAndStart = async () => {
  if (!proposalConfig.value || !proposalId.value || isStarting.value) return
  const confirmed = await confirmDialog.showConfirm(
    '确认按建议启动训练',
    '将使用当前 Agent 草案启动训练。确认后参数草案不能修改，确认令牌仅可使用一次。',
  )
  if (!confirmed) return

  isStarting.value = true
  try {
    const confirmResponse = await confirmTrainAgentProposal(proposalId.value, proposalConfig.value)
    const token = confirmResponse.confirmation_token
    if (!token) throw new Error('确认接口没有返回 confirmation_token')

    const startResponse = await startTrainAgentProposal(proposalId.value, token)
    snackbar.showSnackbar('Agent 训练任务已创建', 'success')
    emit('started', startResponse.train_task_id ?? startResponse.task_id ?? startResponse.id)
    closeDialog()
  } catch (error) {
    console.error('按 Agent 建议启动训练失败:', error)
    snackbar.showSnackbar(getErrorMessage(error, '启动训练失败'), 'error')
  } finally {
    isStarting.value = false
  }
}

const closeDialog = () => {
  if (!isStarting.value) dialogVisible.value = false
}

watch(
  () => props.modelValue,
  (visible) => {
    if (visible && !datasetContext.value) loadContext()
  },
)
</script>

<style scoped>
.agent-dialog-card {
  display: flex;
  max-height: calc(100vh - 72px);
  flex-direction: column;
  overflow: hidden;
  background: var(--studio-surface-1) !important;
  border-radius: 10px !important;
}

.agent-dialog-title,
.agent-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.agent-dialog-title {
  min-height: 58px;
  flex: 0 0 auto;
  padding: 10px 14px 10px 16px;
  background: var(--studio-surface-1);
}

.agent-dialog-heading {
  color: var(--studio-ink);
  font-size: 15px;
  font-weight: 600;
  line-height: 1.35;
}

.agent-dialog-subtitle {
  margin-top: 2px;
  color: var(--studio-ink-tertiary);
  font-size: 11px;
  font-weight: 400;
  line-height: 1.3;
}

.agent-dialog-separator {
  width: 100%;
  height: 1px;
  flex: 0 0 1px;
  background: var(--studio-hairline);
}

.agent-dialog-body {
  display: grid;
  min-height: 0;
  grid-template-columns: 320px minmax(0, 1fr);
  overflow: hidden;
  background: var(--studio-canvas);
}

.agent-context-panel,
.agent-proposal-panel {
  min-height: 0;
  padding: 18px;
  overflow-y: auto;
}

.agent-context-panel {
  border-right: 1px solid var(--studio-hairline);
  background: var(--studio-surface-1);
}

.agent-section-title {
  margin-bottom: 12px;
  color: var(--studio-ink-muted);
  font-size: 13px;
  font-weight: 600;
}

.agent-loading,
.agent-empty-small {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 70px;
  color: var(--studio-ink-subtle);
  font-size: 13px;
}

.context-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.context-stat {
  display: flex;
  min-width: 0;
  padding: 9px 6px;
  flex-direction: column;
  align-items: center;
  border: 1px solid var(--studio-hairline);
  border-radius: 6px;
  background: var(--studio-surface-2);
}

.context-stat span,
.context-detail span {
  color: var(--studio-ink-tertiary);
  font-size: 11px;
}

.context-stat strong {
  margin-top: 3px;
  color: var(--studio-ink);
  font-size: 16px;
  font-weight: 600;
}

.context-detail {
  display: grid;
  gap: 4px;
  margin-top: 12px;
}

.context-detail strong {
  color: var(--studio-ink-muted);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.context-raw {
  margin-top: 12px;
}

.context-separator {
  width: 100%;
  height: 1px;
  margin: 16px 0;
  background: var(--studio-hairline);
}

.agent-context-panel :deep(.v-field) {
  background: var(--studio-canvas);
}

.context-raw pre,
.proposal-json {
  max-height: 260px;
  margin: 0;
  overflow: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  white-space: pre-wrap;
}

.quick-prompts {
  display: flex;
  gap: 6px;
  margin: 10px 0 14px;
  flex-wrap: wrap;
}

.quick-prompt-chip {
  color: var(--studio-ink-subtle) !important;
  background: var(--studio-surface-2) !important;
  border: 1px solid var(--studio-hairline);
}

.quick-prompt-chip:hover {
  color: var(--studio-ink-muted) !important;
  border-color: var(--studio-hairline-strong);
}

.agent-proposal-panel {
  display: flex;
  flex-direction: column;
  background: var(--studio-canvas);
}

.agent-proposal-empty {
  display: flex;
  flex: 1;
  min-height: 340px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--studio-ink-subtle);
  text-align: center;
}

.agent-proposal-empty :deep(.v-icon) {
  color: var(--studio-ink-tertiary) !important;
}

.proposal-content {
  display: grid;
  gap: 14px;
}

.proposal-content :deep(.v-alert) {
  color: var(--studio-ink-muted);
  background: rgba(94, 106, 210, 0.08);
  border: 1px solid rgba(94, 106, 210, 0.2);
}

.proposal-table-wrap {
  overflow: auto;
  border: 1px solid var(--studio-hairline);
  border-radius: 6px;
  background: var(--studio-surface-1);
}

.proposal-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 13px;
}

.proposal-table th,
.proposal-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--studio-hairline);
  text-align: left;
  overflow-wrap: anywhere;
}

.proposal-table th {
  color: var(--studio-ink-subtle);
  background: var(--studio-surface-2);
  font-size: 11px;
  font-weight: 500;
}

.proposal-table td {
  color: var(--studio-ink-muted);
}

.proposal-table tr:last-child td {
  border-bottom: 0;
}

.proposal-table tr.changed td:last-child {
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}

.agent-dialog-actions {
  min-height: 60px;
  flex: 0 0 auto;
  padding: 10px 14px;
  border-top: 1px solid var(--studio-hairline);
  background: var(--studio-surface-1);
}

.agent-expansion-panels {
  overflow: hidden;
  border: 1px solid var(--studio-hairline);
  border-radius: 7px;
  box-shadow: none !important;
}

.agent-expansion-panels :deep(.v-expansion-panel) {
  color: var(--studio-ink-muted);
  background: var(--studio-surface-1);
  box-shadow: none !important;
}

.agent-expansion-panels :deep(.v-expansion-panel-title) {
  min-height: 44px;
  padding: 0 12px;
  color: var(--studio-ink-muted);
  font-size: 12px;
}

.agent-expansion-panels :deep(.v-expansion-panel-title:hover),
.agent-expansion-panels :deep(.v-expansion-panel-title--active) {
  background: var(--studio-surface-2);
}

.agent-expansion-panels :deep(.v-expansion-panel-title__overlay) {
  opacity: 0 !important;
}

.agent-expansion-panels :deep(.v-expansion-panel-text__wrapper) {
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.18);
}

@media (max-width: 760px) {
  .agent-dialog-body {
    display: block;
    overflow-y: auto;
  }

  .agent-context-panel,
  .agent-proposal-panel {
    overflow: visible;
  }

  .agent-context-panel {
    border-right: 0;
    border-bottom: 1px solid var(--studio-hairline);
  }
}
</style>
