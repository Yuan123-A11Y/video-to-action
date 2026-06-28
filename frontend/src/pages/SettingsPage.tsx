import { useState, useEffect } from 'react'
import {
  Check,
  ChevronDown,
  AlertCircle,
  CircleCheck,
  Loader2,
  Server,
} from 'lucide-react'

const SIDEBAR_ITEMS = [
  { id: 'llm', label: 'LLM 配置' },
  { id: 'automation', label: '自动化级别' },
  { id: 'knowledge', label: '知识库' },
  { id: 'appearance', label: '外观' },
]

type LlmProvider = 'openai' | 'ollama' | 'other'
type AutomationLevel = 'extract' | 'observe' | 'confirm' | 'auto'

interface SettingsData {
  provider: LlmProvider
  apiKey: string
  model: string
  automation: AutomationLevel
  dbType: string
  dbConnection: string
}

const STORAGE_KEY = 'video-to-action-settings'

function loadSettings(): SettingsData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return {
    provider: 'openai',
    apiKey: '',
    model: 'gpt-4',
    automation: 'confirm',
    dbType: 'sqlite',
    dbConnection: '',
  }
}

function saveSettings(data: SettingsData) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('llm')
  const [provider, setProvider] = useState<LlmProvider>('openai')
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [apiKeyError, setApiKeyError] = useState<string | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null)
  const [model, setModel] = useState('gpt-4')
  const [automation, setAutomation] = useState<AutomationLevel>('confirm')
  const [dbType, setDbType] = useState('sqlite')
  const [dbConnection, setDbConnection] = useState('')
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  // 加载设置
  useEffect(() => {
    const settings = loadSettings()
    setProvider(settings.provider)
    setApiKey(settings.apiKey)
    setModel(settings.model)
    setAutomation(settings.automation)
    setDbType(settings.dbType)
    setDbConnection(settings.dbConnection)
  }, [])

  // API Key 实时校验
  const validateApiKey = (key: string) => {
    if (!key) return null // 允许为空（用户可能不想现在填）
    if (provider === 'openai' && !key.startsWith('sk-')) return 'OpenAI API Key 应以 sk- 开头'
    if (key.length < 10) return 'API Key 长度不足'
    return null
  }

  const handleApiKeyChange = (value: string) => {
    setApiKey(value)
    setApiKeyError(validateApiKey(value))
    setTestResult(null)
  }

  const handleTestConnection = async () => {
    const err = validateApiKey(apiKey)
    if (err) {
      setApiKeyError(err)
      return
    }
    setTesting(true)
    setTestResult(null)
    // 实际测试连接（调用后端 API 验证 key）
    try {
      const res = await fetch('/api/stats', {
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
      })
      if (res.ok) {
        setTestResult('success')
      } else {
        setTestResult('error')
      }
    } catch {
      setTestResult('error')
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    // 模拟保存到后端的延迟
    await new Promise(r => setTimeout(r, 500))
    const settings: SettingsData = {
      provider,
      apiKey,
      model,
      automation,
      dbType,
      dbConnection,
    }
    saveSettings(settings)
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)]">配置</h1>
        <p className="text-[var(--color-text-secondary)] mt-1">配置 LLM、自动化级别和知识库设置（设置会自动保存到浏览器）</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 shrink-0">
          <nav className="space-y-1">
            {SIDEBAR_ITEMS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === id
                    ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary-strong)]'
                    : 'text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>

        {/* Main Content */}
        <div className="flex-1 max-w-2xl space-y-6">
          {/* LLM 配置 */}
          {activeTab === 'llm' && (
            <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-6 shadow-[var(--shadow-sm)] space-y-6">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">LLM 提供商</h2>

              {/* Provider Selection */}
              <div className="grid grid-cols-3 gap-3">
                {([
                  { id: 'openai', label: 'OpenAI', desc: 'GPT-4 / GPT-3.5' },
                  { id: 'ollama', label: 'Ollama', desc: '本地模型' },
                  { id: 'other', label: '其他', desc: '自定义端点' },
                ] as const).map(({ id, label, desc }) => (
                  <button
                    key={id}
                    onClick={() => setProvider(id)}
                    className={`text-left p-4 rounded-[var(--radius-md)] border-2 transition-all ${
                      provider === id
                        ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]'
                        : 'border-[var(--color-border-default)] hover:border-[var(--color-border-strong)]'
                    }`}
                  >
                    <div className="font-medium text-sm text-[var(--color-text-primary)]">{label}</div>
                    <div className="text-xs text-[var(--color-text-tertiary)] mt-0.5">{desc}</div>
                  </button>
                ))}
              </div>

              {/* API Key */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-[var(--color-text-primary)]">
                  API Key
                </label>
                <div className="relative">
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={(e) => handleApiKeyChange(e.target.value)}
                    placeholder={provider === 'openai' ? 'sk-...' : '输入 API Key'}
                    className={`w-full px-4 py-2.5 rounded-[var(--radius-sm)] border text-sm font-mono transition-all ${
                      apiKeyError
                        ? 'border-red-500 focus:border-red-500 focus:shadow-[0_0_0_3px_rgba(239,68,68,0.1)]'
                        : 'border-[var(--color-border-default)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)]'
                    } outline-none bg-[var(--color-bg-surface)]`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey(!showKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)] text-xs"
                  >
                    {showKey ? '隐藏' : '显示'}
                  </button>
                </div>
                {apiKeyError && (
                  <p className="text-xs text-red-600 flex items-center gap-1">
                    <AlertCircle size={14} />
                    {apiKeyError}
                  </p>
                )}

                {/* Test Connection */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleTestConnection}
                    disabled={testing || !!apiKeyError || !apiKey}
                    className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-[var(--radius-sm)] border transition-all ${
                      testing || !!apiKeyError || !apiKey
                        ? 'border-[var(--color-border-default)] text-[var(--color-text-disabled)] cursor-not-allowed'
                        : 'border-[var(--color-border-default)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
                    }`}
                  >
                    {testing ? (
                      <>
                        <Loader2 className="animate-spin w-4 h-4" />
                        测试中...
                      </>
                    ) : '测试连接'}
                  </button>
                  {testResult === 'success' && (
                    <span className="text-sm text-green-600 flex items-center gap-1">
                      <CircleCheck size={16} />
                      连接成功
                    </span>
                  )}
                  {testResult === 'error' && (
                    <span className="text-sm text-red-600 flex items-center gap-1">
                      <AlertCircle size={16} />
                      连接失败
                    </span>
                  )}
                </div>
              </div>

              {/* Model Selection */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-[var(--color-text-primary)]">
                  模型
                </label>
                <div className="relative">
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] text-sm bg-[var(--color-bg-surface)] outline-none appearance-none cursor-pointer hover:border-[var(--color-border-strong)] focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)]"
                  >
                    <option value="gpt-4">GPT-4</option>
                    <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                    <option value="agnes-2.0-flash">Agnes 2.0 Flash</option>
                    <option value="custom">自定义...</option>
                  </select>
                  <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] pointer-events-none" />
                </div>
              </div>
            </div>
          )}

          {/* 自动化级别 */}
          {activeTab === 'automation' && (
            <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-6 shadow-[var(--shadow-sm)] space-y-4">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">自动化级别</h2>
              <p className="text-sm text-[var(--color-text-secondary)]">
                控制 AI 分析后自动执行命令的程度
              </p>

              {([
                {
                  id: 'extract' as const,
                  title: '仅提取',
                  desc: '只提取操作步骤，不执行任何命令',
                  badge: null,
                },
                {
                  id: 'observe' as const,
                  title: '观察模式',
                  desc: '提取步骤并在沙箱环境中观察执行效果，不实际运行',
                  badge: null,
                },
                {
                  id: 'confirm' as const,
                  title: '确认后执行',
                  desc: '每个命令执行前需要手动确认（推荐）',
                  badge: '推荐',
                },
                {
                  id: 'auto' as const,
                  title: '全自动',
                  desc: '自动执行所有安全命令，危险命令需确认',
                  badge: '谨慎',
                },
              ]).map(({ id, title, desc, badge }) => (
                <button
                  key={id}
                  onClick={() => setAutomation(id)}
                  className={`w-full text-left p-4 rounded-[var(--radius-md)] border-2 transition-all ${
                    automation === id
                      ? 'border-[var(--color-primary)] bg-[var(--color-primary-soft)]'
                      : 'border-[var(--color-border-default)] hover:border-[var(--color-border-strong)]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      automation === id ? 'border-[var(--color-primary)]' : 'border-[var(--color-border-strong)]'
                    }`}>
                      {automation === id && (
                        <Check size={10} className="text-[var(--color-primary)]" strokeWidth={3} />
                      )}
                    </div>
                    <span className="font-medium text-sm text-[var(--color-text-primary)]">{title}</span>
                    {badge && (
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        badge === '推荐'
                          ? 'bg-[var(--color-primary-soft)] text-[var(--color-primary-strong)]'
                          : 'bg-yellow-50 text-yellow-600'
                      }`}>
                        {badge}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-1.5 ml-7">{desc}</p>
                </button>
              ))}
            </div>
          )}

          {/* 知识库配置 */}
          {activeTab === 'knowledge' && (
            <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-6 shadow-[var(--shadow-sm)] space-y-4">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">知识库配置</h2>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-[var(--color-text-primary)]">数据库类型</label>
                <div className="relative">
                  <select
                    value={dbType}
                    onChange={(e) => setDbType(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] text-sm bg-[var(--color-bg-surface)] outline-none appearance-none cursor-pointer"
                  >
                    <option value="sqlite">SQLite（默认）</option>
                    <option value="mysql">MySQL</option>
                    <option value="postgres">PostgreSQL</option>
                  </select>
                  <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)] pointer-events-none" />
                </div>
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-medium text-[var(--color-text-primary)]">连接信息</label>
                <input
                  type="text"
                  value={dbConnection}
                  onChange={(e) => setDbConnection(e.target.value)}
                  placeholder={dbType === 'sqlite' ? 'data/videos.db' : 'mysql://user:pass@localhost:3306/dbname'}
                  className="w-full px-4 py-2.5 rounded-[var(--radius-sm)] border border-[var(--color-border-default)] text-sm font-mono bg-[var(--color-bg-surface)] outline-none focus:border-[var(--color-primary-border)] focus:shadow-[var(--shadow-focus)] transition-all"
                />
              </div>
              <div className="p-3 bg-blue-50 rounded-md text-xs text-blue-700">
                <Server size={14} className="inline mr-1" />
                修改数据库配置后需要重启后端服务才能生效
              </div>
            </div>
          )}

          {/* 外观 */}
          {activeTab === 'appearance' && (
            <div className="bg-[var(--color-bg-surface)] rounded-[var(--radius-lg)] border border-[var(--color-border-subtle)] p-6 shadow-[var(--shadow-sm)] space-y-4">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">外观</h2>
              <p className="text-sm text-[var(--color-text-secondary)]">
                主题设置将在后续版本支持深色模式
              </p>
              <div className="p-4 rounded-[var(--radius-md)] bg-[var(--color-bg-raised)] text-sm text-[var(--color-text-secondary)]">
                当前为浅色主题
              </div>
            </div>
          )}

          {/* Save Button */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2.5 bg-[var(--color-primary)] text-white rounded-[var(--radius-sm)] text-sm font-medium hover:bg-[var(--color-primary-hover)] disabled:opacity-50 transition-colors shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)]"
            >
              {saving ? '保存中...' : '保存配置'}
            </button>
            <button
              onClick={() => {
                setProvider('openai')
                setApiKey('')
                setApiKeyError(null)
                setAutomation('confirm')
                setModel('gpt-4')
                setDbType('sqlite')
                setDbConnection('')
              }}
              className="px-5 py-2.5 text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
            >
              重置
            </button>
            {saved && (
              <span className="text-sm text-green-600 flex items-center gap-1">
                <CircleCheck size={16} />
                已保存到浏览器
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
