export type AiDetectionType = 1 | 2 | 3 | 4

export type RecognitionTaskStatus = 'pending' | 'processing' | 'success' | 'failed'

export interface AiPageOptions {
  page?: number
  pageSize?: number
}

export interface AiPage<T> {
  page: number
  pageSize: number
  totalPages: number
  total: number
  items: T[]
}

export interface RecognitionRequest {
  detection_type: AiDetectionType
  images: string[]
  text?: string
  project_name?: string
}

export type FixedRecognitionRequest = Omit<RecognitionRequest, 'detection_type'>

export interface RecognitionSubmitResult {
  task_id: string
  status: RecognitionTaskStatus
}

export interface RecognitionTask {
  task_id: string
  status: RecognitionTaskStatus
  detection_type: AiDetectionType
  text: string | null
  project_name: string
  image_count: number
  error: string | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  created_at: string
  updated_at: string
}

export interface RecognitionTaskQuery extends AiPageOptions {
  status?: RecognitionTaskStatus
  createdAtStart?: string
  createdAtEnd?: string
  detectionType?: AiDetectionType
  projectName?: string
}

export interface AiCocoImage {
  id: number
  file_name: string
  width: number
  height: number
}

export interface AiCocoAnnotation {
  id: number
  image_id: number
  category_id: number
  bbox: [number, number, number, number]
  score: number
  segmentation: number[][]
}

export interface AiCocoCategory {
  id: number
  name: string
  supercategory: string
}

export interface RecognitionResultItem {
  image_index: number
  url: string
  service: string
  detection_type: string
  count: number
  image_key: string
  coco_key: string
  images: AiCocoImage[]
  annotations: AiCocoAnnotation[]
  categories: AiCocoCategory[]
  created_at: string
}

export interface DirectModelRecognitionRequest {
  file: File
  model_uuid: string
  confidence?: number
}

export interface DirectModelRecognitionResponse {
  model: Pick<AiModel, 'uuid' | 'name' | 'detection_type'>
  result: Pick<
    RecognitionResultItem,
    'service' | 'detection_type' | 'count' | 'url' | 'images' | 'annotations' | 'categories'
  >
}

export interface AiModel {
  id?: number
  uuid: string
  name: string
  detection_type: AiDetectionType
  prompt: string | null
  model_file: string | null
  storage_key: string | null
  project_name: string
  is_deleted: boolean
  description: string | null
  created_at: string
  updated_at: string
  owner_subject_id: string | null
  can_manage: boolean
}

export interface CreateAiModelRequest {
  uuid?: string
  name: string
  detection_type: AiDetectionType
  model_file?: string
  storage_key?: string
  prompt?: string
  project_name?: string
  description?: string
}

export type UpdateAiModelRequest = Partial<Omit<CreateAiModelRequest, 'uuid'>>

export interface AiModelQuery extends AiPageOptions {
  detection_type?: AiDetectionType
  includeDeleted?: boolean
}

export interface UploadAiModelRequest {
  file: File
  name: string
  detection_type: AiDetectionType
  prompt?: string
  project_name?: string
  description?: string
  storage_key?: string
}

export interface DeleteAiResourceResult {
  deleted: boolean
  uuid: string
}

export interface AiCombination {
  uuid: string
  name: string
  project_name: string
  description: string | null
  is_deleted: boolean
  models: AiModel[]
  created_at: string
  updated_at: string
  owner_subject_id: string | null
  can_manage: boolean
}

export interface CreateAiCombinationRequest {
  name: string
  model_uuids: string[]
  project_name?: string
  description?: string
}

export type UpdateAiCombinationRequest = Partial<CreateAiCombinationRequest> & {
  is_deleted?: boolean
}

export interface AiCombinationQuery extends AiPageOptions {
  projectName?: string
  includeDeleted?: boolean
}

export interface AiServiceDictionaryItem {
  [key: string]: unknown
}
