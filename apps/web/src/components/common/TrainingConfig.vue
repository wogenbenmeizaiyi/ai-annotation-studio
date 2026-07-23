<template>
  <div class="yolo-trainer">
    <!-- 左右分栏布局 -->
    <div class="train-layout">
      <!-- 左侧：训练列表 -->
      <v-card class="train-sidebar" rounded="lg">
        <div class="d-flex align-center justify-space-between pa-4 sidebar-header">
          <div>
            <div class="sidebar-title">训练记录</div>
            <div class="sidebar-caption">选择记录查看训练详情</div>
          </div>
          <v-btn
            v-if="canManage"
            color="primary"
            size="small"
            prepend-icon="mdi-plus"
            @click="showConfigDialog = true"
          >
            新增
          </v-btn>
        </div>

        <div class="sidebar-separator" />

        <!-- 加载中 -->
        <div v-if="isLoading" class="d-flex align-center justify-center pa-10 text-grey">
          <v-progress-circular indeterminate size="24" class="mr-3" />
          加载中...
        </div>

        <!-- 训练列表 -->
        <v-list v-else-if="trainList.length > 0" class="sidebar-list pa-2" density="compact">
          <v-list-item
            v-for="item in trainList"
            :key="item.id"
            :active="selectedTrainId === item.id"
            rounded="lg"
            color="primary"
            class="train-history-item mb-1"
            @click="selectedTrainId = item.id"
          >
            <div class="d-flex align-center justify-space-between mb-1">
              <span class="train-model-name text-truncate">{{ item.model_name }}</span>
              <div class="d-flex align-center ga-1">
                <v-icon
                  class="train-status-dot"
                  icon="mdi-circle"
                  size="8"
                  :color="statusColorMap[item.status.toLowerCase()] || 'grey'"
                />
                <v-btn
                  v-if="item.can_manage && item.status === 'ERROR'"
                  icon="mdi-restart"
                  size="x-small"
                  variant="text"
                  density="compact"
                  class="row-action-btn"
                  title="重试训练"
                  @click.stop="handleRetryTrain(item)"
                />
                <v-btn
                  v-if="item.can_manage"
                  icon="mdi-close"
                  size="x-small"
                  variant="text"
                  density="compact"
                  class="row-action-btn"
                  title="删除训练记录"
                  @click.stop="handleDeleteTrain(item)"
                />
              </div>
            </div>
            <div class="train-history-meta">
              <span>#{{ item.id }}</span>
              <span>{{ item.current_epoch }}/{{ item.total_epochs }} epoch</span>
            </div>
            <v-progress-linear
              v-if="isActiveTrainStatus(item.status)"
              :model-value="item.progress"
              color="primary"
              height="4"
              rounded
              class="mb-1"
            />
            <div class="train-history-time">{{ formatTime(item.created_at) }}</div>
          </v-list-item>
        </v-list>

        <!-- 无训练记录 -->
        <div v-else class="d-flex flex-column align-center justify-center pa-10">
          <v-icon icon="mdi-clipboard-text-outline" size="40" color="grey-lighten-1" class="mb-3" />
          <p class="text-body-2 text-grey mb-3">暂无训练记录</p>
          <v-btn v-if="canManage" color="primary" size="small" @click="showConfigDialog = true"
            >开始训练</v-btn
          >
        </div>
      </v-card>

      <!-- 右侧：训练详情 -->
      <div class="train-detail">
        <TrainMonitor
          v-if="selectedTrainId"
          :key="selectedTrainId"
          :task-id="selectedTrainId"
          @progress="onTrainProgress"
          @started="handleAgentStarted"
        />

        <v-card
          v-else
          class="d-flex flex-column align-center justify-center detail-empty"
          rounded="lg"
        >
          <v-icon icon="mdi-layers-outline" size="48" color="grey-lighten-1" class="mb-4" />
          <p class="text-body-1 text-grey">选择左侧训练记录查看详情</p>
        </v-card>
      </div>
    </div>

    <!-- 训练配置弹窗 -->
    <v-dialog v-model="showConfigDialog" max-width="1120" persistent>
      <v-card rounded="lg" class="train-config-dialog-card">
        <v-card-title class="train-config-dialog-header d-flex align-center justify-space-between">
          <div>
            <div class="dialog-title">YOLO 训练配置</div>
            <div class="dialog-subtitle">选择本次训练需要提交的参数</div>
          </div>
          <div class="d-flex align-center ga-2">
            <v-btn
              color="primary"
              variant="tonal"
              size="small"
              prepend-icon="mdi-auto-fix"
              @click="showAgentDialog = true"
            >
              智能建议
            </v-btn>
            <v-btn icon="mdi-close" variant="text" size="small" @click="showConfigDialog = false" />
          </div>
        </v-card-title>

        <div class="train-dialog-separator" />

        <v-card-text class="train-config-dialog-body pa-0">
          <div class="config-builder">
            <div class="selected-params">
              <div class="config-section-header">
                <div>
                  <div class="text-subtitle-1 font-weight-bold">当前训练参数</div>
                  <div class="text-caption text-medium-emphasis">
                    可用表单或 JSON 编辑配置；两边会自动同步，未出现的参数不会提交。
                  </div>
                </div>
                <v-chip size="small" variant="tonal" color="primary">
                  {{ selectedTrainParams.length }} 项
                </v-chip>
              </div>

              <v-row density="comfortable">
                <v-col v-for="param in selectedTrainParams" :key="param.key" cols="12" sm="6">
                  <div class="param-field">
                    <div class="param-field-title">
                      <span>{{ param.label }}</span>
                      <v-btn
                        icon="mdi-close"
                        size="x-small"
                        variant="text"
                        density="compact"
                        @click="removeTrainParam(param.key)"
                      />
                    </div>

                    <v-switch
                      v-if="param.input === 'boolean'"
                      v-model="config[param.key]"
                      :label="param.key"
                      color="primary"
                      density="compact"
                      hide-details
                    />
                    <v-select
                      v-else-if="param.input === 'select'"
                      v-model="config[param.key]"
                      :items="param.options"
                      item-title="label"
                      item-value="value"
                      :label="param.key"
                      variant="outlined"
                      density="compact"
                      hide-details
                    />
                    <v-textarea
                      v-else-if="param.input === 'json'"
                      v-model="config[param.key]"
                      :label="param.key"
                      :placeholder="param.placeholder"
                      variant="outlined"
                      density="compact"
                      rows="2"
                      auto-grow
                      hide-details
                    />
                    <v-text-field
                      v-else
                      v-model="config[param.key]"
                      :label="param.key"
                      :type="param.input === 'number' ? 'number' : 'text'"
                      :min="param.min"
                      :max="param.max"
                      :step="param.step"
                      :placeholder="param.placeholder"
                      variant="outlined"
                      density="compact"
                      hide-details
                    />

                    <div class="param-help">{{ param.description }}</div>
                  </div>
                </v-col>
              </v-row>

              <div class="json-config-panel">
                <div class="config-section-header json-header">
                  <div>
                    <div class="text-subtitle-2 font-weight-bold">JSON 配置</div>
                    <div class="text-caption text-medium-emphasis">
                      修改 JSON 会同步勾选参数库；删除字段也会从表单移除。
                    </div>
                  </div>
                  <v-chip v-if="jsonConfigError" size="small" color="error" variant="tonal">
                    JSON 有误
                  </v-chip>
                </div>
                <v-textarea
                  v-model="jsonConfigText"
                  variant="outlined"
                  density="compact"
                  rows="9"
                  auto-grow
                  hide-details
                  spellcheck="false"
                  class="json-config-editor"
                  @update:model-value="syncJsonToForm"
                />
                <div v-if="jsonConfigError" class="json-error">
                  {{ jsonConfigError }}
                </div>
              </div>
            </div>

            <div class="param-library">
              <div class="config-section-header">
                <div>
                  <div class="text-subtitle-1 font-weight-bold">参数库</div>
                  <div class="text-caption text-medium-emphasis">
                    按重要程度分类，勾选后添加到左侧配置界面。
                  </div>
                </div>
              </div>

              <v-expansion-panels
                multiple
                variant="accordion"
                density="compact"
                class="param-library-panels"
              >
                <v-expansion-panel
                  v-for="group in parameterGroups"
                  :key="group.key"
                  :value="group.key"
                >
                  <v-expansion-panel-title>
                    <div class="d-flex align-center justify-space-between w-100 pr-3">
                      <span>{{ group.label }}</span>
                      <v-chip size="x-small" variant="tonal">
                        {{ paramsByGroup[group.key]?.length || 0 }}
                      </v-chip>
                    </div>
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-checkbox
                      v-for="param in paramsByGroup[group.key]"
                      :key="param.key"
                      v-model="selectedParamKeys"
                      :value="param.key"
                      color="primary"
                      density="compact"
                      hide-details
                    >
                      <template #label>
                        <div class="param-option">
                          <div class="param-option-title">{{ param.label }}</div>
                          <div class="param-option-desc">
                            {{ param.key }} · {{ param.description }}
                          </div>
                        </div>
                      </template>
                    </v-checkbox>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </div>
          </div>
        </v-card-text>

        <v-card-actions class="train-config-dialog-actions pa-4">
          <v-text-field
            v-model.number="trainPriority"
            label="队列优先级"
            type="number"
            :min="-100"
            :max="100"
            density="compact"
            variant="outlined"
            hide-details
            class="priority-field"
          />
          <v-spacer />
          <v-btn variant="text" @click="showConfigDialog = false" :disabled="isSubmitting">
            取消
          </v-btn>
          <v-btn variant="tonal" color="warning" @click="resetConfig" :disabled="isSubmitting">
            重置
          </v-btn>
          <v-btn color="primary" @click="startTraining" :loading="isSubmitting"> 开始训练 </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <TrainingAgentDialog
      v-model="showAgentDialog"
      :task-name="taskName || ''"
      :current-config="agentCurrentConfig"
      @apply="applyAgentConfig"
      @started="handleAgentStarted"
    />

    <AppConfirmDialog />
    <AppSnackbar />
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, inject, onMounted, watch } from 'vue'
import { createTrain, getTask, getTrainList, deleteTrain, retryTrain } from '@/api/services'
import type { TrainTask, TrainTaskStatus } from '@/types/train'
import type { TrainConfig } from '@/types/ImageItem'
import TrainMonitor from '@/components/common/TrainMonitor.vue'
import TrainingAgentDialog from '@/components/common/TrainingAgentDialog.vue'
import AppConfirmDialog from '@/components/common/AppConfirmDialog.vue'
import AppSnackbar from '@/components/common/AppSnackbar.vue'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'

