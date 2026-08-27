# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前远端 `main` 基线：`8d16915f7f24ca081df4e26ed8b196da4697e263`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；Frontend / Browser E2E 与历史 Real API 验收已完成，本轮不再作为主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成，DAG Resume / Branch / Join / Automatic Recovery / Recovery Trace / Worker Reclaim / Lease Fencing / Lease Loss Active Abort / Terminal Ownership Boundary 均已落地；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**继续按最新治理规则推进，不作为当前主线阻塞条件。**
- Frontend Phase 1.3：**SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费迁移均已完成；当前进入 Chat / Runtime 失败、断流、取消 UI 生命周期。**
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
- `frontend/src/api/chat.ts`：统一 SSE Parser 消费并支持 `AbortSignal`；
- `frontend/tests/api/chat.test.ts`：Chat streaming 边界 Unit Test；
- `frontend/tests/views/Runtime.test.ts`：Runtime 页面 Unit Test；
- `frontend/scripts/test/phase-1-3-runtime-hardening.ps1`：可重复测试入口；
- Chat / Runtime UI 失败、断流、取消生命周期为当前下一任务。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境可通过 GitHub Repository API 直接核对和修改远端 `main`，但无法在本地启动完整项目执行 pytest / npm；因此本轮不伪造 Unit Test 结果。

## 下一主线

**Frontend Phase 1.3 — Chat / Runtime 失败、断流、取消 UI 生命周期**，并行推进 **Phase 2.7-A Conditional Branching Closure**。

```text
Chat streaming migration
  ↓ 已完成
Chat / Runtime failure / disconnect / cancel lifecycle
  ↓ 当前
Unit Test 实际执行
  ↓
Conditional Branching Unit Test 实际执行
  ↓
Phase 2.7-A Real API acceptance（后续）
  ↓
继续 Phase 2.7 后续主线
```

Phase 2.7 禁止创建第二套 DAG Planner / Runtime / State Merge；Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Worker → Runtime。
