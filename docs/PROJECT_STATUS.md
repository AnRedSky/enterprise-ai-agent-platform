# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 本轮代码基线：`8d16915f7f24ca081df4e26ed8b196da4697e263`。
- 本轮已落地：**Conditional Branching 首次执行 Runtime Integration**；同时修正 Conditional Join state 只能消费 Planner selected predecessor 的边界。
- 最新代码提交：`deb9143166a059ddde0aa1c2d69ee19098ba7933`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**已完成既定实现范围，不作为当前主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**继续按最新治理规则推进，不作为当前主线阻塞条件。**
- Frontend Phase 1.3：**SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。**
- Phase 2.7 Advanced Workflow Orchestration：**开发中；Conditional Branching 首个交付单元已完成 Condition Evaluator / DAG Contract / Planner / Resume Runtime Integration，并在本轮完成首次执行 Runtime Integration。**

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
- **首次执行存在 DAG edges 时现在也通过统一 `WorkflowDagResumePlanner` / `WorkflowDagResumeRuntimePlanner` 计算 frontier；**
- **Conditional Join state 使用 Planner selected predecessor facts，不再按静态全部 predecessor 读取状态；**
- 无 DAG edges 的历史顺序 Workflow 保留原执行路径。

## Frontend Phase 1.3 当前实现

- SSE / Runtime 公共边界完成；
- Runtime Execution 页面完成；
- Chat streaming 消费统一使用共享 SSE Parser；
- Chat 生命周期统一为 `idle / streaming / completed / failed / cancelled`；
- `AbortController`、SSE error、stale stream race protection 已完成；
- 当前完整 Frontend Release Gate / Browser E2E 暂停。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境可通过 GitHub Repository API 直接核对和修改远端 `main`，但无法在本地启动完整项目执行 pytest / npm；因此本轮不伪造 Unit Test 结果。

## 当前主线

```text
Frontend Phase 1.3
  ↓ 已完成
Phase 2.7-A Conditional Branching
  ├── Evaluator                    ✅
  ├── DAG Contract                ✅
  ├── Conditional Planner         ✅
  ├── Resume Runtime Integration  ✅
  ├── Initial Execution Runtime   ✅ 本轮完成
  ├── Unit Test 实际执行           ⏳
  └── Real API acceptance          ⏸ 暂停
          ↓
Phase 2.7-A Closure
          ↓
Phase 2.7 后续 orchestration capability
          ↓
继续主线直到全部任务完成
```

Phase 2.7 禁止创建第二套 DAG Planner / Runtime / State Merge；Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Worker → Runtime。