const taskName = inject<string>('taskId')
const detectionType = inject<string>('detectionType')

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()

// 状态
const isLoading = ref(true)
const isSubmitting = ref(false)
const showConfigDialog = ref(false)
const showAgentDialog = ref(false)
const trainPriority = ref(0)
const selectedTrainId = ref<number | null>(null)
const trainList = ref<TrainTask[]>([])
const canManage = ref(false)

const statusColorMap: Record<string, string> = {
  pending: 'warning',
  queued: 'warning',
  claimed: 'info',
  recovering: 'info',
  running: 'blue',
  finished: 'success',
  error: 'error',
  cancelled: 'grey',
}

const activeTrainStatuses = new Set<TrainTaskStatus>([
  'PENDING',
  'QUEUED',
  'CLAIMED',
  'RECOVERING',
  'RUNNING',
])

const isActiveTrainStatus = (status: TrainTaskStatus) => activeTrainStatuses.has(status)

interface SelectOption {
  label: string
  value: string | number | boolean | null
}

interface TrainParameter {
  key: string
  label: string
  group: string
  input: 'number' | 'text' | 'boolean' | 'select' | 'json'
  defaultValue: string | number | boolean | null
  description: string
  options?: SelectOption[]
  min?: number
  max?: number
  step?: number
  placeholder?: string
}

