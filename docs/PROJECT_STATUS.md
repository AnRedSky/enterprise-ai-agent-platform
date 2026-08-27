# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 本轮开发基线：`8d16915f7f24ca081df4e26ed8b196da4697e263`。
- 本轮已落地：Chat stream transport hardening + Chat / Runtime failure / disconnect / cancel UI lifecycle。
- 本轮最新代码提交：`bfaec2e4ba81aeeea7481fa5af2251dd66e3d56c`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；Frontend / Browser E2E 与历史 Real API 验收已完成，本轮不再作为主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成，DAG Resume / Branch / Join / Automatic Recovery / Recovery Trace / Worker Reclaim / Lease Fencing / Lease Loss Active Abort / Terminal Ownership Boundary 均已落地；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**继续按最新治理规则推进，不作为当前主线阻塞条件。**
- Frontend Phase 1.3：**SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。**
- Phase 2.7 Advanced Workflow Orchestration：**开发中；Conditional Branching 首个交付单元生产代码与 Unit Test 覆盖已完成，当前等待开发者本地 Unit Test 实际执行。**

## Phase 2.7-A 当前实现

- `WorkflowConditionEvaluator` 是唯一条件求值入口；
- DSL 支持 `eq / ne / gt / gte / lt / lte / in / contains / and / or / not`；
- 条件只读取当前持久化 Node state，禁止代码执行、外部调用和危险类型转换；
- 已实现深度 / 节点数上限；
- DAG Edge 支持 `condition` / `default`，统一 Contract 校验 source、default 数量、重复 edge、未知 Node 和循环图；
- Conditional frontier 按 Definition 顺序确定性选择并允许多个条件同时命中形成并行 frontier；
- Planner 输出 selected predecessor facts，Join readiness 不复制条件解析；
- Resume 从持久化 completed Node output 重新计算 frontier；
- Runtime 复用现有 DAG Planner / State Merge；
- Condition Evaluator 与 Conditional Branching Unit Test 覆盖已建立，实际执行结果仍待开发者本地反馈。

## Frontend Phase 1.3 当前实现

- `frontend/src/utils/sse.ts`：统一 SSE Parser；
- `frontend/src/utils/runtime.ts`：统一 Runtime status / latency / ID / error helper；
- `frontend/src/views/runtime/components/RuntimeExecutions.vue`：统一 Execution / Trace / Request / Session 展示与复制；
- `frontend/src/api/chat.ts`：统一 SSE Parser 消费、AbortSignal、SSE error event；
- `frontend/src/views/agents/components/AgentWorkbench.vue`：Chat 生命周期已统一为 `idle / streaming / completed / failed / cancelled`；
- Chat 请求通过 `AbortController` 支持主动停止，并在关闭页面 / 组件卸载时主动取消；
- 使用 `activeRun` 防止旧请求在新请求启动后继续写入 UI，避免断流/竞态覆盖；
- Chat UI 展示真实 `request_id / trace_id / session_id / execution_id`；
- 后端 SSE `error` event 会进入明确的 failed 状态，不伪装成成功完成；
- `frontend/tests/api/chat.test.ts` 已覆盖 SSE chunk、最终 flush、AbortSignal、HTTP failure、无 body；
- Runtime 页面已有 Unit Test；
- 完整 Frontend Release Gate / Browser E2E 当前仍暂停。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境可通过 GitHub Repository API 直接核对和修改远端 `main`，但无法在本地启动完整项目执行 pytest / npm；因此本轮不伪造 Unit Test 结果。

## 下一主线

Frontend Phase 1.3 已完成当前生命周期交付，下一步不再继续堆叠 Chat UI；主线切回 **Phase 2.7-A Conditional Branching Closure / Advanced Workflow Orchestration**。

```text
Frontend Chat lifecycle
  ↓ 已完成
Conditional Branching Unit Test 实际执行
  ↓
Phase 2.7-A Real API acceptance（后续）
  ↓
Phase 2.7-A Closure
  ↓
Phase 2.7 后续 orchestration capability
  ↓
继续主线直到全部任务完成
```

Phase 2.7 禁止创建第二套 DAG Planner / Runtime / State Merge；Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Worker → Runtime。
