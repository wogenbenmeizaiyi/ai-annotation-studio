export type TrainAgentConfig = Record<string, unknown>

export interface TrainOptimizationDraft {
  config: TrainAgentConfig
  sourceTrainTaskId: number
}

export interface TrainAgentChatRequest {
  session_id: string | null
  task_name: string
  message: string
  current_config: TrainAgentConfig
  train_task_id: number | null
}

export interface TrainAgentChatResponse {
  session_id?: string | null
  proposal_id?: string
  config?: TrainAgentConfig
  message?: string
  reply?: string
  content?: string
  changes?: Array<{
    field: string
    before?: unknown
    after?: unknown
    reason: string
  }>
  warnings?: string[]
  questions?: string[]
  ready_to_apply?: boolean
  [key: string]: unknown
}

export interface TrainAgentContext {
  image_count?: number
  total_images?: number
  annotation_count?: number
  total_annotations?: number
  category_distribution?: unknown
  object_size_distribution?: unknown
  available_models?: unknown
  [key: string]: unknown
}

export interface TrainAgentConfirmResponse {
  confirmation_token?: string
  expires_at?: string
  expires_in?: number
  [key: string]: unknown
}

export interface TrainAgentStartResponse {
  proposal_id?: string
  train_task_id?: number
  status?: string
  task_id?: number
  id?: number
  [key: string]: unknown
}

export type TrainAgentAnalysis = Record<string, unknown>

export type TrainAgentAutoAnalysisStatus = 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED'

export interface TrainAgentAutoAnalysis {
  train_task_id?: number
  status: TrainAgentAutoAnalysisStatus
  analysis?: TrainAgentAnalysis | null
  model_result?: {
    reply?: string
    [key: string]: unknown
  } | null
  error_message?: string | null
  [key: string]: unknown
}
