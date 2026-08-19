<template>
  <v-card class="train-monitor" rounded="lg">
    <div class="monitor-header d-flex align-center justify-space-between">
      <span class="monitor-title">训练监控</span>
      <div class="monitor-actions">
        <button
          v-if="trainStatus === 'FINISHED'"
          type="button"
          class="monitor-action"
          @click="showAnalysisDialog = true"
        >
          训练分析
        </button>
        <button
          v-if="trainStatus === 'FINISHED' && modelOutputPath"
          type="button"
          class="monitor-action is-success"
          :disabled="isDownloading"
          @click="downloadModel"
        >
          下载模型
        </button>
        <span class="monitor-status-chip" :class="`is-${(trainStatus || 'default').toLowerCase()}`">
          <span class="monitor-status-dot" />
          {{ statusTextMap[trainStatus] || trainStatus || '--' }}
        </span>
        <button
          v-if="trainStatus === 'FINISHED' || trainStatus === 'ERROR'"
          type="button"
          class="monitor-action"
          @click="loadMetrics"
        >
          刷新指标
        </button>
      </div>
    </div>

    <v-card-text class="monitor-content">
      <!-- 进度条 -->
      <div v-if="currentEpoch > 0" class="mb-6">
        <div class="d-flex justify-space-between text-body-2 text-medium-emphasis mb-2">
          <span>进度: {{ currentEpoch }} / {{ totalEpochs }} 轮</span>
          <span>{{ progressPercent }}%</span>
        </div>
        <v-progress-linear :model-value="progressPercent" color="primary" height="12" rounded />
      </div>

      <!-- 错误信息 -->
      <v-alert v-if="trainStatus === 'ERROR'" type="error" variant="tonal" class="mb-6">
        <strong>训练错误：</strong>{{ errorMessage }}
      </v-alert>

      <!-- 折线图区域 -->
      <div v-if="metrics.length > 0" class="charts-section mb-6">
        <v-card
          v-for="chart in chartConfigs"
          :key="chart.title"
          variant="outlined"
          rounded="lg"
          class="pa-4"
        >
          <div class="chart-header mb-2">
            <span class="text-subtitle-2 font-weight-bold">{{ chart.title }}</span>
            <v-tooltip location="top" max-width="320" content-class="metric-tooltip-content">
              <template #activator="{ props: tooltipProps }">
                <button
                  v-bind="tooltipProps"
                  type="button"
                  class="metric-help"
                  :aria-label="`${chart.title}指标说明`"
                >
                  <Icon name="help" :size="16" />
                </button>
              </template>
              <div class="metric-tooltip">
                <div class="metric-tooltip-section metric-tooltip-simple">
                  <div class="metric-tooltip-title">通俗看法</div>
                  <div v-for="line in chart.simpleHelp" :key="line">{{ line }}</div>
                </div>
                <div class="metric-tooltip-section metric-tooltip-professional">
                  <div class="metric-tooltip-title">专业参考</div>
                  <div v-for="line in chart.professionalHelp" :key="line">{{ line }}</div>
                </div>
              </div>
            </v-tooltip>
          </div>
          <v-chart class="chart" :option="chart.option.value" autoresize />
        </v-card>
      </div>

      <!-- 等待数据 -->
      <div
        v-if="metrics.length === 0 && isActiveTrainStatus(trainStatus)"
        class="d-flex align-center justify-center pa-10 text-grey"
      >
        <v-progress-circular indeterminate size="24" class="mr-3" />
        {{ waitingStatusText }}
      </div>
    </v-card-text>

    <TrainingAnalysisDialog
      v-model="showAnalysisDialog"
      :task-id="taskId"
      @started="handleOptimizationStarted"
    />
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import TrainingAnalysisDialog from '@/components/common/TrainingAnalysisDialog.vue'
import { refreshSession } from '@/api/session'
import type { TrainTaskStatus, TrainEpochMetric, TrainStreamData } from '@/types/train'
import type { ComposeOption } from 'echarts/core'
import type { LineSeriesOption } from 'echarts/charts'
import type {
  TitleComponentOption,
  TooltipComponentOption,
  LegendComponentOption,
  GridComponentOption,
  DataZoomComponentOption,
} from 'echarts/components'
import {
  getTrainStatus,
  getTrainMetrics,
  createTrainEventSource,
  getModelDownloadUrl,
} from '@/api/services'
import { Icon } from '@/components/icons'

type ECOption = ComposeOption<
  | LineSeriesOption
  | TitleComponentOption
  | TooltipComponentOption
  | LegendComponentOption
  | GridComponentOption
  | DataZoomComponentOption
