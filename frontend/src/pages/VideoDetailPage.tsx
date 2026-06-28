import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getVideo } from '../api/client'
import type { Video, AnalysisResult, AnalysisStep } from '../types'

const STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '等待中', color: 'text-gray-600', bg: 'bg-gray-100' },
  downloading: { label: '下载中', color: 'text-blue-600', bg: 'bg-blue-50' },
  downloaded: { label: '已下载', color: 'text-blue-500', bg: 'bg-blue-50' },
  processing: { label: '处理中', color: 'text-orange-600', bg: 'bg-orange-50' },
  completed: { label: '已完成', color: 'text-green-600', bg: 'bg-green-50' },
  failed: { label: '失败', color: 'text-red-600', bg: 'bg-red-50' },
}

export default function VideoDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [video, setVideo] = useState<Video | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'transcription' | 'raw'>('overview')

  // Bug 1 fix: Safely parse video ID
  const parseVideoId = (idStr: string | undefined): number | null => {
    if (!idStr) return null
    const videoId = parseInt(idStr, 10)
    if (isNaN(videoId)) return null
    return videoId
  }

  useEffect(() => {
    const videoId = parseVideoId(id)
    if (videoId === null) {
      setError('无效的视频 ID')
      setLoading(false)
      return
    }
    loadVideo(videoId)
  }, [id])

  async function loadVideo(videoId: number) {
    setLoading(true)
    setError(null)
    try {
      const data = await getVideo(videoId)
      setVideo(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : '视频不存在或已被删除'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  // 加载状态
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-gray-200 rounded-lg animate-pulse" />
          <div className="h-8 bg-gray-200 rounded w-64 animate-pulse" />
        </div>
        <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 space-y-4">
          <div className="h-6 bg-gray-200 rounded w-48 animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-full animate-pulse" />
          <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse" />
        </div>
      </div>
    )
  }

  // 错误状态
  if (error || !video) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => navigate('/videos')}
          className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          返回视频列表
        </button>
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-[var(--color-border)]">
          <p className="text-6xl mb-4">😕</p>
          <p className="text-lg text-[var(--color-text)] font-medium mb-2">无法加载视频</p>
          <p className="text-sm text-[var(--color-text-secondary)] mb-4">{error || '视频不存在'}</p>
          <button
            onClick={() => {
              const videoId = parseVideoId(id)
              if (videoId !== null) loadVideo(videoId)
            }}
            className="px-4 py-2 bg-[var(--color-primary)] text-white rounded-lg text-sm hover:bg-[var(--color-primary-dark)] transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  const statusInfo = STATUS_MAP[video.status] || STATUS_MAP.pending
  const analysisResult: AnalysisResult | undefined = video.analysis_result

  // Bug 2 fix: Calculate available tabs and validate activeTab
  const availableTabs: Array<'overview' | 'transcription' | 'raw'> = ['overview']
  if (video.transcription_text) availableTabs.push('transcription')
  if (analysisResult?.raw_output) availableTabs.push('raw')

  const currentTab = availableTabs.includes(activeTab) ? activeTab : 'overview'

  return (
    <div className="space-y-6">
      {/* 顶部导航 */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/videos')}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="返回视频列表"
        >
          <svg className="w-5 h-5 text-[var(--color-text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h1 className="text-2xl font-bold text-[var(--color-text)] flex-1 truncate">
          {video.title || '未命名视频'}
        </h1>
        {/* 刷新按钮 */}
        <button
          onClick={() => {
            const videoId = parseVideoId(id)
            if (videoId !== null) loadVideo(videoId)
          }}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="刷新"
        >
          <svg className="w-5 h-5 text-[var(--color-text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* 基础信息区 */}
      <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <p className="text-xs text-[var(--color-text-secondary)] mb-1">平台</p>
            <p className="text-sm font-medium text-[var(--color-text)]">{video.platform}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-secondary)] mb-1">状态</p>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.bg} ${statusInfo.color}`}>
              {statusInfo.label}
            </span>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-secondary)] mb-1">创建时间</p>
            <p className="text-sm text-[var(--color-text)]">
              {/* Bug 3 fix: Add date error handling */}
              {isNaN(new Date(video.created_at).getTime()) 
                ? '-' 
                : new Date(video.created_at).toLocaleString('zh-CN')
              }
            </p>
          </div>
          <div>
            <p className="text-xs text-[var(--color-text-secondary)] mb-1">时长</p>
            <p className="text-sm text-[var(--color-text)]">{video.duration || '-'}</p>
          </div>
        </div>

        {/* 视频链接 */}
        <div className="pt-4 border-t border-[var(--color-border)]">
          <a
            href={video.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-[var(--color-primary)] hover:underline flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            查看原视频
          </a>
        </div>
      </div>

      {/* 状态处理 */}
      {video.status !== 'completed' && (
        <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm">
          {video.status === 'failed' ? (
            <div className="text-center py-8">
              <div className="text-6xl mb-4">❌</div>
              <p className="text-lg text-red-600 font-medium mb-2">处理失败</p>
              <p className="text-sm text-[var(--color-text-secondary)] max-w-md mx-auto">
                {video.error_message || '未知错误'}
              </p>
            </div>
          ) : (
            <div className="text-center py-12">
              <svg className="animate-spin w-12 h-12 text-[var(--color-primary)] mx-auto mb-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75"/>
              </svg>
              <p className="text-lg text-[var(--color-text)] font-medium mb-2">
                {statusInfo.label}
              </p>
              <p className="text-sm text-[var(--color-text-secondary)]">
                {video.status === 'pending' && '视频已提交，等待处理...'}
                {video.status === 'downloading' && '正在下载视频，请稍候...'}
                {video.status === 'downloaded' && '视频下载完成，准备处理...'}
                {video.status === 'processing' && '正在分析视频内容，这可能需要几分钟...'}
              </p>
              <button
                onClick={() => {
                  const videoId = parseVideoId(id)
                  if (videoId !== null) loadVideo(videoId)
                }}
                className="mt-4 text-sm text-[var(--color-primary)] hover:underline"
              >
                刷新状态
              </button>
            </div>
          )}
        </div>
      )}

      {/* 分析结果展示 (status=completed) */}
      {video.status === 'completed' && analysisResult && (
        <div className="space-y-6">
          {/* Tab 切换 */}
          <div className="flex gap-2 border-b border-[var(--color-border)]">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
                currentTab === 'overview'
                  ? 'text-[var(--color-primary)] border-[var(--color-primary)]'
                  : 'text-[var(--color-text-secondary)] border-transparent hover:text-[var(--color-text)]'
              }`}
            >
              分析概览
            </button>
            {video.transcription_text && (
              <button
                onClick={() => setActiveTab('transcription')}
                className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
                  currentTab === 'transcription'
                    ? 'text-[var(--color-primary)] border-[var(--color-primary)]'
                    : 'text-[var(--color-text-secondary)] border-transparent hover:text-[var(--color-text)]'
                }`}
              >
                转录文本
              </button>
            )}
            {analysisResult.raw_output && (
              <button
                onClick={() => setActiveTab('raw')}
                className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-[1px] ${
                  currentTab === 'raw'
                    ? 'text-[var(--color-primary)] border-[var(--color-primary)]'
                    : 'text-[var(--color-text-secondary)] border-transparent hover:text-[var(--color-text)]'
                }`}
              >
                原始输出
              </button>
            )}
          </div>

          {/* 概览 Tab */}
          {currentTab === 'overview' && (
            <div className="space-y-6">
              {/* 主题 & 摘要 */}
              {(analysisResult.theme || analysisResult.summary) && (
                <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm">
                  <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">主题与摘要</h2>
                  {analysisResult.theme && (
                    <div className="mb-4">
                      <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-2">主题</h3>
                      <p className="text-lg text-[var(--color-text)] leading-relaxed">{analysisResult.theme}</p>
                    </div>
                  )}
                  {analysisResult.summary && (
                    <div>
                      <h3 className="text-sm font-medium text-[var(--color-text-secondary)] mb-2">摘要</h3>
                      <p className="text-[var(--color-text)] leading-relaxed whitespace-pre-wrap">{analysisResult.summary}</p>
                    </div>
                  )}
                </div>
              )}

              {/* 提取的工具 */}
              {analysisResult.tools && analysisResult.tools.length > 0 && (
                <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm">
                  <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">提取的工具</h2>
                  <div className="grid gap-4">
                    {analysisResult.tools.map((tool, index) => (
                      <div key={index} className="border border-[var(--color-border)] rounded-lg p-4 hover:border-[var(--color-primary)] transition-colors">
                        <h3 className="font-medium text-[var(--color-text)] mb-1">{tool.name}</h3>
                        {tool.purpose && (
                          <p className="text-sm text-[var(--color-text-secondary)] mb-3">{tool.purpose}</p>
                        )}
                        {tool.install_commands && tool.install_commands.length > 0 && (
                          <div className="mb-3">
                            <p className="text-xs font-medium text-[var(--color-text-secondary)] mb-1">安装命令</p>
                            <pre className="bg-gray-900 text-gray-100 rounded-lg p-3 overflow-x-auto text-sm">
                              <code>{tool.install_commands.join('\n')}</code>
                            </pre>
                          </div>
                        )}
                        {tool.links && tool.links.length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-[var(--color-text-secondary)] mb-1">相关链接</p>
                            <div className="flex flex-wrap gap-2">
                              {tool.links.map((link, linkIndex) => (
                                <a
                                  key={linkIndex}
                                  href={link}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-[var(--color-primary)] hover:underline flex items-center gap-1"
                                >
                                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                  </svg>
                                  {link}
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                        {tool.warnings && tool.warnings.length > 0 && (
                          <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                            <p className="text-xs font-medium text-yellow-800 mb-1">⚠️ 注意事项</p>
                            <ul className="list-disc list-inside text-xs text-yellow-700">
                              {tool.warnings.map((warning, wIndex) => (
                                <li key={wIndex}>{warning}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 操作步骤 */}
              {analysisResult.steps && analysisResult.steps.length > 0 && (
                <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm">
                  <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">操作步骤</h2>
                  <div className="space-y-4">
                    {analysisResult.steps.map((step: AnalysisStep, index: number) => (
                      <div key={index} className="flex gap-4">
                        <div className="flex-shrink-0 w-8 h-8 bg-[var(--color-primary)] text-white rounded-full flex items-center justify-center text-sm font-bold">
                          {step.step_number || index + 1}
                        </div>
                        <div className="flex-1 border-l-2 border-gray-200 pl-4 pb-4">
                          <h3 className="font-medium text-[var(--color-text)] mb-1">{step.title}</h3>
                          <p className="text-sm text-[var(--color-text-secondary)] mb-2">{step.description}</p>
                          {step.commands && step.commands.length > 0 && (
                            <pre className="bg-gray-900 text-gray-100 rounded-lg p-3 overflow-x-auto text-sm">
                              <code>{step.commands.join('\n')}</code>
                            </pre>
                          )}
                          {step.explanation && (
                            <p className="text-xs text-[var(--color-text-secondary)] mt-2 italic">{step.explanation}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 命令列表 */}
              {analysisResult.commands && analysisResult.commands.length > 0 && (
                <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm">
                  <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">命令列表</h2>
                  <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm">
                    <code>{analysisResult.commands.join('\n')}</code>
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* 转录文本 Tab */}
          {currentTab === 'transcription' && video.transcription_text && (
            <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">转录文本</h2>
              <div className="prose max-w-none">
                <pre className="whitespace-pre-wrap text-sm text-[var(--color-text)] leading-relaxed font-sans">
                  {video.transcription_text}
                </pre>
              </div>
            </div>
          )}

          {/* 原始输出 Tab */}
          {currentTab === 'raw' && analysisResult.raw_output && (
            <div className="bg-white rounded-xl border border-[var(--color-border)] p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-[var(--color-text)] mb-4">原始输出</h2>
              <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm max-h-96 overflow-y-auto">
                <code>{analysisResult.raw_output}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
