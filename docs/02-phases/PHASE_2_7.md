# Phase 2.7 — Advanced Workflow Orchestration / Conditional Branching

> 状态：**开发中**。
> 基线：`main`，2026-08-27。
> 当前交付单元：Phase 2.7-A Conditional Branching Durable Recovery Closure。
> Contract：`docs/02-phases/PHASE_2_7_A_CONTRACT.md`。

## 1. 当前目标

在现有 Workflow DAG、Checkpoint、Resume、Branch、Join 基础上增加确定性 Conditional Branching，并保证首次执行与 Durable Resume 使用同一套 Planner / Runtime 语义；恢复过程只能依赖持久化完成事实，且所有完成 Node state 与 Checkpoint 读取均保持 tenant boundary。

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
      ↓
Checkpoint / Trace
      ↓
Recovery Resume
      ↓
重新构建 frontier
```

不引入第二套 DAG Planner、Runtime 或 State Merge；条件规则只存在于统一 Condition Evaluator，Runtime 只消费 Planner 结果。

## 2. 已完成实现

- `WorkflowConditionEvaluator`：有限 JSON Condition DSL；
- `eq / ne / gt / gte / lt / lte / in / contains`；
- `and / or / not` 短路求值；
- 点号路径读取当前 `state_data`；
- 严格 JSON 类型比较；
- Condition 最大深度 8、最大节点数 64；
- DAG Edge 支持 `condition` / `default`；
- 同一 source 禁止无条件边与条件/default 边混用；
- 同一 source 最多一个 default；
- Conditional frontier 按 Definition 顺序确定性选择；
- 多个条件同时命中允许形成并行 frontier；
- Planner 输出 selected predecessor facts；
- Join readiness 消费 Planner 已选 predecessor；
- 首次执行与 Resume 均通过统一 DAG Planner；
- 多 root 首次执行为每个 root 建立独立输入 state；
- `dag_runtime.py` 不复制基础 Runtime 的 DAG state / Resume 逻辑；
- Conditional Join 只消费 Planner selected predecessor；
- Durable Resume completed Node 查询强制当前 `tenant_id` scope；
- Checkpoint latest 查询通过 `WorkflowExecution` JOIN 支持 tenant scope；Automatic Recovery 强制使用当前 Execution 的 `tenant_id`；
- 无 DAG edges 的历史顺序 Workflow 保留原顺序执行兼容语义。

## 3. 本轮安全边界加固

发现 Checkpoint 表本身没有重复保存 `tenant_id`，而 Recovery 读取最新 Checkpoint 时原先只按 `execution_id` 查询。虽然上游正常调用链已经拥有 tenant-scoped Execution，但恢复领域服务自身仍应形成防御式租户边界。

已修复：

```text
Automatic Recovery
      ↓
execution.id + execution.tenant_id
      ↓
Checkpoint.latest(..., tenant_id=...)
      ↓
JOIN workflow_executions
      ↓
WorkflowExecution.tenant_id = tenant_id
      ↓
latest durable checkpoint
```

这样 Checkpoint Recovery 与此前 NodeExecution Recovery 一样，不依赖调用者单独保证租户隔离。

## 4. 单元测试

已有：

```text
backend/tests/unit/test_workflow_condition_evaluator.py
backend/tests/unit/test_workflow_conditional_branching.py
backend/tests/unit/test_workflow_runtime.py
backend/tests/unit/test_workflow_dag_runtime_initialization.py
```

本轮补充：

```text
backend/tests/unit/test_workflow_checkpoint_tenant_scope.py
```

覆盖：

- Checkpoint latest 显式 tenant scope；
- SQL 查询包含 `workflow_executions.tenant_id`；
- 未提供 tenant_id 时保持明确的历史兼容调用契约；
- Automatic Recovery 强制将当前 Execution tenant_id 传给 Checkpoint latest。

**当前环境未执行仓库本地 pytest，因此不得记录 Unit Test 为 PASS。**

## 5. 当前下一交付

```text
Condition Evaluator              ✅
DAG Contract                    ✅
Conditional frontier planner    ✅
Initial Execution Runtime       ✅
Multi-root initialization       ✅
Resume Runtime integration      ✅
Conditional Join                ✅
Runtime inheritance cleanup     ✅
NodeExecution tenant boundary   ✅
Checkpoint tenant boundary      ✅ 本轮完成
        ↓
Durable Recovery Closure        ← 当前主线
        ├── Checkpoint fact 完整性
        ├── Conditional decision 可重建性
        ├── Trace lineage 连续性
        └── Recovery 后 frontier 一致性
        ↓
Phase 2.7-A Closure
        ↓
Phase 2.7 后续 orchestration capability
```

Real API acceptance 后续必须验证真实 HTTP、真实 PostgreSQL 持久化事实以及 Worker → Runtime 链路；当前不使用 Mock、JSON fixture 或 GitHub Actions 替代本地验收。

## 6. 明确不实现

- 人工审批节点；
- Saga / compensation；
- 通用 Policy DSL；
- 任意代码表达式；
- MQ / Kafka / Event Bus；
- 跨 Workflow Version Resume；
- 第二套 DAG Planner / Runtime / State Merge。
