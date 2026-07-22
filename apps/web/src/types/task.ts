import type { CocoCategory } from './CocoCategory'

// types/task.ts
export enum TaskStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in-progress',
  COMPLETED = 'completed',
}

export interface Assignment {
  id: number
  name: string
  categories: CocoCategory[]
  startTime: Date
  updateTime: Date
  description: string
  detection_type: string
}

export interface AssignmentDTO {
  id: number
  name: string
  description: string
  categories: CocoCategory[]
  created_at: string // ISO 字符串
  updated_at: string
  detection_type: string
}

export type NewTask = {
  name: string
  detection_type: string
  description: string
  categories: { id: number | null; name: string; supercategory: string }[]
}

export interface UpdateTask {
  name: string
  detection_type: string
  description: string
  categories: { id: number | null; name: string; supercategory: string }[]
}

export const TaskStatusText: Record<TaskStatus, string> = {
  [TaskStatus.PENDING]: '待开始',
  [TaskStatus.IN_PROGRESS]: '进行中',
  [TaskStatus.COMPLETED]: '已完成',
}
