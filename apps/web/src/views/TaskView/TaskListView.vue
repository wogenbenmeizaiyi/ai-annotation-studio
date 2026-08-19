<template>
  <div class="task-list-page">
    <PageHeader title="标注任务" description="管理检测与分割数据集，并从同一任务进入标注和训练。">
      <template #actions>
        <v-btn color="primary" @click="showAddForm = true">
          <template #prepend>
            <Icon name="plus" :size="16" />
          </template>
          添加新任务
        </v-btn>
      </template>
    </PageHeader>

    <!-- 任务列表 -->
    <div class="tasks-grid">
      <article
        v-for="(task, index) in tasks"
        :key="task.id"
        class="task-card"
        tabindex="0"
        role="button"
        @click="onTaskClick(task)"
        @keydown.enter="onTaskClick(task)"
      >
        <div class="task-card-content">
          <div class="task-card-title-row">
            <div class="task-title">{{ task.name }}</div>
            <span class="task-index">#{{ index + 1 }}</span>
          </div>

          <div class="task-type-row">
            <span
              class="task-type-chip"
              :class="task.detection_type === 'segmentation' ? 'is-sage' : 'is-cinnabar'"
            >
              {{ getDetectionTypeLabel(task.detection_type) }}
            </span>
          </div>

          <div v-if="task.categories.length" class="task-category-section">
            <div class="task-section-label">分类标签</div>
            <div class="task-category-chips">
              <span v-for="category in task.categories" :key="category.id" class="task-category-chip">
                {{ category.name }}
                <span v-if="category.supercategory" class="task-category-sup">
                  ({{ category.supercategory }})
                </span>
              </span>
            </div>
          </div>

          <div v-if="task.description" class="task-description-section">
            <div class="task-section-label">任务描述</div>
            <div class="description-text">{{ task.description }}</div>
          </div>
        </div>

        <div v-if="task.can_manage" class="task-card-actions">
          <button class="task-action" type="button" @click.stop="trainTask(task)">
            <Icon name="play" :size="14" /> 训练
          </button>
          <button class="task-action is-danger" type="button" @click.stop="handleDeleteTask(task.name)">
            <Icon name="delete-outline" :size="14" /> 删除
          </button>
        </div>
      </article>
    </div>

    <!-- 空状态 -->
    <div v-if="tasks.length === 0" class="empty-state">
      <Icon name="clipboard" :size="64" class="empty-icon" />
      <h3 class="empty-title">暂无任务</h3>
      <p class="empty-hint">点击"添加新任务"按钮开始创建您的第一个任务</p>
      <v-btn color="primary" class="mt-4" @click="showAddForm = true">创建任务</v-btn>
    </div>

    <!-- 添加任务弹窗 -->
    <v-dialog v-model="showAddForm" max-width="500" persistent>
      <v-card class="app-confirm-card">
        <v-card-title class="app-confirm-title d-flex align-center justify-space-between">
          <span>创建新任务</span>
          <button class="dialog-close-btn" type="button" aria-label="关闭" @click="showAddForm = false">
            <Icon name="close" :size="18" />
          </button>
        </v-card-title>

        <v-divider />

        <v-card-text class="app-confirm-text">
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

        <v-card-actions class="app-confirm-actions pa-4">
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
import PageHeader from '@/components/common/PageHeader.vue'
import router from '@/router'
import { createTask, deleteTask, getTasks } from '@/api/services'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import { useSnackbar } from '@/composables/useSnackbar'
import AppConfirmDialog from '@/components/common/AppConfirmDialog.vue'
import AppSnackbar from '@/components/common/AppSnackbar.vue'
import { Icon } from '@/components/icons'

const confirmDialog = useConfirmDialog()
const snackbar = useSnackbar()

let tasks = ref<AssignmentDTO[]>([])

onMounted(async () => {
  document.title = '任务列表 - AI Studio'
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

const detectionTypes = [
  { value: 'segmentation', label: '分割', description: '像素级别的图像分割' },
  { value: 'detection', label: '检测', description: '边界框目标检测' },
]

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
    query: { type: task.detection_type },
  })
}

const getDetectionTypeLabel = (type: string) => {
  const found = detectionTypes.find((t) => t.value === type)
  return found ? found.label : type
}

const getErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'string') return error
  if (error instanceof Error && error.message) return error.message
  return fallback
}

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
    params: { id: task.name },
    query: { type: task.detection_type },
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
  background: var(--bg-app);
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
  gap: 18px;
}

.task-card {
  cursor: pointer;
  display: flex;
  min-height: 0;
  flex-direction: column;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-card-sm);
  transition:
    transform 0.18s,
    border-color 0.18s,
    box-shadow 0.18s;
}
.task-card:hover,
.task-card:focus-visible {
  transform: translateY(-2px);
  border-color: var(--ink);
  outline: none;
}

.task-card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 18px;
}

.task-card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.task-title {
  min-width: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.35;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  letter-spacing: -0.02em;
}

.task-index {
  flex: 0 0 auto;
  padding: 2px 7px;
  color: var(--text-subtle);
  background: var(--bg-sunken);
  font-family: var(--font-mono);
  font-size: 11px;
}

.task-type-row {
  margin-bottom: 14px;
}
.task-type-chip {
  display: inline-flex;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.task-type-chip.is-cinnabar {
  background: var(--accent-soft);
  color: var(--accent);
}
.task-type-chip.is-sage {
  background: var(--status-success-bg);
  color: var(--status-success);
}

.task-section-label {
  color: var(--text-label);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.task-category-section {
  margin-bottom: 12px;
}
.task-category-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.task-category-chip {
  display: inline-flex;
  padding: 3px 8px;
  color: var(--text);
  background: var(--bg-sunken);
  border: 1px solid var(--border);
  font-size: 12px;
}
.task-category-sup {
  color: var(--text-subtle);
  margin-left: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
}

.task-description-section {
  margin-top: auto;
  margin-bottom: 0;
}
.description-text {
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.6;
  max-height: 4.5em;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.task-card-actions {
  display: flex;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-elevated);
  border-top: 1px solid var(--border);
}
.task-action {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 12px;
  color: var(--text);
  background: transparent;
  border: 1px solid var(--border);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, transform 0.15s, color 0.15s, border-color 0.15s;
}
.task-action:hover {
  background: var(--bg-sunken);
  border-color: var(--border-strong);
  transform: translateY(-1px);
}
.task-action.is-danger {
  color: var(--text-muted);
  border-color: var(--border);
}
.task-action.is-danger:hover {
  color: var(--status-error);
  border-color: var(--status-error);
  background: var(--status-error-bg);
}

.dialog-close-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border);
  cursor: pointer;
}
.dialog-close-btn:hover {
  background: var(--bg-sunken);
  color: var(--ink);
  border-color: var(--ink);
}

.empty-state {
  max-width: 400px;
  margin: 60px auto;
  display: grid;
  justify-items: center;
  gap: 8px;
  text-align: center;
  padding: 40px;
}
.empty-icon {
  color: var(--text-subtle);
  opacity: 0.5;
}
.empty-title {
  margin: 8px 0 0;
  color: var(--text);
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
}
.empty-hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}

@media (max-width: 768px) {
  .task-list-page {
    padding: 16px;
  }
  .tasks-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media (min-width: 1025px) {
  .tasks-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}
</style>
