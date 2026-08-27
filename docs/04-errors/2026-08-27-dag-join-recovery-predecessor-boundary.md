# 2026-08-27 DAG Join Recovery predecessor 边界

## 问题

`WorkflowDagJoinReadinessService` 在未传入 `predecessor_node_ids` 时曾直接把 Definition 的全部入边作为 Join predecessor。对于 Conditional DAG，这会把未被唯一 Planner 选中的分支错误地视为 Join 输入，导致 Recovery / Replay 在部分分支完成时提前进入 Join。

## 根因

Join Readiness 本身不负责条件求值；条件边的命中结果由唯一 `WorkflowDagResumePlanner` 产生。若 Join 层回退到 Definition 全部入边，就形成第二套 predecessor 决策逻辑。

## 修复

- Conditional / default 入边存在时，必须显式提供 Planner 选定的 predecessor 快照；
- 显式 predecessor 必须全部属于当前 Join 的直接入边；
- predecessor 不允许重复；
- 非条件 DAG 仍可按 Definition 直接入边生成默认 predecessor；
- Join Readiness 继续只消费已完成 durable Node facts，不执行条件表达式、不读取数据库、不修改 Execution。

## 边界

```text
DAG Planner
  ↓
selected predecessor snapshot
  ↓
Join Readiness
  ↓
all selected predecessor completed
  ↓
state merge
  ↓
Join Node
```

Recovery / Replay 必须复用同一 Planner 决策，禁止 Join 层重新解释 Conditional Edge。
