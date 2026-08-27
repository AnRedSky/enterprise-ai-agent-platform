# Frontend Phase 1.3：Runtime 流式链路与可观测性基础加固

## 1. 目标

本阶段以前端当前已经接入的 `/api/v1` 后端体系为基线，优先处理运行时链路中最容易因网络分片、事件格式差异和后端错误结构变化而产生的脆弱点。

本阶段不重新设计后端 API，也不在前端伪造执行状态；前端只负责可靠解析后端真实返回的数据，并保留 request/trace/session/execution 等执行上下文。

## 2. 已实现

### 2.1 SSE Parser

`src/utils/sse.ts` 建立统一 SSE Parser：

- 支持一个 SSE event 被拆成多个 HTTP 网络 chunk。
- 支持 LF / CRLF。
- 支持 SSE comment heartbeat。
- 支持 `event`、多行 `data`、`id`、`retry`。
- 支持流结束时 flush 未以空行结束的最后一个事件。
- JSON data 自动解析；非 JSON data 保留原始字符串。

Runtime、Chat、Tool streaming 后续统一复用该解析边界，不在页面自行 `split('\\n\\n')`。

### 2.2 Runtime Context / Status

`src/utils/runtime.ts` 建立统一展示边界：

- Runtime 状态归一化及展示文案。
- Element Plus Tag 类型映射。
- latency 格式化。
- execution/request/trace/session 长 ID 缩略。
- `detail/error/message` 后端错误提取。

这些 helper 不改变后端协议，只集中前端展示规则。

### 2.3 Runtime Execution 页面迁移

`RuntimeExecutions.vue` 已迁移到公共 Runtime helper：

- Execution / Trace / Request / Session 使用统一长 ID 展示。
- 状态使用统一状态枚举与 Tag 展示。
- Duration 使用统一 latency 格式化。
- 保留真实后端 `execution_id` / `trace_id` / `request_id` / `session_id`，不在前端生成替代 ID。
- 提供执行上下文复制能力，复制内容直接来自后端字段。
- Workflow Trace 的 Trace ID 同样使用统一缩略规则。

### 2.4 自动化 Unit Test

新增：

- `src/utils/sse.test.ts`
- `src/utils/runtime.test.ts`
- `tests/views/Runtime.test.ts` 对 Runtime 页面消费边界进行补充验证。
- `scripts/test/phase-1-3-runtime-hardening.ps1` 提供可重复的 frontend test/build 入口。

测试重点覆盖网络分片、SSE 事件格式、状态归一化、延迟展示、错误提取、Execution Trace 加载及执行上下文复制。

## 3. 与后端关系

当前后端已经具备 Agent Runtime、Model Gateway、SSE、Session/Message 以及 request_id / trace_id / execution_id 等执行上下文。前端不重复实现这些能力，而是围绕真实 API 返回增强消费层稳定性。

特别注意：

- 不使用 JSON 文件模拟 Runtime 数据。
- 不在前端生成虚假的 execution_id / trace_id。
- 不把后端执行状态写死为“成功”。
- Provider / Tool / Runtime 错误必须沿真实 API 响应传递到 UI。

## 4. 当前阶段边界

公共 SSE / Runtime 数据边界与 Runtime Execution 页面迁移已经完成。下一步继续处理 Chat streaming 及 Runtime 失败、断流、取消场景，但不引入第二套 SSE 或状态解析实现。

下一步优先级：

1. 将现有 Chat streaming 消费逻辑迁移到 `createSseParser`。
2. 梳理 Runtime 相关页面，消除重复状态 / ID / latency 展示逻辑。
3. 增加 Chat / Runtime 断流、失败、取消组件级 Unit Test。
4. 后端新增 Runtime/DAG 执行字段后，先补充 API 契约测试，再扩展 UI，不通过 mock 数据掩盖接口差异。

## 5. 本地验收

在 `frontend` 目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-1-3-runtime-hardening.ps1
```

当前按主线开发策略仅要求 Unit Test 实际通过；production build 属于完整 Frontend Gate，暂不作为主线阻塞条件。任何实际执行结果必须如实记录，不得预填“通过”。