const imgszOptions: SelectOption[] = [
  { label: '320x320', value: 320 },
  { label: '416x416', value: 416 },
  { label: '512x512', value: 512 },
  { label: '640x640', value: 640 },
  { label: '768x768', value: 768 },
  { label: '1024x1024', value: 1024 },
]

const parameterGroups = [
  { key: 'core', label: '核心参数' },
  { key: 'common', label: '常用优化' },
  { key: 'augment', label: '数据增强' },
  { key: 'loss', label: '损失与任务' },
  { key: 'advanced', label: '高级训练' },
]

// 根据任务类型返回模型列表
let defaultModelName = 'yolo26n.pt'
const getModelListByType = (detectionType: string | undefined) => {
  switch (detectionType) {
    case 'segmentation':
      defaultModelName = 'yolo26n-seg.pt'
      return [
        { value: 'yolo26n-seg.pt', label: 'YOLO26 Nano Seg (最快)' },
        { value: 'yolo26s-seg.pt', label: 'YOLO26 Small Seg' },
        { value: 'yolo26m-seg.pt', label: 'YOLO26 Medium Seg (推荐)' },
        { value: 'yolo26l-seg.pt', label: 'YOLO26 Large Seg' },
        { value: 'yolo26x-seg.pt', label: 'YOLO26 XLarge Seg (最准)' },
      ]

    case 'detection':
      defaultModelName = 'yolo26n.pt'
      return [
        { value: 'yolo26n.pt', label: 'YOLO26 Nano (最快)' },
        { value: 'yolo26s.pt', label: 'YOLO26 Small' },
        { value: 'yolo26m.pt', label: 'YOLO26 Medium (推荐, 平衡速度与精度)' },
        { value: 'yolo26l.pt', label: 'YOLO26 Large' },
        { value: 'yolo26x.pt', label: 'YOLO26 XLarge (最准, mAP 57.5)' },
      ]

    default:
      return []
  }
}

const modelList = getModelListByType(detectionType)

