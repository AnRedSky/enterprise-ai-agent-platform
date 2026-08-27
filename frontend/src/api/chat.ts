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

export type ChatEvent = ChatStartEvent | ChatDeltaEvent | ChatDoneEvent;

const apiOrigin = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

/**
 * 通过后端 SSE 接口流式执行对话，并将真实事件按顺序交给调用方。
 *
 * Args:
 *   payload: Chat 请求参数。
 *   onEvent: 收到完整 Chat 事件后的回调。
 *   signal: 可选的请求取消信号。
 *
 * Returns:
 *   流正常结束时返回 Promise<void>；HTTP、流读取或事件解析失败时抛出异常。
 *
 * 重要约束：SSE 分片必须通过统一解析器处理，避免网络 chunk 边界被误认为事件边界；取消由调用方通过 AbortController 管理 fetch 生命周期。
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

  while (true) {
    const { done, value } = await reader.read();
    const chunk = decoder.decode(value || new Uint8Array(), { stream: !done });
    for (const event of parser.push(chunk)) {
      if (!event.data) continue;
      onEvent(parseSseData<ChatEvent>(event) as ChatEvent);
    }
    if (done) break;
  }

  for (const event of parser.flush()) {
    if (!event.data) continue;
    onEvent(parseSseData<ChatEvent>(event) as ChatEvent);
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
