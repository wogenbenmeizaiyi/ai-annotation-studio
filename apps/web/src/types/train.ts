import type { TrainConfig } from './ImageItem'

export type TrainTaskStatus =
  | 'PENDING'
  | 'QUEUED'
  | 'CLAIMED'
  | 'RECOVERING'
  | 'RUNNING'
  | 'FINISHED'
  | 'ERROR'
  | 'CANCELLED'

export interface TrainTask {
  id: number
  task_id: number
  model_name: string
  status: TrainTaskStatus
  pid: number | null
  progress: number
  current_epoch: number
  total_epochs: number
  error_message: string | null
  config: TrainConfig
  log_path: string
  output_path: string
  created_at: string
  updated_at: string
}

export interface TrainEpochMetric {
  id?: number
  train_task_id?: number
  epoch: number
  time_cost?: number
  train_box_loss?: number | null
  train_seg_loss?: number | null
  train_cls_loss?: number | null
  train_dfl_loss?: number | null
  val_box_loss?: number | null
  val_seg_loss?: number | null
  val_cls_loss?: number | null
  val_dfl_loss?: number | null
  precision?: number | null
  recall?: number | null
  map50?: number | null
  map50_95?: number | null
  mask_precision?: number | null
  mask_recall?: number | null
  mask_map50?: number | null
  mask_map50_95?: number | null
  fitness?: number | null
  per_class_metrics?: unknown
  lr_pg0?: number | null
  lr_pg1?: number | null
  lr_pg2?: number | null
  is_best?: boolean
  created_at?: string
  [key: string]: unknown
}

export interface TrainMetricsResponse {
  task: TrainTask
  metrics: TrainEpochMetric[]
}

export interface ModelDownloadResponse {
  download_url: string
  expires_in: number
  model_name: string
  filename: string
}

export interface TrainStreamData {
  status: TrainTaskStatus | string
  epoch?: number
  total_epochs?: number
  progress?: number
  metrics?: TrainEpochMetric[]
  s3_model_url?: string
  error_message?: string
}
