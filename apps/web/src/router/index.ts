import { createRouter, createWebHistory } from 'vue-router'
import DataAnnotationView from '../views/DataAnnotationView.vue'
import TaskDetail from '@/views/TaskView/TaskDetail.vue'
import TrainTaskView from '@/views/TaskView/TrainTaskView.vue'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/task',
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/AuthView/LoginView.vue'),
      meta: { public: true, publicLayout: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/AuthView/RegisterView.vue'),
      meta: { public: true, publicLayout: true },
    },
    {
      path: '/change-password',
      name: 'changePassword',
      component: () => import('@/views/AuthView/ChangePasswordView.vue'),
      meta: { publicLayout: true },
    },
    {
      path: '/admin/users',
      name: 'userManagement',
      component: () => import('@/views/AuthView/UserManagementView.vue'),
      meta: { navigation: 'users', superAdmin: true },
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

router.beforeEach(async (to) => {
  const auth = useAuthStore(pinia)
  if (!auth.initialized) await auth.loadCurrentUser()

  if (to.meta.public === true) {
    if (auth.isAuthenticated) {
      return auth.user?.must_change_password ? { name: 'changePassword' } : { name: 'taskList' }
    }
    return true
  }
  if (!auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (auth.user?.must_change_password && to.name !== 'changePassword') {
    return { name: 'changePassword' }
  }
  if (!auth.user?.must_change_password && to.name === 'changePassword') {
    return { name: 'taskList' }
  }
  if (to.meta.superAdmin === true && !auth.isSuperAdmin) {
    return { name: 'taskList' }
  }
  return true
})

export default router
