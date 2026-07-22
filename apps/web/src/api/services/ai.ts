import aiHttp from '../aiHttp'
import type {
  AiCombination,
  AiCombinationQuery,
  AiDetectionType,
  AiModel,
  AiModelQuery,
  AiPage,
  AiPageOptions,
  AiServiceDictionaryItem,
  CreateAiCombinationRequest,
  CreateAiModelRequest,
  DeleteAiResourceResult,
  DirectModelRecognitionRequest,
  DirectModelRecognitionResponse,
  FixedRecognitionRequest,
  RecognitionRequest,
  RecognitionResultItem,
  RecognitionSubmitResult,
  RecognitionTask,
  RecognitionTaskQuery,
  UpdateAiCombinationRequest,
  UpdateAiModelRequest,
  UploadAiModelRequest,
} from '@/types/ai'

const fixedRecognitionPaths: Record<AiDetectionType, string> = {
  1: '/recognition/recognize/yolo-detection',
  2: '/recognition/recognize/yolo-segmentation',
  3: '/recognition/recognize/sam-segmentation',
  4: '/recognition/recognize/multimodal',
}

const toFormData = (data: DirectModelRecognitionRequest | UploadAiModelRequest): FormData => {
  const formData = new FormData()

  Object.entries(data).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      formData.append(key, value instanceof File ? value : String(value))
    }
  })

  return formData
}

export const submitRecognition = async (
  data: RecognitionRequest,
): Promise<RecognitionSubmitResult> => {
  return aiHttp.post<RecognitionSubmitResult>('/recognition/recognize', data)
}

export const submitFixedRecognition = async (
  detectionType: AiDetectionType,
  data: FixedRecognitionRequest,
): Promise<RecognitionSubmitResult> => {
  return aiHttp.post<RecognitionSubmitResult>(fixedRecognitionPaths[detectionType], data)
}

export const getRecognitionTasks = async (
  options: RecognitionTaskQuery = {},
): Promise<AiPage<RecognitionTask>> => {
  return aiHttp.get<AiPage<RecognitionTask>>('/recognition/tasks', { params: options })
}

export const getRecognitionTaskResults = async (
  taskId: string,
  options: AiPageOptions = {},
): Promise<AiPage<RecognitionResultItem>> => {
  return aiHttp.get<AiPage<RecognitionResultItem>>('/recognition/tasks/results', {
    params: { task_id: taskId, ...options },
  })
}

export const recognizeModelDirectly = async (
  data: DirectModelRecognitionRequest,
): Promise<DirectModelRecognitionResponse> => {
  return aiHttp.post<DirectModelRecognitionResponse>(
    '/recognition/recognize/direct',
    toFormData(data),
    {
      headers: { 'Content-Type': 'multipart/form-data' },
    },
  )
}

export const getAiServiceDictionary = async (): Promise<AiServiceDictionaryItem[]> => {
  return aiHttp.get<AiServiceDictionaryItem[]>('/dict/services')
}

export const getYoloModelDictionary = async (): Promise<string[]> => {
  return aiHttp.get<string[]>('/dict/models/yolo')
}

export const createAiModel = async (data: CreateAiModelRequest): Promise<AiModel> => {
  return aiHttp.post<AiModel>('/models', data)
}

export const getAiModels = async (options: AiModelQuery = {}): Promise<AiPage<AiModel>> => {
  return aiHttp.get<AiPage<AiModel>>('/models', { params: options })
}

export const getAiModel = async (modelUuid: string): Promise<AiModel> => {
  return aiHttp.get<AiModel>(`/models/${encodeURIComponent(modelUuid)}`)
}

export const updateAiModel = async (
  modelUuid: string,
  data: UpdateAiModelRequest,
): Promise<AiModel> => {
  return aiHttp.put<AiModel>(`/models/${encodeURIComponent(modelUuid)}`, data)
}

export const deleteAiModel = async (modelUuid: string): Promise<DeleteAiResourceResult> => {
  return aiHttp.delete<DeleteAiResourceResult>(`/models/${encodeURIComponent(modelUuid)}`)
}

export const uploadAiModel = async (data: UploadAiModelRequest): Promise<AiModel> => {
  return aiHttp.post<AiModel>('/models/upload', toFormData(data), {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const createAiCombination = async (
  data: CreateAiCombinationRequest,
): Promise<AiCombination> => {
  return aiHttp.post<AiCombination>('/combinations', data)
}

export const getAiCombinations = async (
  options: AiCombinationQuery = {},
): Promise<AiPage<AiCombination>> => {
  return aiHttp.get<AiPage<AiCombination>>('/combinations', { params: options })
}

export const getAiCombination = async (combinationUuid: string): Promise<AiCombination> => {
  return aiHttp.get<AiCombination>('/combinations/detail', {
    params: { uuid: combinationUuid },
  })
}

export const updateAiCombination = async (
  combinationUuid: string,
  data: UpdateAiCombinationRequest,
): Promise<AiCombination> => {
  return aiHttp.put<AiCombination>('/combinations', data, {
    params: { uuid: combinationUuid },
  })
}

export const deleteAiCombination = async (
  combinationUuid: string,
): Promise<DeleteAiResourceResult> => {
  return aiHttp.delete<DeleteAiResourceResult>('/combinations', {
    params: { uuid: combinationUuid },
  })
}
