import type { AssignmentDTO, NewTask, UpdateTask } from '@/types/task'
import http from '../http'

export const getTask = async (taskName: string): Promise<AssignmentDTO> => {
  return http.get<AssignmentDTO>('/tasks/task', {
    params: { name: taskName },
  })
}

export const getTasks = async (): Promise<AssignmentDTO[]> => {
  return http.get<AssignmentDTO[]>('/tasks/list')
}

export const createTask = async (task: NewTask): Promise<AssignmentDTO> => {
  return http.post<AssignmentDTO>('/tasks/create', task)
}

export const updateTask = async (task: UpdateTask): Promise<AssignmentDTO> => {
  return http.put<AssignmentDTO>('/tasks/update', task)
}

export const deleteTask = async (taskName: string) => {
  return http.delete('/tasks/delete', {
    params: { name: taskName },
  })
}
