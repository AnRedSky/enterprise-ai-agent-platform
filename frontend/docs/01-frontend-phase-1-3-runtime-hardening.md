# Frontend Phase 1.3：Runtime 流式链路与可观测性基础加固

## 1. 目标

本阶段以前端当前已经接入的 `/api/v1` 后端体系为基线，优先处理运行时链路中最容易因网络分片、事件格式差异和后端错误结构变化而产生的脆弱点。

本阶段不重新设计后端 API，也不在前端伪造执行状态；前端只负责可靠解析后端真实返回的数据，并保留 request/trace/session/execution 等执行上下文。

## 2. 本次实现

### 2.1 SSE Parser

新增 `src/utils/sse.ts`：

- 支持一个 SSE event 被拆成多个 HTTP 网络 chunk。
- 支持 LF / CRLF。
- 支持 SSE comment heartbeat。
- 支持 `event`、多行 `data`、`id`、`retry`。
- 支持流结束时 flush 未以空行结束的最后一个事件。
- JSON data 自动解析；非 JSON data 保留原始字符串。

这一层与具体 Runtime 页面解耦，后续 Runtime、Chat、Tool streaming 都应复用同一解析器，而不是各页面自行 `split('\\n\\n')`。

### 2.2 Runtime Context / Status

新增 `src/utils/runtime.ts`：

- 统一 Runtime 状态枚举。
- 统一状态展示文案和 Element Plus Tag 类型。
- 统一 latency 格式化。
- 统一 execution/request/trace 等长 ID 的展示缩略。
- 统一从 `detail/error/message` 提取后端错误。

这些 helper 不改变后端协议，只把展示规则集中到一个边界层。

### 2.3 自动化测试

新增：

- `src/utils/sse.test.ts`
- `src/utils/runtime.test.ts`
- `scripts/test/phase-1-3-runtime-hardening.ps1`

测试重点不是 Vue DOM 快照，而是 Runtime 数据边界：网络分片、事件解析、状态归一化、延迟展示和错误提取。

## 3. 与当前后端的关系

当前后端已经具备 Agent Runtime、Model Gateway、SSE、Session/Message 以及 request_id / trace_id / execution_id 等执行上下文。前端本阶段不重复实现这些能力，而是围绕这些真实上下文增强消费层的稳定性。

特别注意：

- 不使用 JSON 文件模拟 Runtime 数据。
- 不在前端生成虚假的 execution_id / trace_id。
- 不把后端执行状态写死为“成功”。
- Provider / Tool / Runtime 错误必须沿真实 API 响应传递到 UI。

## 4. 当前阶段边界

本阶段先完成公共数据边界和自动化回归门禁，再继续改造 Runtime 页面本身。页面改造应直接复用本阶段 helper，避免在组件内复制 SSE 和状态解析逻辑。

下一步优先级：

1. 将现有 Runtime / Chat streaming 消费逻辑迁移到 `createSseParser`。
2. Runtime execution 列表统一使用 `getRuntimeStatusMeta`、`formatLatency` 和 `shortRuntimeId`。
3. 在页面中完整展示 request_id、trace_id、session_id、execution_id，并提供复制能力。
4. 增加 Runtime 失败、断流、重连/取消等组件级测试。
5. 后端新增 Runtime/DAG 执行字段后，先补充契约测试，再扩展 UI，不通过 mock 数据掩盖接口差异。

## 5. 本地验收

在 `frontend` 目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-1-3-runtime-hardening.ps1
```

该脚本必须依次完成：

1. Node/npm 版本检查。
2. `npm ci` 锁定依赖。
3. `npm test -- --run`。
4. `npm run build`。

任何一步失败都应停止并返回非 0 状态。