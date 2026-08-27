# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前 `main` HEAD：继续推进 Phase 2.7-A Durable Recovery Closure。
- 本轮已完成：**Single DAG Decision Planning Boundary**；一次 Runtime Resolution 只计算一次 `WorkflowDagResumePlan`，Runtime Planner 直接消费 immutable plan，避免同一执行边界重复计算 Decision。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**已完成既定实现范围，不作为当前主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**继续按最新治理规则推进，不作为当前主线阻塞条件。**
- Frontend Phase 1.3：**SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。**
- Phase 2.7 Advanced Workflow Orchestration：**开发中；Conditional Branching 已完成 Evaluator / DAG Contract / Planner / Initial Runtime / Resume Runtime / Join / Durable tenant boundary / Conditional Decision Trace / Resume Contract tenant scope / Branch Checkpoint Gate / Decision Fingerprint / Runtime Plan fingerprint / Recovery Frontier Replay Guard / Decision Trace Idempotency / Sequence Plan metadata / Checkpoint sequence serialization / Checkpoint Durable Fact completeness / Recovery Trace Checkpoint Lineage / Conditional Decision Rebuild / Trace Lineage 连续性 / Decision Trace 幂等 Payload Drift Guard / Deterministic Decision Fingerprint JSON Boundary / Single DAG Decision Planning Boundary，并继续进行 Phase 2.7-A Closure。**

## Phase 2.7-A 当前实现

- `WorkflowConditionEvaluator` 是唯一条件求值入口；
- DSL 支持 `eq / ne / gt / gte / lt / lte / in / contains / and / or / not`；
- 条件只读取当前持久化 Node state，禁止代码执行、外部调用和危险类型转换；
- 已实现深度 / 节点数上限；
- DAG Edge 支持 `condition` / `default`，统一 Contract 校验 source、default 数量、重复 edge、未知 Node 和循环图；当前第一版 DAG Contract 要求单 root，不能将多个静态 root 视为已完成能力；
- Conditional frontier 按 Definition 顺序确定性选择并允许多个条件同时命中形成并行 frontier；
- Planner 输出 selected predecessor facts，Join readiness 不复制条件解析；
- 首次执行与 Resume 均通过统一 DAG Planner；
- Conditional Join 只消费 Planner selected predecessor；
- Durable Resume completed Node 查询强制当前 `tenant_id` scope；
- Checkpoint latest 查询通过 `WorkflowExecution` JOIN 支持 tenant scope；Automatic Recovery 强制使用当前 Execution 的 `tenant_id`；
- Resume Contract 在 Source Execution row lock 后再次强制使用 `locked_execution.tenant_id` 查询最新 Checkpoint；
- Runtime 持久化 `workflow.dag.frontier_decided` decision metadata；
- Planner 生成 deterministic `decision_fingerprint`，同时绑定 completed Node facts、条件 source state、frontier 与 selected predecessor；
- Runtime Plan 显式携带 Planner fingerprint，Runtime 不再复制 Decision identity 计算逻辑；
- Decision Trace 不保存业务 state_data，只保存 fingerprint 和可审计的节点选择 metadata，不能替代 PostgreSQL durable facts；
- Multi-frontier Executor 只有在所有 Branch Checkpoint callback 成功后才允许生成 merged state / `join_ready=true`；
- 未提供 Checkpoint writer 时仍可收集 Branch execution result，但明确保持 `join_ready=false` 且不生成 merged state；
- 同一 Recovery trace 下相同 durable completed facts 必须保持相同 `decision_fingerprint`，Replay Guard 对不一致 Decision 立即失败；
- DAG Decision Trace 使用 execution + tenant + workflow version + trace + decision fingerprint 作为幂等 identity，Recovery 重试不会重复创建相同 Decision event；
- 顺序 Resume Sequence Planner 完整传递 Planner 的 selected predecessor 与 decision fingerprint，不允许在顺序 Runtime 边界丢失 Durable Decision identity；
- 无 DAG edges 的历史顺序 Workflow 保留原执行路径；
- Checkpoint 自动序号分配现在先锁定目标 `WorkflowExecution` 再读取最大 sequence，确保同一 Execution 的并发 Checkpoint 写入具有确定的序号分配边界；
- Checkpoint 若绑定 Node，则 Recovery 可通过 `assert_node_fact_complete()` 校验 NodeExecution 的 node、status、attempt、output_data；execution-level checkpoint 不要求 NodeExecution；
- Recovery Trace → Resume lineage 强制校验 `resume_of_execution_id`、tenant、workflow version 与真实存在的 `resume_checkpoint_sequence`，并将 checkpoint sequence 作为 lineage audit metadata；
- Conditional Decision Replay 不仅比较 fingerprint，还比较历史 Decision 的 frontier 与 selected predecessor outputs，保证同一 durable completed facts 的 Decision 能完整重建；
- Recovery Trace 幂等命中已有 lineage event 后重新校验 Source / Resume / Checkpoint identity，避免旧数据污染被静默接受；
- `get_trace_id()` 同时限定 Resume Execution 的 tenant 与 workflow version，避免跨版本恢复错误 trace；
- Decision Trace 幂等命中已有 event 后重新校验 decision_id、completed_node_ids、frontier_node_ids、selected_predecessors，避免历史 Decision payload drift 被静默接受；
- Decision fingerprint canonicalization 严格要求 JSON-safe condition state，禁止 `default=str` 隐式转换，并拒绝 NaN / Infinity 等非标准 JSON 数值；
- `WorkflowDagResumeRuntimePlanner` 可以直接消费已计算的 immutable `WorkflowDagResumePlan`，正式 `_resolve_dag_context()` 不再对同一 Runtime Resolution 二次运行 Planner，保证单一 Decision calculation boundary。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test 结果。

## 当前主线

```text
Phase 2.7-A Conditional Branching
  ├── Evaluator                         ✅
  ├── DAG Contract                     ✅
  ├── Conditional Planner              ✅
  ├── Initial Execution Runtime        ✅
  ├── Resume Runtime Integration       ✅
  ├── Conditional Join                 ✅
  ├── Durable tenant boundary          ✅
  ├── Checkpoint tenant boundary       ✅
  ├── Conditional Decision Trace       ✅
  ├── Resume Contract tenant scope     ✅
  ├── Branch Checkpoint Gate           ✅
  ├── Decision Fingerprint             ✅
  ├── Runtime Plan fingerprint         ✅
  ├── Recovery Frontier Replay Guard   ✅
  ├── Decision Trace Idempotency       ✅
  ├── Sequence Plan metadata           ✅
  ├── Checkpoint sequence serialization ✅
  ├── Checkpoint fact completeness     ✅
  ├── Recovery Trace Checkpoint Lineage ✅
  ├── Conditional Decision Rebuild     ✅
  ├── Trace Lineage 连续性             ✅
  ├── Decision Trace payload drift guard ✅
  ├── Deterministic fingerprint JSON boundary ✅
  ├── Single DAG Decision Planning Boundary ✅ 本轮完成
  ├── Unit Test 实际执行               ⏳
  └── Real API acceptance              ⏸ 暂停
          ↓
Phase 2.7-A Closure
  └── Closure review / invariant sweep  ← 当前
          ↓
Phase 2.7 后续 orchestration capability
          ↓
继续主线直到全部任务完成
```

Phase 2.7 禁止创建第二套 DAG Planner / Runtime / State Merge；Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Worker → Runtime。