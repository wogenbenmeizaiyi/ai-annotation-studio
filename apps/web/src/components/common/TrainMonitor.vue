<template>
  <v-card class="train-monitor" rounded="lg">
    <div class="monitor-header d-flex align-center justify-space-between">
      <span class="text-h6 font-weight-bold">训练监控</span>
      <div class="d-flex align-center ga-3">
        <v-btn
          v-if="trainStatus === 'FINISHED'"
          color="primary"
          size="small"
          variant="tonal"
          prepend-icon="mdi-chart-box-outline"
          @click="showAnalysisDialog = true"
        >
          训练分析
        </v-btn>
        <v-btn
          v-if="trainStatus === 'FINISHED' && modelOutputPath"
          color="success"
          size="small"
          variant="tonal"
          prepend-icon="mdi-download"
          :loading="isDownloading"
          @click="downloadModel"
        >
          下载模型
        </v-btn>
        <v-chip :color="statusChipColor" variant="flat" size="small" label>
          {{ statusTextMap[trainStatus] || trainStatus || '--' }}
        </v-chip>
        <v-btn
          v-if="trainStatus === 'FINISHED' || trainStatus === 'ERROR'"
          color="primary"
          size="small"
          variant="tonal"
          prepend-icon="mdi-refresh"
          @click="loadMetrics"
        >
          刷新指标
        </v-btn>
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
                <v-btn
                  v-bind="tooltipProps"
                  icon="mdi-help-circle-outline"
                  variant="text"
                  density="compact"
                  size="small"
                  class="metric-help"
                  :aria-label="`${chart.title}指标说明`"
                />
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
      @edit="handleOptimizationEdit"
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
import type { TrainOptimizationDraft } from '@/types/trainAgent'
import {
  getTrainStatus,
  getTrainMetrics,
  createTrainEventSource,
  getModelDownloadUrl,
} from '@/api/services'

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
  (e: 'edit', draft: TrainOptimizationDraft): void
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

const handleOptimizationEdit = (draft: TrainOptimizationDraft) => {
  showAnalysisDialog.value = false
  emit('edit', draft)
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

// 通用的折线图配置生成
const makeChartOption = (
  keys: { label: string; key: string }[],
  yName: string,
  decimals: number = 4,
): ECOption => {
  const series = extractSeries(keys)
  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 16, 17, 0.96)',
      borderColor: '#34343a',
      textStyle: { color: '#f7f8f8', fontSize: 12 },
      valueFormatter: (val: unknown) => (typeof val === 'number' ? val.toFixed(decimals) : '-'),
    },
    legend: {
      data: keys.map((k) => k.label),
      top: 0,
      textStyle: { color: '#8a8f98', fontSize: 12 },
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
      axisLine: { lineStyle: { color: '#34343a' } },
      axisLabel: { color: '#8a8f98' },
      nameTextStyle: { color: '#8a8f98', fontSize: 12 },
    },
    yAxis: {
      type: 'value',
      name: yName,
      nameTextStyle: { color: '#8a8f98', fontSize: 12 },
      axisLine: { lineStyle: { color: '#34343a' } },
      axisLabel: { color: '#8a8f98' },
      splitLine: { lineStyle: { color: '#23252a' } },
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 5,
        borderColor: '#34343a',
        backgroundColor: '#0f1011',
        fillerColor: 'rgba(94, 106, 210, 0.22)',
        textStyle: { color: '#8a8f98' },
      },
    ],
    series: series.map((s) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
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
  background: var(--studio-surface-1);
}

.monitor-header {
  flex: 0 0 auto;
  padding: 16px 18px 8px;
}

.monitor-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 18px 18px;
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.charts-section :deep(.v-card) {
  background: var(--studio-surface-2);
}

.chart-header {
  display: flex;
  align-items: center;
  gap: 4px;
}

.metric-help {
  color: rgba(var(--v-theme-on-surface), 0.62);
}

.metric-tooltip {
  display: grid;
  gap: 10px;
  line-height: 1.5;
  font-size: 13px;
}

.metric-tooltip-section {
  display: grid;
  gap: 4px;
  padding-left: 8px;
  border-left: 3px solid currentColor;
}

.metric-tooltip-title {
  font-weight: 700;
}

.metric-tooltip-simple {
  color: #43a047;
}

.metric-tooltip-professional {
  color: #42a5f5;
}

:global(.metric-tooltip-content) {
  background: rgba(33, 33, 33, 0.92) !important;
}

.chart {
  width: 100%;
  height: 300px;
}

@media (max-width: 900px) {
  .charts-section {
    grid-template-columns: 1fr;
  }
}
</style>
