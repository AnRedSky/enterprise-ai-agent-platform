# Phase 2.7 — Advanced Workflow Orchestration / Conditional Branching

> 状态：**开发中**。
> 基线：`main`，2026-08-27。
> 当前交付单元：Phase 2.7-A Conditional Branching。
> Contract：`docs/02-phases/PHASE_2_7_A_CONTRACT.md`。

## 1. 当前目标

在现有 Workflow DAG、Checkpoint、Resume、Branch、Join 基础上增加确定性 Conditional Branching：

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

## 2. 本轮已实现

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
- Resume 从持久化 completed Node output 重新计算 frontier，不使用创建 Resume 时缓存 frontier；
- Runtime 接入现有 DAG Runtime Planner，未新增第二套 Runtime。

## 3. 单元测试

新增：

```text
backend/tests/unit/test_workflow_conditional_branching.py
```

覆盖：

- 严格类型比较；
- 数字比较；
- 字符串 / 数组 contains；
- 缺失 path；
- and / or / not；
- 非法字段与结构；
- 深度 / 节点数限制；
- condition frontier；
- default fallback；
- 多条件同时命中顺序；
- 未命中分支不进入 Join predecessor；
- Runtime Planner 透传 selected predecessor；
- 混合 edge / 多 default Contract 拒绝；
- 缺失持久化 source state 拒绝。

**本轮当前执行环境未运行本地 pytest，因此不得记录 Unit Test 为 PASS。** 按当前开发策略，完整 Backend / Frontend / Browser / Real API Gate 继续暂停，不作为主线阻塞条件。

## 4. 下一交付

```text
Conditional evaluator + DAG Contract
        ↓ 当前已完成
Conditional frontier planner
        ↓ 当前已完成
Runtime integration
        ↓ 当前已完成首版接入
Unit Test 实际执行
        ↓ 待开发者本地执行
Real API acceptance
        ↓ 后续
Phase 2.7-A Closure
```

Real API acceptance 必须验证真实 HTTP、真实 PostgreSQL 持久化事实以及 Worker → Runtime 链路；当前不使用 Mock、JSON fixture 或 GitHub Actions 替代本地验收。

## 5. 明确不实现

- 人工审批节点；
- Saga / compensation；
- 通用 Policy DSL；
- 任意代码表达式；
- MQ / Kafka / Event Bus；
- 跨 Workflow Version Resume；
- 第二套 DAG Planner / Runtime / State Merge。