>

use([
  CanvasRenderer,
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
])

const props = defineProps<{
  taskId: number
}>()

const emit = defineEmits<{
  (
    e: 'progress',
    payload: {
      id: number
      status: string
      currentEpoch: number
      totalEpochs: number
      progress: number
    },
  ): void
  (e: 'started', taskId: number): void
}>()

const trainStatus = ref<TrainTaskStatus | ''>('')
const currentEpoch = ref(0)
const totalEpochs = ref(0)
const metrics = ref<TrainEpochMetric[]>([])
const errorMessage = ref('')
const modelOutputPath = ref('')
const isDownloading = ref(false)
const showAnalysisDialog = ref(false)

const handleOptimizationStarted = (taskId: number) => {
  showAnalysisDialog.value = false
  emit('started', taskId)
}

let eventSource: EventSource | null = null

const statusTextMap: Record<string, string> = {
  PENDING: '等待中',
  QUEUED: '排队中',
  CLAIMED: '已领取',
  RECOVERING: '恢复训练中',
  RUNNING: '训练中',
  FINISHED: '已完成',
  ERROR: '错误',
  CANCELLED: '已取消',
}

const statusChipColor = computed(() => {
  const map: Record<string, string> = {
    PENDING: 'warning',
    QUEUED: 'warning',
    CLAIMED: 'info',
    RECOVERING: 'info',
    RUNNING: 'info',
    FINISHED: 'success',
    ERROR: 'error',
    CANCELLED: 'grey',
  }
  return map[trainStatus.value] || 'default'
})

const activeTrainStatuses = new Set<TrainTaskStatus>([
  'PENDING',
  'QUEUED',
  'CLAIMED',
  'RECOVERING',
  'RUNNING',
])

const isActiveTrainStatus = (status: TrainTaskStatus | '') =>
  Boolean(status && activeTrainStatuses.has(status))

const waitingStatusText = computed(() => {
  const messages: Partial<Record<TrainTaskStatus, string>> = {
    PENDING: '等待训练任务进入队列...',
    QUEUED: '正在排队，等待 GPU Worker...',
    CLAIMED: 'GPU Worker 已领取任务，正在准备训练...',
    RECOVERING: '正在从断点恢复训练...',
    RUNNING: '等待训练指标...',
  }
  return trainStatus.value ? messages[trainStatus.value] || '等待训练数据...' : '等待训练数据...'
})

const progressPercent = computed(() => {
  if (totalEpochs.value === 0) return 0
  return Math.round((currentEpoch.value / totalEpochs.value) * 100)
})

// 从 metrics 中提取数据序列
const extractSeries = (
  keys: { label: string; key: string }[],
): { name: string; data: (number | null)[] }[] => {
  return keys.map((k) => ({
    name: k.label,
    data: metrics.value.map((m) => {
      const v = m[k.key]
      return typeof v === 'number' ? v : null
    }),
  }))
}

const epochs = computed(() => metrics.value.map((m) => m.epoch))

const hasMetricValue = (key: keyof TrainEpochMetric) =>
  metrics.value.some((metric) => typeof metric[key] === 'number')

// ECharts 主题 — Paper + Ink + Cinnabar
const ECHARTS_PALETTE = ['#cf4a36', '#5e6b55', '#8a6e4b', '#b08a3a', '#7b2519', '#d97757']

const ECHARTS_THEME = {
  ink: '#4a4036',
  paper: '#f5f0e6',
  muted: 'rgba(74, 64, 54, 0.5)',
  line: 'rgba(74, 64, 54, 0.17)',
  faint: 'rgba(74, 64, 54, 0.08)',
  accent: '#cf4a36',
} as const

