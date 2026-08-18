import { getToken } from "./auth";

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

export async function streamChat(
  payload: ChatRequest,
  onEvent: (event: ChatEvent) => void,
): Promise<void> {
  const response = await fetch(`${apiOrigin}/api/v1/agents/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Chat request failed: ${response.status}`);
  }
  if (!response.body) throw new Error("Chat response body is unavailable");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";

    for (const frame of frames) {
      const data = frame
        .split("\n")
        .find((line) => line.startsWith("data: "))
        ?.slice(6)
        .trim();
      if (data) onEvent(JSON.parse(data) as ChatEvent);
    }
    if (done) break;
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
