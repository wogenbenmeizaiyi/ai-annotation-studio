import http from '../http'
import { API_BASE_URL } from '@/config/env'
import type { CreateTrainRequest } from '@/types/ImageItem'
import type { TrainTask, TrainMetricsResponse, ModelDownloadResponse } from '@/types/train'

export const createTrain = async (data: CreateTrainRequest) => {
  return http.post('/train/create', data)
}

export const getTrainList = async (taskName?: string): Promise<TrainTask[]> => {
  return http.get<TrainTask[]>('/train/list', { params: taskName ? { task_name: taskName } : {} })
}

export const getTrainStatus = async (taskId: number): Promise<TrainTask> => {
  return http.get<TrainTask>(`/train/${taskId}`)
}

export const getTrainMetrics = async (taskId: number): Promise<TrainMetricsResponse> => {
  return http.get<TrainMetricsResponse>(`/train/${taskId}/metrics`)
}

export const getModelDownloadUrl = async (taskId: number): Promise<ModelDownloadResponse> => {
  return http.get<ModelDownloadResponse>(`/train/${taskId}/model/download`)
}

export const deleteTrain = async (taskId: number): Promise<void> => {
  return http.delete(`/train/${taskId}`)
}

export const retryTrain = async (taskId: number): Promise<{ task_id: number }> => {
  return http.post<{ task_id: number }>(`/train/${taskId}/retry`)
}

export const createTrainEventSource = (taskId: number): EventSource => {
  const url = `${API_BASE_URL}/train/${taskId}/stream`
  return new EventSource(url)
}