// 通用的折线图配置生成
const makeChartOption = (
  keys: { label: string; key: string }[],
  yName: string,
  decimals: number = 4,
): ECOption => {
  const series = extractSeries(keys)
  return {
    color: ECHARTS_PALETTE,
    tooltip: {
      trigger: 'axis',
      backgroundColor: ECHARTS_THEME.ink,
      borderColor: ECHARTS_THEME.ink,
      textStyle: { color: ECHARTS_THEME.paper, fontSize: 12, fontFamily: 'DM Sans, system-ui' },
      valueFormatter: (val: unknown) => (typeof val === 'number' ? val.toFixed(decimals) : '-'),
    },
    legend: {
      data: keys.map((k) => k.label),
      top: 0,
      textStyle: { color: ECHARTS_THEME.muted, fontSize: 12 },
    },
    grid: {
      left: 60,
      right: 20,
      top: 40,
      bottom: 50,
    },
    xAxis: {
      type: 'category',
      data: epochs.value,
      name: 'Epoch',
      nameLocation: 'middle',
      nameGap: 25,
      axisLine: { lineStyle: { color: ECHARTS_THEME.line } },
      axisLabel: { color: ECHARTS_THEME.muted },
      nameTextStyle: { color: ECHARTS_THEME.muted, fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      name: yName,
      nameTextStyle: { color: ECHARTS_THEME.muted, fontSize: 12 },
      axisLine: { lineStyle: { color: ECHARTS_THEME.line } },
      axisLabel: { color: ECHARTS_THEME.muted },
      splitLine: { lineStyle: { color: ECHARTS_THEME.faint } },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 5,
        borderColor: ECHARTS_THEME.line,
        backgroundColor: 'transparent',
        fillerColor: 'rgba(207, 74, 54, 0.18)',
        textStyle: { color: ECHARTS_THEME.muted },
        handleStyle: { color: ECHARTS_THEME.paper, borderColor: ECHARTS_THEME.line },
      },
    ],
    series: series.map((s, i) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      lineStyle: { width: 1.8, color: ECHARTS_PALETTE[i % ECHARTS_PALETTE.length] },
      itemStyle: { color: ECHARTS_PALETTE[i % ECHARTS_PALETTE.length] },
    })),
  }
}

const trainLossOption = computed(() =>
  makeChartOption(
    [
      { label: '边框损失（train_box_loss）', key: 'train_box_loss' },
      ...(hasMetricValue('train_seg_loss')
        ? [{ label: '分割损失（train_seg_loss）', key: 'train_seg_loss' }]
        : []),
      { label: '分类损失（train_cls_loss）', key: 'train_cls_loss' },
      { label: '分布损失（train_dfl_loss）', key: 'train_dfl_loss' },
    ],
    'Loss',
  ),
)

const valLossOption = computed(() =>
  makeChartOption(
    [
      { label: '边框损失（val_box_loss）', key: 'val_box_loss' },
      ...(hasMetricValue('val_seg_loss')
        ? [{ label: '分割损失（val_seg_loss）', key: 'val_seg_loss' }]
        : []),
      { label: '分类损失（val_cls_loss）', key: 'val_cls_loss' },
      { label: '分布损失（val_dfl_loss）', key: 'val_dfl_loss' },
    ],
    'Loss',
  ),
)

const precisionOption = computed(() =>
  makeChartOption(
    [
      { label: '精确率（precision）', key: 'precision' },
      { label: '召回率（recall）', key: 'recall' },
      { label: '平均精度50（map50）', key: 'map50' },
      { label: '平均精度50-95（map50_95）', key: 'map50_95' },
    ],
    'Value',
  ),
)

const hasMaskMetrics = computed(() =>
  ['mask_precision', 'mask_recall', 'mask_map50', 'mask_map50_95'].some((key) =>
    hasMetricValue(key as keyof TrainEpochMetric),
  ),
)

const maskPrecisionOption = computed(() =>
  makeChartOption(
    [
      { label: '轮廓精确率（mask_precision）', key: 'mask_precision' },
      { label: '轮廓召回率（mask_recall）', key: 'mask_recall' },
      { label: '轮廓平均精度50（mask_map50）', key: 'mask_map50' },
      { label: '轮廓平均精度50-95（mask_map50_95）', key: 'mask_map50_95' },
    ],
    'Value',
  ),
)

const lrOption = computed(() =>
  makeChartOption(
    [
      { label: '学习率组0（lr_pg0）', key: 'lr_pg0' },
      { label: '学习率组1（lr_pg1）', key: 'lr_pg1' },
      { label: '学习率组2（lr_pg2）', key: 'lr_pg2' },
    ],
    'LR',
    6,
  ),
)

