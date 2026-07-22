<template>
  <div class="task-list-page">
    <!-- 页面标题和添加按钮 -->
    <div class="page-header">
      <h1 class="page-title">任务列表</h1>
      <div class="page-actions">
        <v-btn color="primary" prepend-icon="mdi-plus" @click="showAddForm = true">
          添加新任务
        </v-btn>
      </div>
    </div>

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
            <v-chip size="x-small" variant="flat" color="grey-lighten-3" class="ml-2">
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
                variant="outlined"
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

        <v-divider />

        <v-card-actions>
          <v-btn
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
    <v-dialog v-model="showAddForm" max-width="500" persistent>
      <v-card>
        <v-card-title class="d-flex align-center justify-space-between">
          <span>创建新任务</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="showAddForm = false" />
        </v-card-title>

        <v-divider />

        <v-card-text>
          <v-form @submit.prevent="handleAddTask">
            <v-text-field
              v-model="newTask.name"
              label="任务名称 *"
              placeholder="请输入任务名称"
              variant="outlined"
              density="comfortable"
              class="mb-4"
              :rules="[rules.required]"
            />

            <div class="text-subtitle-2 mb-2">检测类型 *</div>
            <v-radio-group v-model="newTask.detection_type" class="mb-4" inline>
              <v-radio
                v-for="type in detectionTypes"
                :key="type.value"
                :value="type.value"
                :label="`${type.label} - ${type.description}`"
              />
            </v-radio-group>

            <v-text-field
              v-model="categoryInput"
              label="分类名称"
              placeholder="请输入分类名称"
              variant="outlined"
              density="comfortable"
              class="mb-4"
            />

            <v-textarea
              v-model="newTask.description"
              label="任务描述"
              placeholder="请输入任务描述"
              variant="outlined"
              density="comfortable"
              rows="4"
            />
          </v-form>
        </v-card-text>

        <v-divider />

        <v-card-actions class="pa-4">
          <v-btn variant="outlined" @click="showAddForm = false">取消</v-btn>
          <v-spacer />
          <v-btn color="primary" @click="handleAddTask">创建任务</v-btn>
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
  },
  {
    value: 'detection',
    label: '检测',
    description: '边界框目标检测',
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
  min-height: 100%;
  box-sizing: border-box;
  background: rgb(var(--v-theme-background));
  padding: 24px;
}

.page-header {
  max-width: 1200px;
  margin: 0 auto 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-background));
  margin: 0;
}

.page-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tasks-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px;
}

.task-card {
  cursor: pointer;
  display: flex;
  min-height: 268px;
  flex-direction: column;
}

.task-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.task-card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  min-height: 32px;
  margin-bottom: 12px;
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
  min-height: 32px;
  margin-bottom: 12px;
}

.task-category-section {
  min-height: 56px;
  margin-bottom: 12px;
}

.task-description-section {
  min-height: 50px;
}

.task-description-section.is-empty {
  visibility: hidden;
}

.task-card :deep(.v-card-actions) {
  margin-top: auto;
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

@media (max-width: 768px) {
  .task-list-page {
    padding: 16px;
  }

  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .page-actions {
    width: 100%;
  }

  .tasks-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media (min-width: 1025px) {
  .tasks-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}
</style>
