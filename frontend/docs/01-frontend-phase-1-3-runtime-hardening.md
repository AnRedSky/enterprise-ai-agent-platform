# Frontend Phase 1.3：Runtime 流式链路与可观测性基础加固

## 1. 目标

本阶段以前端当前已经接入的 `/api/v1` 后端体系为基线，优先处理运行时链路中最容易因网络分片、事件格式差异和后端错误结构变化而产生的脆弱点。

本阶段不重新设计后端 API，也不在前端伪造执行状态；前端只负责可靠解析后端真实返回的数据，并保留 request/trace/session/execution 等执行上下文。

## 2. 已实现

### 2.1 SSE Parser

`src/utils/sse.ts` 建立统一 SSE Parser，处理网络 chunk、LF/CRLF、heartbeat comment、多行 data、id/retry 及最终 flush。Runtime、Chat、Tool streaming 统一复用该边界。

### 2.2 Runtime Context / Status

`src/utils/runtime.ts` 统一 Runtime 状态归一化、Tag 类型、latency、长 ID 和后端错误提取，不改变后端协议。

### 2.3 Runtime Execution 页面

`RuntimeExecutions.vue` 已迁移公共 helper，统一展示并复制真实 Execution / Trace / Request / Session 上下文，Workflow Trace 同样使用统一 ID 展示。

### 2.4 Chat Streaming 消费迁移

`src/api/chat.ts` 已迁移到 `createSseParser` / `parseSseData`：

- 不再自行按网络 chunk 切分 SSE frame。
- 支持跨 chunk 事件与最终 flush。
- HTTP 非 2xx 继续抛出真实后端错误。
- 支持 `AbortSignal` 取消 fetch 生命周期。
- 不生成虚假的执行上下文 ID。

### 2.5 自动化 Unit Test

新增 `tests/api/chat.test.ts`，覆盖跨 chunk、最终 flush、AbortSignal、HTTP 错误及 response body 缺失；既有 Runtime / SSE / helper Unit Test 继续保留。

## 3. 当前阶段边界

公共 SSE、Runtime Execution、Chat streaming 消费迁移已经完成。下一步处理 Chat / Runtime UI 的失败、断流、取消生命周期，并继续消除重复状态解析。

下一步优先级：

1. 梳理 Chat 页面实际调用 `streamChat` 的生命周期，补充取消按钮与流状态收口。
2. 增加 Chat / Runtime 断流、失败、取消组件级 Unit Test。
3. 梳理其他 Runtime 页面，消除重复状态 / ID / latency 展示逻辑。
4. 后端新增 Runtime/DAG 字段后，先补充 API 契约测试，再扩展 UI。

## 4. 测试范围

当前只执行 Unit Test；Frontend production build、Browser E2E、Real API 和完整 Release Gate 暂不作为主线阻塞条件。实际执行结果必须如实记录，不得预填通过。

```powershell
cd frontend
npm test -- --run tests/api/chat.test.ts tests/views/Runtime.test.ts src/utils/sse.test.ts src/utils/runtime.test.ts
```
