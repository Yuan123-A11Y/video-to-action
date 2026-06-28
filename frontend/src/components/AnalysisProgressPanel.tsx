import { useState, useEffect, useRef } from 'react'
import type { ProgressUpdate } from '../types'
import {
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
  Wifi,
  WifiOff,
  Terminal,
  ChevronDown,
  ChevronUp,
  Video,
  Search,
  Brain,
  ClipboardList,
  CircleCheck,
  XCircle,
} from 'lucide-react'

interface AnalysisProgressPanelProps {
  progress: ProgressUpdate | null
  status: string | null
  connected: boolean
  taskId: string | null
  mode?: 'ws' | 'polling' | 'idle'
}

/* ── 步骤定义 ── */
const ANALYSIS_STEPS = [
  {
    key: 1,
    name: '下载视频',
    desc: '从视频平台拉取原始文件',
    icon: Video,
    color: '#3B82F6',
    bgColor: '#EFF6FF',
    detailHints: ['正在解析视频链接...', '下载进度：', '视频大小：', '格式转换中...'],
  },
  {
    key: 2,
    name: '内容提取',
    desc: '音频转录 + 关键帧采样',
    icon: Search,
    color: '#8B5CF6',
    bgColor: '#F5F3FF',
    detailHints: ['正在提取音频轨道...', '语音识别中...', '关键帧采样：', '文字识别完成'],
  },
  {
    key: 3,
    name: '智能分析',
    desc: 'AI 理解视频内容与操作逻辑',
    icon: Brain,
    color: '#00D9A3',
    bgColor: '#E6FFF8',
    detailHints: ['正在分析视频主题...', '提取操作步骤...', '识别使用工具...', '生成分析报告'],
  },
  {
    key: 4,
    name: '生成方案',
    desc: '输出可执行的操作方案',
    icon: ClipboardList,
    color: '#F59E0B',
    bgColor: '#FFFBEB',
    detailHints: ['整理操作步骤...', '生成命令脚本...', '补充说明文档...', '方案校验中'],
  },
  {
    key: 5,
    name: '处理完成',
    desc: '分析结果已就绪',
    icon: CircleCheck,
    color: '#16A34A',
    bgColor: '#DCFCE7',
    detailHints: [],
  },
]

/* ── 获取步骤状态 ── */
function getStepState(stepKey: number, currentStep: number, taskStatus: string | null): 'completed' | 'active' | 'pending' | 'failed' {
  if (taskStatus === 'failed') return stepKey <= currentStep ? (stepKey < currentStep ? 'completed' : 'failed') : 'pending'
  if (taskStatus === 'completed') return 'completed'
  // 当 status=processing 但没有详细步骤信息(currentStep=0)时，默认激活第一步
  const effectiveStep = currentStep > 0 ? currentStep : 1
  if (stepKey < effectiveStep) return 'completed'
  if (stepKey === effectiveStep) return 'active'
  return 'pending'
}