const allTrainParams: TrainParameter[] = [
  {
    key: 'model',
    label: '模型权重',
    group: 'core',
    input: 'select',
    defaultValue: defaultModelName,
    description: '本地模型文件名或路径',
    options: modelList,
  },
  {
    key: 'epochs',
    label: '训练轮数',
    group: 'core',
    input: 'number',
    defaultValue: 100,
    description: '最大训练轮数',
    min: 1,
    max: 500,
    step: 1,
  },
  {
    key: 'batch',
    label: '批次大小',
    group: 'core',
    input: 'number',
    defaultValue: 16,
    description: '每批训练图片数量',
    min: 1,
    max: 128,
    step: 1,
  },
  {
    key: 'imgsz',
    label: '输入尺寸',
    group: 'core',
    input: 'select',
    defaultValue: 640,
    description: '训练输入图片尺寸',
    options: imgszOptions,
  },
  {
    key: 'val_split',
    label: '验证集比例',
    group: 'core',
    input: 'number',
    defaultValue: 0.2,
    description: '构建数据集时验证集占比',
    min: 0.05,
    max: 0.5,
    step: 0.05,
  },
  {
    key: 'val',
    label: '训练中验证',
    group: 'core',
    input: 'boolean',
    defaultValue: true,
    description: '训练过程中是否执行验证',
  },
  {
    key: 'lr0',
    label: '初始学习率',
    group: 'common',
    input: 'number',
    defaultValue: 0.01,
    description: '训练初始学习率',
    min: 0.0001,
    max: 0.1,
    step: 0.0001,
  },
  {
    key: 'optimizer',
    label: '优化器',
    group: 'common',
    input: 'select',
    defaultValue: 'auto',
    description: '优化器类型',
    options: ['auto', 'SGD', 'Adam', 'AdamW', 'RMSprop'].map((v) => ({ label: v, value: v })),
  },
  {
    key: 'patience',
    label: '早停等待',
    group: 'common',
    input: 'number',
    defaultValue: 100,
    description: 'Early stopping 等待轮数',
    min: 0,
    max: 300,
    step: 1,
  },
  {
    key: 'weight_decay',
    label: '权重衰减',
    group: 'common',
    input: 'number',
    defaultValue: 0.0005,
    description: '优化器权重衰减',
    min: 0,
    max: 0.01,
    step: 0.0001,
  },
  {
    key: 'lrf',
    label: '最终学习率系数',
    group: 'common',
    input: 'number',
    defaultValue: 0.01,
    description: '学习率衰减末值系数',
    min: 0,
    max: 1,
    step: 0.001,
  },
  {
    key: 'momentum',
    label: '动量',
    group: 'common',
    input: 'number',
    defaultValue: 0.937,
    description: 'SGD momentum / Adam beta1',
    min: 0,
    max: 1,
    step: 0.001,
  },
  {
    key: 'warmup_epochs',
    label: '预热轮数',
    group: 'common',
    input: 'number',
    defaultValue: 3.0,
    description: '学习率 warmup 轮数',
    min: 0,
    step: 0.5,
  },
  {
    key: 'warmup_momentum',
    label: '预热动量',
    group: 'common',
    input: 'number',
    defaultValue: 0.8,
    description: 'warmup 初始 momentum',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'warmup_bias_lr',
    label: '预热 bias 学习率',
    group: 'common',
    input: 'number',
    defaultValue: 0.1,
    description: 'warmup bias 学习率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'hsv_h',
    label: '色相增强',
    group: 'augment',
    input: 'number',
    defaultValue: 0.015,
    description: 'HSV 色相增强',
    min: 0,
    max: 1,
    step: 0.001,
  },
  {
    key: 'hsv_s',
    label: '饱和度增强',
    group: 'augment',
    input: 'number',
    defaultValue: 0.7,
    description: 'HSV 饱和度增强',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'hsv_v',
    label: '明度增强',
    group: 'augment',
    input: 'number',
    defaultValue: 0.4,
    description: 'HSV 明度增强',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'degrees',
    label: '旋转角度',
    group: 'augment',
    input: 'number',
    defaultValue: 0.0,
    description: '随机旋转角度',
    min: 0,
    max: 180,
    step: 1,
  },
  {
    key: 'translate',
    label: '平移比例',
    group: 'augment',
    input: 'number',
    defaultValue: 0.1,
    description: '随机平移比例',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'scale',
    label: '缩放比例',
    group: 'augment',
    input: 'number',
    defaultValue: 0.5,
    description: '随机缩放比例',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'shear',
    label: '剪切角度',
    group: 'augment',
    input: 'number',
    defaultValue: 0.0,
    description: '随机剪切角度',
    min: 0,
    max: 45,
    step: 1,
  },
  {
    key: 'perspective',
    label: '透视比例',
    group: 'augment',
    input: 'number',
    defaultValue: 0.0,
    description: '透视变换比例',
    min: 0,
    max: 0.001,
    step: 0.0001,
  },
  {
    key: 'flipud',
    label: '上下翻转',
    group: 'augment',
    input: 'number',
    defaultValue: 0.0,
    description: '上下翻转概率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'fliplr',
    label: '左右翻转',
    group: 'augment',
    input: 'number',
    defaultValue: 0.5,
    description: '左右翻转概率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'bgr',
    label: 'BGR 交换',
    group: 'augment',
    input: 'number',
    defaultValue: 0.0,
    description: 'BGR 通道交换概率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'mosaic',
    label: 'Mosaic',
    group: 'augment',
    input: 'number',
    defaultValue: 1.0,
    description: 'mosaic 增强概率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'mixup',
    label: 'MixUp',
    group: 'augment',
    input: 'number',
    defaultValue: 0.0,
    description: 'mixup 增强概率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'cutmix',
    label: 'CutMix',
    group: 'augment',
    input: 'number',
    defaultValue: 0.0,
    description: 'cutmix 增强概率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'copy_paste',
    label: 'Copy-paste',
    group: 'augment',
    input: 'number',
    defaultValue: 0.0,
    description: 'copy-paste 概率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'copy_paste_mode',
    label: 'Copy-paste 模式',
    group: 'augment',
    input: 'select',
    defaultValue: 'flip',
    description: 'copy-paste 模式',
    options: [
      { label: 'flip', value: 'flip' },
      { label: 'mixup', value: 'mixup' },
    ],
  },
  {
    key: 'auto_augment',
    label: '自动增强',
    group: 'augment',
    input: 'text',
    defaultValue: 'randaugment',
    description: '自动增强策略',
  },
  {
    key: 'erasing',
    label: '随机擦除',
    group: 'augment',
    input: 'number',
    defaultValue: 0.4,
    description: 'random erasing 概率',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'augmentations',
    label: '自定义增强',
    group: 'augment',
    input: 'json',
    defaultValue: null,
    description: 'Ultralytics 自定义增强配置',
    placeholder: '[{\"name\":\"...\"}]',
  },
  {
    key: 'box',
    label: 'Box loss 权重',
    group: 'loss',
    input: 'number',
    defaultValue: 7.5,
    description: 'box loss 权重',
    min: 0,
    step: 0.1,
  },
  {
    key: 'cls',
    label: 'Cls loss 权重',
    group: 'loss',
    input: 'number',
    defaultValue: 0.5,
    description: 'class loss 权重',
    min: 0,
    step: 0.1,
  },
  {
    key: 'cls_pw',
    label: '分类正样本权重',
    group: 'loss',
    input: 'number',
    defaultValue: 0.0,
    description: 'YOLO26 分类正样本权重',
    min: 0,
    step: 0.1,
  },
  {
    key: 'dfl',
    label: 'DFL loss 权重',
    group: 'loss',
    input: 'number',
    defaultValue: 1.5,
    description: 'DFL loss 权重',
    min: 0,
    step: 0.1,
  },
  {
    key: 'pose',
    label: 'Pose loss 权重',
    group: 'loss',
    input: 'number',
    defaultValue: 12.0,
    description: 'pose loss 权重',
    min: 0,
    step: 0.1,
  },
  {
    key: 'kobj',
    label: 'KObj loss 权重',
    group: 'loss',
    input: 'number',
    defaultValue: 1.0,
    description: 'keypoint objectness loss 权重',
    min: 0,
    step: 0.1,
  },
  {
    key: 'rle',
    label: 'RLE loss 权重',
    group: 'loss',
    input: 'number',
    defaultValue: 1.0,
    description: 'RLE loss 权重',
    min: 0,
    step: 0.1,
  },
  {
    key: 'angle',
    label: 'Angle loss 权重',
    group: 'loss',
    input: 'number',
    defaultValue: 1.0,
    description: 'angle/OBB loss 权重',
    min: 0,
    step: 0.1,
  },
  {
    key: 'nbs',
    label: '名义 batch',
    group: 'loss',
    input: 'number',
    defaultValue: 64,
    description: 'nominal batch size',
    min: 1,
    step: 1,
  },
  {
    key: 'overlap_mask',
    label: 'Mask 重叠',
    group: 'loss',
    input: 'boolean',
    defaultValue: true,
    description: '分割训练是否允许 mask 重叠',
  },
  {
    key: 'mask_ratio',
    label: 'Mask 下采样',
    group: 'loss',
    input: 'number',
    defaultValue: 4,
    description: 'mask 下采样比例',
    min: 1,
    step: 1,
  },
  {
    key: 'dropout',
    label: 'Dropout',
    group: 'loss',
    input: 'number',
    defaultValue: 0.0,
    description: 'dropout 比例',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'pretrained',
    label: '预训练权重',
    group: 'advanced',
    input: 'select',
    defaultValue: true,
    description: '是否使用预训练权重',
    options: [
      { label: 'true', value: true },
      { label: 'false', value: false },
    ],
  },
  {
    key: 'single_cls',
    label: '单类别训练',
    group: 'advanced',
    input: 'boolean',
    defaultValue: false,
    description: '是否把所有类别当成单类',
  },
  {
    key: 'classes',
    label: '指定类别',
    group: 'advanced',
    input: 'json',
    defaultValue: null,
    description: '只训练指定类别 ID 数组',
    placeholder: '[0,1,2]',
  },
  {
    key: 'rect',
    label: 'Rect 训练',
    group: 'advanced',
    input: 'boolean',
    defaultValue: false,
    description: '是否启用 rectangular training',
  },
  {
    key: 'multi_scale',
    label: '多尺度训练',
    group: 'advanced',
    input: 'number',
    defaultValue: 0.0,
    description: '多尺度训练范围',
    min: 0,
    step: 0.1,
  },
  {
    key: 'cos_lr',
    label: 'Cosine LR',
    group: 'advanced',
    input: 'boolean',
    defaultValue: false,
    description: '是否使用 cosine LR',
  },
  {
    key: 'close_mosaic',
    label: '关闭 Mosaic 轮数',
    group: 'advanced',
    input: 'number',
    defaultValue: 10,
    description: '最后 N 轮关闭 mosaic',
    min: 0,
    step: 1,
  },
  {
    key: 'fraction',
    label: '数据比例',
    group: 'advanced',
    input: 'number',
    defaultValue: 1.0,
    description: '使用训练数据比例',
    min: 0,
    max: 1,
    step: 0.01,
  },
  {
    key: 'freeze',
    label: '冻结层',
    group: 'advanced',
    input: 'json',
    defaultValue: null,
    description: '冻结层编号或数组',
    placeholder: '10 或 [0,1,2]',
  },
]

