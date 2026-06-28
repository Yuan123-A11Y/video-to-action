import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Link2,
  Upload,
  Film,
  Clipboard,
  Loader2,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  AlertCircle,
  Zap,
} from 'lucide-react'
import { processVideo, getStats, getVideos, getTask } from '../api/client'
import type { Stats, Video } from '../types'
import AnalysisProgressPanel from '../components/AnalysisProgressPanel'
import { PieChart } from '../components/SimpleCharts'
import { useWebSocket } from '../hooks/useWebSocket'

export default function HomePage() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  // 从 sessionStorage 恢复 taskId（解决刷新后进度面板消失的问题）
  const [taskId, setTaskId] = useState<string | null>(() => {
    try { return sessionStorage.getItem('vta_current_taskId') } catch { return null }
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 统计数据
  const [stats, setStats] = useState<Stats | null>(null)
  const [statsLoading, setStatsLoading] = useState(true)

  // 最近视频
  const [recentVideos, setRecentVideos] = useState<Video[]>([])
  const [videosLoading, setVideosLoading] = useState(true)

  const ws = useWebSocket({
    taskId,
    onComplete: async () => {
      try {
        const task = await getTask(taskId!)
        const videoId = task.result?.video_id ?? task.video_id
        if (videoId) {
          setTimeout(() => navigate(`/videos/${videoId}`), 1500)
        }
      } catch {
        // 获取失败不跳转
      } finally {
        // 任务完成/失败后清除持久化的 taskId
        sessionStorage.removeItem('vta_current_taskId')
      }
    },
    onError: (msg) => {
      setError(msg)
      sessionStorage.removeItem('vta_current_taskId')
    },
  })

  // 持久化 taskId 到 sessionStorage（刷新页面后可恢复）
  useEffect(() => {
    if (taskId) {
      sessionStorage.setItem('vta_current_taskId', taskId)
    }
  }, [taskId])

  // 页面加载时自动检测是否有活跃任务（处理中/等待中的任务）
  const [checkedActiveTask, setCheckedActiveTask] = useState(false)
  useEffect(() => {
    if (checkedActiveTask || taskId) return // 已有 taskId 或已检查过
    let cancelled = false
    const detectActiveTask = async () => {
      try {
        const resp = await fetch('/api/tasks?limit=5&status_filter=processing')
        if (!resp.ok) return
        const data = await resp.json()
        const activeTask = data.tasks?.[0]
        if (activeTask && !cancelled) {
          setTaskId(String(activeTask.id))
        }
      } catch { /* 静默 */ }
      setCheckedActiveTask(true)
    }
    detectActiveTask()
    return () => { cancelled = true }
  }, [checkedActiveTask, taskId])

  // 加载统计数据
  const loadStats = useCallback(async () => {
    try {
      const data = await getStats()
      setStats(data)
    } catch (err) {
      console.error('Failed to load stats:', err)
    } finally {
      setStatsLoading(false)
    }
  }, [])

  // 加载最近视频
  const loadRecentVideos = useCallback(async () => {
    try {
      const data = await getVideos(1, 5)
      setRecentVideos(data.videos || [])
    } catch (err) {
      console.error('Failed to load recent videos:', err)
    } finally {
      setVideosLoading(false)
    }
  }, [])

  // 图表数据：获取更多视频用于平台分布和趋势
  const [chartVideos, setChartVideos] = useState<Video[]>([])
  const [chartLoading, setChartLoading] = useState(true)

  const loadChartData = useCallback(async () => {
    try {
      const data = await getVideos(1, 200)
      setChartVideos(data.videos || [])
    } catch (err) {
      console.error('Failed to load chart data:', err)
    } finally {
      setChartLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStats()
    loadRecentVideos()
    loadChartData()
  }, [loadStats, loadRecentVideos, loadChartData])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setSubmitting(true)
    setError(null)

    try {
      const result = await processVideo({ url: url.trim() })
      setTaskId(result.task_id)
      setSubmitting(false)
      loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : '提交失败')
      setSubmitting(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setSubmitting(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/api/upload', { method: 'POST', body: formData })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || data.error?.message || '上传失败')
      }

      const result = await response.json()
      setTaskId(result.task_id)
      loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败')
      setSubmitting(false)
    }
  }

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText()
      if (text) setUrl(text)
    } catch { /* clipboard API 可能不支持 */ }
  }

  // 图表数据计算
  const platformData = useMemo(() => {
    const map: Record<string, number> = {}
    chartVideos.forEach(v => {
      const p = v.platform || '其他'
      map[p] = (map[p] || 0) + 1
    })
    const colors = ['#00D9A3', '#6366F1', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4']
    return Object.entries(map).map(([label, value], i) => ({
      label, value, color: colors[i % colors.length]
    }))
  }, [chartVideos])

  const statusChartData = useMemo(() => {
    if (!stats) return []
    return [
      { label: '已完成', value: stats.completed_tasks, color: '#16A34A' },
      { label: '处理中', value: stats.pending_tasks, color: '#D97706' },
      { label: '失败', value: stats.failed_tasks, color: '#DC2626' },
    ].filter(d => d.value > 0)
  }, [stats])


  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <div className="text-center py-6">
        <div className="flex items-center justify-center gap-2 mb-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-primary-soft)] flex items-center justify-center">
            <Zap size={24} className="text-[var(--color-primary)]" />
          </div>
          <h1 className="text-3xl font-bold text-[var(--color-text-primary)]">
            视频智能分析
          </h1>
        </div>
        <p className="text-lg text-[var(--color-text-secondary)] max-w-2xl mx-auto">
          提交视频链接或上传视频文件，AI 自动分析内容并生成可执行的操作步骤和命令
        </p>
      </div>

      {/* Stats Cards */}
      {!statsLoading && stats && (
        <div className="max-w-3xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-3 stagger">
          <div className="card-lift bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)]">
            <div className="flex items-center gap-2 mb-1">
              <Film size={16} className="text-[var(--color-text-tertiary)]" />
              <span className="text-xs text-[var(--color-text-tertiary)] font-medium">总视频数</span>
            </div>
            <p className="text-2xl font-bold text-[var(--color-text-primary)]">{stats.total_videos}</p>
          </div>
          <div className="card-lift bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)]">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 size={16} className="text-green-500" />
              <span className="text-xs text-[var(--color-text-tertiary)] font-medium">已完成</span>
            </div>
            <p className="text-2xl font-bold text-green-600">{stats.completed_tasks}</p>
          </div>
          <div className="card-lift bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)]">
            <div className="flex items-center gap-2 mb-1">
              <Loader2 size={16} className="text-orange-500 animate-spin" />
              <span className="text-xs text-[var(--color-text-tertiary)] font-medium">处理中</span>
            </div>
            <p className="text-2xl font-bold text-orange-600">{stats.pending_tasks}</p>
          </div>
          <div className="card-lift bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)]">
            <div className="flex items-center gap-2 mb-1">
              <AlertCircle size={16} className="text-red-500" />
              <span className="text-xs text-[var(--color-text-tertiary)] font-medium">失败</span>
            </div>
            <p className="text-2xl font-bold text-red-600">{stats.failed_tasks}</p>
          </div>
        </div>
      )}

      {/* Charts Section */}
      {!chartLoading && chartVideos.length > 0 && (
        <div className="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-in">
          {/* Status Distribution */}
          <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-5 shadow-[var(--shadow-sm)]">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
              <BarChart3 size={16} />
              任务状态分布
            </h3>
            <div className="flex items-center gap-6">
              <PieChart data={statusChartData} size={130} />
              <div className="flex-1 space-y-2">
                {statusChartData.map((d, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                    <span className="text-[var(--color-text-secondary)]">{d.label}</span>
                    <span className="ml-auto font-medium text-[var(--color-text-primary)]">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Platform Distribution */}
          <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-5 shadow-[var(--shadow-sm)]">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
              <Film size={16} />
              平台分布
            </h3>
            {platformData.length > 0 ? (
              <div className="flex items-center gap-6">
                <PieChart data={platformData} size={130} />
                <div className="flex-1 space-y-2">
                  {platformData.map((d, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                      <span className="text-[var(--color-text-secondary)] truncate">{d.label}</span>
                      <span className="ml-auto font-medium text-[var(--color-text-primary)]">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-[var(--color-text-tertiary)]">暂无数据</p>
            )}
          </div>

        </div>
      )}

      {/* Input Form */}
      <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-6 shadow-[var(--shadow-sm)] max-w-3xl mx-auto">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* URL Input */}
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
              视频链接
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]">
                  <Link2 size={18} />
                </span>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="支持 B站、抖音、YouTube 等主流平台..."
                  className="w-full pl-10 pr-4 py-3 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] font-mono text-sm focus:bg-white focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] outline-none transition-all"
                  disabled={submitting || !!taskId}
                />
              </div>
              <button
                type="button"
                onClick={handlePaste}
                className="px-3 py-2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] border border-[var(--color-border-default)] rounded-[var(--radius-sm)] hover:bg-[var(--color-bg-hover)] transition-all"
                title="粘贴"
              >
                <Clipboard size={18} />
              </button>
              <button
                type="submit"
                disabled={submitting || !url.trim() || !!taskId}
                className="px-6 py-3 bg-[var(--color-primary)] text-white rounded-[var(--radius-sm)] font-medium text-sm hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] btn-press"
              >
                {submitting && !taskId ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="animate-spin w-4 h-4" />
                    提交中...
                  </span>
                ) : '开始分析'}
              </button>
            </div>
          </div>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[var(--color-border-subtle)]" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-[var(--color-bg-surface)] px-3 text-[var(--color-text-tertiary)]">或者</span>
            </div>
          </div>

          {/* File Upload */}
          <div>
            <label
              className={`flex flex-col items-center justify-center px-6 py-10 border-2 border-dashed rounded-[var(--radius-lg)] cursor-pointer transition-all ${
                submitting
                  ? 'border-[var(--color-border-default)] bg-[var(--color-bg-raised)] cursor-not-allowed'
                  : 'border-[var(--color-border-default)] hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-soft)]'
              }`}
            >
              <input
                type="file"
                accept="video/*,.mp4,.mkv,.avi,.mov"
                onChange={handleFileUpload}
                disabled={submitting || !!taskId}
                className="hidden"
              />
              <Upload size={32} className="text-[var(--color-text-tertiary)] mb-3" />
              <p className="text-sm text-[var(--color-text-secondary)]">
                点击上传本地视频文件
              </p>
              <p className="text-xs text-[var(--color-text-tertiary)] mt-1">
                支持 MP4, MKV, AVI, MOV（最大 500MB）
              </p>
            </label>
          </div>

          {/* Supported Platforms */}
          <div className="flex items-center gap-2 pt-1 text-xs text-[var(--color-text-tertiary)] flex-wrap">
            <span>支持平台：</span>
            <span className="px-2 py-0.5 rounded-full bg-pink-50 text-pink-600 font-medium">B站</span>
            <span className="px-2 py-0.5 rounded-full bg-[var(--color-bg-raised)] text-[var(--color-text-secondary)]">抖音</span>
            <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-600 font-medium">YouTube</span>
            <span className="px-2 py-0.5 rounded-full bg-[var(--color-primary-soft)] text-[var(--color-primary-strong)] font-medium">其他（yt-dlp）</span>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-3 bg-[var(--color-error-soft)] border border-[var(--color-error)]/20 rounded-[var(--radius-sm)] text-sm text-[var(--color-error)] flex items-start gap-2 fade-in">
            <AlertTriangle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Analysis Progress Panel */}
      {taskId && (
        <AnalysisProgressPanel
          progress={ws.progress}
          status={ws.status}
          connected={ws.connected}
          taskId={taskId}
          mode={ws.mode}
        />
      )}

      {/* Recent Videos */}
      {!taskId && (
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <Film size={18} />
              最近视频
            </h2>
            <button
              onClick={() => navigate('/videos')}
              className="text-xs text-[var(--color-primary)] hover:underline font-medium"
            >
              查看全部 →
            </button>
          </div>

          {videosLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 stagger">
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)] animate-pulse">
                  <div className="flex gap-3">
                    <div className="w-20 h-12 bg-[var(--color-bg-raised)] rounded-md" />
                    <div className="flex-1">
                      <div className="h-4 bg-[var(--color-bg-raised)] rounded w-3/4 mb-2" />
                      <div className="h-3 bg-[var(--color-bg-raised)] rounded w-1/2" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : recentVideos.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 stagger">
              {recentVideos.map((video) => (
                <button
                  key={video.id}
                  onClick={() => video.status === 'completed' && navigate(`/videos/${video.id}`)}
                  className={`card-lift bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] hover:border-[var(--color-primary-border)] transition-all text-left group ${
                    video.status === 'completed' ? 'cursor-pointer' : 'cursor-default opacity-60'
                  }`}
                >
                  <div className="flex gap-3">
                    <div className="w-20 h-12 rounded-md bg-[var(--color-bg-raised)] shrink-0 flex items-center justify-center group-hover:bg-[var(--color-primary-soft)] transition-colors">
                      {video.status === 'completed' ? (
                        <Film size={16} className="text-[var(--color-text-tertiary)] group-hover:text-[var(--color-primary)] transition-colors" />
                      ) : (
                        <Loader2 size={16} className="text-[var(--color-text-tertiary)] animate-spin" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm text-[var(--color-text-primary)] line-clamp-2 group-hover:text-[var(--color-primary)] transition-colors">
                        {video.title || `视频 ${video.id}`}
                      </h3>
                      <div className="flex items-center gap-2 mt-1">
                        {video.platform && (
                          <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--color-bg-raised)] text-[var(--color-text-secondary)]">
                            {video.platform}
                          </span>
                        )}
                        <span className={`text-xs ${
                          video.status === 'completed' ? 'text-green-600' :
                          video.status === 'failed' ? 'text-red-600' :
                          'text-orange-600'
                        }`}>
                          {video.status === 'completed' ? '已完成' :
                           video.status === 'failed' ? '失败' :
                           video.status === 'processing' ? '处理中' : '等待中'}
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border-default)] p-8 text-center">
              <p className="text-2xl mb-2">🎬</p>
              <p className="text-sm text-[var(--color-text-secondary)]">暂无视频记录</p>
              <p className="text-xs text-[var(--color-text-tertiary)] mt-1">提交第一个视频后，预览将显示在这里</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