/* ── 格式化耗时 ── */
function formatElapsed(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const sec = Math.floor(ms / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const remainSec = sec % 60
  return `${min}m ${remainSec}s`
}

/* ── 主组件 ── */
export default function AnalysisProgressPanel({
  progress,
  status,
  connected,
  taskId,
  mode = 'idle',
}: AnalysisProgressPanelProps) {
  const [showLog, setShowLog] = useState(true)
  const [logMessages, setLogMessages] = useState<Array<{ time: string; msg: string; type: 'info' | 'success' | 'warn' | 'error' }>>([])
  const [elapsed, setElapsed] = useState(0)
  const startTimeRef = useRef<number>(Date.now())
  const prevProgressRef = useRef<string>('')

  /* ── 耗时计时器 ── */
  useEffect(() => {
    if (status === 'completed' || status === 'failed') return
    // 初始状态（taskId 存在但 status 为 null）也开始计时
    if (!status && !taskId) return
    const timer = setInterval(() => setElapsed(Date.now() - startTimeRef.current), 250)
    return () => clearInterval(timer)
  }, [status, taskId])

  /* ── 日志消息收集（去重） ── */
  useEffect(() => {
    if (!progress?.message || !status || status === 'pending') return
    const key = `[${progress.step}]${progress.message}`
    if (key === prevProgressRef.current) return
    prevProgressRef.current = key

    const now = new Date()
    const timeStr = now.toLocaleTimeString('zh-CN', { hour12: false })
    const msgType: 'info' | 'success' | 'warn' | 'error' =
      progress.message.includes('失败') || progress.message.includes('错误') ? 'error' :
      progress.message.includes('完成') || progress.message.includes('成功') ? 'success' :
      progress.message.includes('警告') || progress.message.includes('等待') ? 'warn' : 'info'

    setLogMessages(prev => {
      const next = [...prev, { time: timeStr, msg: progress!.message, type: msgType }]
      // 只保留最近 50 条，防止内存膨胀
      return next.slice(-50)
    })
  }, [progress?.message, progress?.step, status])

  /* ── 重置（taskId 变化时） ── */
  useEffect(() => {
    startTimeRef.current = Date.now()
    setElapsed(0)
    setLogMessages([])
    prevProgressRef.current = ''
  }, [taskId])

  /* ── 当 taskId 存在但 WS 尚未连接时，仍显示初始面板 ── */
  const isInitial = !status || status === 'pending'
  if (isInitial && !taskId) return null

  const isCompleted = status === 'completed'
  const isFailed = status === 'failed'
  const isProcessing = status === 'processing'
  const currentStep = progress?.step ?? 0
  const percentage = progress?.percentage ?? 0

  return (
    <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-xl)] border border-[var(--color-border-subtle)] shadow-[var(--shadow-lg)] overflow-hidden fade-in max-w-3xl mx-auto">
      {/* ════════════════ 顶部状态栏 ════════════════ */}
      <div className="px-6 py-4 border-b border-[var(--color-border-subtle)] bg-gradient-to-r from-[var(--color-bg-surface)] to-[var(--color-bg-raised)]">
        <div className="flex items-center justify-between">
          {/* 左侧：标题 + 状态 */}
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-[var(--radius-md)] flex items-center justify-center ${
              isCompleted ? 'bg-green-100' : isFailed ? 'bg-red-100' : 'bg-[var(--color-primary-soft)]'
            }`}>
              {isCompleted ? (
                <CheckCircle2 size={20} className="text-green-600" />
              ) : isFailed ? (
                <XCircle size={20} className="text-red-500" />
              ) : (
                <Loader2 size={20} className="text-[var(--color-primary)] animate-spin" />
              )}
            </div>
            <div>
              <h3 className="text-base font-semibold text-[var(--color-text-primary)]">
                {isCompleted ? '分析完成' : isFailed ? '分析失败' : isInitial ? '已提交任务' : '正在分析...'}
              </h3>
              <p className="text-xs text-[var(--color-text-tertiary)] mt-0.5">
                {progress?.step_name || (isInitial
                  ? (mode === 'polling'
                      ? '正在通过轮询获取进度...'
                      : connected
                        ? '等待服务端响应...'
                        : '正在建立实时连接...')
                  : isProcessing
                    ? '正在处理中，请稍候...'
                    : '准备启动分析流程')}
              </p>
            </div>
          </div>

          {/* 右侧：指标标签组 */}
          <div className="flex items-center gap-2 flex-wrap justify-end">
            {/* 连接状态 */}
            <span className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${
              connected
                ? 'bg-blue-50 text-blue-600 border border-blue-200'
                : mode === 'polling'
                  ? 'bg-purple-50 text-purple-600 border border-purple-200'
                  : 'bg-yellow-50 text-yellow-600 border border-yellow-200'
            }`}>
              {connected
                ? <><Wifi size={12} /> 实时连接</>
                : mode === 'polling'
                  ? <><Clock size={12} /> 轮询模式</>
                  : <><WifiOff size={12} /> 断线重连</>}
            </span>

            {/* 耗时 */}
            {(isProcessing || isInitial) && (
              <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium bg-gray-100 text-gray-600 border border-gray-200">
                <Clock size={12} />
                {formatElapsed(elapsed)}
              </span>
            )}

            {/* 整体百分比 */}
            <span className={`text-sm font-bold px-3 py-1 rounded-full ${
              isCompleted ? 'bg-green-100 text-green-700' :
              isFailed ? 'bg-red-100 text-red-600' :
              'bg-[var(--color-primary-soft)] text-[var(--color-primary-strong)]'
            }`}>
              {isCompleted ? '100%' : isFailed ? '失败' : isInitial ? '连接中' : (percentage > 0 ? `${percentage}%` : '处理中')}
            </span>
          </div>
        </div>

        {/* 总进度条 */}
        {(isProcessing || isInitial) && (
          <div className="mt-3 w-full">
            <div className="h-2 bg-[var(--color-bg-overlay)] rounded-full overflow-hidden">
              {isInitial ? (
                /* 初始状态：脉冲动画条 */
                <div className="h-full w-1/3 rounded-full animate-pulse-slow" style={{
                  background: `linear-gradient(90deg, #00D9A3 0%, #00B894 50%, #16A34A 100%)`,
                  animationDuration: '1.5s',
                }} />
              ) : (
                <div
                  className="h-full rounded-full transition-all duration-500 ease-out relative"
                  style={{
                    width: `${percentage}%`,
                    background: `linear-gradient(90deg, #00D9A3 0%, #00B894 50%, #16A34A 100%)`,
                  }}
                >
                  {/* 光泽动画 */}
                  <div className="absolute inset-0 bg-white/20 animate-pulse-slow" style={{ animationDuration: '2s' }} />
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ════════════════ 步骤时间线 ════════════════ */}
      <div className="px-6 py-5">
        <div className="space-y-0">
          {ANALYSIS_STEPS.map((stepInfo, idx) => {
            const stepState = getStepState(stepInfo.key, currentStep, status)
            const IconComp = stepInfo.icon
            const isActive = stepState === 'active'
            const isDone = stepState === 'completed'

            return (
              <div key={stepInfo.key} className="relative">
                {/* 时间线竖线 */}
                {idx < ANALYSIS_STEPS.length - 1 && (
                  <div
                    className={`absolute left-[19px] top-10 w-0.5 transition-all duration-500 ${
                      isDone ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-border-subtle)]'
                    }`}
                    style={{ height: idx === currentStep - 1 ? 'calc(100% - 4px)' : '100%' }}
                  />
                )}

                <div className={`flex gap-4 pb-5 ${isActive ? '' : 'opacity-70 hover:opacity-100'} transition-opacity`}>
                  {/* 步骤图标 */}
                  <div
                    className={`relative z-10 shrink-0 w-10 h-10 rounded-[var(--radius-md)] flex items-center justify-center border-2 transition-all duration-300 ${
                      isDone
                        ? `border-[${stepInfo.color}] shadow-sm`
                        : isActive
                          ? `border-${stepInfo.color} ring-4 ring-offset-2 animate-pulse-slow`
                          : 'border-[var(--color-border-default)] bg-[var(--color-bg-raised)]'
                    }`}
                    style={{
                      backgroundColor: isDone ? stepInfo.bgColor : isActive ? stepInfo.bgColor : undefined,
                      borderColor: isDone ? stepInfo.color : isActive ? stepInfo.color : undefined,
                      ...(isActive ? { '--tw-ring-color': stepInfo.color + '40', boxShadow: `0 0 0 4px ${stepInfo.color}20` } as React.CSSProperties : {}),
                    }}
                  >
                    {isDone ? (
                      <CheckCircle2 size={18} style={{ color: stepInfo.color }} />
                    ) : isActive ? (
                      <Loader2 size={18} className="animate-spin" style={{ color: stepInfo.color }} />
                    ) : stepState === 'failed' ? (
                      <AlertCircle size={18} className="text-red-500" />
                    ) : (
                      <IconComp size={18} className="text-[var(--color-text-tertiary)]" />
                    )}
                  </div>

                  {/* 步骤内容 */}
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div className="flex items-center justify-between">
                      <span className={`text-sm font-semibold ${
                        isDone ? 'text-[var(--color-text-primary)]' :
                        isActive ? 'text-[var(--color-text-primary)]' :
                        'text-[var(--color-text-tertiary)]'
                      }`}>
                        {stepInfo.name}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        isDone ? 'bg-green-50 text-green-600' :
                        isActive ? 'text-[var(--color-primary)] bg-[var(--color-primary-soft)]' :
                        stepState === 'failed' ? 'bg-red-50 text-red-500' :
                        'bg-gray-100 text-gray-400'
                      }`}>
                        {isDone ? '已完成' : isActive ? '进行中...' : stepState === 'failed' ? '失败' : '等待中'}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--color-text-tertiary)] mt-0.5">{stepInfo.desc}</p>

                    {/* 当前步骤的子进度条和消息 */}
                    {isActive && progress && (
                      <div className="mt-2.5 pl-3 border-l-2 border-[var(--color-primary-soft)]">
                        <div className="flex items-center gap-2 mb-1.5">
                          <div className="flex-1 h-1.5 bg-[var(--color-bg-overlay)] rounded-full overflow-hidden max-w-[200px]">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{
                                width: `${(percentage % 100)}%`,
                                backgroundColor: stepInfo.color,
                              }}
                            />
                          </div>
                          <span className="text-xs font-mono text-[var(--color-text-secondary)]">{percentage}%</span>
                        </div>
                        {progress.message && (
                          <p className="text-xs text-[var(--color-text-secondary)] bg-[var(--color-bg-raised)] rounded-[var(--radius-sm)] px-2.5 py-1.5 font-mono leading-relaxed">
                            {progress.message}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ════════════════ 实时日志面板 ════════════════ */}
      {(isProcessing || logMessages.length > 0) && (
        <div className="border-t border-[var(--color-border-subtle)]">
          {/* 日志头部折叠按钮 */}
          <button
            onClick={() => setShowLog(!showLog)}
            className="w-full px-6 py-2.5 flex items-center justify-between text-xs font-medium text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)] transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <Terminal size={13} />
              实时日志
              {logMessages.length > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-[var(--color-bg-overlay)] text-[var(--color-text-tertiary)] tabular-nums">
                  {logMessages.length}
                </span>
              )}
            </span>
            {showLog ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {/* 日志内容区 */}
          {showLog && (
            <div className="px-6 pb-4">
              <div className="bg-[#0D1117] rounded-[var(--radius-md)] p-4 max-h-[220px] overflow-y-auto font-mono text-xs leading-6 space-y-0.5 custom-scrollbar">
                {logMessages.length === 0 ? (
                  <div className="text-gray-500">等待日志输出...</div>
                ) : (
                  logMessages.map((entry, i) => (
                    <div key={i} className="flex gap-2 items-start">
                      <span className="shrink-0 text-gray-600 select-none">{entry.time}</span>
                      <span className={
                        entry.type === 'error' ? 'text-red-400' :
                        entry.type === 'success' ? 'text-green-400' :
                        entry.type === 'warn' ? 'text-yellow-400' :
                        'text-gray-300'
                      }>
                        <span className="select-none mr-1.5 opacity-60">
                          {entry.type === 'error' ? '✖' : entry.type === 'success' ? '✔' : entry.type === 'warn' ? '⚡' : '▸'}
                        </span>
                        {entry.msg}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ════════════════ 底部完成提示 ════════════════ */}
      {isCompleted && (
        <div className="px-6 py-4 border-t border-[var(--color-border-subtle)] bg-green-50/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle2 size={18} />
              <span className="text-sm font-medium">视频分析已完成！</span>
              <span className="text-xs text-green-600">总耗时 {formatElapsed(elapsed)}</span>
            </div>
            <div className="text-xs text-green-600">正在跳转到结果页面...</div>
          </div>
        </div>
      )}

      {isFailed && (
        <div className="px-6 py-4 border-t border-[var(--color-border-subtle)] bg-red-50/50">
          <div className="flex items-center gap-2 text-red-600">
            <XCircle size={18} />
            <span className="text-sm font-medium">分析过程中出现错误</span>
            <span className="text-xs text-red-400 ml-auto">总耗时 {formatElapsed(elapsed)}</span>
          </div>
        </div>
      )}

      {/* ════════════════ 任务 ID 信息栏 ════════════════ */}
      {taskId && (
        <div className="px-6 py-2 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-raised)] flex items-center justify-between">
          <span className="text-xs text-[var(--color-text-tertiary)] font-mono">
            Task ID: <span className="text-[var(--color-text-secondary)]">{taskId.slice(0, 12)}...{taskId.slice(-6)}</span>
          </span>
          <span className="text-xs text-[var(--color-text-tertiary)]">
            Video-to-Action Engine v2.0
          </span>
        </div>
      )}
    </div>
  )
}