const defaultSelectedParamKeys = ['model', 'epochs', 'batch', 'imgsz', 'val_split']
const selectedParamKeys = ref<string[]>([...defaultSelectedParamKeys])
const config = reactive<Record<string, string | number | boolean | null>>({})
const jsonConfigText = ref('')
const jsonConfigError = ref('')
let isSyncingConfig = false
let isEditingJsonConfig = false

for (const param of allTrainParams) {
  config[param.key] = param.defaultValue
}

const paramsByGroup = computed(() =>
  parameterGroups.reduce<Record<string, TrainParameter[]>>((groups, group) => {
    groups[group.key] = allTrainParams.filter((param) => param.group === group.key)
    return groups
  }, {}),
)

const selectedTrainParams = computed(() =>
  allTrainParams.filter((param) => selectedParamKeys.value.includes(param.key)),
)

const trainParamsByKey = computed(() =>
  allTrainParams.reduce<Record<string, TrainParameter>>((params, param) => {
    params[param.key] = param
    return params
  }, {}),
)

const removeTrainParam = (key: string) => {
  selectedParamKeys.value = selectedParamKeys.value.filter((paramKey) => paramKey !== key)
}

const parseConfigValue = (param: TrainParameter) => {
  const value = config[param.key]
  if (value === '' || value === null) return null
  if (param.input !== 'json') return value

  try {
    return JSON.parse(String(value))
  } catch {
    throw new Error(`${param.label} 必须是合法 JSON`)
  }
}

const buildTrainConfig = (): Record<string, unknown> => {
  const payload: Record<string, unknown> = {}

  for (const param of selectedTrainParams.value) {
    const value = parseConfigValue(param)
    if (value !== null) {
      payload[param.key] = value
    }
  }

  return payload
}

const toFieldValue = (param: TrainParameter, value: unknown) => {
  if (value === undefined || value === null) return null
  if (param.input === 'json') {
    return typeof value === 'string' ? value : JSON.stringify(value)
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value
  }
  return JSON.stringify(value)
}

