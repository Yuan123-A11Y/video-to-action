import type { ProgressUpdate } from '../types'

interface ProgressBarProps {
  progress: ProgressUpdate | null
  status: string | null
  connected: boolean
}

const STEP_LABELS: Record<number, { name: string; icon: string }> = {
  1: { name: '下载视频', icon: '📥' },
  2: { name: '内容提取', icon: '🔍' },
  3: { name: '智能分析', icon: '🧠' },
  4: { name: '生成方案', icon: '📋' },
  5: { name: '处理完成', icon: '✅' },
}

export default function ProgressBar({ progress, status, connected }: ProgressBarProps) {
  if (!status || status === 'pending') return null

  const isCompleted = status === 'completed'
  const isFailed = status === 'failed'
  const isProcessing = status === 'processing'

  return (
    <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          {isCompleted && <span className="text-green-500">✅</span>}
          {isFailed && <span className="text-red-500">❌</span>}
          {isProcessing && (
            <span className="animate-pulse-slow inline-block w-3 h-3 rounded-full bg-blue-500" />
          )}
          处理进度
        </h3>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${
          isCompleted ? 'bg-green-100 text-green-700' :
          isFailed ? 'bg-red-100 text-red-700' :
          connected ? 'bg-blue-100 text-blue-700' : 'bg-yellow-100 text-yellow-700'
        }`}>
          {isCompleted ? '已完成' : isFailed ? '失败' : connected ? '连接中...' : '重连中...'}
        </span>
      </div>

      {/* Progress Steps */}
      <div className="mb-4">
        <div className="flex items-center justify-between relative">
          {/* 连接线 */}
          <div className="absolute top-3 left-6 right-6 h-0.5 bg-gray-200 -z-10">
            <div
              className="h-full bg-[var(--color-primary)] transition-all duration-500"
              style={{ width: `${progress ? ((progress.step - 1) / Math.max(progress.total_steps - 1, 1)) * 100 : 0}%` }}
            />
          </div>

          {/* 步骤点 */}
          {[1, 2, 3, 4, 5].map((step) => {
            const currentStep = progress?.step ?? 0
            const isCurrentStep = step === currentStep
            const isPastStep = step < currentStep
            const info = STEP_LABELS[step]

            return (
              <div key={step} className="flex flex-col items-center z-10">
                <div className={`
                  w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300
                  ${isPastStep ? 'bg-[var(--color-primary)] text-white shadow-md shadow-blue-200' :
                    isCurrentStep ? 'bg-white border-3 border-[var(--color-primary)] text-[var(--color-primary)] ring-4 ring-blue-100 animate-pulse-slow' :
                    'bg-gray-100 text-gray-400'}
                `}>
                  {isPastStep ? '✓' : info.icon}
                </div>
                <span className={`mt-2 text-xs font-medium whitespace-nowrap ${
                  isPastStep ? 'text-[var(--color-primary)]' :
                  isCurrentStep ? 'text-[var(--color-text)] font-bold' :
                  'text-gray-400'
                }`}>
                  {info.name}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Progress Bar + Message */}
      {(isProcessing || (progress && !isCompleted)) && (
        <>
          <div className="mb-2">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="font-medium text-[var(--color-text)]">
                {progress?.step_name || '准备中...'}
              </span>
              <span className="text-[var(--color-text-secondary)]">
                {progress?.percentage ?? 0}%
              </span>
            </div>
            <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-[var(--color-primary)] to-blue-400 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress?.percentage ?? 0}%` }}
              />
            </div>
          </div>
          {progress?.message && (
            <p className="text-sm text-[var(--color-text-secondary)] mt-2 bg-gray-50 rounded-lg px-3 py-2">
              {progress.message}
            </p>
          )}
        </>
      )}

      {isCompleted && (
        <p className="text-green-600 font-medium text-center py-2 bg-green-50 rounded-lg">
          🎉 视频分析完成！点击下方查看结果
        </p>
      )}
    </div>
  )
}
