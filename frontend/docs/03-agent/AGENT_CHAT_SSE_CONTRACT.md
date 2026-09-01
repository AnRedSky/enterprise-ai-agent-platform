# Agent 对话调试 SSE Contract

## 目的

记录 AgentWorkbench 对话调试与后端 `/api/v1/agents/stream` SSE Contract 的前端映射，避免页面实现与 API 类型漂移。

## 请求 Contract

`streamChat(payload, onEvent, signal)` 的参数顺序为：

1. `payload: ChatRequest`
2. `onEvent: (event: ChatEvent) => void`
3. `signal?: AbortSignal`

请求字段使用后端定义的 `agent_id`、`input`、`session_id`；前端不得把页面内部的 `message` 或 `request_id` 当作请求 Contract 字段。

## 事件映射

| SSE event | 页面处理 |
| --- | --- |
| `start` | 保存 `request_id`、`trace_id`、`session_id` |
| `delta` | 追加 assistant 消息内容 |
| `done` | 保存 `execution_id`；流结束后进入 completed |
| `error` | 保存用户可见错误并进入 failed |

## 取消与并发

- 使用 `AbortController` 取消当前流式请求。
- 使用递增 `activeRun` 忽略已经失效的旧流事件，避免快速切换/重试导致消息串写。
- `AbortError` 映射为 `cancelled`，不显示普通后端失败提示。

## 回归要求

AgentWorkbench targeted test 至少验证：

- 请求字段符合 `ChatRequest`；
- `start / delta / done / error` 均使用真实 `ChatEvent` discriminant；
- request / trace / session / execution 标识能够正确回填；
- delta 按顺序累积到当前 assistant 消息；
- 取消不会被误判为普通失败。
