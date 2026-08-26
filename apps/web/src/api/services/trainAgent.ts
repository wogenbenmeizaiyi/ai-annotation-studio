import http from '../http'
import type {
  TrainAgentAnalysis,
  TrainAgentAutoAnalysis,
  TrainAgentChatRequest,
  TrainAgentChatResponse,
  TrainAgentConfig,
  TrainAgentConfirmResponse,
  TrainAgentContext,
  TrainAgentStartResponse,
} from '@/types/trainAgent'

export const chatWithTrainAgent = async (
  data: TrainAgentChatRequest,
): Promise<TrainAgentChatResponse> => {
  return http.post<TrainAgentChatResponse>('/train/agent/chat', data)
}

export const getTrainAgentContext = async (taskName: string): Promise<TrainAgentContext> => {
  return http.get<TrainAgentContext>(`/train/agent/context/${encodeURIComponent(taskName)}`)
}

export const getTrainAgentAnalysis = async (trainTaskId: number): Promise<TrainAgentAnalysis> => {
  return http.get<TrainAgentAnalysis>(`/train/agent/analysis/${trainTaskId}`)
}

export const getTrainAgentAutoAnalysis = async (
  trainTaskId: number,
): Promise<TrainAgentAutoAnalysis> => {
  return http.get<TrainAgentAutoAnalysis>(`/train/agent/analysis/${trainTaskId}/auto`)
}

export const retryTrainAgentAutoAnalysis = async (
  trainTaskId: number,
): Promise<TrainAgentAutoAnalysis> => {
  return http.post<TrainAgentAutoAnalysis>(`/train/agent/analysis/${trainTaskId}/auto/retry`)
}

export const createTrainAgentOptimizationProposal = async (
  trainTaskId: number,
  instruction = '基于本次训练报告生成下一轮优化训练参数草案',
): Promise<TrainAgentChatResponse> => {
  return http.post<TrainAgentChatResponse>(`/train/agent/analysis/${trainTaskId}/proposal`, {
    instruction,
  })
}

export const confirmTrainAgentProposal = async (
  proposalId: string,
  expectedConfig: TrainAgentConfig,
): Promise<TrainAgentConfirmResponse> => {
  return http.post<TrainAgentConfirmResponse>(
    `/train/agent/proposals/${encodeURIComponent(proposalId)}/confirm`,
    { expected_config: expectedConfig },
  )
}

export const startTrainAgentProposal = async (
  proposalId: string,
  confirmationToken: string,
): Promise<TrainAgentStartResponse> => {
  return http.post<TrainAgentStartResponse>(
    `/train/agent/proposals/${encodeURIComponent(proposalId)}/start`,
    { confirmation_token: confirmationToken },
  )
}