const agentCurrentConfig = computed<Record<string, unknown>>(() => {
  try {
    return buildTrainConfig()
  } catch {
    return {}
  }
})

const applyAgentConfig = (proposal: Record<string, unknown>) => {
  const proposalKeys = Object.keys(proposal)
  const knownKeys = proposalKeys.filter((key) => trainParamsByKey.value[key])
  const unknownKeys = proposalKeys.filter((key) => !trainParamsByKey.value[key])

  if (knownKeys.length === 0) {
    snackbar.showSnackbar('Agent 返回的参数不在当前参数库中', 'warning')
    return
  }

  isSyncingConfig = true
  selectedParamKeys.value = knownKeys
  for (const param of allTrainParams) {
    config[param.key] = Object.prototype.hasOwnProperty.call(proposal, param.key)
      ? toFieldValue(param, proposal[param.key])
      : param.defaultValue
  }
  isSyncingConfig = false
  syncFormToJson()

  if (unknownKeys.length > 0) {
    snackbar.showSnackbar(`已应用建议，忽略未知参数：${unknownKeys.join(', ')}`, 'warning', 5000)
  }
}

const getTopLevelJsonKeys = (json: string) => {
  const keys: string[] = []
  let depth = 0
  let index = 0
  let isInString = false
  let isEscaped = false
  let stringStart = -1
  let lastTopLevelString: string | null = null

  while (index < json.length) {
    const char = json[index]!

    if (isInString) {
      if (isEscaped) {
        isEscaped = false
      } else if (char === '\\') {
        isEscaped = true
      } else if (char === '"') {
        isInString = false
        if (depth === 1 && stringStart >= 0) {
          lastTopLevelString = json.slice(stringStart, index)
        }
      }
      index += 1
      continue
    }

    if (char === '"') {
      isInString = true
      stringStart = index + 1
    } else if (char === '{' || char === '[') {
      depth += 1
    } else if (char === '}' || char === ']') {
      depth -= 1
    } else if (char === ':' && depth === 1 && lastTopLevelString !== null) {
      keys.push(lastTopLevelString)
      lastTopLevelString = null
    } else if (char === ',' && depth === 1) {
      lastTopLevelString = null
    }

    index += 1
  }

  return keys
}

const getDuplicateKeys = (keys: string[]) => {
  const seen = new Set<string>()
  const duplicates = new Set<string>()

  for (const key of keys) {
    if (seen.has(key)) {
      duplicates.add(key)
    }
    seen.add(key)
  }

  return [...duplicates]
}

const syncFormToJson = () => {
  if (isSyncingConfig || isEditingJsonConfig) return
  try {
    jsonConfigText.value = JSON.stringify(buildTrainConfig(), null, 2)
    jsonConfigError.value = ''
  } catch (err) {
    jsonConfigError.value = err instanceof Error ? err.message : '配置格式有误'
  }
}

const syncJsonToForm = () => {
  if (isSyncingConfig) return
  isEditingJsonConfig = true

  try {
    const topLevelKeys = getTopLevelJsonKeys(jsonConfigText.value || '{}')
    const duplicateKeys = getDuplicateKeys(topLevelKeys)
    if (duplicateKeys.length > 0) {
      throw new Error(`JSON 中存在重复参数：${duplicateKeys.join(', ')}`)
    }

    const parsed = JSON.parse(jsonConfigText.value || '{}') as Record<string, unknown>
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error('JSON 配置必须是对象')
    }

    const keys = Object.keys(parsed)
    const unknownKeys = keys.filter((key) => !trainParamsByKey.value[key])
    if (unknownKeys.length > 0) {
      throw new Error(`参数库中不存在这些参数：${unknownKeys.join(', ')}`)
    }

    isSyncingConfig = true
    selectedParamKeys.value = keys
    for (const param of allTrainParams) {
      if (Object.prototype.hasOwnProperty.call(parsed, param.key)) {
        config[param.key] = toFieldValue(param, parsed[param.key])
      } else {
        config[param.key] = param.defaultValue
      }
    }
    jsonConfigError.value = ''
  } catch (err) {
    jsonConfigError.value = err instanceof Error ? err.message : 'JSON 配置格式有误'
  } finally {
    isSyncingConfig = false
    window.setTimeout(() => {
      isEditingJsonConfig = false
    }, 0)
  }
}

watch(
  () => ({
    keys: [...selectedParamKeys.value],
    values: selectedParamKeys.value.map((key) => config[key]),
  }),
  syncFormToJson,
  { immediate: true, deep: true },
)

// 加载训练列表
const loadTrainList = async (silent = false) => {
  if (!taskName) return
  if (!silent) isLoading.value = true
  try {
    trainList.value = await getTrainList(taskName)
    // 静默刷新时：仅当选中项不存在于新列表中才重新选择
    if (silent && selectedTrainId.value) {
      const stillExists = trainList.value.some((t) => t.id === selectedTrainId.value)
      if (stillExists) return
    }
    // 默认选中第一条（最新），或正在运行的训练
    if (trainList.value.length > 0) {
      const running = trainList.value.find((item) => isActiveTrainStatus(item.status))
      selectedTrainId.value = running ? running.id : trainList.value[0]!.id
    } else {
      selectedTrainId.value = null
    }
  } catch (err) {
    console.error('加载训练列表失败:', err)
  } finally {
    if (!silent) isLoading.value = false
  }
}

