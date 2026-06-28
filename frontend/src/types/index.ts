// API 响应类型

export interface Video {
  id: number
  url: string
  platform: string
  title?: string
  theme?: string
  summary?: string
  topic?: string
  duration?: string
  transcription_text?: string
  analysis_result?: AnalysisResult
  status: VideoStatus
  created_at: string
  updated_at?: string
  error_message?: string
}

export type VideoStatus = 'pending' | 'downloading' | 'downloaded' | 'processing' | 'completed' | 'failed'

export interface AnalysisResult {
  theme?: string
  summary?: string
  tools?: Array<{
    name: string
    purpose?: string
    install_commands?: string[]
    config_steps?: string[]
    run_commands?: string[]
    warnings?: string[]
    links?: string[]
  }>
  steps?: AnalysisStep[]
  commands?: string[]
  raw_output?: string
}

export interface AnalysisStep {
  step_number: number
  title: string
  description: string
  commands?: string[]
  explanation?: string
  tools?: string[]
}

export interface Tool {
  id: number
  name: string
  category?: string
  description?: string
  purpose?: string
  install_commands?: string[]
  config_steps?: string[]
  usage_examples?: string[]
  example?: string
  homepage_url?: string
  is_paid: boolean
}

export interface Task {
  task_id: string
  status: TaskStatus
  progress?: ProgressUpdate
  video_id?: number
  result?: TaskResult
  error?: string
  created_at: string
  updated_at: string
}

export interface TaskResult {
  video_id?: number
  theme?: string
  summary?: string
  tools?: string[]
  video_path?: string
  transcription_length?: number
  frame_count?: number
}

export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface ProgressUpdate {
  step: number
  total_steps: number
  step_name: string
  message: string
  percentage: number
}

export interface ProcessRequest {
  url: string
  level?: string
  save_to_kb?: boolean
}

export interface ProcessResponse {
  task_id: string
  message: string
}

export interface BatchProcessRequest {
  urls: string[]
}

export interface SearchParams {
  q: string
  type?: 'video' | 'tool' | 'all'
  page?: number
  page_size?: number
  platform?: string
  category?: string
  sort_by?: 'relevance' | 'date'
}

export interface SearchResult {
  videos: Video[]
  tools: Tool[]
  total: number
  page?: number
  page_size?: number
}

export interface Stats {
  total_videos: number
  total_tools: number
  completed_tasks: number
  pending_tasks: number
  failed_tasks: number
}
