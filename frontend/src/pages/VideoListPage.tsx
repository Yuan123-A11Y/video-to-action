import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getVideos } from '../api/client'
import type { Video } from '../types'
import { Film, Grid3X3, List, Search, Loader2, AlertCircle, Eye } from 'lucide-react'

type ViewMode = 'table' | 'card'

const STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '等待中', color: 'text-gray-600', bg: 'bg-gray-100' },
  downloading: { label: '下载中', color: 'text-blue-600', bg: 'bg-blue-50' },
  downloaded: { label: '已下载', color: 'text-blue-500', bg: 'bg-blue-50' },
  processing: { label: '处理中', color: 'text-orange-600', bg: 'bg-orange-50' },
  completed: { label: '已完成', color: 'text-green-600', bg: 'bg-green-50' },
  failed: { label: '失败', color: 'text-red-600', bg: 'bg-red-50' },
}

export default function VideoListPage() {
  const navigate = useNavigate()
  const [videos, setVideos] = useState<Video[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 10

  // 搜索 + 视图模式
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<ViewMode>('table')

  const filteredVideos = useMemo(() => {
    if (!searchQuery.trim()) return videos
    const q = searchQuery.toLowerCase()
    return videos.filter(v =>
      (v.title && v.title.toLowerCase().includes(q)) ||
      v.url.toLowerCase().includes(q) ||
      (v.theme && v.theme.toLowerCase().includes(q))
    )
  }, [videos, searchQuery])

  useEffect(() => {
    loadVideos()
  }, [page])

  async function loadVideos() {
    setLoading(true)
    try {
      const result = await getVideos(page, pageSize)
      setVideos(result.videos || [])
      setTotal(result.total || 0)
    } catch {
      // 静默错误
    } finally {
      setLoading(false)
    }
  }

  // 卡片视图组件
  const VideoCard = ({ video }: { video: Video }) => {
    const statusInfo = STATUS_MAP[video.status] || STATUS_MAP.pending
    const isCompleted = video.status === 'completed'
    return (
      <button
        key={video.id}
        onClick={() => isCompleted && navigate(`/videos/${video.id}`)}
        className={`w-full text-left bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] hover:border-[var(--color-primary-border)] transition-all group ${
          isCompleted ? 'cursor-pointer' : 'cursor-default opacity-70'
        }`}
      >
        <div className="flex items-start gap-4">
          {/* 图标区 */}
          <div className="w-12 h-12 rounded-[var(--radius-md)] bg-[var(--color-bg-raised)] shrink-0 flex items-center justify-center group-hover:bg-[var(--color-primary-soft)] transition-colors">
            {isCompleted ? (
              <Film size={20} className="text-[var(--color-text-tertiary)] group-hover:text-[var(--color-primary)] transition-colors" />
            ) : video.status === 'failed' ? (
              <AlertCircle size={18} className="text-red-500" />
            ) : (
              <Loader2 size={18} className="animate-spin text-[var(--color-primary)]" />
            )}
          </div>

          {/* 内容区 */}
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-sm text-[var(--color-text-primary)] truncate group-hover:text-[var(--color-primary)] transition-colors">
              {video.title || video.url}
            </h3>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              {video.platform && (
                <span className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-bg-raised)] text-[var(--color-text-secondary)]">
                  {video.platform}
                </span>
              )}
              {video.theme && (
                <span className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-primary-soft)] text-[var(--color-primary-strong)]">
                  {video.theme}
                </span>
              )}
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusInfo.bg} ${statusInfo.color}`}>
                {statusInfo.label}
              </span>
            </div>
            <p className="text-xs text-[var(--color-text-tertiary)] mt-1.5">
              {new Date(video.created_at).toLocaleString('zh-CN')}
            </p>
          </div>

          {/* 操作按钮 */}
          {isCompleted && (
            <div className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <Eye size={16} className="text-[var(--color-text-tertiary)] hover:text-[var(--color-primary)]" />
            </div>
          )}
        </div>
      </button>
    )
  }

  return (
    <div className="space-y-6">
      {/* 顶部栏 */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">视频库</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">
            共 {total} 条记录
          </p>
        </div>

        {/* 搜索 + 视图切换 */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="搜索视频标题..."
              className="pl-9 pr-4 py-2 rounded-[999px] border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] text-sm focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] outline-none transition-all w-56"
            />
          </div>

          {/* 视图切换 */}
          <div className="flex items-center border border-[var(--color-border-default)] rounded-[var(--radius-sm)] overflow-hidden">
            <button
              onClick={() => setViewMode('table')}
              className={`p-2 transition-colors ${
                viewMode === 'table'
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--color-bg-surface)] text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'
              }`}
              title="表格视图"
            >
              <List size={16} />
            </button>
            <button
              onClick={() => setViewMode('card')}
              className={`p-2 transition-colors ${
                viewMode === 'card'
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--color-bg-surface)] text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'
              }`}
              title="卡片视图"
            >
              <Grid3X3 size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* 内容区 */}
      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 size={32} className="animate-spin text-[var(--color-primary)]" />
        </div>
      ) : filteredVideos.length === 0 ? (
        <div className="text-center py-20 bg-[var(--color-bg-surface)] rounded-[var(--radius-xl)] border border-dashed border-[var(--color-border-default)]">
          {searchQuery ? (
            <>
              <Search size={40} className="mx-auto mb-3 text-[var(--color-text-tertiary)] opacity-30" />
              <p className="text-[var(--color-text-secondary)] font-medium">没有找到匹配的视频</p>
              <p className="text-xs text-[var(--color-text-tertiary)] mt-1">尝试修改搜索关键词</p>
            </>
          ) : (
            <>
              <div className="mx-auto w-16 h-16 rounded-2xl bg-[var(--color-bg-raised)] flex items-center justify-center mb-4">
                <Film size={28} className="text-[var(--color-text-tertiary)]" />
              </div>
              <p className="text-[var(--color-text-secondary)] font-medium">暂无视频记录</p>
              <p className="text-xs text-[var(--color-text-tertiary)] mt-1 mb-4">提交第一个视频，开始智能分析之旅</p>
              <button
                onClick={() => navigate('/')}
                className="px-5 py-2.5 bg-[var(--color-primary)] text-white rounded-[var(--radius-sm)] text-sm font-medium hover:bg-[var(--color-primary-hover)] transition-colors shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)]"
              >
                去提交第一个视频
              </button>
            </>
          )}
        </div>
      ) : viewMode === 'table' ? (
        /* 表格视图 */
        <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] shadow-[var(--shadow-sm)] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[var(--color-bg-raised)] border-b border-[var(--color-border-subtle)]">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-[var(--color-text-tertiary)] text-xs uppercase tracking-wider">标题</th>
                <th className="px-4 py-3 text-left font-medium text-[var(--color-text-tertiary)] text-xs uppercase tracking-wider w-24">平台</th>
                <th className="px-4 py-3 text-left font-medium text-[var(--color-text-tertiary)] text-xs uppercase tracking-wider w-24">状态</th>
                <th className="px-4 py-3 text-left font-medium text-[var(--color-text-tertiary)] text-xs uppercase tracking-wider w-36">时间</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--color-border-subtle)]">
              {filteredVideos.map((video) => {
                const statusInfo = STATUS_MAP[video.status] || STATUS_MAP.pending
                return (
                  <tr
                    key={video.id}
                    onClick={() => video.status === 'completed' && navigate(`/videos/${video.id}`)}
                    className={`hover:bg-[var(--color-bg-hover)] transition-colors ${video.status === 'completed' ? 'cursor-pointer' : 'cursor-default'}`}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-[var(--color-text-primary)] truncate max-w-md">{video.title || video.url}</div>
                      {video.theme && (
                        <div className="text-xs text-[var(--color-text-secondary)] mt-0.5">{video.theme}</div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs">{video.platform}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusInfo.bg} ${statusInfo.color}`}>
                        {statusInfo.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-[var(--color-text-secondary)] whitespace-nowrap">
                      {new Date(video.created_at).toLocaleString('zh-CN')}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          {/* Pagination */}
          {total > pageSize && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--color-border-subtle)] bg-[var(--color-bg-raised)]">
              <span className="text-xs text-[var(--color-text-secondary)]">
                第 {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} 条，共 {total} 条
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-xs rounded-[var(--radius-sm)] border border-[var(--color-border-default)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  上一页
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= Math.ceil(total / pageSize)}
                  className="px-3 py-1.5 text-xs rounded-[var(--radius-sm)] border border-[var(--color-border-default)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* 卡片视图 */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filteredVideos.map(video => (
            <VideoCard key={video.id} video={video} />
          ))}
        </div>
      )}

      {/* 卡片视图的加载更多（简化版，实际用分页） */}
      {!loading && filteredVideos.length > 0 && viewMode === 'card' && total > pageSize && (
        <div className="flex justify-center pt-4">
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 text-xs rounded-[var(--radius-sm)] border border-[var(--color-border-default)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              上一页
            </button>
            <span className="px-3 py-1.5 text-xs text-[var(--color-text-secondary)]">
              第 {page} 页 / 共 {Math.ceil(total / pageSize)} 页
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= Math.ceil(total / pageSize)}
              className="px-3 py-1.5 text-xs rounded-[var(--radius-sm)] border border-[var(--color-border-default)] hover:bg-[var(--color-bg-hover)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              下一页
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
