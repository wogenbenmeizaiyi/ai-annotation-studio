// 图片列表响应
export interface ImageItem {
  id: number
  task_id: number
  file_name: string
  original_name: string
  s3_key: string
  url: string
  width: number
  height: number
  file_size: number
  detection_type: string
  is_annotated: boolean
  is_deleted: boolean
  annotation_jsonb: unknown
  created_at: string
  updated_at: string
}

export interface ImageUploadResponse {
  count: number
  files: ImageItem[]
}

export interface ImageListPage {
  list: ImageItem[]
  page: number
  page_size: number
  total: number
  annotated_count: number
  total_pages: number
}

// 训练配置
export interface TrainConfig {
  [key: string]: unknown
}

export interface CreateTrainRequest {
  task_name: string
  priority?: number
  config?: Partial<TrainConfig>
  parent_train_task_id?: number
}