const chartConfigs = computed(() => {
  const charts = [
    {
      title: '训练损失',
      option: trainLossOption,
      simpleHelp: ['合格形状：一路往下，最后变平。', '不合格：上下乱跳，或者后面又升高。'],
      professionalHelp: [
        '整体应持续下降并趋于平稳。',
        '后期明显反弹，可能是学习率偏高或数据不稳定。',
        '训练损失低但验证损失高，可能过拟合。',
      ],
    },
    {
      title: '验证损失',
      option: valLossOption,
      simpleHelp: ['合格形状：整体往下，最后稳定。', '不合格：一直升高，或长期不下降。'],
      professionalHelp: [
        '应随训练下降，并在后期接近稳定。',
        '持续升高通常表示泛化较差。',
        '长期不下降建议检查标注质量和类别分布。',
      ],
    },
    {
      title: '检测框精度',
      option: precisionOption,
      simpleHelp: [
        '合格形状：几条线往上升，最后接近平稳。',
        '参考值：precision、recall、map50 越接近 1 越好。',
        '不合格：长期很低，或后面明显下降。',
      ],
      professionalHelp: [
        'precision：建议 >= 0.80，越高误检越少。',
        'recall：建议 >= 0.80，越高漏检越少。',
        'map50：建议 >= 0.75；map50_95：建议 >= 0.50。',
      ],
    },
  ]

  if (hasMaskMetrics.value) {
    charts.push({
      title: '分割轮廓精度',
      option: maskPrecisionOption,
      simpleHelp: [
        '合格形状：几条线往上升，最后接近平稳。',
        '分割任务主要看 mask_map50_95，越高越好。',
      ],
      professionalHelp: [
        'mask_precision 越高，轮廓误检越少。',
        'mask_recall 越高，轮廓漏检越少。',
        '分割模型应优先使用 mask_map50_95 判断整体质量。',
      ],
    })
  }

  charts.push({
    title: '学习率',
    option: lrOption,
    simpleHelp: ['合格形状：平滑变化，不突然乱跳。', '不合格：曲线突然大幅跳动。'],
    professionalHelp: [
      '应按训练计划平滑变化。',
      '损失剧烈震荡时，通常需要降低学习率。',
      '学习率过低会导致收敛很慢。',
    ],
  })

  return charts
})

const parseTrainStreamData = (raw: string): TrainStreamData | null => {
  try {
    return JSON.parse(raw) as TrainStreamData
  } catch {
    try {
      const normalized = raw
        .replace(/(:\s*)(NaN|Infinity|-Infinity)(?=\s*[,}\]])/g, '$1null')
        .replace(/([\[,]\s*)(NaN|Infinity|-Infinity)(?=\s*[,}\]])/g, '$1null')
      return JSON.parse(normalized) as TrainStreamData
    } catch (err) {
      console.error('解析训练 SSE 数据失败:', err, raw)
      return null
    }
  }
}

// SSE 连接
const closeSSE = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

const connectSSE = async () => {
  closeSSE()

  try {
    await refreshSession()
  } catch (error) {
    console.error('训练监控会话续期失败:', error)
    window.dispatchEvent(new CustomEvent('studio:session-expired'))
    return
  }

  eventSource = createTrainEventSource(props.taskId)

  eventSource.onmessage = (event) => {
    const data = parseTrainStreamData(event.data)
    if (!data) return

    if (data.status === 'FINISHED') {
      trainStatus.value = 'FINISHED'
      if (data.metrics) metrics.value = data.metrics
      if (data.s3_model_url) modelOutputPath.value = data.s3_model_url
      emit('progress', {
        id: props.taskId,
        status: 'FINISHED',
        currentEpoch: currentEpoch.value,
        totalEpochs: totalEpochs.value,
        progress: 100,
      })
      closeSSE()
    } else if (data.status === 'ERROR') {
      trainStatus.value = 'ERROR'
      errorMessage.value = data.error_message || '训练出错'
      emit('progress', {
        id: props.taskId,
        status: 'ERROR',
        currentEpoch: currentEpoch.value,
        totalEpochs: totalEpochs.value,
        progress: 0,
      })
      closeSSE()
    } else {
      const nextStatus = data.status as TrainTaskStatus
      trainStatus.value = activeTrainStatuses.has(nextStatus) ? nextStatus : 'RUNNING'
      if (data.epoch) currentEpoch.value = data.epoch
      if (data.total_epochs) totalEpochs.value = data.total_epochs
      if (data.metrics) metrics.value = data.metrics
      const pct =
        totalEpochs.value > 0 ? Math.round((currentEpoch.value / totalEpochs.value) * 100) : 0
      emit('progress', {
        id: props.taskId,
        status: trainStatus.value,
        currentEpoch: currentEpoch.value,
        totalEpochs: totalEpochs.value,
        progress: pct,
      })
    }
  }

  eventSource.onerror = () => {
    closeSSE()
  }
}

const loadMetrics = async () => {
  try {
    const res = await getTrainMetrics(props.taskId)
    if (res.task) {
      trainStatus.value = res.task.status
      currentEpoch.value = res.task.current_epoch
      totalEpochs.value = res.task.total_epochs
      modelOutputPath.value = res.task.output_path || ''
      errorMessage.value = res.task.error_message || ''
    }
    if (res.metrics) {
      metrics.value = res.metrics
    }
  } catch (err) {
    console.error('Failed to load metrics:', err)
  }
}

