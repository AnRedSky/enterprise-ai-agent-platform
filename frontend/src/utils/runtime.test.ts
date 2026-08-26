import { describe, expect, it } from 'vitest'
import { formatLatency, firstRuntimeError, getRuntimeStatusMeta, normalizeRuntimeStatus, shortRuntimeId } from './runtime'

describe('runtime helpers', () => {
  it('normalizes known and unknown statuses', () => {
    expect(normalizeRuntimeStatus('RUNNING')).toBe('running')
    expect(normalizeRuntimeStatus('not-a-status')).toBe('unknown')
    expect(getRuntimeStatusMeta('completed')).toEqual({ label: '已完成', type: 'success' })
  })

  it('formats latency for milliseconds and seconds', () => {
    expect(formatLatency(42)).toBe('42 ms')
    expect(formatLatency(1250)).toBe('1.25 s')
    expect(formatLatency(null)).toBe('-')
  })

  it('shortens execution identifiers without hiding short values', () => {
    expect(shortRuntimeId('exec-123')).toBe('exec-123')
    expect(shortRuntimeId('1234567890abcdef1234567890abcdef', 4)).toBe('1234...cdef')
    expect(shortRuntimeId(null)).toBe('-')
  })

  it('extracts a useful backend error message', () => {
    expect(firstRuntimeError({ detail: 'timeout' })).toBe('timeout')
    expect(firstRuntimeError({ error: 'provider failed' })).toBe('provider failed')
    expect(firstRuntimeError({})).toBeNull()
  })
})
