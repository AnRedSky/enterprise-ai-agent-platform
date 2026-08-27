# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 本轮最新代码提交：`4e8cd16cee0470c00fb4675cffcf6bad488a6e23`。
- 本轮已完成：**DAG Multi-frontier Join readiness 的 Checkpoint Gate 收敛**；Branch 执行结果只有在所有 frontier Branch Checkpoint callback 成功完成后才能形成 merged state 并声明 `join_ready=true`，避免未持久化结果被错误视为可 Join。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**已完成既定实现范围，不作为当前主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**继续按最新治理规则推进，不作为当前主线阻塞条件。**
- Frontend Phase 1.3：**SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。**
- Phase 2.7 Advanced Workflow Orchestration：**开发中；Conditional Branching 已完成 Evaluator / DAG Contract / Planner / Initial Runtime / Multi-root / Resume Runtime / Join / Runtime inheritance cleanup / Durable tenant boundary / Conditional Decision Trace / Resume Contract tenant scope，并继续进行 Durable Recovery 一致性加固。**

## Phase 2.7-A 当前实现

- `WorkflowConditionEvaluator` 是唯一条件求值入口；
- DSL 支持 `eq / ne / gt / gte / lt / lte / in / contains / and / or / not`；
- 条件只读取当前持久化 Node state，禁止代码执行、外部调用和危险类型转换；
- 已实现深度 / 节点数上限；
- DAG Edge 支持 `condition` / `default`，统一 Contract 校验 source、default 数量、重复 edge、未知 Node 和循环图；
- Conditional frontier 按 Definition 顺序确定性选择并允许多个条件同时命中形成并行 frontier；
- Planner 输出 selected predecessor facts，Join readiness 不复制条件解析；
- 首次执行与 Resume 均通过统一 DAG Planner；
- 多 root 首次执行为每个 root 建立独立输入 state；
- `dag_runtime.py` 不复制基础 Runtime 的 DAG state / Resume 逻辑；
- Conditional Join 只消费 Planner selected predecessor；
- Durable Resume completed Node 查询强制当前 `tenant_id` scope；
- Checkpoint latest 查询通过 `WorkflowExecution` JOIN 支持 tenant scope；Automatic Recovery 强制使用当前 Execution 的 `tenant_id`；
- Resume Contract 在 Source Execution row lock 后再次强制使用 `locked_execution.tenant_id` 查询最新 Checkpoint；
- Runtime 持久化 `workflow.dag.frontier_decided` decision metadata，包含 deterministic `decision_id`、completed Node、frontier 与 selected predecessor；
- Decision Trace 不保存业务 state_data，不能替代 PostgreSQL durable facts；
- Multi-frontier Executor 现在只有在所有 Branch Checkpoint callback 成功后才允许生成 merged state / `join_ready=true`；
- 未提供 Checkpoint writer 时仍可收集 Branch execution result，但明确保持 `join_ready=false` 且不生成 merged state；
- 无 DAG edges 的历史顺序 Workflow 保留原执行路径。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test 结果。

## 当前主线

```text
Phase 2.7-A Conditional Branching
  ├── Evaluator                     ✅
  ├── DAG Contract                 ✅
  ├── Conditional Planner          ✅
  ├── Initial Execution Runtime    ✅
  ├── Multi-root Initialization    ✅
  ├── Resume Runtime Integration   ✅
  ├── Runtime inheritance cleanup  ✅
  ├── Conditional Join             ✅
  ├── Durable tenant boundary      ✅
  ├── Checkpoint tenant boundary   ✅
  ├── Conditional Decision Trace   ✅
  ├── Resume Contract tenant scope ✅
  ├── Branch Checkpoint Gate       ✅ 本轮完成
  ├── Unit Test 实际执行            ⏳
  └── Real API acceptance           ⏸ 暂停
          ↓
Phase 2.7-A Durable Recovery Closure
  ├── Checkpoint fact 完整性
  ├── Conditional decision 可重建性
  ├── Trace lineage 连续性
  └── Recovery 后 frontier 一致性
          ↓
Phase 2.7-A Closure
          ↓
Phase 2.7 后续 orchestration capability
          ↓
继续主线直到全部任务完成
```

Phase 2.7 禁止创建第二套 DAG Planner / Runtime / State Merge；Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Worker → Runtime。