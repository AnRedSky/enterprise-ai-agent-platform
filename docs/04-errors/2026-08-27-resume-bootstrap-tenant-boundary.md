# 2026-08-27 Resume Bootstrap tenant boundary

## 问题

`WorkflowExecutionResumeBootstrapService` 在复制 Source Execution 的 completed `WorkflowNodeExecution` 时，原查询只按 `execution_id` 限定，没有在 SQL 层同时表达 tenant boundary；Resume 已进入同一 tenant contract，但 Bootstrap 本身缺少最后一道领域级 tenant invariant。

## 根因

Recovery / Resume 属于跨 Execution 的 durable lineage 操作。仅依赖调用方此前的 tenant 校验不足以表达查询边界；后续查询、复制和幂等读取都必须继续携带 tenant scope，避免领域服务未来被独立调用时形成跨租户数据访问路径。

## 修复

- Bootstrap 开始时显式校验 Source / Resume `tenant_id` 一致；
- Source completed Node 查询通过 `WorkflowExecution` JOIN 同时限定 Source execution 与 tenant；
- Resume 已存在 Node lineage 查询同样通过 `WorkflowExecution` JOIN 限定 Resume tenant；
- 复制完成后仍由唯一 DAG Planner 计算首个 Frontier，不改变既有 Recovery / Replay 算法。

## 边界

```text
Source Execution
  ↓ tenant invariant
Source completed Node facts
  ↓ same tenant
Resume Node lineage
  ↓
Planner
  ↓
Resume Frontier
```

Resume Bootstrap 不负责身份认证，也不替代 Recovery Contract；它负责保证 durable lineage 复制阶段自身不会失去 tenant boundary。
