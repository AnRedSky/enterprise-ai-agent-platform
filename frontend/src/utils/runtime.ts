export type RuntimeStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'unknown'

export interface RuntimeContext {
  request_id?: string | null
  trace_id?: string | null
  session_id?: string | null
  agent_id?: string | null
  agent_version?: string | number | null
  model_id?: string | null
  execution_id?: string | null
  latency_ms?: number | null
}

export interface RuntimeStatusMeta {
  label: string
  type: 'info' | 'primary' | 'success' | 'danger' | 'warning'
}

const STATUS_META: Record<RuntimeStatus, RuntimeStatusMeta> = {
  queued: { label: '排队中', type: 'info' },
  running: { label: '运行中', type: 'primary' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
  cancelled: { label: '已取消', type: 'warning' },
  unknown: { label: '未知', type: 'info' },
}

export function normalizeRuntimeStatus(value: unknown): RuntimeStatus {
  if (typeof value !== 'string') return 'unknown'
  const normalized = value.toLowerCase()
  return normalized in STATUS_META ? (normalized as RuntimeStatus) : 'unknown'
}

export function getRuntimeStatusMeta(value: unknown): RuntimeStatusMeta {
  return STATUS_META[normalizeRuntimeStatus(value)]
}

export function formatLatency(value: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return '-'
  if (value < 1000) return `${Math.round(value)} ms`
  return `${(value / 1000).toFixed(2)} s`
}

export function shortRuntimeId(value: unknown, visibleLength = 8): string {
  if (typeof value !== 'string' || value.length === 0) return '-'
  if (value.length <= visibleLength * 2 + 3) return value
  return `${value.slice(0, visibleLength)}...${value.slice(-visibleLength)}`
}

export function firstRuntimeError(payload: unknown): string | null {
  if (!payload || typeof payload !== 'object') return null
  const record = payload as Record<string, unknown>
  for (const key of ['detail', 'error', 'message']) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return null
}
