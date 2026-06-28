import { useState, useEffect, useCallback } from 'react'
import {
  Search,
  Play,
  Wrench,
  ArrowUpRight,
  Calendar,
  SlidersHorizontal,
  Loader2,
} from 'lucide-react'
import { getVideos, getTools, search } from '../api/client'
import type { Video, Tool } from '../types'

type TabType = 'videos' | 'tools'

export default function KnowledgePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('videos')
  const [platformFilter, setPlatformFilter] = useState('all')
  const [sortBy, setSortBy] = useState('date')
  const [videos, setVideos] = useState<Video[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(true)
  const [toolsLoading, setToolsLoading] = useState(false)

  // 加载视频列表
  const loadVideos = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getVideos(1, 50)
      setVideos(data.videos)
    } catch (err) {
      console.error('Failed to load videos:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  // 加载工具列表
  const loadTools = useCallback(async () => {
    setToolsLoading(true)
    try {
      const data = await getTools(1, 50)
      setTools(data.tools)
    } catch (err) {
      console.error('Failed to load tools:', err)
    } finally {
      setToolsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadVideos()
  }, [loadVideos])

  useEffect(() => {
    if (activeTab === 'tools' && tools.length === 0) {
      loadTools()
    }
  }, [activeTab, tools.length, loadTools])

  // 搜索（输入变化时调用搜索 API）
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<{ videos: Video[]; tools: Tool[] } | null>(null)

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults(null)
      return
    }
    setSearching(true)
    const timer = setTimeout(async () => {
      try {
        const type = activeTab === 'videos' ? 'video' : 'tool'
        const data = await search({ q: searchQuery, type: type as 'video' | 'tool', page_size: 50 })
        setSearchResults({
          videos: data.videos || [],
          tools: data.tools || [],
        })
      } catch (err) {
        console.error('Search failed:', err)
      } finally {
        setSearching(false)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, activeTab])

  // 过滤和排序逻辑
  const platforms = ['全部', ...Array.from(new Set(videos.map(v => v.platform).filter(Boolean)))]

  const filteredVideos = (searchResults ? searchResults.videos : videos).filter(v => {
    if (platformFilter !== 'all' && v.platform !== platformFilter) return false
    return true
  }).sort((a, b) => {
    if (sortBy === 'date') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    return 0
  })

  const displayTools = searchResults ? searchResults.tools : tools

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">知识库</h1>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">搜索已收集的视频、工具和操作命令</p>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-xl">
        <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="搜索视频、工具、命令..."
          className="w-full pl-11 pr-4 py-3 rounded-[999px] border border-[var(--color-border-default)] bg-[var(--color-bg-surface)] text-sm focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] outline-none transition-all"
        />
        {searching && (
          <Loader2 size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] animate-spin" />
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1.5">
          <SlidersHorizontal size={14} className="text-[var(--color-text-tertiary)]" />
          <span className="text-xs text-[var(--color-text-tertiary)] mr-1">平台:</span>
          {platforms.map(p => (
            <button
              key={p}
              onClick={() => setPlatformFilter(p)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                platformFilter === p
                  ? 'bg-[var(--color-primary)] text-white'
                  : 'bg-[var(--color-bg-raised)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5 ml-auto">
          <Calendar size={14} className="text-[var(--color-text-tertiary)]" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-2 py-1 rounded-[var(--radius-sm)] text-xs bg-transparent border-none outline-none cursor-pointer text-[var(--color-text-secondary)]"
          >
            <option value="date">最新</option>
            <option value="relevance">相关度</option>
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-[var(--color-border-subtle)]">
        <div className="flex gap-6">
          {([
            { key: 'videos' as const, label: '视频' },
            { key: 'tools' as const, label: '工具' },
          ]).map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-[var(--color-primary)] text-[var(--color-primary-strong)]'
                  : 'border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
              }`}
            >
              <span className="inline-flex items-center gap-1.5">
                {tab.key === 'videos' ? <Play size={14} /> : <Wrench size={14} />}
                {tab.label}
              </span>
              <span className="ml-1.5 text-xs text-[var(--color-text-tertiary)]">
                ({tab.key === 'videos' ? filteredVideos.length : displayTools.length})
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {loading && activeTab === 'videos' ? (
        <div className="flex justify-center py-12">
          <Loader2 size={32} className="animate-spin text-[var(--color-primary)]" />
        </div>
      ) : activeTab === 'videos' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredVideos.map(video => (
            <div
              key={video.id}
              className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] hover:border-[var(--color-primary-border)] transition-all group cursor-pointer"
              onClick={() => window.location.href = `/videos/${video.id}`}
            >
              <div className="flex gap-4">
                <div className="w-36 h-20 rounded-md bg-[var(--color-bg-raised)] shrink-0 flex items-center justify-center group-hover:bg-[var(--color-primary-soft)] transition-colors">
                  <Play size={20} className="text-[var(--color-text-tertiary)] group-hover:text-[var(--color-primary)] transition-colors" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm text-[var(--color-text-primary)] line-clamp-2 group-hover:text-[var(--color-primary)] transition-colors">
                    {video.title || `视频 ${video.id}`}
                  </h3>
                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {video.platform && (
                      <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-pink-50 text-pink-600">{video.platform}</span>
                    )}
                    {video.theme && (
                      <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-[var(--color-primary-soft)] text-[var(--color-primary-strong)]">{video.theme}</span>
                    )}
                    {video.status && (
                      <span className={`text-xs ${
                        video.status === 'completed' ? 'text-green-600' :
                        video.status === 'failed' ? 'text-red-600' :
                        'text-orange-600'
                      }`}>{video.status}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-[var(--color-text-tertiary)]">
                    <span className="flex items-center gap-1">
                      <Calendar size={12} />
                      {new Date(video.created_at).toLocaleDateString('zh-CN')}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {filteredVideos.length === 0 && !loading && (
            <div className="col-span-2 py-12 text-center text-[var(--color-text-tertiary)]">
              <Search size={32} className="mx-auto mb-2 opacity-30" />
              <p>没有找到匹配的视频</p>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {toolsLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 size={32} className="animate-spin text-[var(--color-primary)]" />
            </div>
          ) : (
            displayTools.map(tool => (
              <div
                key={tool.id}
                className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-4 shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-all"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-[var(--radius-md)] bg-[var(--color-primary-soft)] flex items-center justify-center shrink-0">
                      <Wrench size={18} className="text-[var(--color-primary)]" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-mono font-semibold text-sm text-[var(--color-text-primary)]">{tool.name}</h3>
                      </div>
                      {tool.purpose && (
                        <p className="text-sm text-[var(--color-text-secondary)] mt-1">{tool.purpose}</p>
                      )}
                      {tool.install_commands && tool.install_commands.length > 0 && (
                        <code className="block mt-2 px-3 py-2 bg-[var(--color-bg-app)] rounded-[var(--radius-sm)] text-xs text-[var(--color-text-primary)] font-mono border border-[var(--color-border-subtle)]">
                          $ {tool.install_commands[0]}
                        </code>
                      )}
                    </div>
                  </div>
                  <button className="shrink-0 p-1.5 text-[var(--color-text-tertiary)] hover:text-[var(--color-primary)] hover:bg-[var(--color-primary-soft)] rounded-md transition-all">
                    <ArrowUpRight size={16} />
                  </button>
                </div>
              </div>
            ))
          )}
          {!toolsLoading && displayTools.length === 0 && (
            <div className="py-12 text-center text-[var(--color-text-tertiary)]">
              <p>没有找到匹配的工具</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
