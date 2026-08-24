<template>
  <div class="task-list-page">
    <PageHeader title="标注任务" description="管理检测与分割数据集，并从同一任务进入标注和训练。">
      <template #actions>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="showAddForm = true">
          添加新任务
        </v-btn>
      </template>
    </PageHeader>

    <!-- 任务列表 -->
    <div class="tasks-grid">
      <v-card
        v-for="(task, index) in tasks"
        :key="task.id"
        class="task-card"
        hover
        @click="onTaskClick(task)"
      >
        <v-card-text class="task-card-content">
          <div class="task-card-title-row">
            <div class="task-title text-h6 font-weight-bold">{{ task.name }}</div>
            <v-chip size="x-small" variant="tonal" color="secondary" class="ml-2">
              #{{ index + 1 }}
            </v-chip>
          </div>

          <!-- 检测类型标签 -->
          <div class="task-type-row">
            <v-chip
              size="small"
              :color="task.detection_type === 'segmentation' ? 'success' : 'primary'"
              variant="tonal"
            >
              {{ getDetectionTypeLabel(task.detection_type) }}
            </v-chip>
          </div>

          <!-- 分类标签 -->
          <div class="task-category-section">
            <div class="text-caption text-medium-emphasis mb-1">分类标签</div>
            <div class="d-flex flex-wrap ga-1">
              <v-chip
                v-for="category in task.categories"
                :key="category.id"
                size="x-small"
                variant="flat"
                class="task-category-chip"
              >
                {{ category.name }}
                <span v-if="category.supercategory" class="text-medium-emphasis ml-1">
                  ({{ category.supercategory }})
                </span>
              </v-chip>
            </div>
          </div>

          <div class="task-description-section" :class="{ 'is-empty': !task.description }">
            <div class="text-caption text-medium-emphasis mb-1">任务描述</div>
            <div class="description-text text-body-2">{{ task.description }}</div>
          </div>
        </v-card-text>

        <v-card-actions>
          <v-btn
            v-if="task.can_manage"
            variant="tonal"
            color="primary"
            prepend-icon="mdi-play"
            size="small"
            @click.stop="trainTask(task)"
          >
            训练
          </v-btn>
          <v-spacer />
          <v-btn
            v-if="task.can_manage"
            variant="tonal"
            color="error"
            prepend-icon="mdi-delete-outline"
            size="small"
            @click.stop="handleDeleteTask(task.name)"
          >
            删除
          </v-btn>
        </v-card-actions>
      </v-card>
    </div>

    <!-- 空状态 -->
    <div v-if="tasks.length === 0" class="empty-state">
      <v-icon icon="mdi-clipboard-text-outline" size="64" color="grey-lighten-1" />
      <h3 class="text-h6 mt-4">暂无任务</h3>
      <p class="text-body-2 text-medium-emphasis mt-1">
        点击"添加新任务"按钮开始创建您的第一个任务
      </p>
      <v-btn color="primary" class="mt-4" @click="showAddForm = true">创建任务</v-btn>
    </div>

    <!-- 添加任务弹窗 -->
    <v-dialog v-model="showAddForm" max-width="660" persistent scrollable>
      <v-card class="studio-dialog-card task-create-dialog">
        <v-card-title class="studio-dialog-header">
          <div class="studio-dialog-heading">
            <div class="studio-dialog-title">创建标注任务</div>
            <p class="studio-dialog-subtitle">设置任务类型、标注类别和基础说明。</p>
          </div>
          <v-btn
            icon="mdi-close"
            variant="text"
            size="small"
            class="studio-dialog-close"
            aria-label="关闭创建任务弹窗"
            @click="showAddForm = false"
          />
        </v-card-title>

        <v-card-text class="studio-dialog-body">
          <v-form class="task-create-form" @submit.prevent="handleAddTask">
            <section class="studio-dialog-section">
              <div class="studio-dialog-section-heading">
                <span class="studio-dialog-section-title">任务设置</span>
                <span class="studio-dialog-section-copy">
                  每个标注任务当前只使用一种检测类型和一个分类。
                </span>
              </div>

              <v-text-field
                v-model="newTask.name"
                label="任务名称 *"
                placeholder="例如：道路锥桶检测"
                variant="outlined"
                density="comfortable"
                hide-details="auto"
                :rules="[rules.required]"
              />

              <fieldset class="detection-type-fieldset">
                <legend>检测类型 *</legend>
                <div class="detection-type-grid">
                  <button
                    v-for="type in detectionTypes"
                    :key="type.value"
                    type="button"
                    class="detection-type-option"
                    :class="{ 'is-selected': newTask.detection_type === type.value }"
                    role="radio"
                    :aria-checked="newTask.detection_type === type.value"
                    @click="newTask.detection_type = type.value"
                  >
                    <span class="detection-type-icon">
                      <v-icon :icon="type.icon" size="19" />
                    </span>
                    <span class="detection-type-copy">
                      <strong>{{ type.label }}</strong>
                      <small>{{ type.description }}</small>
                    </span>
                    <v-icon
                      :icon="
                        newTask.detection_type === type.value
                          ? 'mdi-check-circle'
                          : 'mdi-circle-outline'
                      "
                      size="18"
                      class="detection-type-check"
                    />
                  </button>
                </div>
              </fieldset>

              <v-text-field
                v-model="categoryInput"
                label="分类名称"
                placeholder="例如：锥桶"
                variant="outlined"
                density="comfortable"
                hide-details="auto"
              />

              <v-textarea
                v-model="newTask.description"
                label="任务描述"
                placeholder="补充任务目标或标注要求"
                variant="outlined"
                density="comfortable"
                rows="3"
                hide-details="auto"
              />
            </section>
          </v-form>
        </v-card-text>

        <v-card-actions class="studio-dialog-actions">
          <v-btn variant="text" @click="showAddForm = false">取消</v-btn>
          <v-spacer />
          <v-btn color="primary" variant="flat" prepend-icon="mdi-plus" @click="handleAddTask">
            创建任务
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <AppConfirmDialog />
    <AppSnackbar />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { type AssignmentDTO, type NewTask } from '@/types/task'
