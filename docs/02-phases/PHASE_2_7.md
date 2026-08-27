# Phase 2.7 — Advanced Workflow Orchestration / Conditional Branching

> 状态：**开发中**。
> 基线：`main`，2026-08-27。
> 当前交付单元：Phase 2.7-A Conditional Branching。
> Contract：`docs/02-phases/PHASE_2_7_A_CONTRACT.md`。

## 1. 当前目标

在现有 Workflow DAG、Checkpoint、Resume、Branch、Join 基础上增加确定性 Conditional Branching，并保证**首次执行与 Durable Resume 使用同一套 Planner / Runtime 语义**：

```text
持久化 Node state
      ↓
Condition Evaluator
      ↓
Conditional DAG Planner
      ↓
selected frontier
      ↓
existing Branch / Join / Runtime
```

不引入第二套 DAG Planner、Runtime 或 State Merge；条件规则只存在于统一 Condition Evaluator，Runtime 只消费 Planner 结果。

## 2. 本轮实现推进

- `WorkflowConditionEvaluator`：有限 JSON Condition DSL；
- `eq / ne / gt / gte / lt / lte / in / contains`；
- `and / or / not` 短路求值；
- 点号路径读取当前 `state_data`；
- 严格 JSON 类型比较，禁止 `bool` 与 `number` 隐式相等；
- 缺失 path 不隐式转换为 `null`；
- Condition 最大深度 8、最大节点数 64；
- DAG Edge 支持 `condition` / `default`；
- 同一 source 禁止无条件边与条件/default 边混用；
- 同一 source 最多一个 default；
- Conditional frontier 按 Definition 顺序确定性选择；
- 多个条件同时命中时允许进入并行 frontier；
- 无条件边继续保持原 DAG 语义；
- Planner 输出 selected predecessor facts；
- Join readiness 消费 Planner 已选 predecessor，不自行解析条件；
- Resume 从持久化 completed Node output 重新计算 frontier；
- Runtime 复用现有 DAG Runtime Planner；
- **首次执行现在同样进入 DAG Planner，条件边不再只在 Resume 路径生效；**
- **首次执行存在多个 root 时，为每个 root 建立独立输入快照，再进入现有 Multi-frontier Runtime；**
- **Join Branch state 优先消费 Planner 选中的 predecessor，未命中条件分支不会被当作 Join 输入；**
- 修正 `app/runtime/workflow/dag_runtime.py` 与基础 Runtime 的 `_build_frontier_branch_states()` 契约不一致问题，删除重复的 DAG state / Resume 逻辑，仅保留 Join 与 Recovery Trace 扩展；
- 无 `edges` 的历史顺序 Workflow 保留原顺序执行兼容语义。

## 3. 单元测试

已有：

```text
backend/tests/unit/test_workflow_condition_evaluator.py
backend/tests/unit/test_workflow_conditional_branching.py
backend/tests/unit/test_workflow_runtime.py
backend/tests/unit/test_workflow_dag_runtime_initialization.py
```

新增覆盖：

- Conditional Join 只使用 selected predecessor；
- 初始 DAG Execution 从 root frontier 启动并复用同一 Planner Contract；
- 多 root 初始 DAG 为每个 frontier 建立独立输入 state；
- Join Node 类型扩展不复制基础 Runtime 的执行能力；
- 既有线性 Runtime 与 Agent governance 行为保持覆盖。

**当前环境未执行仓库本地 pytest，因此不得记录 Unit Test 为 PASS。** 按当前开发策略，完整 Backend / Frontend / Browser / Real API Gate 继续暂停，不作为主线阻塞条件。

## 4. 当前下一交付

```text
Condition Evaluator
        ↓ 已完成
DAG Contract
        ↓ 已完成
Conditional frontier planner
        ↓ 已完成
首次执行 Runtime integration
        ↓ 已完成
多 root Initial frontier initialization
        ↓ 已完成
Resume Runtime integration
        ↓ 已完成
Unit Test 实际执行
        ↓ 待开发者本地执行
Phase 2.7-A Closure hardening
        ↓ 当前主线
Phase 2.7 后续 orchestration capability
```

下一主线继续检查 Conditional Decision、Checkpoint、Workflow Trace 与 Recovery Resume 的可重建一致性，重点保证恢复后不依赖进程内临时状态，并继续复用现有 Planner / Runtime / State Merge。

Real API acceptance 后续必须验证真实 HTTP、真实 PostgreSQL 持久化事实以及 Worker → Runtime 链路；当前不使用 Mock、JSON fixture 或 GitHub Actions 替代本地验收。

## 5. 明确不实现

- 人工审批节点；
- Saga / compensation；
- 通用 Policy DSL；
- 任意代码表达式；
- MQ / Kafka / Event Bus；
- 跨 Workflow Version Resume；
- 第二套 DAG Planner / Runtime / State Merge。
