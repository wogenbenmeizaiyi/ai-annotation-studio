import { createRouter, createWebHistory } from 'vue-router'
import DataAnnotationView from '../views/DataAnnotationView.vue'
import TaskDetail from '@/views/TaskView/TaskDetail.vue'
import TrainTaskView from '@/views/TaskView/TrainTaskView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/task',
    },
    {
      path: '/ai',
      redirect: '/ai/recognition',
    },
    {
      path: '/ai/recognition',
      name: 'aiRecognition',
      component: () => import('@/views/AiView/AiRecognitionTaskView.vue'),
      meta: { navigation: 'ai-recognition' },
    },
    {
      path: '/ai/models',
      name: 'aiModels',
      component: () => import('@/views/AiView/AiModelView.vue'),
      meta: { navigation: 'ai-models' },
    },
    {
      path: '/ai/combinations',
      name: 'aiCombinations',
      component: () => import('@/views/AiView/AiCombinationView.vue'),
      meta: { navigation: 'ai-combinations' },
    },
    {
      path: '/task',
      name: 'taskList',
      component: DataAnnotationView,
      meta: { navigation: 'tasks' },
    },
    {
      path: '/task/:id',
      name: 'taskDetail',
      component: TaskDetail,
      props: true,
      meta: { navigation: 'tasks' },
    },
    {
      path: '/task/:id/train',
      name: 'trainTask',
      component: TrainTaskView,
      props: true,
      meta: { navigation: 'tasks', focusMode: true },
    },
    {
      path: '/task/:taskId/:imageName/detect',
      name: 'detectionAnnotation',
      component: () => import('@/views/TaskView/DetectionAnnotationView.vue'),
      props: true,
      meta: { navigation: 'tasks', focusMode: true },
    },
    {
      path: '/task/:taskId/:imageName/segment',
      name: 'segmentationAnnotation',
      component: () => import('@/views/TaskView/SegmentationAnnotationView.vue'),
      props: true,
      meta: { navigation: 'tasks', focusMode: true },
    },
  ],
})

export default router