import PageHeader from '@/components/common/PageHeader.vue'
import router from '@/router'
import { createTask, deleteTask, getTasks } from '@/api/services'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'
import AppConfirmDialog from '@/components/common/AppConfirmDialog.vue'
import AppSnackbar from '@/components/common/AppSnackbar.vue'

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()

let tasks = ref<AssignmentDTO[]>([])

onMounted(async () => {
  document.title = '任务列表 - 数据标注与模型训练平台'
  try {
    tasks.value = await getTasks()
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '加载任务列表失败'), 'error')
  }
})

const showAddForm = ref(false)

const rules = {
  required: (v: string) => !!v?.trim() || '此字段为必填项',
}

// 检测类型选项
const detectionTypes = [
  {
    value: 'segmentation',
    label: '分割',
    description: '像素级别的图像分割',
    icon: 'mdi-vector-polygon',
  },
  {
    value: 'detection',
    label: '检测',
    description: '边界框目标检测',
    icon: 'mdi-vector-square',
  },
]

// 响应式表单数据
const newTask = reactive<NewTask>({
  name: '',
  detection_type: 'detection',
  description: '',
  categories: [],
})

const categoryInput = ref('')

function onTaskClick(task: AssignmentDTO) {
  router.push({
    path: `/task/${task.name}`,
    query: {
      type: task.detection_type,
    },
  })
}

// 获取检测类型标签
const getDetectionTypeLabel = (type: string) => {
  const found = detectionTypes.find((t) => t.value === type)
  return found ? found.label : type
}

const getErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'string') return error
  if (error instanceof Error && error.message) return error.message
  return fallback
}

// 处理添加任务
const handleAddTask = async (): Promise<void> => {
  if (!newTask.name.trim()) {
    snackbar.showSnackbar('请输入任务名称', 'warning')
    return
  }

  if (!newTask.detection_type) {
    snackbar.showSnackbar('请选择检测类型', 'warning')
    return
  }

  const task: NewTask = {
    name: newTask.name.trim(),
    detection_type: newTask.detection_type,
    description: newTask.description.trim(),
    categories: categoryInput.value.trim()
      ? [{ id: 1, name: categoryInput.value.trim(), supercategory: '' }]
      : [],
  }

  try {
    await createTask(task)
    resetNewTask()
    showAddForm.value = false
    tasks.value = await getTasks()
  } catch (error) {
    snackbar.showSnackbar(getErrorMessage(error, '创建任务失败'), 'error')
  }
}

