# 2026-08-27 Phase 2.7 Recovery Trace Lineage Continuity

## 问题

Recovery Trace 已经校验 Source、Resume、tenant、workflow version 与 checkpoint sequence，但幂等命中已有 `recovery.trace_linked` 时，原逻辑直接返回旧事件，没有再次验证事件内部保存的 Source/Resume/checkpoint identity。

因此异常历史数据可能形成：

```text
同一 Resume Execution + trace_id
        ↓
命中旧 Trace Event
        ↓
旧 Event 指向错误 Source 或 Checkpoint
        ↓
错误 lineage 被静默接受
```

## 修复

`WorkflowRecoveryTraceLinkService.link()` 在幂等命中后重新验证：

- `source_execution_id`
- `resume_execution_id`
- `resume_checkpoint_sequence`

三项必须与当前已经验证的 Recovery lineage 完全一致；任意字段不一致立即抛出 `ValueError`。

同时 `get_trace_id()` 增加 `workflow_version_id` tenant/version 边界，避免恢复 trace 时跨版本命中事件。

## 设计边界

- PostgreSQL WorkflowExecution / Checkpoint 仍是 Durable Recovery 的事实来源。
- WorkflowTraceEvent 只承担审计、lineage 与 replay consistency。
- 不新增第二套 Trace SDK 或 Recovery State Store。
- 不使用 Trace Event 的业务 state_data 作为恢复状态。

## 验证范围

本轮新增 Unit Contract，覆盖已有 lineage event 身份不一致时拒绝、身份一致时允许，以及既有 Source/Checkpoint lineage 校验。

完整 Backend Regression、Real API、Frontend 与 E2E 按当前主线策略暂不执行；不得将未实际执行的测试记录为通过。
