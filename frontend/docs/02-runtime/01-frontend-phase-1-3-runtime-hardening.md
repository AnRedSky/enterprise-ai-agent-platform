# Frontend Phase 1.3：Runtime 流式链路与可观测性基础加固

## 1. 目标

本阶段以前端当前已经接入的 `/api/v1` 后端体系为基线，优先处理运行时链路中最容易因网络分片、事件格式差异、取消竞态和后端错误结构变化而产生的脆弱点。

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
- 支持后端 `error` SSE event，并将其作为业务事件交给 UI。
- 不生成虚假的执行上下文 ID。

### 2.5 Chat / Runtime UI 生命周期

`AgentWorkbench.vue` 已完成真实流式请求生命周期收口：

```text
idle
  ↓
streaming
  ├── completed
  ├── failed
  └── cancelled
```

具体实现：

- 每次 Chat 创建独立 `AbortController`。
- 用户可以点击“停止生成”主动取消。
- 关闭 Chat Dialog 时主动取消仍在运行的请求。
- 组件卸载时主动取消，避免后台遗留流。
- `activeRun` 作为请求代次标识，旧请求事件不能写入新请求 UI。
- 后端 `error` event 进入明确 failed 状态。
- HTTP / transport 异常进入 failed 状态。
- Abort 后进入 cancelled 状态，不显示为失败。
- 页面展示真实 `request_id / trace_id / session_id / execution_id`。
- 流正常结束但没有 done event 时，仍将当前流收口为 completed；execution_id 只有真实 done event 才写入。

### 2.6 自动化 Unit Test

`tests/api/chat.test.ts` 覆盖：

- 跨网络 chunk；
- 最终 flush；
- AbortSignal 透传；
- HTTP 错误；
- response body 缺失；
- SSE error event。

Runtime / SSE / helper Unit Test 继续保留。

## 3. 当前阶段 Closure

Phase 1.3 当前功能主线已经完成：

```text
SSE Parser                       ✅
Runtime helper                  ✅
Runtime Execution               ✅
Chat streaming                  ✅
Chat failure handling           ✅
Chat disconnect handling        ✅
Chat cancellation              ✅
stale stream race protection    ✅
real execution context         ✅
```

因此不再继续向该 Phase 堆叠 UI 功能。后续如果发现问题，只做必要回归修复；主线开发转回 Phase 2.7 Advanced Workflow Orchestration。

## 4. 测试范围

当前只执行 Unit Test；Frontend production build、Browser E2E、Real API 和完整 Release Gate 暂不作为主线阻塞条件。实际执行结果必须如实记录，不得预填通过。

```powershell
cd frontend
npm test -- --run tests/api/chat.test.ts tests/views/Runtime.test.ts src/utils/sse.test.ts src/utils/runtime.test.ts
```

当前执行环境不能启动本地 npm，因此本轮只提交测试代码，不伪造测试执行结果。