const resetNewTask = (): void => {
  newTask.name = ''
  newTask.detection_type = 'detection'
  newTask.description = ''
  newTask.categories = []
  categoryInput.value = ''
}

const trainTask = (task: AssignmentDTO): void => {
  router.push({
    name: 'trainTask',
    params: {
      id: task.name,
    },
    query: {
      type: task.detection_type,
    },
  })
}

const handleDeleteTask = async (taskName: string): Promise<void> => {
  const confirmed = await confirmDialog.showConfirm('确认删除', '确定要删除这个任务吗？')
  if (confirmed) {
    try {
      await deleteTask(taskName)
      tasks.value = await getTasks()
    } catch (error) {
      snackbar.showSnackbar(getErrorMessage(error, '删除任务失败'), 'error')
    }
  }
}
</script>

<style scoped>
.task-list-page {
  height: 100%;
  min-height: 100%;
  box-sizing: border-box;
  background: rgb(var(--v-theme-background));
  padding: 28px;
  overflow-y: auto;
}

.task-list-page > :deep(.studio-page-header) {
  max-width: 1360px;
  margin: 0 auto 22px;
}

.tasks-grid {
  max-width: 1360px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.task-card {
  cursor: pointer;
  display: flex;
  min-height: 0;
  flex-direction: column;
  background: var(--studio-surface-1);
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    transform 0.15s ease;
}

.task-card:hover {
  background: var(--studio-surface-2);
  transform: translateY(-1px);
}

.task-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 14px;
}

.task-card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 10px;
}

.task-title {
  min-width: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.35;
}

.task-type-row {
  margin-bottom: 10px;
}

.task-category-section {
  margin-bottom: 10px;
}

.task-description-section {
  margin-bottom: 2px;
}

.task-description-section.is-empty {
  display: none;
}

.task-category-chip {
  color: var(--studio-ink-muted) !important;
  background: var(--studio-surface-2) !important;
  border: 1px solid var(--studio-hairline) !important;
}

.task-card :deep(.v-card-actions) {
  margin-top: auto;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.015);
  border-top: 1px solid var(--studio-hairline);
}

.description-text {
  max-height: 4.5em;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.empty-state {
  max-width: 400px;
  margin: 60px auto;
  text-align: center;
  padding: 40px;
}

.task-create-dialog {
  width: 100%;
}

.task-create-form {
  display: grid;
}

.detection-type-fieldset {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.detection-type-fieldset legend {
  margin-bottom: 8px;
  color: var(--studio-ink-muted);
  font-size: 12px;
  font-weight: 600;
}

.detection-type-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.detection-type-option {
  min-width: 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  color: var(--studio-ink-muted);
  text-align: left;
  background: var(--studio-surface-1);
  border: 1px solid var(--studio-hairline-strong);
  border-radius: 8px;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.detection-type-option:hover {
  background: var(--studio-surface-3);
  border-color: rgba(var(--v-theme-primary), 0.45);
}

.detection-type-option.is-selected {
  color: var(--studio-ink);
  background: rgba(var(--v-theme-primary), 0.13);
  border-color: rgba(var(--v-theme-primary), 0.62);
  box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.12);
}

.detection-type-icon {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--studio-ink-subtle);
  background: var(--studio-surface-3);
  border: 1px solid var(--studio-hairline);
  border-radius: 7px;
}

.detection-type-option.is-selected .detection-type-icon,
.detection-type-option.is-selected .detection-type-check {
  color: rgb(var(--v-theme-primary));
}

.detection-type-copy {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.detection-type-copy strong {
  color: inherit;
  font-size: 13px;
  font-weight: 600;
}

.detection-type-copy small {
  overflow: hidden;
  color: var(--studio-ink-subtle);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detection-type-check {
  color: var(--studio-ink-tertiary);
}

@media (max-width: 768px) {
  .task-list-page {
    padding: 16px;
  }

  .tasks-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .detection-type-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 1025px) {
  .tasks-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}
</style>
