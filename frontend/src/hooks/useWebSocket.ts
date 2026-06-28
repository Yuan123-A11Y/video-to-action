import { useEffect, useRef, useState, useCallback } from 'react'
import type { ProgressUpdate, TaskStatus } from '../types'
import { getTask } from '../api/client'

interface UseWebSocketOptions {
  taskId: string | null
  onProgress?: (progress: ProgressUpdate) => void
  onComplete?: () => void
  onError?: (error: string) => void
}

interface WebSocketState {
  connected: boolean
  status: TaskStatus | null
  progress: ProgressUpdate | null
  error: null | string
  mode: 'ws' | 'polling' | 'idle'
}

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
const POLL_INTERVAL = 1000      // 轮询间隔缩短到 1s，进度更实时
const WS_DATA_TIMEOUT = 15000   // WS 连上但 N 秒没收到数据 → 切轮询（加长到 15s，避免长步骤被切断）

export function useWebSocket({ taskId, onProgress, onComplete, onError }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const timersRef = useRef({
    connectTimeout: null as number | null,
    dataTimeout: null as number | null,
    heartbeat: null as number | null,
    poll: null as number | null,
  })
  const [state, setState] = useState<WebSocketState>({
    connected: false, status: null, progress: null, error: null, mode: 'idle',
  })

  // ── Timer helpers ──
  const clearTimers = useCallback((which?: keyof typeof timersRef.current | 'all' | Array<keyof typeof timersRef.current>) => {
    if (!which || which === 'all') {
      Object.values(timersRef.current).forEach(t => { try { clearTimeout(t) } catch {}; try { clearInterval(t) } catch {} })
      timersRef.current = { connectTimeout: null, dataTimeout: null, heartbeat: null, poll: null }
      return
    }
    if (Array.isArray(which)) {
      which.forEach(k => { const t = timersRef.current[k]; if (t != null) { try { clearTimeout(t) } catch {}; try { clearInterval(t) } catch {}; timersRef.current[k] = null } })
      return
    }
    const t = timersRef.current[which]
    if (t != null) { try { clearTimeout(t) } catch {}; try { clearInterval(t) } catch {}; timersRef.current[which] = null }
  }, [])

  const cleanupWs = useCallback(() => {
    clearTimers(['connectTimeout', 'dataTimeout', 'heartbeat'])
    const ws = wsRef.current
    if (ws) {
      ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close()
      wsRef.current = null
    }
  }, [clearTimers])

  const stopPolling = useCallback(() => clearTimers('poll'), [clearTimers])

  // ── HTTP 轮询（核心降级方案）──
  const startPolling = useCallback(() => {
    cleanupWs()
    clearTimers()
    setState(prev => ({ ...prev, mode: 'polling', connected: false }))

    const poll = async () => {
      if (!taskId) return
      try {
        const task = await getTask(taskId)
        const newStatus = task.status as TaskStatus
        setState(prev => ({
          ...prev,
          status: newStatus,
          progress: task.progress || prev.progress,
          error: task.error || null,
        }))
        if (newStatus === 'completed') { stopPolling(); onComplete?.() }
        else if (newStatus === 'failed') {
          stopPolling()
          const errMsg = task.error || '处理失败'
          setState(prev => ({ ...prev, error: errMsg })); onError?.(errMsg)
        }
      } catch { /* 静默，下次轮询 */ }
    }

    poll()                          // 立即执行一次
    timersRef.current.poll = window.setInterval(poll, POLL_INTERVAL)
  }, [taskId, onComplete, onError, cleanupWs, clearTimers, stopPolling])

  // ── WS 连接成功后，立即用 HTTP 同步一次当前状态（解决"迟到者"问题）──
  const syncOnce = useCallback(async () => {
    if (!taskId) return
    try {
      console.log('[WS] 连接成功，立即同步任务状态...')
      const task = await getTask(taskId)
      const newStatus = task.status as TaskStatus
      if (newStatus) {
        console.log(`[WS] 同步到状态: ${newStatus}`)
        setState(prev => ({
          ...prev,
          status: newStatus,
          progress: task.progress || prev.progress,
          error: task.error || null,
        }))
        if (newStatus === 'completed') { cleanupWs(); onComplete?.() }
        else if (newStatus === 'failed') {
          const err = task.error || '处理失败'
          setState(prev => ({ ...prev, error: err })); onError?.(err); cleanupWs()
        }
      }
    } catch (e) {
      console.warn('[WS] 同步失败:', e)
    }
  }, [taskId, onComplete, onError, cleanupWs])

  // ── 心跳 ──
  const startHeartbeat = useCallback(() => {
    clearTimers('heartbeat')
    timersRef.current.heartbeat = window.setInterval(() => {
      wsRef.current?.send(JSON.stringify({ type: 'ping' }))
    }, 30000)
  }, [clearTimers])

  // ── 建立 WS ──
  const connect = useCallback(() => {
    if (!taskId) return
    cleanupWs()
    clearTimers('poll')
    setState(prev => ({ ...prev, mode: 'ws', error: null, connected: false }))

    const url = `${WS_BASE_URL.replace(/^http/, 'ws')}/ws/tasks/${taskId}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    // ① 连接超时：5s 没连上 → 切轮询
    timersRef.current.connectTimeout = window.setTimeout(() => {
      if (ws.readyState === WebSocket.CONNECTING) {
        console.log('[WS] ⏱ 连接超时(5s)，切轮询')
        ws.close(4001); startPolling()
      }
    }, 5000)

    // ② 数据超时：连上了但 N 秒没收到任何消息 → 切轮询（覆盖"连上了但后端不推数据"的场景）
    const startDataTimeout = () => {
      clearTimers('dataTimeout')
      timersRef.current.dataTimeout = window.setTimeout(() => {
        console.log(`[WS] ⏱ 已连接 ${WS_DATA_TIMEOUT / 1000}s 未收到数据，切轮询`)
        cleanupWs(); startPolling()
      }, WS_DATA_TIMEOUT)
    }

    ws.onopen = () => {
      clearTimers('connectTimeout')
      setState(prev => ({ ...prev, connected: true, mode: 'ws' }))
      startHeartbeat()
      startDataTimeout()
      syncOnce()           // ← 立即同步！
    }

    ws.onmessage = (event) => {
      clearTimers('dataTimeout')     // 收到数据就重置数据超时
      try {
        const msg = JSON.parse(event.data)
        switch (msg.type) {
          case 'progress': {
            const p: ProgressUpdate = msg.data
            setState(prev => ({ ...prev, progress: p, status: 'processing' }))
            onProgress?.(p); break
          }
          case 'status':
            setState(prev => ({ ...prev, status: msg.data.status }))
            if (msg.data.status === 'completed') { cleanupWs(); onComplete?.() }
            else if (msg.data.status === 'failed') {
              const err = msg.data.error || '处理失败'
              setState(prev => ({ ...prev, error: err })); onError?.(err); cleanupWs()
            }
            break
          case 'pong': break
          default: console.warn('[WS] Unknown msg:', msg.type)
        }
      } catch (e) { console.error('[WS] parse error:', e) }
    }

    ws.onerror = () => { setState(prev => ({ ...prev, connected: false })) }

    ws.onclose = (event) => {
      clearTimers(['connectTimeout', 'dataTimeout', 'heartbeat'])
      setState(prev => ({ ...prev, connected: false }))
      // 非主动关闭 → 切轮询
      if (event.code !== 1000 && event.code !== 4001 && taskId) {
        console.log(`[WS] closed(code=${event.code}), 切轮询`)
        startPolling()
      }
    }
  }, [taskId, onProgress, onComplete, onError, cleanupWs, clearTimers, startHeartbeat, startPolling, syncOnce])

  // ── taskId 变化时启动 ──
  useEffect(() => {
    if (taskId) connect()
    else { cleanupWs(); clearTimers() }
    return () => { cleanupWs(); clearTimers() }
  }, [taskId]) // eslint-disable-line react-hooks/exhaustive-deps

  const disconnect = useCallback(() => {
    cleanupWs(); clearTimers()
    setState({ connected: false, status: null, progress: null, error: null, mode: 'idle' })
  }, [cleanupWs, clearTimers])

  return { ...state, disconnect }
}
