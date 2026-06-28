import { useState, useEffect, useRef } from 'react'
import {
  Plus,
  X,
  CheckCircle2,
  Clock,
  AlertCircle,
  Eye,
  Loader2,
  Trash2,
} from 'lucide-react'
import { batchProcessVideos, getBatchStatus } from '../api/client'

interface BatchTask {
  id: string
  url: string
  title: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  error?: string
  duration?: string
  startTime?: number
}

export default function BatchPage() {
  const [showInput, setShowInput] = useState(false)
  const [urls, setUrls] = useState('')
  const [concurrency, setConcurrency] = useState(2)
  const [tasks, setTasks] = useState<BatchTask[]>([])
  const [submitting, setSubmitting] = useState(false)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 轮询任务状态
  useEffect(() => {
    const pendingTasks = tasks.filter(t => t.status === 'pending' || t.status === 'processing')
    if (pendingTasks.length === 0) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
      return
    }

    pollingRef.current = setInterval(async () => {
      const pendingIds = pendingTasks.map(t => t.id)
      try {
        const statusData = await getBatchStatus(pendingIds)
        setTasks(prev => prev.map(task => {
          const updated = statusData.tasks.find(u => u.task_id === task.id)
          if (!updated) return task
          return {
            ...task,
            status: updated.status as BatchTask['status'],
            error: updated.error,
            progress: updated.status === 'completed' ? 100 : updated.status === 'failed' ? 0 : task.progress,
          }
        }))
      } catch (err) {
        console.error('Failed to poll task status:', err)
      }
    }, 2000)

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [tasks])

  const handleAddTasks = async () => {
    if (!urls.trim()) return
    const lines = urls.split('\n').filter(l => l.trim())
    if (lines.length === 0) return

    setSubmitting(true)
    try {
      const result = await batchProcessVideos({ urls: lines })
      const newTasks: BatchTask[] = result.task_ids.map((item: { url: string; task_id: string }, i: number) => ({
        id: item.task_id,
        url: item.url,
        title: `视频 ${tasks.length + i + 1}`,
        status: 'pending' as const,
        progress: 0,
        startTime: Date.now(),
      }))
      setTasks([...newTasks, ...tasks])
      setUrls('')
      setShowInput(false)
    } catch (err) {
      alert(`提交失败: ${err instanceof Error ? err.message : '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  const handleRemoveTask = (taskId: string) => {
    setTasks(tasks.filter(t => t.id !== taskId))
  }

  const handleClearCompleted = () => {
    setTasks(tasks.filter(t => t.status !== 'completed' && t.status !== 'failed'))
  }

  const statusConfig: Record<BatchTask['status'], { label: string; color: string; icon: typeof CheckCircle2 }> = {
    completed: { label: '已完成', color: 'text-green-600 bg-green-50', icon: CheckCircle2 },
    processing: { label: '处理中', color: 'text-blue-600 bg-blue-50', icon: Loader2 },
    pending: { label: '等待中', color: 'text-gray-600 bg-gray-50', icon: Clock },
    failed: { label: '失败', color: 'text-red-600 bg-red-50', icon: AlertCircle },
  }

  const stats = {
    total: tasks.length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length,
    processing: tasks.filter(t => t.status === 'processing').length,
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">批量处理</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-1">批量提交多个视频链接，并行处理并统一管理结果</p>
        </div>
        <button
          onClick={() => setShowInput(!showInput)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-[var(--color-primary)] text-white rounded-[var(--radius-sm)] text-sm font-medium hover:bg-[var(--color-primary-hover)] transition-colors shadow-[var(--shadow-sm)]"
        >
          <Plus size={16} />
          新建任务
        </button>
      </div>

      {/* Input Panel */}
      {showInput && (
        <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-5 shadow-[var(--shadow-sm)] space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-primary)] mb-2">
              视频链接（每行一个）
            </label>
            <textarea
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              placeholder={"https://www.bilibili.com/video/BVxxxxx\nhttps://www.youtube.com/watch?v=xxxxx"}
              rows={4}
              className="w-full px-4 py-3 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] bg-[var(--color-bg-raised)] text-sm font-mono resize-y focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] outline-none transition-all"
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <label className="text-sm text-[var(--color-text-secondary)]">并发数：</label>
              <select
                value={concurrency}
                onChange={(e) => setConcurrency(Number(e.target.value))}
                className="px-3 py-1.5 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] text-sm bg-[var(--color-bg-surface)] outline-none cursor-pointer"
              >
                {[1, 2, 3, 5].map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => { setShowInput(false); setUrls('') }}
                className="px-4 py-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleAddTasks}
                disabled={!urls.trim() || submitting}
                className="inline-flex items-center gap-2 px-4 py-2 bg-[var(--color-primary)] text-white rounded-[var(--radius-sm)] text-sm font-medium hover:bg-[var(--color-primary-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                提交处理
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stats Bar */}
      <div className="flex items-center gap-6 py-3 px-4 bg-[var(--color-bg-surface)] rounded-[var(--radius-md)] border border-[var(--color-border-subtle)] text-sm">
        <span className="text-[var(--color-text-secondary)]">
          共 <span className="font-semibold text-[var(--color-text-primary)]">{stats.total}</span> 个任务
        </span>
        <span className="text-green-600 flex items-center gap-1">
          <CheckCircle2 size={14} /> 已完成 {stats.completed}
        </span>
        {stats.processing > 0 && (
          <span className="text-blue-600 flex items-center gap-1">
            <Loader2 size={14} className="animate-spin" /> 处理中 {stats.processing}
          </span>
        )}
        <span className="text-red-600 flex items-center gap-1">
          <AlertCircle size={14} /> 失败 {stats.failed}
        </span>
        <div className="ml-auto flex gap-2">
          {stats.completed + stats.failed > 0 && (
            <button
              onClick={handleClearCompleted}
              className="text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-error)] transition-colors"
            >
              清空已完成
            </button>
          )}
        </div>
      </div>

      {/* Task Table */}
      <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] shadow-[var(--shadow-sm)] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-raised)]">
              <th className="text-left px-4 py-3 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider w-12">#</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider">视频链接</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider w-28">状态</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider w-36">进度</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider w-24">耗时</th>
              <th className="text-right px-4 py-3 text-xs font-medium text-[var(--color-text-tertiary)] uppercase tracking-wider w-24">操作</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task, idx) => {
              const config = statusConfig[task.status]
              const StatusIcon = config.icon
              const elapsed = task.startTime ? Math.round((Date.now() - task.startTime) / 1000) : 0
              const elapsedStr = elapsed > 60 ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s` : `${elapsed}s`
              return (
                <tr
                  key={task.id}
                  className={`border-b border-[var(--color-border-subtle)] last:border-b-0 hover:bg-[var(--color-bg-hover)] transition-colors ${
                    idx % 2 === 0 ? '' : 'bg-[var(--color-bg-raised)]'
                  }`}
                >
                  <td className="px-4 py-3 text-[var(--color-text-tertiary)]">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-[var(--color-text-primary)] max-w-md truncate">{task.url}</div>
                    {task.error && (
                      <div className="text-xs text-red-600 mt-0.5 truncate max-w-md" title={task.error}>{task.error}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
                      {task.status === 'processing' ? (
                        <StatusIcon size={12} className="animate-spin" />
                      ) : (
                        <StatusIcon size={12} />
                      )}
                      {config.label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-[var(--color-bg-raised)] rounded-full overflow-hidden max-w-24">
                        <div
                          className={`h-full rounded-full transition-all ${
                            task.status === 'failed' ? 'bg-red-500' : 'bg-[var(--color-primary)]'
                          }`}
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-[var(--color-text-tertiary)] w-8">{task.progress}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[var(--color-text-tertiary)] text-xs">
                    {task.status === 'completed' ? (task.duration || elapsedStr) : task.status === 'processing' ? elapsedStr : '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {task.status === 'completed' && (
                        <button
                          onClick={() => window.location.href = `/videos/${task.id}`}
                          className="p-1.5 text-[var(--color-text-tertiary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary-soft)] rounded-md transition-all"
                          title="查看结果"
                        >
                          <Eye size={14} />
                        </button>
                      )}
                      {(task.status === 'failed') && (
                        <button
                          onClick={() => handleRemoveTask(task.id)}
                          className="p-1.5 text-[var(--color-text-tertiary)] hover:text-[var(--color-error)] hover:bg-red-50 rounded-md transition-all"
                          title="移除"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                      {(task.status === 'processing' || task.status === 'pending') && (
                        <button
                          onClick={() => handleRemoveTask(task.id)}
                          className="p-1.5 text-[var(--color-text-tertiary)] hover:text-[var(--color-error)] hover:bg-red-50 rounded-md transition-all"
                          title="取消"
                        >
                          <X size={14} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {tasks.length === 0 && (
          <div className="py-16 text-center text-[var(--color-text-tertiary)]">
            <svg width={40} height={40} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="mx-auto mb-3 opacity-30">
              <rect x={3} y={3} width={18} height={18} rx={2} />
              <path d="M3 9h18M9 21V9" />
            </svg>
            <p>暂无批量处理任务</p>
            <p className="text-xs mt-1">点击「新建任务」添加视频链接</p>
          </div>
        )}
      </div>
    </div>
  )
}