// 开始训练
const startTraining = async () => {
  if (isSubmitting.value || !taskName) return

  isSubmitting.value = true

  try {
    if (jsonConfigError.value) {
      throw new Error(jsonConfigError.value)
    }

    const body = {
      task_name: taskName,
      priority: Math.max(-100, Math.min(100, Number(trainPriority.value) || 0)),
      config: buildTrainConfig(),
    }

    // 配置校验通过后再关闭弹窗，避免 JSON 参数写错时丢失当前输入
    showConfigDialog.value = false
    await createTrain(body)
    snackbar.showSnackbar('训练任务已进入队列', 'success')

    // 无论成功失败都刷新列表
    await loadTrainList()
    if (trainList.value.length > 0) {
      selectedTrainId.value = trainList.value[0]!.id
    }
  } catch (err) {
    console.error('训练失败:', err)
    const message = err instanceof Error ? err.message : '训练任务创建失败'
    snackbar.showSnackbar(message, 'error')
  } finally {
    isSubmitting.value = false
  }
}

const handleAgentStarted = async (taskId?: number) => {
  showAgentDialog.value = false
  showConfigDialog.value = false
  await loadTrainList()

  if (taskId && trainList.value.some((item) => item.id === taskId)) {
    selectedTrainId.value = taskId
  } else if (trainList.value.length > 0) {
    selectedTrainId.value = trainList.value[0]!.id
  }
}

// 重置配置
const resetConfig = () => {
  trainPriority.value = 0
  selectedParamKeys.value = [...defaultSelectedParamKeys]
  for (const param of allTrainParams) {
    config[param.key] = param.defaultValue
  }
  syncFormToJson()
}

// SSE 进度更新 -> 同步到左侧列表
const onTrainProgress = (payload: {
  id: number
  status: string
  currentEpoch: number
  totalEpochs: number
  progress: number
}) => {
  const item = trainList.value.find((t) => t.id === payload.id)
  if (item) {
    item.status = payload.status as TrainTaskStatus
    item.current_epoch = payload.currentEpoch
    item.total_epochs = payload.totalEpochs
    item.progress = payload.progress
  }
}

// 删除训练记录
const handleDeleteTrain = async (item: TrainTask) => {
  if (['CLAIMED', 'RECOVERING', 'RUNNING'].includes(item.status)) {
    snackbar.showSnackbar('训练中的任务不能删除', 'warning')
    return
  }
  const confirmed = await confirmDialog.showConfirm(
    '删除训练记录',
    `确定删除训练记录 #${item.id}（${item.model_name}）？`,
  )
  if (!confirmed) return
  try {
    await deleteTrain(item.id)
  } catch (err) {
    console.error('删除训练记录失败:', err)
    return
  }
  // 删除成功后静默刷新列表（loadTrainList 会自动处理选中项）
  await loadTrainList(true)
}

const handleRetryTrain = async (item: TrainTask) => {
  if (item.status !== 'ERROR') {
    snackbar.showSnackbar('只有失败的训练任务可以重新入队', 'warning')
    return
  }

  try {
    await retryTrain(item.id)
    snackbar.showSnackbar('训练任务已重新进入队列', 'success')
    await loadTrainList(true)
    selectedTrainId.value = item.id
  } catch (err) {
    console.error('重试训练失败:', err)
    snackbar.showSnackbar('重试训练失败', 'error')
  }
}

// 格式化时间
const formatTime = (isoStr: string): string => {
  if (!isoStr) return '-'
  const d = new Date(isoStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// 页面加载
onMounted(async () => {
  if (taskName) {
    try {
      canManage.value = (await getTask(taskName)).can_manage
    } catch (error) {
      console.error('加载训练权限失败:', error)
    }
  }
  await loadTrainList()
})
</script>

<style scoped>
.yolo-trainer {
  box-sizing: border-box;
  height: 100%;
  min-height: 0;
  padding: 12px 14px 14px;
  overflow: hidden;
}

.train-layout {
  display: flex;
  gap: 12px;
  height: 100%;
  min-height: 0;
}

.train-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--studio-surface-1);
}

.sidebar-header {
  min-height: 58px;
  padding: 10px 12px !important;
}

.sidebar-title {
  color: var(--studio-ink);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
}

.sidebar-caption {
  margin-top: 2px;
  color: var(--studio-ink-tertiary);
  font-size: 11px;
  line-height: 1.3;
}

.sidebar-separator,
.train-dialog-separator {
  width: 100%;
  height: 1px;
  flex: 0 0 1px;
  background: var(--studio-hairline);
}

.sidebar-list {
  flex: 1;
  padding: 6px !important;
  overflow-y: auto;
  background: transparent;
}

.train-history-item {
  position: relative;
  min-height: 72px;
  padding: 8px 9px;
  color: var(--studio-ink-muted) !important;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px !important;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease;
}

.train-history-item:hover {
  background: rgba(255, 255, 255, 0.025);
  border-color: var(--studio-hairline);
}

.train-history-item.v-list-item--active {
  background: rgba(94, 106, 210, 0.11);
  border-color: rgba(94, 106, 210, 0.28);
}

.train-history-item.v-list-item--active::before {
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: -1px;
  width: 2px;
  border-radius: 0 2px 2px 0;
  background: var(--studio-primary);
  content: '';
}

.train-history-item :deep(.v-list-item__overlay) {
  opacity: 0 !important;
}

.train-model-name {
  min-width: 0;
  color: var(--studio-ink);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
}

