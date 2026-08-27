export interface SseEvent {
  event: string
  data: string
  id?: string
  retry?: number
}

export interface SseParser {
  push(chunk: string): SseEvent[]
  flush(): SseEvent[]
  reset(): void
}

function parseEvent(block: string): SseEvent | null {
  const lines = block.split(/\r?\n/)
  const data: string[] = []
  let event = 'message'
  let id: string | undefined
  let retry: number | undefined

  for (const line of lines) {
    if (!line || line.startsWith(':')) continue
    const separator = line.indexOf(':')
    const field = separator === -1 ? line : line.slice(0, separator)
    const value = separator === -1 ? '' : line.slice(separator + 1).replace(/^ /, '')

    switch (field) {
      case 'event':
        event = value
        break
      case 'data':
        data.push(value)
        break
      case 'id':
        id = value
        break
      case 'retry': {
        const parsed = Number(value)
        if (Number.isInteger(parsed) && parsed >= 0) retry = parsed
        break
      }
    }
  }

  if (data.length === 0 && id === undefined && retry === undefined) return null
  return { event, data: data.join('\n'), ...(id === undefined ? {} : { id }), ...(retry === undefined ? {} : { retry }) }
}

export function createSseParser(): SseParser {
  let buffer = ''

  const consume = (final = false): SseEvent[] => {
    const normalized = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
    const blocks = normalized.split('\n\n')
    if (!final) buffer = blocks.pop() ?? ''
    else buffer = ''

    return blocks.map(parseEvent).filter((event): event is SseEvent => event !== null)
  }

  return {
    push(chunk) {
      buffer += chunk
      return consume(false)
    },
    flush() {
      return consume(true)
    },
    reset() {
      buffer = ''
    },
  }
}

export function parseSseData<T = unknown>(event: SseEvent): T | string {
  try {
    return JSON.parse(event.data) as T
  } catch {
    return event.data
  }
}