const downloadModel = async () => {
  if (isDownloading.value) return
  isDownloading.value = true
  try {
    const res = await getModelDownloadUrl(props.taskId)
    const a = document.createElement('a')
    a.href = res.download_url
    a.download = res.filename
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } catch (err) {
    console.error('Failed to get download URL:', err)
  } finally {
    isDownloading.value = false
  }
}

onMounted(async () => {
  try {
    const task = await getTrainStatus(props.taskId)
    trainStatus.value = task.status
    currentEpoch.value = task.current_epoch
    totalEpochs.value = task.total_epochs
    modelOutputPath.value = task.output_path || ''
    errorMessage.value = task.error_message || ''

    if (isActiveTrainStatus(task.status)) {
      await connectSSE()
    } else if (task.status === 'FINISHED') {
      await loadMetrics()
    }
  } catch (err) {
    console.error('Failed to get train status:', err)
  }
})

onUnmounted(() => {
  closeSSE()
})
</script>

<style scoped>
.train-monitor {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-card-sm);
}

.monitor-header {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 20px 14px;
  border-bottom: 1px solid var(--border);
}

.monitor-title {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: -0.04em;
}

.monitor-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.monitor-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 0 12px;
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, transform 0.15s, border-color 0.15s;
}
.monitor-action:hover {
  background: var(--bg-sunken);
  border-color: var(--border-strong);
  transform: translateY(-1px);
}
.monitor-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}
.monitor-action.is-success {
  color: var(--accent);
  border-color: var(--accent);
}
.monitor-action.is-success:hover {
  background: var(--accent-soft);
}

.monitor-status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 32px;
  padding: 0 12px;
  color: var(--text);
  background: var(--bg-sunken);
  font-size: 12px;
  font-weight: 500;
}
.monitor-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-subtle);
  box-shadow: 0 0 0 3px rgba(74, 64, 54, 0.08);
}
.monitor-status-chip.is-running .monitor-status-dot,
.monitor-status-chip.is-pending .monitor-status-dot,
.monitor-status-chip.is-queued .monitor-status-dot,
.monitor-status-chip.is-claimed .monitor-status-dot,
.monitor-status-chip.is-recovering .monitor-status-dot {
  background: var(--sage-dot);
  box-shadow: 0 0 0 3px rgba(127, 157, 108, 0.18);
  animation: live-pulse 1.6s ease-in-out infinite;
}
.monitor-status-chip.is-finished .monitor-status-dot {
  background: var(--sage);
}
.monitor-status-chip.is-error .monitor-status-dot {
  background: var(--status-error);
  box-shadow: 0 0 0 3px rgba(123, 37, 25, 0.18);
}
@keyframes live-pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(127, 157, 108, 0.18); }
  50%      { box-shadow: 0 0 0 6px rgba(127, 157, 108, 0.05); }
}

.monitor-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px 20px;
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.chart-card {
  padding: 16px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
}

.chart-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.chart-title {
  color: var(--ink);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.metric-help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  color: var(--text-subtle);
  border: 0;
  cursor: help;
}
.metric-help:hover {
  color: var(--accent);
}

.metric-tooltip {
  display: grid;
  gap: 10px;
  line-height: 1.5;
  font-size: 13px;
  color: var(--text-on-ink);
}

.metric-tooltip-section {
  display: grid;
  gap: 4px;
  padding-left: 10px;
  border-left: 3px solid currentColor;
}

.metric-tooltip-title {
  font-weight: 700;
}

.metric-tooltip-simple {
  color: var(--sage-dot);
}

.metric-tooltip-professional {
  color: var(--accent);
}

:global(.metric-tooltip-content) {
  background: var(--ink) !important;
  color: var(--paper) !important;
  border: 1px solid var(--ink) !important;
  border-radius: 0 !important;
  padding: 12px 14px !important;
}

.chart {
  width: 100%;
  height: 300px;
}

.monitor-progress {
  margin-bottom: 20px;
}
.monitor-progress-head {
  display: flex;
  justify-content: space-between;
  color: var(--text-muted);
  font-size: 13px;
  margin-bottom: 6px;
}
.monitor-progress-bar {
  height: 8px;
  background: var(--bg-sunken);
  position: relative;
  overflow: hidden;
}
.monitor-progress-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: var(--accent);
  transition: width 0.3s ease;
}

.monitor-waiting {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-subtle);
}

@media (max-width: 900px) {
  .charts-section {
    grid-template-columns: 1fr;
  }
  .monitor-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
