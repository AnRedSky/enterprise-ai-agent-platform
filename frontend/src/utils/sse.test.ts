import { describe, expect, it } from 'vitest'
import { createSseParser, parseSseData } from './sse'

describe('createSseParser', () => {
  it('parses events split across network chunks', () => {
    const parser = createSseParser()

    expect(parser.push('event: delta\ndata: {"text":"hel')).toEqual([])
    expect(parser.push('lo"}\n\n')).toEqual([
      { event: 'delta', data: '{"text":"hello"}' },
    ])
  })

  it('supports CRLF, comments and multiline data', () => {
    const parser = createSseParser()
    const events = parser.push(': heartbeat\r\nevent: message\r\ndata: first\r\ndata: second\r\nid: 42\r\n\r\n')

    expect(events).toEqual([
      { event: 'message', data: 'first\nsecond', id: '42' },
    ])
  })

  it('flushes the final unterminated event', () => {
    const parser = createSseParser()
    parser.push('event: done\ndata: {"ok":true}')

    expect(parser.flush()).toEqual([
      { event: 'done', data: '{"ok":true}' },
    ])
  })

  it('parses JSON payloads and preserves plain text', () => {
    const parser = createSseParser()
    const [jsonEvent] = parser.push('data: {"execution_id":"exec-1"}\n\n')
    const [textEvent] = parser.push('data: done\n\n')

    expect(parseSseData(jsonEvent)).toEqual({ execution_id: 'exec-1' })
    expect(parseSseData(textEvent)).toBe('done')
  })
})