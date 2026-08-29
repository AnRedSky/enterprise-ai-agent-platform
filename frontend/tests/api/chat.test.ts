import { beforeEach, describe, expect, it, vi } from "vitest";
import { streamChat } from "../../src/api/chat";

vi.mock("../../src/api/auth", () => ({ getToken: vi.fn(() => "test-token") }));

describe("streamChat", () => {
  beforeEach(() => vi.restoreAllMocks());

  function responseFromChunks(chunks: string[], ok = true) {
    const encoder = new TextEncoder();
    let index = 0;
    const read = vi.fn(async () => {
      if (index >= chunks.length) return { done: true, value: undefined };
      return { done: false, value: encoder.encode(chunks[index++]) };
    });
    const releaseLock = vi.fn();
    return {
      ok,
      status: ok ? 200 : 502,
      text: vi.fn().mockResolvedValue(ok ? "" : "provider failed"),
      body: {
        getReader: () => ({ read, releaseLock }),
      },
    } as unknown as Response;
  }

  it("uses the shared SSE parser across network chunk boundaries", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(responseFromChunks([
      "event: message\ndata: {\"type\":\"delta\",\"content\":\"hel",
      "lo\"}\n\nevent: message\ndata: {\"type\":\"done\",\"execution_id\":\"e1\",\"latency_ms\":12}\n\n",
    ]));
    const events: unknown[] = [];

    await streamChat({ agent_id: "a1", input: "hello" }, (event) => events.push(event));

    expect(events).toEqual([
      { type: "delta", content: "hello" },
      { type: "done", execution_id: "e1", latency_ms: 12 },
    ]);
  });

  it("flushes a final SSE event without a trailing blank line", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(responseFromChunks([
      "data: {\"type\":\"done\",\"execution_id\":\"e2\",\"latency_ms\":null}",
    ]));
    const events: unknown[] = [];

    await streamChat({ agent_id: "a1", input: "hello" }, (event) => events.push(event));

    expect(events).toEqual([{ type: "done", execution_id: "e2", latency_ms: null }]);
  });

  it("passes the abort signal to the real fetch request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(responseFromChunks([]));
    const controller = new AbortController();

    await streamChat({ agent_id: "a1", input: "hello" }, vi.fn(), controller.signal);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/agents/stream"),
      expect.objectContaining({ signal: controller.signal }),
    );
  });

  it("surfaces backend HTTP errors instead of parsing them as SSE", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(responseFromChunks([], false));

    await expect(streamChat({ agent_id: "a1", input: "hello" }, vi.fn())).rejects.toThrow("provider failed");
  });

  it("rejects when the streaming response has no body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true, status: 200, body: null } as Response);

    await expect(streamChat({ agent_id: "a1", input: "hello" }, vi.fn())).rejects.toThrow("Chat response body is unavailable");
  });
});
