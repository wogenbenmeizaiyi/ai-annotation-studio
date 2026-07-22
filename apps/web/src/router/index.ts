import { createRouter, createWebHistory } from 'vue-router'
import DataAnnotationView from '../views/DataAnnotationView.vue'
import TaskDetail from '@/views/TaskView/TaskDetail.vue'
import TrainTaskView from '@/views/TaskView/TrainTaskView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/center',
    },
    {
      path: '/center',
      name: 'workspaceCenter',
      component: () => import('@/views/WorkspaceCenterView.vue'),
    },
    {
      path: '/ai',
      redirect: '/ai/recognition',
    },
    {
      path: '/ai/recognition',
      name: 'aiRecognition',
      component: () => import('@/views/AiView/AiRecognitionTaskView.vue'),
    },
    {
      path: '/ai/models',
      name: 'aiModels',
      component: () => import('@/views/AiView/AiModelView.vue'),
    },
    {
      path: '/ai/combinations',
      name: 'aiCombinations',
      component: () => import('@/views/AiView/AiCombinationView.vue'),
    },
    {
      path: '/task',
      name: 'taskList',
      component: DataAnnotationView,
    },
    {
      path: '/task/:id',
      name: 'taskDetail',
      component: TaskDetail,
      props: true,
    },
    {
      path: '/task/:id/train',
      name: 'trainTask',
      component: TrainTaskView,
      props: true,
    },
    {
      path: '/task/:taskId/:imageName/detect',
      name: 'detectionAnnotation',
      component: () => import('@/views/TaskView/DetectionAnnotationView.vue'),
      props: true,
    },
    {
      path: '/task/:taskId/:imageName/segment',
      name: 'segmentationAnnotation',
      component: () => import('@/views/TaskView/SegmentationAnnotationView.vue'),
      props: true,
    },
  ],
})

export default router
