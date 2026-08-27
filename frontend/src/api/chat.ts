import { getToken } from "./auth";
import { createSseParser, parseSseData } from "@/utils/sse";

export interface ChatRequest {
  agent_id: string;
  input: string;
  session_id?: string;
  memory_limit?: number;
}

export interface ChatStartEvent {
  type: "start";
  request_id: string;
  trace_id: string;
  session_id: string;
  agent_id: string;
  agent_version: string;
  model_id: string;
  memory_count: number;
}

export interface ChatDoneEvent {
  type: "done";
  execution_id: string;
  latency_ms: number | null;
}

export interface ChatDeltaEvent {
  type: "delta";
  content: string;
}

export interface ChatErrorEvent {
  type: "error";
  message: string;
  code?: string;
}

export type ChatEvent = ChatStartEvent | ChatDeltaEvent | ChatDoneEvent | ChatErrorEvent;

const apiOrigin = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

/**
 * 通过后端 SSE 接口流式执行对话，并将真实事件按顺序交给调用方。
 * 取消由调用方通过 AbortController 管理 fetch 生命周期。
 */
export async function streamChat(
  payload: ChatRequest,
  onEvent: (event: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken();
  const response = await fetch(`${apiOrigin}/api/v1/agents/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Chat request failed: ${response.status}`);
  }
  if (!response.body) throw new Error("Chat response body is unavailable");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parser = createSseParser();

  try {
    while (true) {
      const { done, value } = await reader.read();
      const chunk = decoder.decode(value || new Uint8Array(), { stream: !done });
      for (const event of parser.push(chunk)) {
        if (!event.data) continue;
        const data = parseSseData<ChatEvent>(event);
        if (typeof data !== "string") onEvent(data);
      }
      if (done) break;
    }

    for (const event of parser.flush()) {
      if (!event.data) continue;
      const data = parseSseData<ChatEvent>(event);
      if (typeof data !== "string") onEvent(data);
    }
  } finally {
    reader.releaseLock();
  }
}

export async function listSessionMessages(sessionId: string) {
  const token = getToken();
  const response = await fetch(`${apiOrigin}/api/v1/agents/sessions/${sessionId}/messages`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<Array<{ id: string; role: string; content: string; created_at: string }>>;
}
