import { getToken } from "./auth";
const apiOrigin = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export async function streamChat(payload, onEvent) {
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
    if (!response.body)
        throw new Error("Chat response body is unavailable");
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
            if (data)
                onEvent(JSON.parse(data));
        }
        if (done)
            break;
    }
}
export async function listSessionMessages(sessionId) {
    const token = getToken();
    const response = await fetch(`${apiOrigin}/api/v1/agents/sessions/${sessionId}/messages`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok)
        throw new Error(await response.text());
    return response.json();
}