.train-history-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
  color: var(--studio-ink-subtle);
  font-size: 11px;
  line-height: 1.35;
}

.train-history-meta span + span::before {
  margin-right: 8px;
  color: var(--studio-hairline-strong);
  content: '·';
}

.train-history-time {
  color: var(--studio-ink-tertiary);
  font-size: 11px;
  line-height: 1.35;
}

.train-status-dot {
  opacity: 0.82;
}

.row-action-btn {
  opacity: 0;
  transition: opacity 0.15s;
}

.train-history-item:hover .row-action-btn,
.train-history-item:focus-within .row-action-btn {
  opacity: 1;
}

.train-detail {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.detail-empty {
  height: 100%;
  background: var(--studio-surface-1);
}

.train-config-dialog-card {
  display: flex;
  height: calc(100vh - 96px);
  max-height: calc(100vh - 96px);
  flex-direction: column;
  overflow: hidden;
  background: var(--studio-surface-1) !important;
  border-radius: 10px !important;
}

.train-config-dialog-header {
  min-height: 58px;
  padding: 10px 14px 10px 16px !important;
  background: var(--studio-surface-1);
}

.dialog-title {
  color: var(--studio-ink);
  font-size: 15px;
  font-weight: 600;
  line-height: 1.35;
}

.dialog-subtitle {
  margin-top: 2px;
  color: var(--studio-ink-tertiary);
  font-size: 11px;
  font-weight: 400;
  line-height: 1.3;
}

.train-config-dialog-body {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--studio-canvas);
}

.train-config-dialog-actions {
  min-height: 60px;
  flex: 0 0 auto;
  padding: 10px 14px !important;
  border-top: 1px solid var(--studio-hairline);
  background: var(--studio-surface-1);
}

.priority-field {
  max-width: 150px;
}

.priority-field :deep(.v-field) {
  background: var(--studio-canvas);
}

.config-builder {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  min-height: 100%;
  align-items: start;
}

.selected-params {
  min-width: 0;
  padding: 18px;
}

.selected-params :deep(.v-row) {
  margin: -6px;
}

.selected-params :deep(.v-col) {
  padding: 6px;
}

.param-library {
  position: sticky;
  top: 0;
  min-width: 0;
  max-height: calc(100vh - 178px);
  padding: 16px 14px;
  overflow-y: auto;
  border-left: 1px solid var(--studio-hairline);
  background: var(--studio-surface-1);
}

.config-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.param-field {
  height: 100%;
  padding: 11px;
  border: 1px solid var(--studio-hairline);
  border-radius: 8px;
  background: var(--studio-surface-1);
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease;
}

.param-field:hover {
  background: var(--studio-surface-2);
  border-color: var(--studio-hairline-strong);
}

.param-field:focus-within {
  border-color: rgba(94, 106, 210, 0.48);
}

.param-field-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--studio-ink-muted);
  font-size: 13px;
  font-weight: 600;
}

.param-field :deep(.v-field) {
  background: var(--studio-canvas);
}

.param-help {
  margin-top: 7px;
  color: var(--studio-ink-tertiary);
  font-size: 11px;
  line-height: 1.4;
}

.json-config-panel {
  margin-top: 18px;
  padding: 14px;
  border: 1px solid var(--studio-hairline);
  border-radius: 8px;
  background: var(--studio-surface-1);
}

.json-header {
  margin-bottom: 10px;
}

.json-config-editor :deep(textarea) {
  font-family:
    ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: 12px;
  line-height: 1.45;
}

.json-config-editor :deep(.v-field) {
  background: var(--studio-canvas);
}

.json-error {
  margin-top: 8px;
  color: rgb(var(--v-theme-error));
  font-size: 12px;
  line-height: 1.4;
}

.param-option {
  min-width: 0;
  padding: 4px 0;
}

.param-option-title {
  color: rgba(var(--v-theme-on-surface), 0.9);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.3;
}

.param-option-desc {
  color: var(--studio-ink-tertiary);
  font-size: 12px;
  line-height: 1.35;
  white-space: normal;
}

.param-library-panels {
  overflow: hidden;
  border: 1px solid var(--studio-hairline);
  border-radius: 8px;
  box-shadow: none !important;
}

.param-library-panels :deep(.v-expansion-panel) {
  color: var(--studio-ink-muted);
  background: transparent;
  box-shadow: none !important;
}

.param-library-panels :deep(.v-expansion-panel::after) {
  border-color: var(--studio-hairline);
}

.param-library-panels :deep(.v-expansion-panel-title) {
  min-height: 48px;
  padding: 0 12px;
  color: var(--studio-ink-muted);
  font-size: 13px;
  font-weight: 600;
}

.param-library-panels :deep(.v-expansion-panel-title:hover),
.param-library-panels :deep(.v-expansion-panel-title--active) {
  background: var(--studio-surface-2);
}

.param-library-panels :deep(.v-expansion-panel-title__overlay) {
  opacity: 0 !important;
}

.param-library-panels :deep(.v-expansion-panel-text__wrapper) {
  padding: 6px 10px 10px;
  background: rgba(0, 0, 0, 0.18);
}

.param-library-panels :deep(.v-selection-control) {
  min-height: 38px;
}

@media (max-width: 900px) {
  .train-layout {
    flex-direction: column;
  }

  .train-sidebar {
    width: 100%;
    max-height: 250px;
  }

  .config-builder {
    grid-template-columns: 1fr;
  }

  .param-library {
    position: static;
    max-height: none;
    border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-left: 0;
  }
}
</style>
